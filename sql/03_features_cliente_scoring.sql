/* ============================================================================
   Proyecto : Identificacion de riesgos y optimizacion de recompensas (ML + IA gen)
              Casino Palacio Real
   Archivo  : features_cliente_scoring.sql
   Requisito: ejecutar antes
                1) cargar_FctPlayerSession.sql
                2) crear_dimensiones_y_vista.sql

   Que hace:
     - vw_FeaturesCliente : una fila por cliente con las variables (features)
       para los modelos de RIESGO y de PROBABILIDAD DE RESPUESTA, calculadas
       desde el historico de sesiones (FctPlayerSession).
     - vw_ClientesScoring : agrega un score y un nivel (Bajo/Medio/Alto) de
       riesgo y un decil de propension, mas una regla base de asignacion de
       recompensa. Sirve como BASELINE y como set de etiquetas debiles para
       arrancar el modelado.

   NOTA: los niveles son PROXY calculados por reglas/percentiles sobre datos
         ficticios. En produccion se reemplazan por (a) historico de campanas
         para la respuesta y (b) marcas de juego responsable para el riesgo.
   ============================================================================ */

USE CasinoPalacioReal;
GO
SET NOCOUNT ON;
GO

IF OBJECT_ID('dbo.vw_ClientesScoring')  IS NOT NULL DROP VIEW dbo.vw_ClientesScoring;
IF OBJECT_ID('dbo.vw_FeaturesCliente')  IS NOT NULL DROP VIEW dbo.vw_FeaturesCliente;
GO


/* ----------------------------------------------------------------------------
   vw_FeaturesCliente
---------------------------------------------------------------------------- */
CREATE VIEW dbo.vw_FeaturesCliente AS
WITH corte AS (
    SELECT
        MAX(CAST(StartTime AS date))                        AS FechaCorte,
        DATEADD(day, -7, MAX(CAST(StartTime AS date)))      AS Fecha7
    FROM dbo.FctPlayerSession
),
ses1 AS (   -- sesion + valores de la sesion anterior del mismo cliente
    SELECT
        f.IdCliente,
        CAST(f.StartTime AS date)   AS Dia,
        f.StartTime,
        f.TimePlayed,
        f.CoinIn, f.Games, f.Win, f.TheoWin, f.AverageBet,
        f.CompEarned, f.PointsEarned, f.Hora, f.IdSala, f.TripNumber,
        LAG(f.Win)    OVER (PARTITION BY f.IdCliente ORDER BY f.StartTime, f.TransID) AS WinPrev,
        LAG(f.CoinIn) OVER (PARTITION BY f.IdCliente ORDER BY f.StartTime, f.TransID) AS CoinInPrev
    FROM dbo.FctPlayerSession f
),
ses2 AS (   -- flags a nivel sesion (aqui SI se pueden usar las columnas de corte)
    SELECT
        s.*,
        c.FechaCorte,
        s.TimePlayed / 60.0                                                       AS Minutos,
        CASE WHEN s.TimePlayed / 60.0 > 120 THEN 1 ELSE 0 END                     AS FlagLarga,
        CASE WHEN s.Hora < 6 THEN 1 ELSE 0 END                                    AS FlagMadrugada,
        CASE WHEN s.Win < 0 THEN -s.Win ELSE 0 END                                AS Perdida,
        CASE WHEN s.WinPrev < 0 AND s.CoinIn > s.CoinInPrev * 1.2 THEN 1 ELSE 0 END AS FlagChasing,
        CASE WHEN s.Dia >= c.Fecha7 THEN 1 ELSE 0 END                             AS FlagU7
    FROM ses1 s
    CROSS JOIN corte c
),
agg AS (
    SELECT
        IdCliente,
        COUNT(*)                                              AS NroSesiones,
        COUNT(DISTINCT Dia)                                   AS DiasActivos,
        MAX(TripNumber)                                       AS NroVisitas,
        MIN(StartTime)                                        AS PrimeraSesion,
        MAX(StartTime)                                        AS UltimaSesion,
        DATEDIFF(day, MAX(Dia), MIN(FechaCorte))              AS DiasDesdeUltimaSesion,
        SUM(CoinIn)                                           AS CoinInTotal,
        AVG(CoinIn)                                           AS CoinInProm,
        SUM(TheoWin)                                          AS ValorTeoricoCasa,
        SUM(Win)                                              AS ResultadoClienteTotal,
        SUM(Perdida)                                          AS PerdidasAcum,
        SUM(TimePlayed) / 3600.0                              AS HorasJugadas,
        AVG(Minutos)                                          AS DuracionPromMin,
        MAX(Minutos)                                          AS DuracionMaxMin,
        AVG(CAST(FlagLarga AS float))                         AS PctSesionesLargas,
        SUM(CoinIn) / NULLIF(SUM(TimePlayed) / 3600.0, 0)     AS CoinInPorHora,
        AVG(AverageBet)                                       AS ApuestaMediaProm,
        MAX(AverageBet)                                       AS ApuestaMax,
        AVG(CAST(FlagMadrugada AS float))                     AS PctJuegoMadrugada,
        STDEV(Win)                                            AS VolatilidadResultado,
        AVG(CAST(FlagChasing AS float))                       AS PctChasing,
        SUM(CompEarned)                                       AS CompsAcum,
        SUM(PointsEarned)                                     AS PuntosAcum,
        COUNT(DISTINCT IdSala)                                AS NroSalas,
        SUM(CASE WHEN FlagU7 = 1 THEN CoinIn ELSE 0 END)      AS CoinIn_U7,
        SUM(CASE WHEN FlagU7 = 0 THEN CoinIn ELSE 0 END)      AS CoinIn_Prev,
        SUM(FlagU7)                                           AS Ses_U7,
        SUM(1 - FlagU7)                                       AS Ses_Prev
    FROM ses2
    GROUP BY IdCliente
)
SELECT
    c.IdCliente,
    c.CodigoCliente,
    c.NombreCompleto,
    c.Segmento,
    c.Ciudad,
    c.FechaAlta,
    DATEDIFF(day, c.FechaAlta, a.UltimaSesion)             AS AntiguedadDias,
    -- ---- actividad / frecuencia ----
    a.NroSesiones,
    a.DiasActivos,
    a.NroVisitas,
    a.DiasDesdeUltimaSesion,
    -- ---- valor / monetario ----
    CAST(a.CoinInTotal           AS decimal(18,2))         AS CoinInTotal,
    CAST(a.CoinInProm            AS decimal(18,2))         AS CoinInPromedioSesion,
    CAST(a.ValorTeoricoCasa      AS decimal(18,2))         AS ValorTeoricoCasa,
    CAST(a.ResultadoClienteTotal AS decimal(18,2))         AS ResultadoClienteTotal,
    CAST(a.PerdidasAcum          AS decimal(18,2))         AS PerdidasAcumuladas,
    CAST(a.CompsAcum             AS decimal(18,2))         AS CompsAcumulados,
    a.PuntosAcum                                           AS PuntosAcumulados,
    -- ---- intensidad / senales de riesgo ----
    CAST(a.HorasJugadas          AS decimal(12,1))         AS HorasJugadas,
    CAST(a.DuracionPromMin       AS decimal(10,1))         AS DuracionPromedioMin,
    CAST(a.DuracionMaxMin        AS decimal(10,1))         AS DuracionMaximaMin,
    CAST(a.PctSesionesLargas     AS decimal(5,3))          AS PctSesionesLargas,
    CAST(a.CoinInPorHora         AS decimal(18,2))         AS CoinInPorHora,
    CAST(a.ApuestaMediaProm      AS decimal(18,2))         AS ApuestaMediaPromedio,
    CAST(a.ApuestaMax            AS decimal(18,2))         AS ApuestaMaxima,
    CAST(a.PctJuegoMadrugada     AS decimal(5,3))          AS PctJuegoMadrugada,
    CAST(a.VolatilidadResultado  AS decimal(18,2))         AS VolatilidadResultado,
    CAST(a.PctChasing            AS decimal(5,3))          AS PctSesionesChasing,
    a.NroSalas,
    -- ---- tendencia (ultimos 7 dias vs. previo) ----
    CAST(a.CoinIn_U7             AS decimal(18,2))         AS CoinIn_Ultimos7d,
    CAST(a.CoinIn_Prev           AS decimal(18,2))         AS CoinIn_Previo,
    CASE WHEN a.CoinIn_Prev > 0
         THEN CAST(a.CoinIn_U7 / a.CoinIn_Prev AS decimal(10,3)) END  AS RatioTendenciaCoinIn,
    a.Ses_U7                                               AS Sesiones_Ultimos7d,
    a.Ses_Prev                                             AS Sesiones_Previo
FROM dbo.DimCliente c
JOIN agg a ON a.IdCliente = c.IdCliente;
GO


/* ----------------------------------------------------------------------------
   vw_ClientesScoring
   - RiesgoScore  : promedio de percentiles de 6 senales de intensidad/riesgo
   - PropScore    : combinacion de recencia, tendencia y uso de beneficios
   - NivelRiesgo  : piramide de RiesgoScore -> ~70% Bajo / ~22% Medio / ~8% Alto
   - DecilPropension : deciles de PropScore (10 = mas propenso a responder)
   - AccionRecomendada : regla base para la asignacion de recompensa
---------------------------------------------------------------------------- */
CREATE VIEW dbo.vw_ClientesScoring AS
WITH s AS (
    SELECT
        f.*,
        ( PERCENT_RANK() OVER (ORDER BY f.PctSesionesChasing)
        + PERCENT_RANK() OVER (ORDER BY f.PctSesionesLargas)
        + PERCENT_RANK() OVER (ORDER BY f.CoinInPorHora)
        + PERCENT_RANK() OVER (ORDER BY f.DuracionMaximaMin)
        + PERCENT_RANK() OVER (ORDER BY f.VolatilidadResultado)
        + PERCENT_RANK() OVER (ORDER BY f.ApuestaMaxima)
        ) / 6.0                                                        AS RiesgoScore,
        ( 0.40 * PERCENT_RANK() OVER (ORDER BY f.DiasDesdeUltimaSesion DESC)
        + 0.35 * PERCENT_RANK() OVER (ORDER BY ISNULL(f.RatioTendenciaCoinIn, 0))
        + 0.25 * PERCENT_RANK() OVER (ORDER BY f.CompsAcumulados)
        )                                                             AS PropScore
    FROM dbo.vw_FeaturesCliente f
)
SELECT
    s.IdCliente,
    s.CodigoCliente,
    s.NombreCompleto,
    s.Segmento,
    s.Ciudad,
    s.NroSesiones,
    s.DiasDesdeUltimaSesion,
    s.CoinInTotal,
    s.ValorTeoricoCasa,
    s.CompsAcumulados,
    s.PctSesionesChasing,
    s.PctSesionesLargas,
    s.PctJuegoMadrugada,
    CAST(s.RiesgoScore AS decimal(5,3))                                AS RiesgoScore,
    -- Piramide de riesgo realista: ~70% Bajo, ~22% Medio, ~8% Alto
    CASE
        WHEN PERCENT_RANK() OVER (ORDER BY s.RiesgoScore) >= 0.92 THEN 'Alto'
        WHEN PERCENT_RANK() OVER (ORDER BY s.RiesgoScore) >= 0.70 THEN 'Medio'
        ELSE 'Bajo'
    END                                                               AS NivelRiesgo,
    CAST(s.PropScore AS decimal(5,3))                                  AS PropensionScore,
    NTILE(10) OVER (ORDER BY s.PropScore)                              AS DecilPropension,
    CASE
        WHEN PERCENT_RANK() OVER (ORDER BY s.RiesgoScore) >= 0.92      THEN 'No incentivar - derivar a juego responsable'
        WHEN NTILE(10) OVER (ORDER BY s.PropScore)  >= 8              THEN 'Recompensa alta (bono + beneficio)'
        WHEN NTILE(10) OVER (ORDER BY s.PropScore)  >= 5              THEN 'Recompensa media (promocion dirigida)'
        ELSE 'Recompensa baja o nutricion de marca'
    END                                                               AS AccionRecomendada
FROM s;
GO


/* ----------------------------------------------------------------------------
   Verificaciones / ejemplos
---------------------------------------------------------------------------- */
SELECT COUNT(*) AS clientes_en_features FROM dbo.vw_FeaturesCliente;   -- esperado: 888

SELECT NivelRiesgo, COUNT(*) AS clientes,
       CAST(AVG(CoinInTotal) AS decimal(18,2))   AS coinin_prom,
       CAST(AVG(PctSesionesChasing) AS decimal(5,3)) AS chasing_prom
FROM dbo.vw_ClientesScoring
GROUP BY NivelRiesgo
ORDER BY clientes DESC;

SELECT AccionRecomendada, COUNT(*) AS clientes
FROM dbo.vw_ClientesScoring
GROUP BY AccionRecomendada
ORDER BY clientes DESC;

SELECT TOP (25) *
FROM dbo.vw_ClientesScoring
ORDER BY PropensionScore DESC;
GO

/* -- Opcional: materializar la tabla analitica para entrenar los modelos en Python
   SELECT * INTO dbo.abt_cliente FROM dbo.vw_FeaturesCliente;
   -- luego: bcp / Export o leer con pandas.read_sql
*/
