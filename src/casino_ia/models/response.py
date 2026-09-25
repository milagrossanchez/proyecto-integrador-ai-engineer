"""Modelo de probabilidad de respuesta a una recompensa.

Clasificacion binaria calibrada. En el prototipo la etiqueta es un *proxy*:
"el cliente muestra momentum positivo de actividad" (su gasto de la ultima
semana supera lo esperado si su ritmo fuera constante). En produccion se
reemplaza por el resultado real de campanas (con grupo de control -> modelo
de uplift).

Mejora sobre v1: en vez de un `GradientBoostingClassifier` con hiperparametros
fijos, se busca la mejor configuracion de un `HistGradientBoostingClassifier`
con `RandomizedSearchCV` (scoring = PR-AUC, mas informativo que ROC-AUC aca
por el desbalance moderado) y luego se calibra con `CalibratedClassifierCV`.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import joblib
import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV, calibration_curve
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score
from sklearn.model_selection import RandomizedSearchCV, StratifiedKFold, train_test_split
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

_PARAM_DIST = {
    "max_iter": [100, 150, 200, 300],
    "max_depth": [3, 4, 5, 6, None],
    "learning_rate": [0.03, 0.05, 0.08, 0.1, 0.15],
    "l2_regularization": [0.0, 0.1, 0.5, 1.0],
    "min_samples_leaf": [10, 20, 30, 50],
}


def etiqueta_proxy(feats: pd.DataFrame) -> pd.Series:
    ratio = feats["RatioTendenciaCoinIn"].fillna(0.0)
    return (ratio >= UMBRAL_MOMENTUM).astype(int)


@dataclass
class ModeloRespuesta:
    features: list[str] = field(default_factory=lambda: list(FEATURES_RESPUESTA))
    n_iter_busqueda: int = 25
    _scaler: StandardScaler = None
    _model: CalibratedClassifierCV = None
    metrics_: dict = None

    def fit(self, feats: pd.DataFrame) -> "ModeloRespuesta":
        y = etiqueta_proxy(feats)
        x = feats[self.features].apply(pd.to_numeric, errors="coerce")
        x = x.fillna(x.median(numeric_only=True))

        x_tr, x_te, y_tr, y_te = train_test_split(
            x, y, test_size=0.3, random_state=42, stratify=y
        )
        self._scaler = StandardScaler().fit(x_tr)
        xs_tr, xs_te = self._scaler.transform(x_tr), self._scaler.transform(x_te)

        cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
        base = HistGradientBoostingClassifier(random_state=42)
        busqueda = RandomizedSearchCV(
            base,
            _PARAM_DIST,
            n_iter=self.n_iter_busqueda,
            scoring="average_precision",  # PR-AUC: mas informativo con clases moderadamente desbalanceadas
            cv=cv,
            random_state=42,
            n_jobs=-1,
        )
        busqueda.fit(xs_tr, y_tr)

        self._model = CalibratedClassifierCV(busqueda.best_estimator_, method="isotonic", cv=3)
        self._model.fit(xs_tr, y_tr)

        p_te = self._model.predict_proba(xs_te)[:, 1]
        baseline = LogisticRegression(max_iter=1000).fit(xs_tr, y_tr)
        p_base = baseline.predict_proba(xs_te)[:, 1]

        frac_pos, media_pred = calibration_curve(y_te, p_te, n_bins=8, strategy="quantile")

        self.metrics_ = {
            "tasa_positivos": round(float(y.mean()), 3),
            "mejores_hiperparametros": busqueda.best_params_,
            "pr_auc_busqueda_cv": round(float(busqueda.best_score_), 3),
            "roc_auc": round(float(roc_auc_score(y_te, p_te)), 3),
            "pr_auc": round(float(average_precision_score(y_te, p_te)), 3),
            "brier": round(float(brier_score_loss(y_te, p_te)), 3),
            "roc_auc_baseline_logistica": round(float(roc_auc_score(y_te, p_base)), 3),
            "pr_auc_baseline_logistica": round(float(average_precision_score(y_te, p_base)), 3),
            "lift_top_decil": round(float(_lift_top_decil(y_te, p_te)), 2),
            "curva_calibracion": {
                "prob_predicha": [round(v, 3) for v in media_pred.tolist()],
                "frac_positivos_real": [round(v, 3) for v in frac_pos.tolist()],
            },
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
