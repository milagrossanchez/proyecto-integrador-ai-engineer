"""Modelo de nivel de riesgo del cliente.

Dos capas:
  1. No supervisada: `IsolationForest` marca perfiles atípicos por intensidad.
  2. Supervisada: `GradientBoostingClassifier` aprende los niveles
     Bajo/Medio/Alto a partir de las etiquetas débiles (percentiles) y generaliza.

En producción la capa supervisada se re-entrena con etiquetas reales del área de
juego responsable y de rentabilidad del incentivo.
"""

from __future__ import annotations

from dataclasses import dataclass

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier, IsolationForest
from sklearn.metrics import classification_report, f1_score
from sklearn.model_selection import cross_val_predict
from sklearn.preprocessing import StandardScaler

from casino_ia.features.build import FEATURES_RIESGO, agregar_scoring_reglas, preparar_matriz_modelo

NIVELES = ["Bajo", "Medio", "Alto"]


@dataclass
class ModeloRiesgo:
    features: list[str] = None
    _scaler: StandardScaler = None
    _iforest: IsolationForest = None
    _clf: GradientBoostingClassifier = None
    metrics_: dict = None

    def __post_init__(self):
        self.features = self.features or FEATURES_RIESGO

    # ------------------------------------------------------------------
    def fit(self, feats: pd.DataFrame) -> "ModeloRiesgo":
        etiquetado = agregar_scoring_reglas(feats)
        y = pd.Categorical(etiquetado["NivelRiesgo"], categories=NIVELES, ordered=True)
        x = preparar_matriz_modelo(feats, self.features)

        self._scaler = StandardScaler().fit(x)
        xs = self._scaler.transform(x)

        self._iforest = IsolationForest(
            n_estimators=200, contamination=0.1, random_state=42
        ).fit(xs)

        self._clf = GradientBoostingClassifier(random_state=42)
        y_cv = cross_val_predict(self._clf, xs, y.codes, cv=5)
        self._clf.fit(xs, y.codes)

        self.metrics_ = {
            "f1_macro_cv": round(float(f1_score(y.codes, y_cv, average="macro")), 3),
            "reporte_cv": classification_report(
                y.codes, y_cv, target_names=NIVELES, output_dict=True, zero_division=0
            ),
            "importancias": dict(
                sorted(
                    zip(self.features, self._clf.feature_importances_.round(3)),
                    key=lambda t: -t[1],
                )
            ),
        }
        return self

    # ------------------------------------------------------------------
    def predict(self, feats: pd.DataFrame) -> pd.DataFrame:
        x = preparar_matriz_modelo(feats, self.features)
        xs = self._scaler.transform(x)
        proba = self._clf.predict_proba(xs)
        codes = proba.argmax(axis=1)
        anomalia = (self._iforest.predict(xs) == -1).astype(int)
        return pd.DataFrame(
            {
                "IdCliente": feats["IdCliente"].to_numpy(),
                "NivelRiesgo": [NIVELES[c] for c in codes],
                "RiesgoScore": (proba * np.array([0.0, 0.5, 1.0])).sum(axis=1).round(3),
                "EsPerfilAtipico": anomalia,
            }
        )

    # ------------------------------------------------------------------
    def save(self, path) -> None:
        joblib.dump(self, path)

    @staticmethod
    def load(path) -> "ModeloRiesgo":
        return joblib.load(path)
