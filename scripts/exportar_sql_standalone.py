"""Exporta TODA la base de datos (esquema + datos) como un único script .sql
autocontenido: sin CSV, sin BULK INSERT, sin permisos de carpeta. Se corre tal
cual en SSMS / sqlcmd sobre una instancia vacia y reconstruye todo con
sentencias CREATE TABLE + INSERT (en lotes) + FKs + vistas.

Uso:
    python scripts/exportar_sql_standalone.py
Salida:
    entregables/CasinoPalacioReal_standalone.sql   (no se versiona en git:
    es datos crudos re-empaquetados, se comparte por Drive/OneDrive igual
    que el .bak; ver entregables/LEEME_restaurar_base.md)
"""

from __future__ import annotations

import datetime
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import numpy as np
import pandas as pd
from sqlalchemy import create_engine, text

from casino_ia.config import DB, ROOT

OUT = ROOT / "entregables" / "CasinoPalacioReal_standalone.sql"
LOTE = 200  # filas por sentencia INSERT (equilibrio legibilidad / velocidad)

# Orden de carga que respeta las foreign keys.
TABLAS = [
    "DimEmpresa", "DimSala", "DimMoneda", "DimNegocio", "DimTipoSesion",
    "DimCalendario", "DimUbicacion", "DimCliente", "DimMaquina", "FctPlayerSession",
]

DDL_TABLAS = r"""
CREATE TABLE dbo.DimEmpresa (
    IdEmpresa INT NOT NULL PRIMARY KEY, RazonSocial VARCHAR(80) NOT NULL,
    RUC CHAR(11) NOT NULL, TipoSede VARCHAR(30) NOT NULL);

CREATE TABLE dbo.DimSala (
    IdSala INT NOT NULL PRIMARY KEY, NombreSala VARCHAR(50) NOT NULL,
    IdEmpresa INT NOT NULL REFERENCES dbo.DimEmpresa(IdEmpresa),
    Piso INT NOT NULL, NroMaquinasAprox INT NULL);

CREATE TABLE dbo.DimMoneda (
    IdMoneda INT NOT NULL PRIMARY KEY, CodigoISO CHAR(3) NOT NULL,
    NombreMoneda VARCHAR(40) NOT NULL, Simbolo VARCHAR(5) NOT NULL);

CREATE TABLE dbo.DimNegocio (
    IdNegocio INT NOT NULL PRIMARY KEY, NombreNegocio VARCHAR(50) NOT NULL);

CREATE TABLE dbo.DimTipoSesion (
    SessionTypeID INT NOT NULL PRIMARY KEY, NombreTipoSesion VARCHAR(40) NOT NULL);

CREATE TABLE dbo.DimCalendario (
    IdCalendario INT NOT NULL PRIMARY KEY, Fecha DATE NOT NULL, Anio INT NOT NULL,
    NumeroMes INT NOT NULL, NombreMes VARCHAR(20) NOT NULL, DiaDelMes INT NOT NULL,
    NombreDia VARCHAR(20) NOT NULL, EsFinDeSemana BIT NOT NULL, NumeroSemana INT NOT NULL);

CREATE TABLE dbo.DimUbicacion (
    Location VARCHAR(20) NOT NULL PRIMARY KEY, Zona CHAR(1) NOT NULL,
    NumeroPosicion INT NULL, Descripcion VARCHAR(60) NOT NULL);

CREATE TABLE dbo.DimCliente (
    IdCliente INT NOT NULL PRIMARY KEY, CodigoCliente VARCHAR(15) NOT NULL,
    NombreCompleto VARCHAR(80) NOT NULL, Segmento VARCHAR(15) NOT NULL,
    Ciudad VARCHAR(30) NOT NULL, FechaAlta DATE NOT NULL, Activo BIT NOT NULL);

CREATE TABLE dbo.DimMaquina (
    Mnum INT NOT NULL PRIMARY KEY, CodigoMaquina VARCHAR(15) NOT NULL,
    TipoJuego VARCHAR(30) NOT NULL, Fabricante VARCHAR(30) NOT NULL, Modelo VARCHAR(40) NOT NULL,
    Denominacion DECIMAL(6,2) NOT NULL, FechaInstalacion DATE NOT NULL,
    SalaPredominante INT NULL REFERENCES dbo.DimSala(IdSala));

CREATE TABLE dbo.FctPlayerSession (
    TransID BIGINT NOT NULL PRIMARY KEY, Mnum INT NOT NULL, IdSala INT NULL,
    IdCliente INT NOT NULL, StartTime DATETIME2(0) NULL, EndTime DATETIME2(0) NULL,
    TimePlayed INT NULL, Location VARCHAR(20) NULL, CoinIn DECIMAL(18,2) NULL,
    CoinOut DECIMAL(18,2) NULL, Games INT NULL, Jackpot DECIMAL(18,2) NULL,
    BillsIn DECIMAL(18,2) NULL, AverageBet DECIMAL(18,4) NULL, Win DECIMAL(18,2) NULL,
    TheoWin DECIMAL(18,4) NULL, CompEarned DECIMAL(18,4) NULL, IdNegocio INT NULL,
    TripNumber INT NULL, XC_Used DECIMAL(18,2) NULL, XC_RPEarned DECIMAL(18,2) NULL,
    XC_PPEarned DECIMAL(18,2) NULL, XC_BSEarned DECIMAL(18,2) NULL, PointsEarned INT NULL,
    RP_PointAdjustment INT NULL, RP_EarnedDay DECIMAL(18,2) NULL, PP_PoolBalance DECIMAL(18,2) NULL,
    PP_LuckyNumber DECIMAL(18,2) NULL, PP_TotalWon DECIMAL(18,2) NULL, PTP_SPUsed INT NULL,
    PTP_SPUsedCents DECIMAL(18,2) NULL, AbandonedCard CHAR(1) NULL, AccountingDate DATE NULL,
    PlayerDay DATE NULL, PointMultiplier DECIMAL(18,2) NULL, PointsMultiplied INT NULL,
    PlayerMod INT NULL, XC_PTPEarned DECIMAL(18,2) NULL, RankedPointMultiplier INT NULL,
    SessionTypeID INT NULL, ManualEdit VARCHAR(5) NULL, IdEmpresa INT NULL, IdMoneda INT NULL,
    IdCalendario INT NULL, Hora INT NULL);
"""

DDL_FKS = r"""
ALTER TABLE dbo.FctPlayerSession ADD CONSTRAINT FK_Fps_Cliente     FOREIGN KEY (IdCliente)     REFERENCES dbo.DimCliente(IdCliente);
ALTER TABLE dbo.FctPlayerSession ADD CONSTRAINT FK_Fps_Maquina     FOREIGN KEY (Mnum)          REFERENCES dbo.DimMaquina(Mnum);
ALTER TABLE dbo.FctPlayerSession ADD CONSTRAINT FK_Fps_Sala        FOREIGN KEY (IdSala)        REFERENCES dbo.DimSala(IdSala);
ALTER TABLE dbo.FctPlayerSession ADD CONSTRAINT FK_Fps_Empresa     FOREIGN KEY (IdEmpresa)     REFERENCES dbo.DimEmpresa(IdEmpresa);
ALTER TABLE dbo.FctPlayerSession ADD CONSTRAINT FK_Fps_Ubicacion   FOREIGN KEY (Location)      REFERENCES dbo.DimUbicacion(Location);
ALTER TABLE dbo.FctPlayerSession ADD CONSTRAINT FK_Fps_Moneda      FOREIGN KEY (IdMoneda)      REFERENCES dbo.DimMoneda(IdMoneda);
ALTER TABLE dbo.FctPlayerSession ADD CONSTRAINT FK_Fps_Negocio     FOREIGN KEY (IdNegocio)     REFERENCES dbo.DimNegocio(IdNegocio);
ALTER TABLE dbo.FctPlayerSession ADD CONSTRAINT FK_Fps_TipoSesion  FOREIGN KEY (SessionTypeID) REFERENCES dbo.DimTipoSesion(SessionTypeID);
ALTER TABLE dbo.FctPlayerSession ADD CONSTRAINT FK_Fps_Calendario  FOREIGN KEY (IdCalendario)  REFERENCES dbo.DimCalendario(IdCalendario);
CREATE INDEX IX_Fps_IdCliente    ON dbo.FctPlayerSession(IdCliente);
CREATE INDEX IX_Fps_Mnum         ON dbo.FctPlayerSession(Mnum);
CREATE INDEX IX_Fps_IdCalendario ON dbo.FctPlayerSession(IdCalendario);
"""

# columnas que hay que citar como fecha / fecha-hora / bit (el resto se infiere del valor Python)
COLS_DATE = {
    ("DimCalendario", "Fecha"), ("DimCliente", "FechaAlta"), ("DimMaquina", "FechaInstalacion"),
    ("FctPlayerSession", "AccountingDate"), ("FctPlayerSession", "PlayerDay"),
}
COLS_DATETIME = {("FctPlayerSession", "StartTime"), ("FctPlayerSession", "EndTime")}
COLS_BIT = {("DimCalendario", "EsFinDeSemana"), ("DimCliente", "Activo")}


def _lit(tabla: str, col: str, v) -> str:
    if v is None or (isinstance(v, float) and np.isnan(v)) or v is pd.NaT:
        return "NULL"
    key = (tabla, col)
    if key in COLS_BIT:
        return "1" if v else "0"
    if key in COLS_DATE:
        d = v.date() if hasattr(v, "date") else v
        return f"'{d.isoformat()}'"
    if key in COLS_DATETIME:
        return f"'{pd.Timestamp(v).strftime('%Y-%m-%d %H:%M:%S')}'"
    if isinstance(v, (bool, np.bool_)):
        return "1" if v else "0"
    if isinstance(v, (int, np.integer)):
        return str(int(v))
    if isinstance(v, (float, np.floating)):
        return format(float(v), ".6f").rstrip("0").rstrip(".") or "0"
    s = str(v).replace("'", "''")
    return f"N'{s}'"


def _insert_batches(tabla: str, df: pd.DataFrame) -> str:
    if df.empty:
        return f"-- {tabla}: sin filas\n"
    cols = list(df.columns)
    col_list = ", ".join(f"[{c}]" for c in cols)
    out = []
    for i in range(0, len(df), LOTE):
        lote = df.iloc[i : i + LOTE]
        filas = []
        for _, row in lote.iterrows():
            vals = ", ".join(_lit(tabla, c, row[c]) for c in cols)
            filas.append(f"({vals})")
        out.append(f"INSERT INTO dbo.[{tabla}] ({col_list}) VALUES\n" + ",\n".join(filas) + ";")
    return "\n".join(out) + "\n"


def main() -> None:
    engine = create_engine(DB.sqlalchemy_url())
    partes = [
        "/* ============================================================================\n"
        "   CasinoPalacioReal - script standalone (esquema + datos completos)\n"
        f"   Generado: {datetime.datetime.now():%Y-%m-%d %H:%M}\n"
        "   No requiere CSV ni BULK INSERT: se corre tal cual en una base nueva.\n"
        "   ============================================================================ */\n",
        "IF DB_ID('CasinoPalacioReal') IS NULL CREATE DATABASE CasinoPalacioReal;\nGO\nUSE CasinoPalacioReal;\nGO\n",
        "-- ---------- 1. Esquema ----------\n" + DDL_TABLAS + "GO\n",
    ]

    with engine.connect() as con:
        for i, t in enumerate(TABLAS, 1):
            df = pd.read_sql(text(f"SELECT * FROM dbo.[{t}]"), con)
            print(f"  [{i}/{len(TABLAS)}] {t}: {len(df)} filas")
            partes.append(f"-- ---------- Datos: {t} ({len(df)} filas) ----------\n")
            partes.append(_insert_batches(t, df))
            partes.append("GO\n")

    partes.append("-- ---------- 2. Claves foraneas e indices ----------\n" + DDL_FKS + "GO\n")

    # Vistas: se reutiliza el texto ya versionado en 02/03 para no duplicar logica.
    sql_dir = ROOT / "sql"
    for script, marcador in [
        ("02_crear_dimensiones_y_vista.sql", "/* ----------------------------------------------------------------------------\n   11. Vistas de consumo"),
        ("03_features_cliente_scoring.sql", "CREATE VIEW dbo.vw_FeaturesCliente"),
    ]:
        texto = (sql_dir / script).read_text(encoding="utf-8")
        inicio = texto.index(marcador)
        fin = texto.index("/* ----------------------------------------------------------------------------\n   12" if "02_" in script else "/* ----------------------------------------------------------------------------\n   Verificaciones", inicio)
        partes.append(f"-- ---------- Vistas de {script} ----------\n" + texto[inicio:fin] + "\nGO\n")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(partes), encoding="utf-8")
    print(f"\nOK -> {OUT}  ({OUT.stat().st_size / 1024 / 1024:.1f} MB)")


if __name__ == "__main__":
    main()
