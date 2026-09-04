"""Construcción de la tabla analítica por cliente (ABT).

Réplica en pandas de la vista SQL `vw_FeaturesCliente`. Se usa como *fallback*
cuando no hay conexión a SQL Server y para las pruebas unitarias.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

# Variables que entran a los modelos (numéricas).
FEATURES_RIESGO = [
    "CoinInPorHora",
    "DuracionMaximaMin",
    "DuracionPromedioMin",
    "PctSesionesLargas",
    "PctJuegoMadrugada",
    "PctSesionesChasing",
    "VolatilidadResultado",
    "ApuestaMaxima",
    "ApuestaMediaPromedio",
    "PerdidasAcumuladas",
]
FEATURES_RESPUESTA = [
    "DiasDesdeUltimaSesion",
    "RatioTendenciaCoinIn",
    "CompsAcumulados",
    "PuntosAcumulados",
    "NroSesiones",
    "CoinInTotal",
    "ValorTeoricoCasa",
    "Sesiones_Ultimos7d",
]


def construir_features_desde_sesiones(sesiones: pd.DataFrame) -> pd.DataFrame:
    """A partir del detalle de sesiones, devuelve una fila por cliente."""
    s = sesiones.copy()
    s["StartTime"] = pd.to_datetime(s["StartTime"])
    s["Dia"] = s["StartTime"].dt.normalize()
    s = s.sort_values(["IdCliente", "StartTime", "TransID"])

    fecha_corte = s["Dia"].max()
    fecha_7 = fecha_corte - pd.Timedelta(days=7)

    g = s.groupby("IdCliente", group_keys=False)
    s["WinPrev"] = g["Win"].shift(1)
    s["CoinInPrev"] = g["CoinIn"].shift(1)

    s["Minutos"] = s["TimePlayed"] / 60.0
    s["FlagLarga"] = (s["Minutos"] > 120).astype(float)
    s["FlagMadrugada"] = (s["Hora"] < 6).astype(float)
    s["Perdida"] = np.where(s["Win"] < 0, -s["Win"], 0.0)
    s["FlagChasing"] = (
        (s["WinPrev"] < 0) & (s["CoinIn"] > s["CoinInPrev"] * 1.2)
    ).astype(float)
    s["EsU7"] = (s["Dia"] >= fecha_7).astype(int)

    by = s.groupby("IdCliente")
    out = pd.DataFrame(index=by.size().index)
    out["NroSesiones"] = by.size()
    out["DiasActivos"] = by["Dia"].nunique()
    out["NroVisitas"] = by["TripNumber"].max()
    out["UltimaSesion"] = by["StartTime"].max()
    out["DiasDesdeUltimaSesion"] = (fecha_corte - by["Dia"].max()).dt.days
    out["CoinInTotal"] = by["CoinIn"].sum()
    out["CoinInPromedioSesion"] = by["CoinIn"].mean()
    out["ValorTeoricoCasa"] = by["TheoWin"].sum()
    out["ResultadoClienteTotal"] = by["Win"].sum()
    out["PerdidasAcumuladas"] = by["Perdida"].sum()
    out["HorasJugadas"] = by["TimePlayed"].sum() / 3600.0
    out["DuracionPromedioMin"] = by["Minutos"].mean()
    out["DuracionMaximaMin"] = by["Minutos"].max()
    out["PctSesionesLargas"] = by["FlagLarga"].mean()
    out["CoinInPorHora"] = out["CoinInTotal"] / out["HorasJugadas"].replace(0, np.nan)
    out["ApuestaMediaPromedio"] = by["AverageBet"].mean()
    out["ApuestaMaxima"] = by["AverageBet"].max()
    out["PctJuegoMadrugada"] = by["FlagMadrugada"].mean()
    out["VolatilidadResultado"] = by["Win"].std()
    out["PctSesionesChasing"] = by["FlagChasing"].mean()
    out["CompsAcumulados"] = by["CompEarned"].sum()
    out["PuntosAcumulados"] = by["PointsEarned"].sum()
    out["NroSalas"] = by["IdSala"].nunique()

    coinin_u7 = s.loc[s["EsU7"] == 1].groupby("IdCliente")["CoinIn"].sum()
    coinin_prev = s.loc[s["EsU7"] == 0].groupby("IdCliente")["CoinIn"].sum()
    ses_u7 = s.loc[s["EsU7"] == 1].groupby("IdCliente").size()
    ses_prev = s.loc[s["EsU7"] == 0].groupby("IdCliente").size()
    out["CoinIn_Ultimos7d"] = coinin_u7.reindex(out.index).fillna(0.0)
    out["CoinIn_Previo"] = coinin_prev.reindex(out.index).fillna(0.0)
    out["Sesiones_Ultimos7d"] = ses_u7.reindex(out.index).fillna(0).astype(int)
    out["Sesiones_Previo"] = ses_prev.reindex(out.index).fillna(0).astype(int)
    out["RatioTendenciaCoinIn"] = np.where(
        out["CoinIn_Previo"] > 0, out["CoinIn_Ultimos7d"] / out["CoinIn_Previo"], np.nan
    )

    out = out.reset_index().rename(columns={"index": "IdCliente"})
    return out


def _percentil(serie: pd.Series) -> pd.Series:
    return serie.rank(pct=True, method="average")


def agregar_scoring_reglas(feats: pd.DataFrame) -> pd.DataFrame:
    """Baseline: `RiesgoScore`, `NivelRiesgo`, `PropensionScore`, `DecilPropension`.

    Réplica de la vista `vw_ClientesScoring`.
    """
    df = feats.copy()
    riesgo = (
        _percentil(df["PctSesionesChasing"])
        + _percentil(df["PctSesionesLargas"])
        + _percentil(df["CoinInPorHora"])
        + _percentil(df["DuracionMaximaMin"])
        + _percentil(df["VolatilidadResultado"])
        + _percentil(df["ApuestaMaxima"])
    ) / 6.0
    df["RiesgoScore"] = riesgo.round(3)
    # Pirámide de riesgo realista: ~70% Bajo, ~22% Medio, ~8% Alto.
    df["NivelRiesgo"] = pd.qcut(
        riesgo.rank(method="first"),
        q=[0, 0.70, 0.92, 1.0],
        labels=["Bajo", "Medio", "Alto"],
    ).astype(str)

    prop = (
        0.40 * _percentil(-df["DiasDesdeUltimaSesion"])
        + 0.35 * _percentil(df["RatioTendenciaCoinIn"].fillna(0))
        + 0.25 * _percentil(df["CompsAcumulados"])
    )
    df["PropensionScore"] = prop.round(3)
    df["DecilPropension"] = pd.qcut(
        prop.rank(method="first"), 10, labels=range(1, 11)
    ).astype(int)
    return df


def preparar_matriz_modelo(
    feats: pd.DataFrame, columnas: list[str]
) -> pd.DataFrame:
    """Selecciona columnas, imputa nulos con la mediana y acota outliers (p1–p99)."""
    x = feats[columnas].apply(pd.to_numeric, errors="coerce")
    x = x.fillna(x.median(numeric_only=True))
    for c in x.columns:
        lo, hi = x[c].quantile([0.01, 0.99])
        x[c] = x[c].clip(lo, hi)
    return x


def split_temporal(
    feats: pd.DataFrame, col_fecha: str = "UltimaSesion", frac_train: float = 0.7
):
    """Partición temporal: los clientes cuya última sesión es más antigua entrenan."""
    if col_fecha not in feats.columns:
        # sin fecha disponible: split aleatorio reproducible
        idx = feats.sample(frac=1.0, random_state=42).index
    else:
        idx = feats.sort_values(col_fecha).index
    corte = int(len(idx) * frac_train)
    return feats.loc[idx[:corte]].copy(), feats.loc[idx[corte:]].copy()
