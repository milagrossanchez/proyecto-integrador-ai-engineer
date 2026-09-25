/* ============================================================================
   Proyecto : Casino Palacio Real - Identificacion de riesgo y recompensas
   Archivo  : 04_catalogo_y_relaciones.sql
   Objetivo : inventario de la base (tablas, vistas, filas, columnas) y el
              mapa de relaciones (foreign keys) entre tablas, todo en SQL
              puro para correr en SSMS sin depender de Python.
   Requiere : haber corrido 01, 02 y 03 antes.
   ============================================================================ */

USE CasinoPalacioReal;
GO
SET NOCOUNT ON;
GO


/* ----------------------------------------------------------------------------
   1. Inventario de tablas (nombre, filas, columnas)
---------------------------------------------------------------------------- */
SELECT
    t.name                                    AS Tabla,
    p.rows                                     AS Filas,
    (SELECT COUNT(*) FROM sys.columns c WHERE c.object_id = t.object_id) AS Columnas,
    CASE WHEN t.name = 'FctPlayerSession' THEN 'Hecho' ELSE 'Dimension' END AS Tipo
FROM sys.tables t
JOIN sys.partitions p ON p.object_id = t.object_id AND p.index_id IN (0, 1)
ORDER BY Tipo, Tabla;
GO


/* ----------------------------------------------------------------------------
   2. Inventario de vistas (nombre, filas)
---------------------------------------------------------------------------- */
DECLARE @vistas TABLE (Vista sysname, Filas INT);
INSERT INTO @vistas (Vista, Filas)
SELECT v.name, NULL
FROM sys.views v;

DECLARE @nombre sysname, @sql nvarchar(400), @n INT;
DECLARE cur CURSOR LOCAL FAST_FORWARD FOR SELECT Vista FROM @vistas;
OPEN cur; FETCH NEXT FROM cur INTO @nombre;
WHILE @@FETCH_STATUS = 0
BEGIN
    SET @sql = N'SELECT @n = COUNT(*) FROM dbo.' + QUOTENAME(@nombre);
    EXEC sp_executesql @sql, N'@n INT OUTPUT', @n = @n OUTPUT;
    UPDATE @vistas SET Filas = @n WHERE Vista = @nombre;
    FETCH NEXT FROM cur INTO @nombre;
END
CLOSE cur; DEALLOCATE cur;

SELECT Vista, Filas FROM @vistas ORDER BY Vista;
GO


/* ----------------------------------------------------------------------------
   3. Mapa de relaciones (foreign keys) - el modelo estrella
---------------------------------------------------------------------------- */
SELECT
    tp.name  AS Tabla_hija,
    cp.name  AS Columna_hija,
    tr.name  AS Tabla_padre,
    cr.name  AS Columna_padre,
    fk.name  AS Nombre_constraint
FROM sys.foreign_keys fk
JOIN sys.foreign_key_columns fkc ON fkc.constraint_object_id = fk.object_id
JOIN sys.tables  tp ON tp.object_id = fkc.parent_object_id
JOIN sys.columns cp ON cp.object_id = fkc.parent_object_id     AND cp.column_id = fkc.parent_column_id
JOIN sys.tables  tr ON tr.object_id = fkc.referenced_object_id
JOIN sys.columns cr ON cr.object_id = fkc.referenced_object_id AND cr.column_id = fkc.referenced_column_id
ORDER BY Tabla_hija, Columna_hija;
GO


/* ----------------------------------------------------------------------------
   4. Diagrama de relaciones en texto (para copiar/pegar en documentacion)
---------------------------------------------------------------------------- */
SELECT
    tp.name + '.' + cp.name + '  ->  ' + tr.name + '.' + cr.name AS Relacion
FROM sys.foreign_keys fk
JOIN sys.foreign_key_columns fkc ON fkc.constraint_object_id = fk.object_id
JOIN sys.tables  tp ON tp.object_id = fkc.parent_object_id
JOIN sys.columns cp ON cp.object_id = fkc.parent_object_id     AND cp.column_id = fkc.parent_column_id
JOIN sys.tables  tr ON tr.object_id = fkc.referenced_object_id
JOIN sys.columns cr ON cr.object_id = fkc.referenced_object_id AND cr.column_id = fkc.referenced_column_id
ORDER BY 1;
GO


/* ----------------------------------------------------------------------------
   5. Columnas de cada tabla (diccionario completo, tabla por tabla)
---------------------------------------------------------------------------- */
SELECT
    t.name                       AS Tabla,
    c.column_id                  AS Orden,
    c.name                       AS Columna,
    ty.name                      AS Tipo,
    c.max_length                 AS LongitudMax,
    c.is_nullable                AS PermiteNulo,
    CASE WHEN pk.column_id IS NOT NULL THEN 'PK' ELSE '' END AS EsPK,
    CASE WHEN fkc.parent_column_id IS NOT NULL THEN 'FK' ELSE '' END AS EsFK
FROM sys.tables t
JOIN sys.columns c   ON c.object_id = t.object_id
JOIN sys.types ty    ON ty.user_type_id = c.user_type_id
LEFT JOIN (
    SELECT ic.object_id, ic.column_id
    FROM sys.index_columns ic
    JOIN sys.indexes i ON i.object_id = ic.object_id AND i.index_id = ic.index_id AND i.is_primary_key = 1
) pk ON pk.object_id = t.object_id AND pk.column_id = c.column_id
LEFT JOIN sys.foreign_key_columns fkc ON fkc.parent_object_id = t.object_id AND fkc.parent_column_id = c.column_id
ORDER BY t.name, c.column_id;
GO


/* ----------------------------------------------------------------------------
   6. Resumen ejecutivo en una sola fila
---------------------------------------------------------------------------- */
SELECT
    DB_NAME()                                                          AS Base_de_datos,
    @@SERVERNAME                                                       AS Servidor,
    (SELECT COUNT(*) FROM sys.tables)                                  AS Nro_tablas,
    (SELECT COUNT(*) FROM sys.views)                                   AS Nro_vistas,
    (SELECT COUNT(*) FROM sys.foreign_keys)                            AS Nro_relaciones_fk,
    (SELECT SUM(p.rows) FROM sys.tables t
        JOIN sys.partitions p ON p.object_id = t.object_id AND p.index_id IN (0,1)) AS Total_filas_tablas,
    CONVERT(varchar(19), GETDATE(), 120)                               AS Generado;
GO
