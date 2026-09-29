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
from casino_ia.models import ModeloRespuesta, ModeloRespuestaNBO, ModeloRiesgo
from casino_ia.optimization.allocate import asignar_recompensas

st.set_page_config(page_title="Palacio Real · Recompensas", layout="wide", page_icon="🎰")


@st.cache_data
def _data():
    return cargar_features_cliente()


@st.cache_resource
def _modelos():
    return (
        ModeloRiesgo.load(config.MODELS_STORE / "modelo_riesgo.joblib"),
        ModeloRespuesta.load(config.MODELS_STORE / "modelo_respuesta.joblib"),
        ModeloRespuestaNBO.load(config.MODELS_STORE / "modelo_respuesta_nbo.joblib"),
    )


def _metricas_guardadas() -> dict:
    p = config.METRICS / "metrics_modelos.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


@st.cache_resource
def _asistente() -> AsistentePoliticas:
    return AsistentePoliticas()


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
    box-shadow: 0 6px 18px rgba(0,0,0,.28);
}
div.st-key-chat_panel {
    position: fixed; bottom: 22px; right: 22px; z-index: 999999;
    width: 380px; max-height: 62vh; overflow-y: auto;
    background: var(--background-color);
    border: 1px solid rgba(120,120,120,.35); border-radius: 16px;
    padding: 14px 16px; box-shadow: 0 10px 34px rgba(0,0,0,.30);
}
</style>
"""


def _widget_flotante() -> None:
    """Asistente en una burbuja fija en la esquina, visible en cualquier
    pestaña. Mismo motor RAG que se conectará a Telegram (ver
    docs/arquitectura_produccion.md) y que atiende tanto al cliente final
    como al operador de marketing preguntando por perfiles de clientes.
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
        c1, c2 = st.columns([5, 1])
        c1.markdown("**🎰 Asistente Palacio Real**")
        if c2.button("✕", key="btn_cerrar_chat"):
            st.session_state.chat_abierto = False
            st.rerun()
        st.caption(
            "Responde con RAG sobre políticas y datos de la cartera. "
            "Mismo asistente disponible por Telegram."
        )

        if not st.session_state.chat_historial:
            st.caption("Ejemplos:")
            for e in _EJEMPLOS_CHAT:
                st.caption(f"· {e}")

        for m in st.session_state.chat_historial:
            st.chat_message(m["role"]).write(m["content"])

        with st.form(key="form_chat", clear_on_submit=True):
            pregunta = st.text_input("Escribe tu pregunta", label_visibility="collapsed",
                                      placeholder="Preguntá algo…")
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
riesgo, respuesta, respuesta_nbo = _modelos()
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
    st.divider()
    st.markdown("**IA generativa**")
    st.caption("🟢 Conectada (API Anthropic)" if config.LLM.enabled else "⚪ Modo plantilla (sin API key)")
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
    cand = asignar_recompensas(pred, presupuesto=presupuesto)
    if len(cand) and "Asignada" not in cand.columns:  # módulo desactualizado en la sesión
        st.error(
            "Reinicia la app (Ctrl+C y volver a lanzar): "
            "hay una versión vieja del optimizador en memoria."
        )
        st.stop()
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

    if len(cand):
        cols = [
            c
            for c in [
                "IdCliente",
                "Segmento",
                "NivelRiesgo",
                "SesionesUltimos90d",
                "ProbRespuesta",
                "Recompensa",
                "Costo",
                "ValorIncremental",
                "ValorEsperado",
                "Eficiencia",
                "GastoAcumulado",
                "Asignada",
                "MotivoDecision",
            ]
            if c in cand.columns
        ]
        st.dataframe(cand[cols], width="stretch", hide_index=True)
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
        "ValorEsperado",
        "Asignada",
        "MotivoDecision",
    ]
    fichas = pred.drop(columns="ProbRespuesta").merge(
        cand[columnas_decision], on="IdCliente", how="left"
    )
    cid = st.selectbox("Cliente", fichas["IdCliente"].tolist())
    ficha = fichas[fichas["IdCliente"] == cid].iloc[0].to_dict()

    c1, c2, c3, c4 = st.columns(4)
    color = {"Bajo": "normal", "Medio": "off", "Alto": "inverse"}.get(ficha["NivelRiesgo"], "normal")
    c1.metric("Nivel de riesgo", ficha["NivelRiesgo"], delta_color=color)
    c2.metric("Probabilidad de respuesta", f"{ficha['ProbRespuesta']:.0%}")
    c3.metric("Segmento", ficha["Segmento"])
    c4.metric("CoinIn total", f"S/ {ficha['CoinInTotal']:,.0f}")
    if ficha.get("EsPerfilAtipico"):
        st.caption("⚠️ Marcado como perfil atípico por el detector de anomalías (IsolationForest).")
    st.caption(
        f"**Decisión del optimizador:** {ficha.get('MotivoDecision') or '—'}"
        + (f" · recompensa **{ficha['Recompensa']}**" if ficha.get("Recompensa") else "")
    )

    with st.spinner("Generando explicación..."):
        textos = explicar_cliente(ficha)
    st.markdown(f"**Explicación**  \n{textos['explicacion']}")
    st.markdown(f"**Oferta**  \n{textos['oferta']}")
    st.markdown(f"**Mensaje**  \n{textos['mensaje']}")

# -------------------------------------------------- asistente (flotante) --
# Vive fuera de las pestañas: no está "dentro" de Cartera ni de Cliente, así
# que al cambiar de pestaña sigue ahí, en la esquina, con su historial intacto.
# Es el mismo motor (genai.rag.AsistentePoliticas) que se conectará a Telegram
# y que responde tanto consultas del analista/operador de marketing sobre
# clientes puntuales como preguntas de política general.
_widget_flotante()
