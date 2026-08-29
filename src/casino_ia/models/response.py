"""Modelo de probabilidad de respuesta a una recompensa.

Clasificación binaria calibrada. En el prototipo la etiqueta es un *proxy*:
"el cliente muestra momentum positivo de actividad" (su gasto de la última semana
supera lo esperado si su ritmo fuera constante). En producción se reemplaza por
el resultado real de campañas (con grupo de control ⇒ modelo de uplift).
"""

from __future__ import annotations

from dataclasses import dataclass

import joblib
import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

# Se excluyen las variables de ventana reciente para no filtrar la etiqueta.
FEATURES_RESPUESTA = [
    "DiasDesdeUltimaSesion",
    "NroSesiones",
    "DiasActivos",
    "CoinInTotal",
    "CoinInPromedioSesion",
    "ValorTeoricoCasa",
    "CompsAcumulados",
    "PuntosAcumulados",
    "ApuestaMediaPromedio",
    "HorasJugadas",
    "AntiguedadDias",
]

# El periodo simulado tiene 15 días; la ventana "últimos 7" vs "8 previos"
# implica ratio esperado ~7/8 si el ritmo fuese constante.
UMBRAL_MOMENTUM = 7 / 8


def etiqueta_proxy(feats: pd.DataFrame) -> pd.Series:
    ratio = feats["RatioTendenciaCoinIn"].fillna(0.0)
    return (ratio >= UMBRAL_MOMENTUM).astype(int)


@dataclass
class ModeloRespuesta:
    features: list[str] = None
    _scaler: StandardScaler = None
    _model: CalibratedClassifierCV = None
    metrics_: dict = None

    def __post_init__(self):
        self.features = self.features or FEATURES_RESPUESTA

    def fit(self, feats: pd.DataFrame) -> "ModeloRespuesta":
        y = etiqueta_proxy(feats)
        x = feats[self.features].apply(pd.to_numeric, errors="coerce")
        x = x.fillna(x.median(numeric_only=True))

        x_tr, x_te, y_tr, y_te = train_test_split(
            x, y, test_size=0.3, random_state=42, stratify=y
        )
        self._scaler = StandardScaler().fit(x_tr)

        base = GradientBoostingClassifier(random_state=42)
        self._model = CalibratedClassifierCV(base, method="isotonic", cv=3)
        self._model.fit(self._scaler.transform(x_tr), y_tr)

        p_te = self._model.predict_proba(self._scaler.transform(x_te))[:, 1]
        baseline = LogisticRegression(max_iter=1000).fit(
            self._scaler.transform(x_tr), y_tr
        )
        p_base = baseline.predict_proba(self._scaler.transform(x_te))[:, 1]

        self.metrics_ = {
            "tasa_positivos": round(float(y.mean()), 3),
            "roc_auc": round(float(roc_auc_score(y_te, p_te)), 3),
            "pr_auc": round(float(average_precision_score(y_te, p_te)), 3),
            "brier": round(float(brier_score_loss(y_te, p_te)), 3),
            "roc_auc_baseline_logistica": round(float(roc_auc_score(y_te, p_base)), 3),
            "lift_top_decil": round(float(_lift_top_decil(y_te, p_te)), 2),
        }
        return self

    def predict_proba(self, feats: pd.DataFrame) -> pd.DataFrame:
        x = feats[self.features].apply(pd.to_numeric, errors="coerce")
        x = x.fillna(x.median(numeric_only=True))
        p = self._model.predict_proba(self._scaler.transform(x))[:, 1]
        return pd.DataFrame(
            {
                "IdCliente": feats["IdCliente"].to_numpy(),
                "ProbRespuesta": p.round(4),
                "DecilPropension": pd.qcut(
                    pd.Series(p).rank(method="first"), 10, labels=range(1, 11)
                ).astype(int),
            }
        )

    def save(self, path) -> None:
        joblib.dump(self, path)

    @staticmethod
    def load(path) -> "ModeloRespuesta":
        return joblib.load(path)


def _lift_top_decil(y_true: pd.Series, p: np.ndarray) -> float:
    d = pd.DataFrame({"y": np.asarray(y_true), "p": p})
    corte = d["p"].quantile(0.9)
    top = d[d["p"] >= corte]
    base = d["y"].mean()
    return (top["y"].mean() / base) if base > 0 else float("nan")
