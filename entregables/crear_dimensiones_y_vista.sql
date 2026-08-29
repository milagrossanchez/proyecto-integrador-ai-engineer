/* ============================================================================
   Proyecto : Sistema de Recomendacion - Casino Palacio Real
   Archivo  : crear_dimensiones_y_vista.sql
   Requisito: primero ejecutar cargar_FctPlayerSession.sql
              (base CasinoPalacioReal + tabla dbo.FctPlayerSession cargada)

   Que hace:
     1. Crea las tablas de dimension relacionadas con los IDs de FctPlayerSession
        (cliente, maquina, sala, empresa, ubicacion, moneda, negocio, tipo de
         sesion, calendario).
     2. Las llena a partir de los datos que ya estan en FctPlayerSession.
        Los atributos descriptivos (nombres, ciudades, fabricantes, etc.) son
        ficticios pero DETERMINISTAS: el script se puede volver a correr y da
        siempre el mismo resultado.
     3. Agrega claves foraneas de FctPlayerSession hacia cada dimension.
     4. Crea vistas de consumo:
          vw_SesionesDetalle   -> cada sesion con todos sus datos relacionados
          vw_ResumenCliente    -> una fila por cliente
          vw_ResumenMaquina    -> una fila por maquina
          vw_ResumenDiario     -> una fila por dia

   Ejecutar en SSMS sobre la base CasinoPalacioReal. Es idempotente.
   ============================================================================ */

USE CasinoPalacioReal;
GO
SET NOCOUNT ON;
GO

/* ----------------------------------------------------------------------------
   0. Limpieza (para poder re-ejecutar el script)
---------------------------------------------------------------------------- */
IF OBJECT_ID('dbo.vw_SesionesDetalle') IS NOT NULL DROP VIEW dbo.vw_SesionesDetalle;
IF OBJECT_ID('dbo.vw_ResumenCliente')  IS NOT NULL DROP VIEW dbo.vw_ResumenCliente;
IF OBJECT_ID('dbo.vw_ResumenMaquina')  IS NOT NULL DROP VIEW dbo.vw_ResumenMaquina;
IF OBJECT_ID('dbo.vw_ResumenDiario')   IS NOT NULL DROP VIEW dbo.vw_ResumenDiario;
GO

DECLARE @fk sysname;
DECLARE cur CURSOR LOCAL FAST_FORWARD FOR
    SELECT name FROM sys.foreign_keys
    WHERE parent_object_id = OBJECT_ID('dbo.FctPlayerSession');
OPEN cur;
FETCH NEXT FROM cur INTO @fk;
WHILE @@FETCH_STATUS = 0
BEGIN
    EXEC('ALTER TABLE dbo.FctPlayerSession DROP CONSTRAINT ' + @fk);
    FETCH NEXT FROM cur INTO @fk;
END
CLOSE cur; DEALLOCATE cur;
GO

IF OBJECT_ID('dbo.DimCliente')     IS NOT NULL DROP TABLE dbo.DimCliente;
IF OBJECT_ID('dbo.DimMaquina')     IS NOT NULL DROP TABLE dbo.DimMaquina;
IF OBJECT_ID('dbo.DimUbicacion')   IS NOT NULL DROP TABLE dbo.DimUbicacion;
IF OBJECT_ID('dbo.DimSala')        IS NOT NULL DROP TABLE dbo.DimSala;
IF OBJECT_ID('dbo.DimEmpresa')     IS NOT NULL DROP TABLE dbo.DimEmpresa;
IF OBJECT_ID('dbo.DimMoneda')      IS NOT NULL DROP TABLE dbo.DimMoneda;
IF OBJECT_ID('dbo.DimNegocio')     IS NOT NULL DROP TABLE dbo.DimNegocio;
IF OBJECT_ID('dbo.DimTipoSesion')  IS NOT NULL DROP TABLE dbo.DimTipoSesion;
IF OBJECT_ID('dbo.DimCalendario')  IS NOT NULL DROP TABLE dbo.DimCalendario;
GO


/* ----------------------------------------------------------------------------
   1. DimEmpresa   (IdEmpresa: 3 = sede central, 6 = sucursal)
---------------------------------------------------------------------------- */
CREATE TABLE dbo.DimEmpresa
(
    IdEmpresa   INT          NOT NULL PRIMARY KEY,
    RazonSocial VARCHAR(80)  NOT NULL,
    RUC         CHAR(11)     NOT NULL,
    TipoSede    VARCHAR(30)  NOT NULL
);
INSERT dbo.DimEmpresa (IdEmpresa, RazonSocial, RUC, TipoSede) VALUES
    (3, 'Casino Palacio Real S.A.C.',        '20512345678', 'Sede central'),
    (6, 'Inversiones Palacio Real S.A.C.',   '20587654321', 'Sucursal');
GO

/* ----------------------------------------------------------------------------
   2. DimSala   (IdSala: 1 y 2)   -- cada sala pertenece a una empresa
---------------------------------------------------------------------------- */
CREATE TABLE dbo.DimSala
(
    IdSala            INT         NOT NULL PRIMARY KEY,
    NombreSala        VARCHAR(50) NOT NULL,
    IdEmpresa         INT         NOT NULL REFERENCES dbo.DimEmpresa(IdEmpresa),
    Piso              INT         NOT NULL,
    NroMaquinasAprox  INT         NULL
);
INSERT dbo.DimSala (IdSala, NombreSala, IdEmpresa, Piso, NroMaquinasAprox)
SELECT s.IdSala,
       CASE s.IdSala WHEN 1 THEN 'Sala Principal' WHEN 2 THEN 'Sala VIP'
            ELSE 'Sala ' + CAST(s.IdSala AS varchar(10)) END,
       CASE s.IdSala WHEN 1 THEN 3 WHEN 2 THEN 6 ELSE 3 END,
       CASE s.IdSala WHEN 1 THEN 1 WHEN 2 THEN 2 ELSE 1 END,
       s.maquinas
FROM (
    SELECT IdSala, COUNT(DISTINCT Mnum) AS maquinas
    FROM dbo.FctPlayerSession
    WHERE IdSala IS NOT NULL
    GROUP BY IdSala
) s;
GO

/* ----------------------------------------------------------------------------
   3. DimMoneda   (IdMoneda: 1 y 2)
---------------------------------------------------------------------------- */
CREATE TABLE dbo.DimMoneda
(
    IdMoneda     INT         NOT NULL PRIMARY KEY,
    CodigoISO    CHAR(3)     NOT NULL,
    NombreMoneda VARCHAR(40) NOT NULL,
    Simbolo      VARCHAR(5)  NOT NULL
);
INSERT dbo.DimMoneda (IdMoneda, CodigoISO, NombreMoneda, Simbolo) VALUES
    (1, 'PEN', 'Sol peruano',            'S/'),
    (2, 'USD', 'Dolar estadounidense',   '$');
GO

/* ----------------------------------------------------------------------------
   4. DimNegocio   (IdNegocio: 1)
---------------------------------------------------------------------------- */
CREATE TABLE dbo.DimNegocio
(
    IdNegocio     INT         NOT NULL PRIMARY KEY,
    NombreNegocio VARCHAR(50) NOT NULL
);
INSERT dbo.DimNegocio (IdNegocio, NombreNegocio)
SELECT DISTINCT IdNegocio,
       'Operacion de casino ' + CAST(IdNegocio AS varchar(10))
FROM dbo.FctPlayerSession
WHERE IdNegocio IS NOT NULL;
GO

/* ----------------------------------------------------------------------------
   5. DimTipoSesion   (SessionTypeID: 1)
---------------------------------------------------------------------------- */
CREATE TABLE dbo.DimTipoSesion
(
    SessionTypeID    INT         NOT NULL PRIMARY KEY,
    NombreTipoSesion VARCHAR(40) NOT NULL
);
INSERT dbo.DimTipoSesion (SessionTypeID, NombreTipoSesion)
SELECT DISTINCT SessionTypeID,
       CASE SessionTypeID WHEN 1 THEN 'Juego en maquina'
            ELSE 'Tipo ' + CAST(SessionTypeID AS varchar(10)) END
FROM dbo.FctPlayerSession
WHERE SessionTypeID IS NOT NULL;
GO

/* ----------------------------------------------------------------------------
   6. DimCalendario   (IdCalendario -> una fecha; 5903 = 2026-07-15 ...)
---------------------------------------------------------------------------- */
CREATE TABLE dbo.DimCalendario
(
    IdCalendario  INT         NOT NULL PRIMARY KEY,
    Fecha         DATE        NOT NULL,
    Anio          INT         NOT NULL,
    NumeroMes     INT         NOT NULL,
    NombreMes     VARCHAR(20) NOT NULL,
    DiaDelMes     INT         NOT NULL,
    NombreDia     VARCHAR(20) NOT NULL,
    EsFinDeSemana BIT         NOT NULL,
    NumeroSemana  INT         NOT NULL
);
INSERT dbo.DimCalendario
    (IdCalendario, Fecha, Anio, NumeroMes, NombreMes, DiaDelMes, NombreDia, EsFinDeSemana, NumeroSemana)
SELECT d.IdCalendario,
       d.Fecha,
       YEAR(d.Fecha),
       MONTH(d.Fecha),
       DATENAME(month, d.Fecha),
       DAY(d.Fecha),
       DATENAME(weekday, d.Fecha),
       CASE WHEN DATEDIFF(day, '2024-01-01', d.Fecha) % 7 IN (5, 6) THEN 1 ELSE 0 END,  -- 2024-01-01 = lunes
       DATEPART(iso_week, d.Fecha)
FROM (
    SELECT IdCalendario, CAST(MIN(AccountingDate) AS date) AS Fecha
    FROM dbo.FctPlayerSession
    WHERE IdCalendario IS NOT NULL AND AccountingDate IS NOT NULL
    GROUP BY IdCalendario
) d;
GO

/* ----------------------------------------------------------------------------
   7. DimUbicacion   (Location = letra de zona + posicion, ej. 'A2019')
---------------------------------------------------------------------------- */
CREATE TABLE dbo.DimUbicacion
(
    Location       VARCHAR(20) NOT NULL PRIMARY KEY,
    Zona           CHAR(1)     NOT NULL,
    NumeroPosicion INT         NULL,
    Descripcion    VARCHAR(60) NOT NULL
);
INSERT dbo.DimUbicacion (Location, Zona, NumeroPosicion, Descripcion)
SELECT DISTINCT
       f.Location,
       LEFT(f.Location, 1),
       TRY_CAST(SUBSTRING(f.Location, 2, 10) AS int),
       'Zona ' + LEFT(f.Location, 1) + ' - posicion ' + SUBSTRING(f.Location, 2, 10)
FROM dbo.FctPlayerSession f
WHERE f.Location IS NOT NULL;
GO

/* ----------------------------------------------------------------------------
   8. DimCliente
      - Segmento: por gasto total (CoinIn) usando cuartiles -> VIP/Alto/Medio/Estandar
      - Nombre y ciudad: ficticios pero deterministas (dependen del IdCliente)
      - FechaAlta: anterior a su primera sesion registrada
---------------------------------------------------------------------------- */
CREATE TABLE dbo.DimCliente
(
    IdCliente      INT          NOT NULL PRIMARY KEY,
    CodigoCliente  VARCHAR(15)  NOT NULL,
    NombreCompleto VARCHAR(80)  NOT NULL,
    Segmento       VARCHAR(15)  NOT NULL,
    Ciudad         VARCHAR(30)  NOT NULL,
    FechaAlta      DATE         NOT NULL,
    Activo         BIT          NOT NULL
);

;WITH agg AS (
    SELECT IdCliente,
           SUM(CoinIn)                     AS TotalCoinIn,
           MIN(CAST(StartTime AS date))    AS PrimeraSesion
    FROM dbo.FctPlayerSession
    WHERE IdCliente IS NOT NULL
    GROUP BY IdCliente
),
seg AS (
    SELECT *, NTILE(4) OVER (ORDER BY TotalCoinIn DESC) AS q FROM agg
)
INSERT dbo.DimCliente (IdCliente, CodigoCliente, NombreCompleto, Segmento, Ciudad, FechaAlta, Activo)
SELECT s.IdCliente,
       'CLI-' + RIGHT('000000' + CAST(s.IdCliente AS varchar(10)), 6),
       n.v + ' ' + a1.v + ' ' + a2.v,
       CASE s.q WHEN 1 THEN 'VIP' WHEN 2 THEN 'Alto' WHEN 3 THEN 'Medio' ELSE 'Estandar' END,
       c.v,
       DATEADD(day, -((CHECKSUM(s.IdCliente, 9) & 2147483647) % 900) - 30, s.PrimeraSesion),
       1
FROM seg s
JOIN (VALUES (0,'Maria'),(1,'Jose'),(2,'Carlos'),(3,'Ana'),(4,'Luis'),(5,'Rosa'),
             (6,'Miguel'),(7,'Carmen'),(8,'Jorge'),(9,'Lucia'),(10,'Pedro'),(11,'Elena'),
             (12,'Juan'),(13,'Sofia'),(14,'Diego'),(15,'Paula'),(16,'Andres'),(17,'Valeria'),
             (18,'Fernando'),(19,'Camila'),(20,'Ricardo'),(21,'Daniela'),(22,'Gabriel'),(23,'Patricia')
     ) n(i, v)   ON n.i  = (CHECKSUM(s.IdCliente, 1) & 2147483647) % 24
JOIN (VALUES (0,'Garcia'),(1,'Rodriguez'),(2,'Gonzalez'),(3,'Fernandez'),(4,'Lopez'),
             (5,'Martinez'),(6,'Sanchez'),(7,'Perez'),(8,'Gomez'),(9,'Diaz'),(10,'Torres'),
             (11,'Flores'),(12,'Rivera'),(13,'Vargas'),(14,'Castro'),(15,'Rojas'),(16,'Ramos'),
             (17,'Chavez'),(18,'Mendoza'),(19,'Quispe')
     ) a1(i, v)  ON a1.i = (CHECKSUM(s.IdCliente, 2) & 2147483647) % 20
JOIN (VALUES (0,'Garcia'),(1,'Rodriguez'),(2,'Gonzalez'),(3,'Fernandez'),(4,'Lopez'),
             (5,'Martinez'),(6,'Sanchez'),(7,'Perez'),(8,'Gomez'),(9,'Diaz'),(10,'Torres'),
             (11,'Flores'),(12,'Rivera'),(13,'Vargas'),(14,'Castro'),(15,'Rojas'),(16,'Ramos'),
             (17,'Chavez'),(18,'Mendoza'),(19,'Quispe')
     ) a2(i, v)  ON a2.i = (CHECKSUM(s.IdCliente, 3) & 2147483647) % 20
JOIN (VALUES (0,'Lima'),(1,'Arequipa'),(2,'Trujillo'),(3,'Cusco'),(4,'Piura'),
             (5,'Chiclayo'),(6,'Huancayo'),(7,'Tacna'),(8,'Iquitos'),(9,'Callao')
     ) c(i, v)   ON c.i  = (CHECKSUM(s.IdCliente, 4) & 2147483647) % 10;
GO

/* ----------------------------------------------------------------------------
   9. DimMaquina
      - TipoJuego / Fabricante / Denominacion: ficticios deterministas (por Mnum)
      - SalaPredominante: sala donde la maquina registro mas sesiones
---------------------------------------------------------------------------- */
CREATE TABLE dbo.DimMaquina
(
    Mnum             INT          NOT NULL PRIMARY KEY,
    CodigoMaquina    VARCHAR(15)  NOT NULL,
    TipoJuego        VARCHAR(30)  NOT NULL,
    Fabricante       VARCHAR(30)  NOT NULL,
    Modelo           VARCHAR(40)  NOT NULL,
    Denominacion     DECIMAL(6,2) NOT NULL,
    FechaInstalacion DATE         NOT NULL,
    SalaPredominante INT          NULL REFERENCES dbo.DimSala(IdSala)
);

;WITH sala_maq AS (
    SELECT Mnum, IdSala,
           ROW_NUMBER() OVER (PARTITION BY Mnum ORDER BY COUNT(*) DESC, IdSala) AS rn
    FROM dbo.FctPlayerSession
    WHERE Mnum IS NOT NULL AND IdSala IS NOT NULL
    GROUP BY Mnum, IdSala
),
maq AS (
    SELECT DISTINCT Mnum FROM dbo.FctPlayerSession WHERE Mnum IS NOT NULL
)
INSERT dbo.DimMaquina (Mnum, CodigoMaquina, TipoJuego, Fabricante, Modelo, Denominacion, FechaInstalacion, SalaPredominante)
SELECT m.Mnum,
       'MAQ-' + CAST(m.Mnum AS varchar(10)),
       tj.v,
       fb.v,
       fb.v + '-' + RIGHT('000' + CAST(m.Mnum AS varchar(10)), 3),
       dn.v,
       DATEADD(day, -((CHECKSUM(m.Mnum, 7) & 2147483647) % 1600), '2026-07-01'),
       sm.IdSala
FROM maq m
JOIN (VALUES (0,'Tragamonedas clasica'),(1,'Video slot'),(2,'Poker electronico'),
             (3,'Ruleta electronica'),(4,'Keno')
     ) tj(i, v) ON tj.i = (CHECKSUM(m.Mnum, 1) & 2147483647) % 5
JOIN (VALUES (0,'IGT'),(1,'Aristocrat'),(2,'Novomatic'),(3,'Konami'),
             (4,'Scientific Games'),(5,'Ainsworth')
     ) fb(i, v) ON fb.i = (CHECKSUM(m.Mnum, 2) & 2147483647) % 6
JOIN (VALUES (0, CAST(0.01 AS decimal(6,2))),(1, CAST(0.05 AS decimal(6,2))),
             (2, CAST(0.10 AS decimal(6,2))),(3, CAST(0.25 AS decimal(6,2)))
     ) dn(i, v) ON dn.i = (CHECKSUM(m.Mnum, 3) & 2147483647) % 4
LEFT JOIN sala_maq sm ON sm.Mnum = m.Mnum AND sm.rn = 1;
GO


/* ----------------------------------------------------------------------------
   10. Claves foraneas en FctPlayerSession
---------------------------------------------------------------------------- */
ALTER TABLE dbo.FctPlayerSession WITH CHECK
    ADD CONSTRAINT FK_Fps_Cliente     FOREIGN KEY (IdCliente)     REFERENCES dbo.DimCliente(IdCliente);
ALTER TABLE dbo.FctPlayerSession WITH CHECK
    ADD CONSTRAINT FK_Fps_Maquina     FOREIGN KEY (Mnum)          REFERENCES dbo.DimMaquina(Mnum);
ALTER TABLE dbo.FctPlayerSession WITH CHECK
    ADD CONSTRAINT FK_Fps_Sala        FOREIGN KEY (IdSala)        REFERENCES dbo.DimSala(IdSala);
ALTER TABLE dbo.FctPlayerSession WITH CHECK
    ADD CONSTRAINT FK_Fps_Empresa     FOREIGN KEY (IdEmpresa)     REFERENCES dbo.DimEmpresa(IdEmpresa);
ALTER TABLE dbo.FctPlayerSession WITH CHECK
    ADD CONSTRAINT FK_Fps_Ubicacion   FOREIGN KEY (Location)      REFERENCES dbo.DimUbicacion(Location);
ALTER TABLE dbo.FctPlayerSession WITH CHECK
    ADD CONSTRAINT FK_Fps_Moneda      FOREIGN KEY (IdMoneda)      REFERENCES dbo.DimMoneda(IdMoneda);
ALTER TABLE dbo.FctPlayerSession WITH CHECK
    ADD CONSTRAINT FK_Fps_Negocio     FOREIGN KEY (IdNegocio)     REFERENCES dbo.DimNegocio(IdNegocio);
ALTER TABLE dbo.FctPlayerSession WITH CHECK
    ADD CONSTRAINT FK_Fps_TipoSesion  FOREIGN KEY (SessionTypeID) REFERENCES dbo.DimTipoSesion(SessionTypeID);
ALTER TABLE dbo.FctPlayerSession WITH CHECK
    ADD CONSTRAINT FK_Fps_Calendario  FOREIGN KEY (IdCalendario)  REFERENCES dbo.DimCalendario(IdCalendario);
GO

CREATE INDEX IX_Fps_IdCliente    ON dbo.FctPlayerSession(IdCliente);
CREATE INDEX IX_Fps_Mnum         ON dbo.FctPlayerSession(Mnum);
CREATE INDEX IX_Fps_IdCalendario ON dbo.FctPlayerSession(IdCalendario);
GO


/* ----------------------------------------------------------------------------
   11. Vistas de consumo
---------------------------------------------------------------------------- */
GO
CREATE VIEW dbo.vw_SesionesDetalle AS
SELECT
    f.TransID,
    cal.Fecha,
    cal.NombreDia,
    cal.EsFinDeSemana,
    f.Hora,
    f.StartTime,
    f.EndTime,
    f.TimePlayed                              AS SegundosJugados,
    CAST(f.TimePlayed / 60.0 AS decimal(10,1)) AS MinutosJugados,
    cli.IdCliente,
    cli.CodigoCliente,
    cli.NombreCompleto                        AS Cliente,
    cli.Segmento,
    cli.Ciudad,
    maq.Mnum,
    maq.CodigoMaquina,
    maq.TipoJuego,
    maq.Fabricante,
    maq.Modelo,
    maq.Denominacion,
    sala.NombreSala,
    emp.RazonSocial                           AS Empresa,
    emp.TipoSede,
    ubi.Location,
    ubi.Zona,
    mon.CodigoISO                             AS Moneda,
    mon.Simbolo,
    neg.NombreNegocio,
    ts.NombreTipoSesion,
    f.Games                                   AS Partidas,
    f.CoinIn,
    f.CoinOut,
    f.BillsIn,
    f.AverageBet,
    f.Win                                     AS ResultadoJugador,
    f.TheoWin                                 AS GananciaTeoricaCasa,
    (f.CoinIn - f.CoinOut)                    AS ResultadoNetoCasa,
    f.Jackpot,
    f.PointsEarned                            AS PuntosGanados,
    f.CompEarned
FROM dbo.FctPlayerSession f
LEFT JOIN dbo.DimCalendario  cal  ON cal.IdCalendario  = f.IdCalendario
LEFT JOIN dbo.DimCliente     cli  ON cli.IdCliente     = f.IdCliente
LEFT JOIN dbo.DimMaquina     maq  ON maq.Mnum          = f.Mnum
LEFT JOIN dbo.DimSala        sala ON sala.IdSala       = f.IdSala
LEFT JOIN dbo.DimEmpresa     emp  ON emp.IdEmpresa     = f.IdEmpresa
LEFT JOIN dbo.DimUbicacion   ubi  ON ubi.Location      = f.Location
LEFT JOIN dbo.DimMoneda      mon  ON mon.IdMoneda      = f.IdMoneda
LEFT JOIN dbo.DimNegocio     neg  ON neg.IdNegocio     = f.IdNegocio
LEFT JOIN dbo.DimTipoSesion  ts   ON ts.SessionTypeID  = f.SessionTypeID;
GO

CREATE VIEW dbo.vw_ResumenCliente AS
SELECT
    cli.IdCliente,
    cli.CodigoCliente,
    cli.NombreCompleto        AS Cliente,
    cli.Segmento,
    cli.Ciudad,
    cli.FechaAlta,
    COUNT(*)                                    AS NroSesiones,
    COUNT(DISTINCT f.Mnum)                      AS MaquinasDistintas,
    COUNT(DISTINCT f.IdCalendario)              AS DiasConJuego,
    CAST(SUM(f.TimePlayed) / 3600.0 AS decimal(12,1)) AS HorasJugadas,
    SUM(f.Games)                               AS PartidasTotales,
    CAST(SUM(f.CoinIn)  AS decimal(18,2))      AS CoinInTotal,
    CAST(SUM(f.TheoWin) AS decimal(18,2))      AS GananciaTeoricaCasa,
    CAST(AVG(f.AverageBet) AS decimal(18,2))   AS ApuestaPromedio,
    SUM(f.PointsEarned)                        AS PuntosGanados,
    MIN(f.StartTime)                           AS PrimeraSesion,
    MAX(f.StartTime)                           AS UltimaSesion
FROM dbo.DimCliente cli
JOIN dbo.FctPlayerSession f ON f.IdCliente = cli.IdCliente
GROUP BY cli.IdCliente, cli.CodigoCliente, cli.NombreCompleto, cli.Segmento, cli.Ciudad, cli.FechaAlta;
GO

CREATE VIEW dbo.vw_ResumenMaquina AS
SELECT
    maq.Mnum,
    maq.CodigoMaquina,
    maq.TipoJuego,
    maq.Fabricante,
    maq.Modelo,
    maq.Denominacion,
    sala.NombreSala           AS SalaPredominante,
    COUNT(*)                                    AS NroSesiones,
    COUNT(DISTINCT f.IdCliente)                 AS JugadoresDistintos,
    CAST(SUM(f.TimePlayed) / 3600.0 AS decimal(12,1)) AS HorasJugadas,
    SUM(f.Games)                               AS PartidasTotales,
    CAST(SUM(f.CoinIn)  AS decimal(18,2))      AS CoinInTotal,
    CAST(SUM(f.TheoWin) AS decimal(18,2))      AS GananciaTeoricaCasa,
    CAST(AVG(f.AverageBet) AS decimal(18,2))   AS ApuestaPromedio
FROM dbo.DimMaquina maq
JOIN dbo.FctPlayerSession f ON f.Mnum = maq.Mnum
LEFT JOIN dbo.DimSala sala  ON sala.IdSala = maq.SalaPredominante
GROUP BY maq.Mnum, maq.CodigoMaquina, maq.TipoJuego, maq.Fabricante, maq.Modelo,
         maq.Denominacion, sala.NombreSala;
GO

CREATE VIEW dbo.vw_ResumenDiario AS
SELECT
    cal.Fecha,
    cal.NombreDia,
    cal.EsFinDeSemana,
    COUNT(*)                                    AS NroSesiones,
    COUNT(DISTINCT f.IdCliente)                 AS JugadoresActivos,
    COUNT(DISTINCT f.Mnum)                      AS MaquinasUsadas,
    CAST(SUM(f.TimePlayed) / 3600.0 AS decimal(12,1)) AS HorasJugadas,
    CAST(SUM(f.CoinIn)  AS decimal(18,2))      AS CoinInTotal,
    CAST(SUM(f.TheoWin) AS decimal(18,2))      AS GananciaTeoricaCasa
FROM dbo.DimCalendario cal
JOIN dbo.FctPlayerSession f ON f.IdCalendario = cal.IdCalendario
GROUP BY cal.Fecha, cal.NombreDia, cal.EsFinDeSemana;
GO


/* ----------------------------------------------------------------------------
   12. Verificaciones
---------------------------------------------------------------------------- */
SELECT 'DimCliente'    AS Tabla, COUNT(*) AS Filas FROM dbo.DimCliente
UNION ALL SELECT 'DimMaquina',    COUNT(*) FROM dbo.DimMaquina
UNION ALL SELECT 'DimSala',       COUNT(*) FROM dbo.DimSala
UNION ALL SELECT 'DimEmpresa',    COUNT(*) FROM dbo.DimEmpresa
UNION ALL SELECT 'DimUbicacion',  COUNT(*) FROM dbo.DimUbicacion
UNION ALL SELECT 'DimMoneda',     COUNT(*) FROM dbo.DimMoneda
UNION ALL SELECT 'DimNegocio',    COUNT(*) FROM dbo.DimNegocio
UNION ALL SELECT 'DimTipoSesion', COUNT(*) FROM dbo.DimTipoSesion
UNION ALL SELECT 'DimCalendario', COUNT(*) FROM dbo.DimCalendario;

SELECT TOP (20) * FROM dbo.vw_SesionesDetalle ORDER BY TransID;
SELECT TOP (10) * FROM dbo.vw_ResumenCliente ORDER BY CoinInTotal DESC;
SELECT TOP (10) * FROM dbo.vw_ResumenMaquina ORDER BY NroSesiones DESC;
SELECT * FROM dbo.vw_ResumenDiario ORDER BY Fecha;
GO
