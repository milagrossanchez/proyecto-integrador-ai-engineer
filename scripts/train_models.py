"""Entrena los modelos de riesgo y de respuesta; guarda artefactos y métricas."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from casino_ia import config
from casino_ia.data import cargar_features_cliente
from casino_ia.models import ModeloRespuesta, ModeloRiesgo


def main() -> None:
    feats = cargar_features_cliente()
    feats.to_parquet(config.DATA_PROCESSED / "abt_cliente.parquet", index=False)

    riesgo = ModeloRiesgo().fit(feats)
    riesgo.save(config.MODELS_STORE / "modelo_riesgo.joblib")

    respuesta = ModeloRespuesta().fit(feats)
    respuesta.save(config.MODELS_STORE / "modelo_respuesta.joblib")

    metrics = {"riesgo": riesgo.metrics_, "respuesta": respuesta.metrics_}
    (config.METRICS / "metrics_modelos.json").write_text(
        json.dumps(metrics, indent=2, ensure_ascii=False, default=str), encoding="utf-8"
    )

    print("== Riesgo ==")
    print("  F1 macro (CV):", riesgo.metrics_["f1_macro_cv"])
    print("  top features:", list(riesgo.metrics_["importancias"])[:4])
    print("== Respuesta ==")
    for k in ("tasa_positivos", "roc_auc", "pr_auc", "brier", "lift_top_decil"):
        print(f"  {k}: {respuesta.metrics_[k]}")
    print(f"\nOK  ->  {config.MODELS_STORE}")


if __name__ == "__main__":
    main()
