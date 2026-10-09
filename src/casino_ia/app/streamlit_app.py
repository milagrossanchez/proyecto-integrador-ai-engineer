"""App de demo: tablero de cartera, ficha por cliente y asistente RAG."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))

import streamlit as st

from casino_ia import config
from casino_ia.data import cargar_features_cliente
from casino_ia.genai import AsistentePoliticas, explicar_cliente
from casino_ia.genai.telegram_bot import enviar_oferta
from casino_ia.models import (
    ModeloRespuesta,
    ModeloRespuestaNBO,
    ModeloRespuestaNBOCalibrado,
    ModeloRiesgo,
)
from casino_ia.optimization.allocate import asignar_recompensas

st.set_page_config(page_title="Palacio Real · Recompensas", layout="wide", page_icon="🎰")


@st.cache_data
def _data():
    return cargar_features_cliente()


@st.cache_resource
def _modelos():
    """Carga riesgo + respuesta V1 + NBO.

    El NBO calibrado (`ModeloRespuestaNBOCalibrado`, anclado a evidencia RCT
    real de Hillstrom/Criteo — ver docs/etapa3_modelo_respuesta_nbo.md) se usa
    si `modelo_respuesta_nbo_calibrado.joblib` existe (se genera con
    `scripts/train_response_nbo.py`, que requiere `ext.HillstromEmail` y
    `ext.CriteoUpliftV21` — ver sql/README.md). Si no existe, cae sin romperse
    al NBO semi-sintético anterior (`ModeloRespuestaNBO`).
    """
    riesgo = ModeloRiesgo.load(config.MODELS_STORE / "modelo_riesgo.joblib")
    respuesta = ModeloRespuesta.load(config.MODELS_STORE / "modelo_respuesta.joblib")
    ruta_calibrado = config.MODELS_STORE / "modelo_respuesta_nbo_calibrado.joblib"
    if ruta_calibrado.exists():
        nbo = ModeloRespuestaNBOCalibrado.load(ruta_calibrado)
        nbo_version = "V2 calibrado (evidencia RCT Hillstrom/Criteo)"
    else:
        nbo = ModeloRespuestaNBO.load(config.MODELS_STORE / "modelo_respuesta_nbo.joblib")
        nbo_version = "V2 semi-sintético (pendiente: cargar ext.HillstromEmail/CriteoUpliftV21)"
    return riesgo, respuesta, nbo, nbo_version


def _metricas_guardadas() -> dict:
    p = config.METRICS / "metrics_modelos.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


@st.cache_resource
def _estado_llm() -> tuple[str, str]:
    """Prueba una sola vez por sesión si la API key realmente funciona
    (no solo si está presente). `count_tokens` no genera salida: es gratis/rápido.
    """
    if not config.LLM.enabled:
        return "⚪", "Sin configurar (falta ANTHROPIC_API_KEY)"
    try:
        import anthropic

        client = anthropic.Anthropic(api_key=config.LLM.api_key)
        client.messages.count_tokens(model=config.LLM.model, messages=[{"role": "user", "content": "hola"}])
        return "🟢", f"Conectada ({config.LLM.model})"
    except Exception as exc:  # noqa: BLE001
        return "🔴", f"Clave inválida o sin acceso ({type(exc).__name__}) — modo plantilla"


@st.cache_resource
def _estado_telegram() -> tuple[str, str]:
    """Igual que `_estado_llm`: prueba una vez por sesión si el bot responde
    de verdad (`getMe`), no solo si hay token configurado."""
    if not config.TELEGRAM.enabled:
        return "⚪", "Sin configurar (falta TELEGRAM_BOT_TOKEN) — modo dry-run"
    try:
        import requests

        r = requests.get(config.TELEGRAM.api_url("getMe"), timeout=10)
        r.raise_for_status()
        username = r.json()["result"]["username"]
        return "🟢", f"Conectado (@{username})"
    except Exception as exc:  # noqa: BLE001
        return "🔴", f"Token inválido o sin acceso ({type(exc).__name__}) — modo dry-run"


@st.cache_data(show_spinner=False)
def _plan_asignacion(presupuesto: float):
    """Cachea la corrida del optimizador por presupuesto: evita recalcularla
    (recorre 888 clientes fila por fila) en cada interacción ajena a Cartera,
    como abrir o cerrar el chat. `pred` es estable durante la sesión."""
    return asignar_recompensas(pred, presupuesto=presupuesto)


@st.cache_resource
def _asistente() -> AsistentePoliticas:
    return AsistentePoliticas()


_DICCIONARIO_CARTERA = [
    ("Cliente", "Nombre del cliente. Dato ficticio generado de forma determinista a partir del IdCliente — no corresponde a una persona real."),
    ("Segmento", "VIP / Alto / Medio / Estándar, por cuartiles de gasto histórico (CoinIn) del cliente."),
    ("NivelRiesgo", "Bajo / Medio / Alto. Salida del modelo de riesgo (HistGradientBoosting) sobre señales de intensidad de juego."),
    ("SesionesUltimos90d", "Sesiones registradas en los últimos 90 días. Requisito de elegibilidad: mínimo 3 para poder recibir una recompensa."),
    ("ProbRespuesta", "Probabilidad de que el cliente responda a ESA recompensa particular (modelo NBO, calibrado con evidencia real Hillstrom/Criteo cuando está disponible)."),
    ("Recompensa", "Tipo elegido por el optimizador: baja, media o alta — o vacío si no se le asigna nada."),
    ("Costo", "Lo que cuesta esa recompensa (parámetro de negocio: alta S/40, media S/15, baja S/5)."),
    ("ValorIncremental", "Cuánto gana el casino si el cliente responde a esa recompensa (salida del modelo de valor)."),
    ("UpliftProbabilidad", "ProbRespuesta con la recompensa menos ProbRespuesta en un grupo de control (sin campaña). Mide cuánto de la respuesta es atribuible a la campaña y no algo que iba a pasar igual. Solo disponible con el NBO calibrado (V2)."),
    ("ValorEsperado", "Beneficio incremental: UpliftProbabilidad × ValorIncremental − Costo cuando hay NBO calibrado (V2); si no, ProbRespuesta × ValorIncremental − Costo (V1). Es el criterio de ranking del optimizador — evita premiar a quien habría vuelto igual sin campaña."),
    ("ValorEsperadoBruto", "ProbRespuesta × ValorIncremental − Costo, sin restar el escenario de control. Se muestra solo para comparar contra ValorEsperado; el optimizador NO decide con este campo."),
    ("Eficiencia", "ValorEsperado ÷ Costo: retorno por cada sol invertido. Es el criterio de orden para repartir el presupuesto."),
    ("GastoAcumulado", "Suma acumulada del costo recorriendo la lista ordenada por Eficiencia, hasta ese cliente — marca dónde se corta el presupuesto."),
    ("Asignada", "True/False — si entró dentro del presupuesto y los topes (25% en recompensas altas, 40% por segmento)."),
    ("MotivoDecision", "Explica el resultado: riesgo alto, pocas sesiones, sin presupuesto, tope de recompensas altas, tope por segmento, o Asignada."),
]

_DICCIONARIO_CLIENTE = [
    ("RiesgoScore", "Probabilidad continua (0 a 1) de ser riesgo Alto, antes de convertirla en categoría Bajo/Medio/Alto."),
    ("CoinInTotal", "Suma histórica del dinero apostado por el cliente (de FctPlayerSession)."),
    ("EsPerfilAtipico", "Marca del detector de anomalías (IsolationForest): si el patrón de juego es inusual frente al resto de la cartera."),
]

_EJEMPLOS_CHAT = [
    "¿Un cliente de riesgo medio puede recibir recompensa alta?",
    "¿Qué pasa con los clientes de riesgo alto?",
    "¿Cómo se elige a quién premiar si el presupuesto no alcanza?",
    "¿Qué incluye la recompensa media?",
]

_CSS_WIDGET = """
<style>
div.st-key-chat_toggle button {
    position: fixed; bottom: 22px; right: 22px; z-index: 999999;
    width: 58px; height: 58px; border-radius: 50%; font-size: 1.4rem;
    background: #142238; color: #ffffff; border: 1px solid #c9a866;
    box-shadow: 0 6px 18px rgba(0,0,0,.28);
}
div.st-key-chat_panel {
    position: fixed; bottom: 22px; right: 22px; z-index: 999999;
    width: min(460px, calc(100vw - 32px));
    max-height: min(82vh, calc(100dvh - 60px)); overflow-y: auto;
    background: #101b2d; color: #f5f7fb; color-scheme: dark;
    border: 1px solid #43516a; border-top: 3px solid #c9a866;
    border-radius: 16px; box-sizing: border-box; isolation: isolate;
    padding: 18px; box-shadow: 0 16px 48px rgba(0,0,0,.45);
    scrollbar-color: #697a94 #101b2d;
}
div.st-key-chat_panel [data-testid="stMarkdownContainer"],
div.st-key-chat_panel label {
    color: #f5f7fb;
}
div.st-key-chat_panel [data-testid="stCaptionContainer"],
div.st-key-chat_panel [data-testid="stCaptionContainer"] p {
    color: #c1cbdc; opacity: 1;
}
div.st-key-chat_panel a { color: #9eceff; }
div.st-key-chat_header [data-testid="stHorizontalBlock"] { flex-wrap: nowrap; }
div.st-key-chat_header [data-testid="stColumn"]:first-child {
    flex: 1 1 auto; min-width: 0;
}
div.st-key-chat_header [data-testid="stColumn"]:last-child {
    flex: 0 0 40px; min-width: 40px;
}
div.st-key-chat_panel [data-testid="stChatMessage"] {
    background: #1c2c44; border: 1px solid #43516a; border-radius: 12px;
}
div.st-key-chat_panel [data-testid="stForm"] {
    background: #101b2d; border: 1px solid #43516a; border-radius: 12px;
}
div.st-key-chat_panel [data-baseweb="input"],
div.st-key-chat_panel input {
    background: #20314a; color: #ffffff; caret-color: #ffffff;
}
div.st-key-chat_panel input::placeholder { color: #c1cbdc; opacity: 1; }
div.st-key-chat_panel button {
    background: #243650; color: #ffffff; border: 1px solid #697a94;
}
div.st-key-chat_panel button:hover,
div.st-key-chat_toggle button:hover {
    background: #354d6b; color: #ffffff; border-color: #c9a866;
}
div.st-key-chat_panel [data-testid="stFormSubmitButton"] button {
    background: #c9a866; color: #101b2d; border-color: #c9a866;
    width: 100%; font-weight: 600;
}
div.st-key-chat_panel [data-testid="stFormSubmitButton"] button:hover {
    background: #dfc38c; border-color: #dfc38c;
}
div.st-key-chat_panel button [data-testid="stMarkdownContainer"],
div.st-key-chat_panel button p { color: inherit; }
div.st-key-chat_panel button:focus-visible,
div.st-key-chat_toggle button:focus-visible {
    outline: 2px solid #e5c98f; outline-offset: 3px;
}
@media (max-width: 480px) {
    div.st-key-chat_panel { bottom: 12px; right: 12px; width: calc(100vw - 24px); }
}
</style>
"""


def _widget_flotante() -> None:
    """Asistente en una burbuja fija en la esquina, visible en cualquier
    pestaña. Comparte el motor RAG de políticas con el prototipo de Telegram
    (ver docs/arquitectura_produccion.md).
    """
    st.markdown(_CSS_WIDGET, unsafe_allow_html=True)
    st.session_state.setdefault("chat_abierto", False)
    st.session_state.setdefault("chat_historial", [])

    if not st.session_state.chat_abierto:
        with st.container(key="chat_toggle"):
            if st.button("💬", key="btn_abrir_chat", help="Abrir el asistente"):
                st.session_state.chat_abierto = True
                st.rerun()
        return

    with st.container(key="chat_panel"):
        with st.container(key="chat_header"):
            c1, c2 = st.columns([5, 1])
            c1.markdown("**Asistente Palacio Real**")
            if c2.button("✕", key="btn_cerrar_chat", help="Cerrar el asistente"):
                st.session_state.chat_abierto = False
                st.rerun()
        st.caption(
            "Consulta las políticas de juego responsable y la guía de recompensas."
        )

        if not st.session_state.chat_historial:
            st.caption("Ejemplos:")
            for e in _EJEMPLOS_CHAT:
                st.caption(f"· {e}")

        for m in st.session_state.chat_historial:
            st.chat_message(m["role"]).write(m["content"])

        with st.form(key="form_chat", clear_on_submit=True):
            pregunta = st.text_input("Escribe tu pregunta", label_visibility="collapsed",
                                      placeholder="Escribe tu consulta…")
            enviado = st.form_submit_button("Enviar")

        if enviado and pregunta:
            st.session_state.chat_historial.append({"role": "user", "content": pregunta})
            with st.spinner("Buscando..."):
                r = _asistente().responder(pregunta)
            texto = r["respuesta"]
            if r["fuentes"]:
                texto += "\n\n_Fuentes: " + ", ".join(sorted(set(r["fuentes"]))) + "_"
            st.session_state.chat_historial.append({"role": "assistant", "content": texto})
            st.rerun()


feats = _data()
riesgo, respuesta, respuesta_nbo, nbo_version = _modelos()
pred = (
    riesgo.predict(feats)[["IdCliente", "NivelRiesgo", "RiesgoScore", "EsPerfilAtipico"]]
    .merge(respuesta.predict_proba(feats), on="IdCliente")
    .merge(respuesta_nbo.predict_wide(feats), on="IdCliente", validate="one_to_one")
    .merge(feats, on="IdCliente")
)
metricas = _metricas_guardadas()

# ---------------------------------------------------------------- sidebar --
with st.sidebar:
    st.markdown("### 🎰 Casino Palacio Real")
    st.caption("Identificación de riesgo + probabilidad de respuesta → optimización de recompensas")
    st.divider()
    st.markdown("**Estado de los modelos**")
    if metricas:
        r_m = metricas.get("riesgo", {})
        p_m = metricas.get("respuesta_v1", metricas.get("respuesta", {}))
        nbo_m = metricas.get("respuesta_v2_nbo", {}).get("respuesta", {})
        st.metric("Riesgo — F1 macro (holdout)", r_m.get("f1_macro_holdout", "—"))
        st.metric("Respuesta V1 — ROC-AUC", p_m.get("roc_auc", "—"),
                   delta=(f"+{round(p_m['roc_auc']-p_m['roc_auc_baseline_logistica'],3)} vs. logística"
                          if p_m.get("roc_auc") and p_m.get("roc_auc_baseline_logistica") else None))
        if nbo_m:
            st.metric("Respuesta V2 (NBO) — PR-AUC", nbo_m.get("pr_auc", "—"))
    else:
        st.caption("Ejecutá `scripts/train_models.py` para ver métricas.")
    st.caption(f"NBO activo: {nbo_version}")
    st.divider()
    st.markdown("**IA generativa**")
    _icono_llm, _detalle_llm = _estado_llm()
    st.caption(f"{_icono_llm} {_detalle_llm}")
    _icono_tg, _detalle_tg = _estado_telegram()
    st.caption(f"{_icono_tg} Telegram: {_detalle_tg}")
    st.divider()
    st.caption(
        "Guardrail: los clientes de **riesgo alto** quedan excluidos de toda "
        "recompensa y se derivan al protocolo de juego responsable."
    )

st.title("Casino Palacio Real — asignación de recompensas")
tab_cartera, tab_cliente = st.tabs(["📊 Cartera", "🧑 Cliente"])

# ----------------------------------------------------------------- cartera --
with tab_cartera:
    presupuesto = st.slider(
        "Presupuesto de la campaña (S/)",
        200,
        40000,
        int(config.REWARDS.presupuesto),
        200,
    )
    cand = _plan_asignacion(presupuesto)
    if len(cand) and "Asignada" not in cand.columns:  # módulo desactualizado en la sesión
        st.error(
            "Reinicia la app (Ctrl+C y volver a lanzar): "
            "hay una versión vieja del optimizador en memoria."
        )
        st.stop()
    if len(cand):
        cand = cand.merge(feats[["IdCliente", "NombreCompleto"]], on="IdCliente", how="left")
    asignadas = cand[cand["Asignada"]] if len(cand) else cand
    candidatas = cand[cand["RecompensaSugerida"].notna()] if len(cand) else cand

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Clientes en cartera", len(pred))
    c2.metric("Riesgo alto (excluidos)", int((pred["NivelRiesgo"] == "Alto").sum()))
    c3.metric("Recompensas asignadas", f"{len(asignadas)} / {len(candidatas)}")
    gasto = asignadas["Costo"].sum() if len(asignadas) else 0
    c4.metric("Gasto / presupuesto", f"{gasto:,.0f} / {presupuesto:,.0f}")

    st.caption(
        "El optimizador rankea a los clientes elegibles por **eficiencia** "
        "(valor esperado por sol) "
        "y evalúa toda la lista aplicando presupuesto, topes y guardrails. "
        "**MotivoDecision** explica el resultado de cada cliente."
    )
    col_a, col_b = st.columns(2)
    with col_a:
        st.caption("Clientes por nivel de riesgo")
        st.bar_chart(pred["NivelRiesgo"].value_counts().reindex(["Bajo", "Medio", "Alto"]))
    with col_b:
        st.caption("Recompensas asignadas por tipo")
        st.bar_chart(asignadas["Recompensa"].value_counts() if len(asignadas) else pred["NivelRiesgo"].value_counts() * 0)

    with st.expander("¿Qué significa cada columna?"):
        st.table({"Columna": [c for c, _ in _DICCIONARIO_CARTERA],
                   "Qué es": [d for _, d in _DICCIONARIO_CARTERA]})

    if len(cand):
        cols = [
            c
            for c in [
                "NombreCompleto",
                "Segmento",
                "NivelRiesgo",
                "SesionesUltimos90d",
                "ProbRespuesta",
                "Recompensa",
                "Costo",
                "ValorIncremental",
                "UpliftProbabilidad",
                "ValorEsperado",
                "Eficiencia",
                "GastoAcumulado",
                "Asignada",
                "MotivoDecision",
            ]
            if c in cand.columns
        ]
        st.dataframe(
            cand[cols].rename(columns={"NombreCompleto": "Cliente"}),
            width="stretch", hide_index=True,
        )
    else:
        st.info("Ningún cliente tiene valor esperado positivo con estos parámetros.")

# ----------------------------------------------------------------- cliente --
with tab_cliente:
    columnas_decision = [
        "IdCliente",
        "Recompensa",
        "Costo",
        "ProbRespuesta",
        "ValorIncremental",
        "UpliftProbabilidad",
        "ValorEsperado",
        "ValorEsperadoBruto",
        "Asignada",
        "MotivoDecision",
    ]
    fichas = pred.drop(columns="ProbRespuesta").merge(
        cand[columnas_decision], on="IdCliente", how="left"
    ).sort_values("NombreCompleto")
    cid = st.selectbox(
        "Cliente",
        fichas["IdCliente"].tolist(),
        format_func=lambda i: fichas.loc[fichas["IdCliente"] == i, "NombreCompleto"].iloc[0],
    )
    ficha = fichas[fichas["IdCliente"] == cid].iloc[0].to_dict()
    with st.expander("¿Qué significa cada dato?"):
        st.table({"Columna": [c for c, _ in _DICCIONARIO_CARTERA + _DICCIONARIO_CLIENTE],
                   "Qué es": [d for _, d in _DICCIONARIO_CARTERA + _DICCIONARIO_CLIENTE]})

    c1, c2, c3, c4 = st.columns(4)
    color = {"Bajo": "normal", "Medio": "off", "Alto": "inverse"}.get(ficha["NivelRiesgo"], "normal")
    c1.metric("Nivel de riesgo", ficha["NivelRiesgo"], delta_color=color)
    c2.metric("Probabilidad de respuesta", f"{ficha['ProbRespuesta']:.0%}")
    c3.metric("Segmento", ficha["Segmento"])
    c4.metric("CoinIn total", f"S/ {ficha['CoinInTotal']:,.0f}")
    if ficha.get("EsPerfilAtipico"):
        st.caption("⚠️ Marcado como perfil atípico por el detector de anomalías (IsolationForest).")
    uplift = ficha.get("UpliftProbabilidad")
    uplift_valido = uplift is not None and isinstance(uplift, (int, float)) and uplift == uplift
    st.caption(
        f"**Decisión del optimizador:** {ficha.get('MotivoDecision') or '—'}"
        + (f" · recompensa **{ficha['Recompensa']}**" if ficha.get("Recompensa") else "")
        + (f" · uplift de respuesta vs. control: **{uplift:+.1%}**" if uplift_valido else "")
    )

    with st.spinner("Generando explicación..."):
        textos = explicar_cliente(ficha)
    st.markdown(f"**Explicación**  \n{textos['explicacion']}")
    st.markdown(f"**Oferta**  \n{textos['oferta']}")
    st.markdown(f"**Mensaje**  \n{textos['mensaje']}")

    with st.expander("📨 Enviar esta oferta por Telegram"):
        _icono_tg_cli, _detalle_tg_cli = _estado_telegram()
        st.caption(f"{_icono_tg_cli} {_detalle_tg_cli}")
        st.caption(
            "Escribile a **@CasinoPalacioReal_bot** en Telegram y mandale `/start`: "
            "te responde con tu `chat_id`. Pegalo acá para recibir esta oferta real "
            "con botones Sí / No."
        )
        chat_id_input = st.text_input("Tu chat_id de Telegram", key="telegram_chat_id")
        if st.button("Enviar oferta por Telegram", disabled=not chat_id_input):
            resultado = enviar_oferta(chat_id_input, ficha, id_campana="DEMO-WEB")
            if resultado["enviado"]:
                st.success("Oferta enviada — revisá tu Telegram.")
            else:
                st.warning(f"No se envió: {resultado['motivo']}")

# -------------------------------------------------- asistente (flotante) --
# Vive fuera de las pestañas: no está "dentro" de Cartera ni de Cliente, así
# que al cambiar de pestaña sigue ahí, en la esquina, con su historial intacto.
# Comparte el motor de políticas (genai.rag.AsistentePoliticas) con Telegram.
_widget_flotante()
