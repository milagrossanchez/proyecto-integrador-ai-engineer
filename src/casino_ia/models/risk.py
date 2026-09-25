"""Modelo de nivel de riesgo del cliente.

Dos capas:
  1. No supervisada: `IsolationForest` marca perfiles atipicos por intensidad
     de juego (no necesita etiquetas).
  2. Supervisada: `HistGradientBoostingClassifier`, con busqueda de
     hiperparametros (`RandomizedSearchCV`) y ponderacion de clase
     (`class_weight='balanced'`) porque la clase "Alto" es minoritaria
     (~8% de la cartera). Aprende los niveles Bajo/Medio/Alto a partir de las
     etiquetas debiles (percentiles, ver `features/build.py`) y generaliza a
     clientes nuevos.

En produccion la capa supervisada se re-entrena con etiquetas reales del area
de juego responsable y de rentabilidad del incentivo, en vez de la etiqueta
debil por percentiles.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier, IsolationForest
from sklearn.inspection import permutation_importance
from sklearn.metrics import classification_report, confusion_matrix, f1_score
from sklearn.model_selection import (
    RandomizedSearchCV,
    StratifiedKFold,
    cross_val_predict,
    train_test_split,
)
from sklearn.preprocessing import StandardScaler

from casino_ia.features.build import FEATURES_RIESGO, agregar_scoring_reglas, preparar_matriz_modelo

NIVELES = ["Bajo", "Medio", "Alto"]

# Espacio de busqueda para el ajuste de hiperparametros (RandomizedSearchCV).
_PARAM_DIST = {
    "max_iter": [100, 150, 200, 300],
    "max_depth": [3, 4, 5, 6, None],
    "learning_rate": [0.03, 0.05, 0.08, 0.1, 0.15],
    "l2_regularization": [0.0, 0.1, 0.5, 1.0],
    "min_samples_leaf": [10, 20, 30, 50],
}


@dataclass
class ModeloRiesgo:
    features: list[str] = field(default_factory=lambda: list(FEATURES_RIESGO))
    n_iter_busqueda: int = 25
    _scaler: StandardScaler = None
    _iforest: IsolationForest = None
    _clf: HistGradientBoostingClassifier = None
    metrics_: dict = None

    # ------------------------------------------------------------------
    def fit(self, feats: pd.DataFrame) -> "ModeloRiesgo":
        etiquetado = agregar_scoring_reglas(feats)
        y = pd.Categorical(etiquetado["NivelRiesgo"], categories=NIVELES, ordered=True).codes
        x = preparar_matriz_modelo(feats, self.features)

        self._scaler = StandardScaler().fit(x)
        xs = self._scaler.transform(x)

        # Partición de validación final, separada de la búsqueda de hiperparámetros.
        x_tr, x_te, y_tr, y_te = train_test_split(
            xs, y, test_size=0.2, random_state=42, stratify=y
        )

        cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
        base = HistGradientBoostingClassifier(random_state=42, class_weight="balanced")
        busqueda = RandomizedSearchCV(
            base,
            _PARAM_DIST,
            n_iter=self.n_iter_busqueda,
            scoring="f1_macro",
            cv=cv,
            random_state=42,
            n_jobs=-1,
        )
        busqueda.fit(x_tr, y_tr)
        self._clf = busqueda.best_estimator_

        # Predicciones "out-of-fold" sobre el set de entrenamiento (para un
        # reporte de CV sin optimismo) + evaluación en el holdout final.
        y_cv = cross_val_predict(self._clf, x_tr, y_tr, cv=cv)
        y_pred_te = self._clf.predict(x_te)

        perm = permutation_importance(
            self._clf, x_te, y_te, n_repeats=15, random_state=42, scoring="f1_macro"
        )
        importancias = dict(
            sorted(
                zip(self.features, perm.importances_mean.round(4)),
                key=lambda t: -t[1],
            )
        )

        self._iforest = IsolationForest(
            n_estimators=200, contamination=0.1, random_state=42
        ).fit(xs)

        self.metrics_ = {
            "mejores_hiperparametros": busqueda.best_params_,
            "f1_macro_busqueda_cv": round(float(busqueda.best_score_), 3),
            "f1_macro_cv_train": round(float(f1_score(y_tr, y_cv, average="macro")), 3),
            "f1_macro_holdout": round(float(f1_score(y_te, y_pred_te, average="macro")), 3),
            "reporte_holdout": classification_report(
                y_te, y_pred_te, target_names=NIVELES, output_dict=True, zero_division=0
            ),
            "matriz_confusion_holdout": confusion_matrix(y_te, y_pred_te).tolist(),
            "importancias_permutacion": importancias,
        }
        # Reentrenar con TODOS los datos (mejores hiperparámetros ya elegidos)
        # para que el modelo entregado use la información completa disponible.
        self._clf.fit(xs, y)
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
