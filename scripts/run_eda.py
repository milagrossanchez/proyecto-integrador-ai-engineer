"""EDA rápido de la tabla analítica por cliente. Genera figuras y un resumen."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from casino_ia import config
from casino_ia.data import cargar_features_cliente
from casino_ia.features.build import agregar_scoring_reglas


def main() -> None:
    feats = cargar_features_cliente()
    scored = agregar_scoring_reglas(feats)

    resumen = feats.describe().T
    resumen.to_csv(config.METRICS / "eda_resumen.csv")
    print(f"Clientes: {len(feats)}  |  columnas: {feats.shape[1]}")
    print(scored["NivelRiesgo"].value_counts().rename("clientes"))

    fig, axes = plt.subplots(2, 2, figsize=(11, 8))
    feats["CoinInTotal"].clip(upper=feats["CoinInTotal"].quantile(0.98)).hist(ax=axes[0, 0], bins=40)
    axes[0, 0].set_title("CoinIn total por cliente")
    feats["PctSesionesChasing"].hist(ax=axes[0, 1], bins=30)
    axes[0, 1].set_title("% sesiones con persecución de pérdidas")
    feats["DuracionPromedioMin"].hist(ax=axes[1, 0], bins=40)
    axes[1, 0].set_title("Duración promedio de sesión (min)")
    scored["NivelRiesgo"].value_counts().reindex(["Bajo", "Medio", "Alto"]).plot.bar(ax=axes[1, 1])
    axes[1, 1].set_title("Clientes por nivel de riesgo (baseline)")
    fig.tight_layout()
    fig.savefig(config.FIGURES / "eda_overview.png", dpi=120)
    print(f"OK  ->  {config.FIGURES / 'eda_overview.png'}")


if __name__ == "__main__":
    main()
