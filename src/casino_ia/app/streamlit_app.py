"""App de demo: tablero de cartera, ficha por cliente y asistente RAG."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))

import pandas as pd
import streamlit as st

from casino_ia import config
from casino_ia.data import cargar_features_cliente
from casino_ia.genai import AsistentePoliticas, explicar_cliente
from casino_ia.models import ModeloRespuesta, ModeloRiesgo
from casino_ia.optimization.allocate import asignar_recompensas

st.set_page_config(page_title="Palacio Real · Recompensas", layout="wide")


@st.cache_data
def _data():
    return cargar_features_cliente()


@st.cache_resource
def _modelos():
    return (
        ModeloRiesgo.load(config.MODELS_STORE / "modelo_riesgo.joblib"),
        ModeloRespuesta.load(config.MODELS_STORE / "modelo_respuesta.joblib"),
    )


feats = _data()
riesgo, respuesta = _modelos()
pred = (
    riesgo.predict(feats)[["IdCliente", "NivelRiesgo", "RiesgoScore"]]
    .merge(respuesta.predict_proba(feats), on="IdCliente")
    .merge(feats, on="IdCliente")
)

st.title("Casino Palacio Real — asignación de recompensas")
tab_cartera, tab_cliente, tab_chat = st.tabs(["Cartera", "Cliente", "Asistente"])

with tab_cartera:
    presupuesto = st.slider("Presupuesto de la campaña", 2000, 40000, int(config.REWARDS.presupuesto), 1000)
    plan = asignar_recompensas(pred, presupuesto=presupuesto)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Clientes en cartera", len(pred))
    c2.metric("Riesgo alto (excluidos)", int((pred["NivelRiesgo"] == "Alto").sum()))
    c3.metric("Recompensas asignadas", len(plan))
    c4.metric("Gasto", f"{plan['Costo'].sum():,.0f}" if len(plan) else "0")
    st.bar_chart(pred["NivelRiesgo"].value_counts())
    st.dataframe(plan, use_container_width=True)

with tab_cliente:
    cid = st.selectbox("Cliente", pred["IdCliente"].tolist())
    ficha = pred[pred["IdCliente"] == cid].iloc[0].to_dict()
    st.json({k: ficha[k] for k in ("NivelRiesgo", "RiesgoScore", "ProbRespuesta", "Segmento", "CoinInTotal")})
    textos = explicar_cliente(ficha)
    st.write("**Explicación**", textos["explicacion"])
    st.write("**Oferta**", textos["oferta"])
    st.write("**Mensaje**", textos["mensaje"])

with tab_chat:
    asistente = AsistentePoliticas()
    q = st.text_input("Pregunta sobre la política de recompensas o juego responsable")
    if q:
        r = asistente.responder(q)
        st.write(r["respuesta"])
        if r["fuentes"]:
            st.caption("Fuentes: " + ", ".join(r["fuentes"]))
