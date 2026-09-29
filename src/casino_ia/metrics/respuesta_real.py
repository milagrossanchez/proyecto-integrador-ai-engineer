"""Medición de la respuesta real de los clientes a las recompensas.

Cierra el loop que hoy corre con datos semi-sintéticos
(`models.response.simular_historico_campanas`): cada vez que se envía una
oferta (por Telegram, web o cualquier canal futuro) y el cliente responde
(o no), se registra una fila acá. Con volumen suficiente, esa tabla reemplaza
directamente al histórico simulado — es EL MISMO esquema de columnas a
propósito, para que `ModeloRespuestaNBO.fit()` no requiera cambios.

En producción esto es una tabla de SQL Server (`FactResultadoCampana`, ver
`docs/arquitectura_produccion.md`); acá se implementa sobre Parquet local para
que el prototipo funcione sin infraestructura adicional.
"""

from __future__ import annotations

import datetime
import uuid

import numpy as np
import pandas as pd

from casino_ia.config import DATA_PROCESSED

RUTA_RESULTADOS = DATA_PROCESSED / "resultados_campana_real.parquet"

COLUMNAS = [
    "IdEvento",
    "IdCampana",
    "IdCliente",
    "Canal",  # telegram | web | otro
    "TipoRecompensa",  # baja | media | alta | control
    "NivelRiesgo",
    "ProbRespuestaPredicha",  # lo que dijo el modelo ANTES de enviar la oferta
    "ValorIncrementalPredicho",
    "FechaOferta",
    "FechaRespuesta",  # NaT si todavía no respondió / no va a responder
    "Respondio",  # 0/1, solo se fija en firme al vencer la ventana de espera
    "ValorGenerado",  # valor real medido (ej. CoinIn incremental de la sesión siguiente)
]

CANALES_VALIDOS = {"telegram", "web", "otro"}


def registrar_resultado(
    id_campana: str,
    id_cliente: int,
    canal: str,
    tipo_recompensa: str,
    nivel_riesgo: str,
    prob_respuesta_predicha: float,
    valor_incremental_predicho: float,
    fecha_oferta: datetime.datetime | None = None,
    fecha_respuesta: datetime.datetime | None = None,
    respondio: int | None = None,
    valor_generado: float | None = None,
) -> str:
    """Agrega una fila al registro de resultados y devuelve su IdEvento.

    Se llama dos veces por interacción real:
      1) al enviar la oferta (fecha_respuesta=None, respondio=None) -> "pendiente"
      2) al cerrar la ventana de espera, con la respuesta real observada.
    La segunda llamada actualiza la fila por IdEvento en vez de duplicarla.
    """
    if canal not in CANALES_VALIDOS:
        raise ValueError(f"Canal inválido: {canal!r} (usar {sorted(CANALES_VALIDOS)})")

    fila = {
        "IdEvento": str(uuid.uuid4()),
        "IdCampana": id_campana,
        "IdCliente": id_cliente,
        "Canal": canal,
        "TipoRecompensa": tipo_recompensa,
        "NivelRiesgo": nivel_riesgo,
        "ProbRespuestaPredicha": prob_respuesta_predicha,
        "ValorIncrementalPredicho": valor_incremental_predicho,
        "FechaOferta": fecha_oferta or datetime.datetime.now(),
        "FechaRespuesta": fecha_respuesta,
        "Respondio": respondio,
        "ValorGenerado": valor_generado,
    }

    if RUTA_RESULTADOS.exists():
        df = pd.read_parquet(RUTA_RESULTADOS)
        df = pd.concat([df, pd.DataFrame([fila])], ignore_index=True)
    else:
        df = pd.DataFrame([fila], columns=COLUMNAS)
    df.to_parquet(RUTA_RESULTADOS, index=False)
    return fila["IdEvento"]


def actualizar_respuesta(
    id_evento: str, respondio: int, valor_generado: float = 0.0,
    fecha_respuesta: datetime.datetime | None = None,
) -> None:
    """Cierra un evento pendiente con el desenlace real."""
    df = pd.read_parquet(RUTA_RESULTADOS)
    idx = df.index[df["IdEvento"] == id_evento]
    if len(idx) == 0:
        raise KeyError(f"IdEvento no encontrado: {id_evento}")
    df.loc[idx, "Respondio"] = respondio
    df.loc[idx, "ValorGenerado"] = valor_generado
    df.loc[idx, "FechaRespuesta"] = fecha_respuesta or datetime.datetime.now()
    df.to_parquet(RUTA_RESULTADOS, index=False)


def cargar_resultados() -> pd.DataFrame:
    if not RUTA_RESULTADOS.exists():
        return pd.DataFrame(columns=COLUMNAS)
    return pd.read_parquet(RUTA_RESULTADOS)


def calcular_metricas_respuesta(df: pd.DataFrame | None = None) -> dict:
    """Las métricas que importan para saber si el sistema funciona con clientes reales.

    Se calculan solo sobre eventos ya resueltos (Respondio no nulo) — los
    pendientes (oferta enviada, sin desenlace todavía) se cuentan aparte.
    """
    df = cargar_resultados() if df is None else df
    pendientes = int(df["Respondio"].isna().sum())
    resueltos = df.dropna(subset=["Respondio"]).copy()
    if resueltos.empty:
        return {"eventos_totales": len(df), "pendientes": pendientes, "resueltos": 0}

    resueltos["Respondio"] = resueltos["Respondio"].astype(int)
    resueltos["horas_respuesta"] = (
        pd.to_datetime(resueltos["FechaRespuesta"]) - pd.to_datetime(resueltos["FechaOferta"])
    ).dt.total_seconds() / 3600.0

    tasa_global = float(resueltos["Respondio"].mean())

    por_canal = (
        resueltos.groupby("Canal")["Respondio"]
        .agg(exposiciones="size", tasa_respuesta="mean")
        .round(4).to_dict("index")
    )
    por_tipo = (
        resueltos.groupby("TipoRecompensa")["Respondio"]
        .agg(exposiciones="size", tasa_respuesta="mean")
        .round(4).to_dict("index")
    )

    # Calibración real: si el modelo dijo 30% de probabilidad, ¿respondió ~30%?
    # (error absoluto medio entre lo predicho y el promedio observado por bins)
    bins = pd.qcut(resueltos["ProbRespuestaPredicha"], q=min(5, resueltos["ProbRespuestaPredicha"].nunique()), duplicates="drop")
    calibracion = (
        resueltos.groupby(bins, observed=True)
        .agg(prob_predicha_media=("ProbRespuestaPredicha", "mean"),
             tasa_real=("Respondio", "mean"), n=("Respondio", "size"))
        .round(4)
    )
    error_calibracion = float(
        (calibracion["prob_predicha_media"] - calibracion["tasa_real"]).abs().mean()
    )

    return {
        "eventos_totales": len(df),
        "pendientes": pendientes,
        "resueltos": len(resueltos),
        "tasa_respuesta_global": round(tasa_global, 4),
        "tiempo_respuesta_promedio_horas": round(float(resueltos["horas_respuesta"].mean()), 2),
        "por_canal": por_canal,
        "por_tipo_recompensa": por_tipo,
        "error_calibracion_absoluto_medio": round(error_calibracion, 4),
        "valor_generado_total": round(float(resueltos["ValorGenerado"].fillna(0).sum()), 2),
    }
