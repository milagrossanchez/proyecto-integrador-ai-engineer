"""Entrena los modelos de riesgo y de respuesta; guarda artefactos y métricas."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from casino_ia import config
from casino_ia.data import cargar_features_cliente
from casino_ia.models import ModeloRespuesta, ModeloRespuestaNBO, ModeloRiesgo
from casino_ia.models.response import simular_historico_campanas


def main() -> None:
    feats = cargar_features_cliente()
    feats.to_parquet(config.DATA_PROCESSED / "abt_cliente.parquet", index=False)

    riesgo = ModeloRiesgo().fit(feats)
    riesgo.save(config.MODELS_STORE / "modelo_riesgo.joblib")

    respuesta = ModeloRespuesta().fit(feats)
    respuesta.save(config.MODELS_STORE / "modelo_respuesta.joblib")

    pred_riesgo = riesgo.predict(feats)
    pred_base = respuesta.predict_proba(feats)
    historico_nbo = simular_historico_campanas(feats, pred_riesgo, pred_base)
    historico_nbo.to_parquet(
        config.DATA_PROCESSED / "historico_campanas_simulado.parquet", index=False
    )
    respuesta_nbo = ModeloRespuestaNBO().fit(historico_nbo)
    respuesta_nbo.save(config.MODELS_STORE / "modelo_respuesta_nbo.joblib")

    metrics = {
        "riesgo": riesgo.metrics_,
        "respuesta_v1": respuesta.metrics_,
        "respuesta_v2_nbo": respuesta_nbo.metrics_,
        "simulacion_nbo": {
            "naturaleza": "semi_sintetica; no representa campañas observadas",
            "semilla": 42,
            "campanas": int(historico_nbo["IdCampana"].nunique()),
            "exposiciones": int(len(historico_nbo)),
            "clientes": int(historico_nbo["IdCliente"].nunique()),
            "resultado_por_tipo": historico_nbo.groupby("TipoRecompensa")["Respondio"]
            .agg(exposiciones="size", respuestas="sum", tasa_respuesta="mean")
            .round(4)
            .to_dict("index"),
        },
    }
    (config.METRICS / "metrics_modelos.json").write_text(
        json.dumps(metrics, indent=2, ensure_ascii=False, default=str), encoding="utf-8"
    )

    print("== Riesgo ==")
    print("  mejores hiperparametros:", riesgo.metrics_["mejores_hiperparametros"])
    print("  F1 macro (busqueda CV):", riesgo.metrics_["f1_macro_busqueda_cv"])
    print("  F1 macro (holdout):    ", riesgo.metrics_["f1_macro_holdout"])
    print("  top features (permutation importance):", list(riesgo.metrics_["importancias_permutacion"])[:4])
    print("== Respuesta V1 (baseline, P(respuesta) unica) ==")
    print("  mejores hiperparametros:", respuesta.metrics_["mejores_hiperparametros"])
    for k in ("tasa_positivos", "pr_auc_busqueda_cv", "roc_auc", "pr_auc", "brier",
              "roc_auc_baseline_logistica", "pr_auc_baseline_logistica", "lift_top_decil"):
        print(f"  {k}: {respuesta.metrics_[k]}")
    print("== Respuesta V2 NBO (siguiente mejor oferta, semi-sintético) ==")
    for k, valor in respuesta_nbo.metrics_["respuesta"].items():
        print(f"  {k}: {valor}")
    print("  valor incremental (MAE / R2):", respuesta_nbo.metrics_["valor_incremental"])
    print(f"\nOK  ->  {config.MODELS_STORE}")


if __name__ == "__main__":
    main()
