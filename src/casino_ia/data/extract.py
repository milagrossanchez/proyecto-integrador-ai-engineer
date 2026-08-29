"""Extracción de datos.

Estrategia: intentar leer desde SQL Server (fuente oficial). Si no hay conexión,
usar como *fallback* el CSV simulado de `data/raw/` y reconstruir la tabla de
features en pandas (`casino_ia.features.build`).
"""

from __future__ import annotations

import logging

import pandas as pd

from casino_ia import config

log = logging.getLogger(__name__)


def _engine():
    from sqlalchemy import create_engine

    return create_engine(config.DB.sqlalchemy_url(), fast_executemany=True)


def _leer_sql(query: str) -> pd.DataFrame | None:
    try:
        with _engine().connect() as con:
            return pd.read_sql(query, con)
    except Exception as exc:  # noqa: BLE001 - queremos degradar con gracia
        log.warning("Sin conexión a SQL Server (%s). Se usará el CSV.", exc.__class__.__name__)
        return None


def cargar_sesiones(usar_sql: bool = True) -> pd.DataFrame:
    """Devuelve el detalle de sesiones (`FctPlayerSession`)."""
    if usar_sql:
        df = _leer_sql("SELECT * FROM dbo.FctPlayerSession")
        if df is not None:
            log.info("Sesiones leídas de SQL Server: %d filas", len(df))
            return df
    df = pd.read_csv(
        config.CSV_SESIONES,
        parse_dates=["StartTime", "EndTime", "AccountingDate", "PlayerDay"],
    )
    log.info("Sesiones leídas del CSV: %d filas", len(df))
    return df


def cargar_features_cliente(usar_sql: bool = True) -> pd.DataFrame:
    """Devuelve la tabla analítica por cliente (una fila por `IdCliente`).

    Prioriza la vista `vw_FeaturesCliente` de SQL Server; si no está disponible,
    la construye desde el CSV.
    """
    if usar_sql:
        df = _leer_sql("SELECT * FROM dbo.vw_FeaturesCliente")
        if df is not None:
            log.info("Features leídas de vw_FeaturesCliente: %d clientes", len(df))
            return df

    from casino_ia.features.build import construir_features_desde_sesiones

    sesiones = cargar_sesiones(usar_sql=False)
    df = construir_features_desde_sesiones(sesiones)
    log.info("Features reconstruidas desde el CSV: %d clientes", len(df))
    return df


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    feats = cargar_features_cliente()
    salida = config.DATA_INTERIM / "features_cliente.parquet"
    feats.to_parquet(salida, index=False)
    print(f"OK  {len(feats)} clientes  ->  {salida}")
