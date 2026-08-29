/* ============================================================================
   Proyecto: Sistema de Recomendaci n de M quinas de Juego - Casino Palacio Real
   Archivo : cargar_FctPlayerSession.sql
   Objetivo: crear la base de datos, crear la tabla FctPlayerSession y cargar
             el CSV ficticio (playersession_ficticio_100k.csv) en SQL Server.
   Motor   : SQL Server 2022 (SQLEXPRESS) - SSMS
   ----------------------------------------------------------------------------
   HAY DOS CAMINOS. Elige UNO:
     CAMINO A (sin c digo): asistente "Import Flat File" de SSMS  -> ver NOTA A
     CAMINO B (con script): CREATE TABLE + BULK INSERT             -> pasos 1..4
   ============================================================================ */


/* ----------------------------------------------------------------------------
   PASO 0 - Copiar el CSV a una carpeta que el servicio de SQL Server pueda leer
   ----------------------------------------------------------------------------
   El servicio "SQL Server (SQLEXPRESS)" normalmente NO tiene permiso para leer
   dentro de OneDrive. Copia el archivo a una carpeta simple, por ejemplo:

       C:\Data\playersession_ficticio_100k.csv

   (Crea la carpeta C:\Data y pega ah  el CSV antes de ejecutar el BULK INSERT.)
---------------------------------------------------------------------------- */


/* ----------------------------------------------------------------------------
   PASO 1 - Base de datos
---------------------------------------------------------------------------- */
IF DB_ID('CasinoPalacioReal') IS NULL
    CREATE DATABASE CasinoPalacioReal;
GO

USE CasinoPalacioReal;
GO


/* ----------------------------------------------------------------------------
   PASO 2 - Crear la tabla FctPlayerSession
   Nota: ManualEdit viene como texto 'True'/'False' en el CSV, por eso se carga
         como VARCHAR(5). AbandonedCard viene como 'N'. PointMultiplier viene
         siempre vac o -> NULL.
---------------------------------------------------------------------------- */
IF OBJECT_ID('dbo.FctPlayerSession') IS NOT NULL
    DROP TABLE dbo.FctPlayerSession;
GO

CREATE TABLE dbo.FctPlayerSession
(
    TransID                 BIGINT        NOT NULL,
    Mnum                    INT           NOT NULL,   -- ID de la m quina (ITEM)
    IdSala                  INT           NULL,
    IdCliente               INT           NOT NULL,   -- ID del jugador (USUARIO)
    StartTime               DATETIME2(0)  NULL,
    EndTime                 DATETIME2(0)  NULL,
    TimePlayed              INT           NULL,        -- segundos jugados (SE AL)
    Location                VARCHAR(20)   NULL,
    CoinIn                  DECIMAL(18,2) NULL,        -- dinero apostado (SE AL)
    CoinOut                 DECIMAL(18,2) NULL,
    Games                   INT           NULL,        -- nro de partidas (SE AL)
    Jackpot                 DECIMAL(18,2) NULL,
    BillsIn                 DECIMAL(18,2) NULL,
    AverageBet              DECIMAL(18,4) NULL,
    Win                     DECIMAL(18,2) NULL,
    TheoWin                 DECIMAL(18,4) NULL,
    CompEarned              DECIMAL(18,4) NULL,
    IdNegocio               INT           NULL,
    TripNumber              INT           NULL,
    XC_Used                 DECIMAL(18,2) NULL,
    XC_RPEarned             DECIMAL(18,2) NULL,
    XC_PPEarned             DECIMAL(18,2) NULL,
    XC_BSEarned             DECIMAL(18,2) NULL,
    PointsEarned            INT           NULL,
    RP_PointAdjustment      INT           NULL,
    RP_EarnedDay            DECIMAL(18,2) NULL,
    PP_PoolBalance          DECIMAL(18,2) NULL,
    PP_LuckyNumber          DECIMAL(18,2) NULL,
    PP_TotalWon             DECIMAL(18,2) NULL,
    PTP_SPUsed              INT           NULL,
    PTP_SPUsedCents         DECIMAL(18,2) NULL,
    AbandonedCard           CHAR(1)       NULL,
    AccountingDate          DATE          NULL,
    PlayerDay               DATE          NULL,
    PointMultiplier         DECIMAL(18,2) NULL,
    PointsMultiplied        INT           NULL,
    PlayerMod               INT           NULL,
    XC_PTPEarned            DECIMAL(18,2) NULL,
    RankedPointMultiplier   INT           NULL,
    SessionTypeID           INT           NULL,
    ManualEdit              VARCHAR(5)    NULL,
    IdEmpresa               INT           NULL,
    IdMoneda                INT           NULL,
    IdCalendario            INT           NULL,
    Hora                    INT           NULL,
    CONSTRAINT PK_FctPlayerSession PRIMARY KEY (TransID)
);
GO


/* ----------------------------------------------------------------------------
   PASO 3 - Cargar el CSV con BULK INSERT
   El CSV es UTF-8, con encabezado en la fila 1 y salto de l nea tipo Unix (LF).
   Ajusta la ruta de DATA_SOURCE / FROM a donde copiaste el archivo (PASO 0).
---------------------------------------------------------------------------- */
BULK INSERT dbo.FctPlayerSession
FROM 'C:\Data\playersession_ficticio_100k.csv'
WITH (
    FORMAT        = 'CSV',
    FIRSTROW      = 2,            -- salta el encabezado
    FIELDTERMINATOR = ',',
    ROWTERMINATOR = '0x0a',      -- LF (si diera error, probar '\n' o '0x0d0a')
    CODEPAGE      = '65001',     -- UTF-8
    TABLOCK,
    MAXERRORS     = 50
);
GO


/* ----------------------------------------------------------------------------
   PASO 4 - Verificaciones r pidas
---------------------------------------------------------------------------- */
SELECT COUNT(*) AS filas FROM dbo.FctPlayerSession;                       -- esperado: 100000
SELECT COUNT(DISTINCT IdCliente) AS jugadores,
       COUNT(DISTINCT Mnum)      AS maquinas,
       MIN(StartTime) AS desde, MAX(StartTime) AS hasta
FROM dbo.FctPlayerSession;
SELECT TOP (10) * FROM dbo.FctPlayerSession ORDER BY TransID;
GO


/* ============================================================================
   NOTA A - CAMINO SIN C DIGO (asistente de SSMS)
   ----------------------------------------------------------------------------
   1. En SSMS: bot n derecho sobre la base CasinoPalacioReal
      -> Tasks / Tareas -> Import Flat File... / Importar archivo plano...
   2. Seleccionar playersession_ficticio_100k.csv
   3. Nombre de la tabla: FctPlayerSession  (esquema dbo)
   4. En "Modify Columns" revisar tipos:
        - TransID     -> bigint, Primary Key, NOT NULL
        - StartTime / EndTime -> datetime2
        - CoinIn, CoinOut, Win, TheoWin, AverageBet -> decimal/float
        - ManualEdit  -> dejar como nvarchar(50) (trae 'True'/'False')
        - PointMultiplier -> permitir NULL
   5. Finish. El asistente crea la tabla y carga las 100 000 filas.
   ============================================================================ */


/* ============================================================================
   PASO 5 (opcional) - Matriz de interacciones para el recomendador
   Agrega las sesiones a nivel jugador x m quina y calcula una se al de
   preferencia impl cita. Esta vista es el insumo del modelo.
   ============================================================================ */
IF OBJECT_ID('dbo.vw_InteraccionJugadorMaquina') IS NOT NULL
    DROP VIEW dbo.vw_InteraccionJugadorMaquina;
GO
CREATE VIEW dbo.vw_InteraccionJugadorMaquina AS
SELECT
    IdCliente,
    Mnum,
    COUNT(*)                       AS n_sesiones,
    SUM(TimePlayed)                AS seg_jugados,
    SUM(Games)                     AS partidas,
    SUM(CoinIn)                    AS coinin_total,
    AVG(AverageBet)                AS apuesta_media,
    MAX(StartTime)                 AS ultima_sesion,
    /* se al impl cita simple: combina intensidad y frecuencia (log para amortiguar colas) */
    LOG(1 + SUM(TimePlayed))
      + LOG(1 + SUM(Games))
      + 0.5 * LOG(1 + SUM(CoinIn)) AS score_preferencia
FROM dbo.FctPlayerSession
GROUP BY IdCliente, Mnum;
GO

-- Ejemplo: top 10 m quinas "preferidas" del jugador 900094
SELECT TOP (10) *
FROM dbo.vw_InteraccionJugadorMaquina
WHERE IdCliente = 900094
ORDER BY score_preferencia DESC;
GO

-- Baseline de popularidad: m quinas m s jugadas del casino
SELECT TOP (20) Mnum,
       COUNT(DISTINCT IdCliente) AS jugadores_distintos,
       COUNT(*)                  AS sesiones
FROM dbo.FctPlayerSession
GROUP BY Mnum
ORDER BY sesiones DESC;
GO
