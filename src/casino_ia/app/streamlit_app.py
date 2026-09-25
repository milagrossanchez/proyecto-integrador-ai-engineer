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
from casino_ia.models import ModeloRespuesta, ModeloRiesgo
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
    )


def _metricas_guardadas() -> dict:
    p = config.METRICS / "metrics_modelos.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


feats = _data()
riesgo, respuesta = _modelos()
pred = (
    riesgo.predict(feats)[["IdCliente", "NivelRiesgo", "RiesgoScore", "EsPerfilAtipico"]]
    .merge(respuesta.predict_proba(feats), on="IdCliente")
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
        p_m = metricas.get("respuesta", {})
        st.metric("Riesgo — F1 macro (holdout)", r_m.get("f1_macro_holdout", "—"))
        st.metric("Respuesta — ROC-AUC", p_m.get("roc_auc", "—"),
                   delta=(f"+{round(p_m['roc_auc']-p_m['roc_auc_baseline_logistica'],3)} vs. logística"
                          if p_m.get("roc_auc") and p_m.get("roc_auc_baseline_logistica") else None))
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
tab_cartera, tab_cliente, tab_chat = st.tabs(["📊 Cartera", "🧑 Cliente", "💬 Asistente"])

# ----------------------------------------------------------------- cartera --
with tab_cartera:
    presupuesto = st.slider("Presupuesto de la campaña (S/)", 200, 40000, int(config.REWARDS.presupuesto), 200)
    cand = asignar_recompensas(pred, presupuesto=presupuesto)
    if len(cand) and "Asignada" not in cand.columns:  # módulo desactualizado en la sesión
        st.error("Reinicia la app (Ctrl+C y volver a lanzar): hay una versión vieja del optimizador en memoria.")
        st.stop()
    asignadas = cand[cand["Asignada"]] if len(cand) else cand

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Clientes en cartera", len(pred))
    c2.metric("Riesgo alto (excluidos)", int((pred["NivelRiesgo"] == "Alto").sum()))
    c3.metric("Recompensas asignadas", f"{len(asignadas)} / {len(cand)}")
    c4.metric("Gasto / presupuesto", f"{asignadas['Costo'].sum():,.0f} / {presupuesto:,.0f}" if len(asignadas) else "0")

    st.caption(
        "El optimizador rankea a los clientes elegibles por **eficiencia** (valor esperado por sol) "
        "y asigna de arriba hacia abajo hasta agotar el presupuesto. "
        "La columna **Asignada** marca cuáles entraron; el resto son candidatos que quedaron fuera por presupuesto."
    )
    col_a, col_b = st.columns(2)
    with col_a:
        st.caption("Clientes por nivel de riesgo")
        st.bar_chart(pred["NivelRiesgo"].value_counts().reindex(["Bajo", "Medio", "Alto"]))
    with col_b:
        st.caption("Recompensas asignadas por tipo")
        st.bar_chart(asignadas["Recompensa"].value_counts() if len(asignadas) else pred["NivelRiesgo"].value_counts() * 0)

    if len(cand):
        cols = [c for c in ["IdCliente", "Segmento", "NivelRiesgo", "ProbRespuesta",
                            "Recompensa", "Costo", "ValorEsperado", "Eficiencia",
                            "GastoAcumulado", "Asignada"] if c in cand.columns]
        st.dataframe(cand[cols], use_container_width=True, hide_index=True)
    else:
        st.info("Ningún cliente tiene valor esperado positivo con estos parámetros.")

# ----------------------------------------------------------------- cliente --
with tab_cliente:
    cid = st.selectbox("Cliente", pred["IdCliente"].tolist())
    ficha = pred[pred["IdCliente"] == cid].iloc[0].to_dict()

    c1, c2, c3, c4 = st.columns(4)
    color = {"Bajo": "normal", "Medio": "off", "Alto": "inverse"}.get(ficha["NivelRiesgo"], "normal")
    c1.metric("Nivel de riesgo", ficha["NivelRiesgo"], delta_color=color)
    c2.metric("Probabilidad de respuesta", f"{ficha['ProbRespuesta']:.0%}")
    c3.metric("Segmento", ficha["Segmento"])
    c4.metric("CoinIn total", f"S/ {ficha['CoinInTotal']:,.0f}")
    if ficha.get("EsPerfilAtipico"):
        st.caption("⚠️ Marcado como perfil atípico por el detector de anomalías (IsolationForest).")

    with st.spinner("Generando explicación..."):
        textos = explicar_cliente(ficha)
    st.markdown(f"**Explicación**  \n{textos['explicacion']}")
    st.markdown(f"**Oferta**  \n{textos['oferta']}")
    st.markdown(f"**Mensaje**  \n{textos['mensaje']}")

# ------------------------------------------------------------------- chat --
with tab_chat:
    st.caption(
        "Chatbot para el analista. Responde con RAG sobre las políticas y la guía de "
        "asignación de recompensas; si algo no está en los documentos, lo dice."
    )

    @st.cache_resource
    def _asistente():
        return AsistentePoliticas()

    asistente = _asistente()
    ejemplos = [
        "¿Un cliente de riesgo medio puede recibir recompensa alta?",
        "¿Qué pasa con los clientes de riesgo alto?",
        "¿Cómo se elige a quién premiar si el presupuesto no alcanza?",
        "¿Qué incluye la recompensa media?",
    ]
    st.write("Ejemplos: " + " · ".join(f"`{e}`" for e in ejemplos))

    if "chat" not in st.session_state:
        st.session_state.chat = []
    for m in st.session_state.chat:
        st.chat_message(m["role"]).write(m["content"])

    pregunta = st.chat_input("Escribe tu pregunta")
    if pregunta:
        st.session_state.chat.append({"role": "user", "content": pregunta})
        st.chat_message("user").write(pregunta)
        with st.spinner("Buscando en las políticas..."):
            r = asistente.responder(pregunta)
        texto = r["respuesta"]
        if r["fuentes"]:
            texto += "\n\n_Fuentes: " + ", ".join(sorted(set(r["fuentes"]))) + "_"
        st.session_state.chat.append({"role": "assistant", "content": texto})
        st.chat_message("assistant").write(texto)
