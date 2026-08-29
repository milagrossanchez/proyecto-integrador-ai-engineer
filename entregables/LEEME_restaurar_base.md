# Casino Palacio Real — cómo cargar la base de datos

Contenido de esta carpeta:

| Archivo | Para qué |
|---|---|
| `CasinoPalacioReal.bak` | **Copia completa de la base** (todas las tablas, datos, vistas y relaciones). Opción rápida. |
| `playersession_ficticio_100k.csv` | Datos crudos de sesiones. |
| `cargar_FctPlayerSession.sql` | (1) crea la tabla de hechos y carga el CSV. |
| `crear_dimensiones_y_vista.sql` | (2) crea el modelo estrella (DimCliente, DimMaquina, ...) y vistas resumen. |
| `features_cliente_scoring.sql` | (3) crea `vw_FeaturesCliente` y `vw_ClientesScoring`. |

Requisito: **SQL Server 2022 (versión 16.x) o superior**. Un `.bak` NO se puede
restaurar en una versión anterior. Comprobar con: `SELECT @@VERSION;`

---

## Opción A — restaurar el .bak (recomendada, 1 archivo)

1. Descargar `CasinoPalacioReal.bak` y ponerlo, por ejemplo, en `C:\Data\`.
2. Crear la carpeta `C:\Data\` si no existe (ahí van los archivos de la base).
3. En SSMS abrir una consulta nueva y ejecutar:

```sql
USE master;
RESTORE DATABASE CasinoPalacioReal
FROM DISK = N'C:\Data\CasinoPalacioReal.bak'
WITH MOVE N'CasinoPalacioReal'     TO N'C:\Data\CasinoPalacioReal.mdf',
     MOVE N'CasinoPalacioReal_log' TO N'C:\Data\CasinoPalacioReal_log.ldf',
     REPLACE, RECOVERY, STATS = 10;
```

   (O con el asistente: clic derecho en **Databases → Restore Database → Device →**
   seleccionar el `.bak` → **OK**.)

4. Verificar:

```sql
USE CasinoPalacioReal;
SELECT COUNT(*) FROM dbo.FctPlayerSession;      -- 100000
SELECT * FROM dbo.vw_ClientesScoring;
```

---

## Opción B — reconstruir desde los scripts (si el .bak no restaura)

1. Crear la base:  `CREATE DATABASE CasinoPalacioReal;`
2. Copiar `playersession_ficticio_100k.csv` a `C:\Data\`.
3. Ejecutar en orden, sobre la base `CasinoPalacioReal`:
   1. `cargar_FctPlayerSession.sql`
   2. `crear_dimensiones_y_vista.sql`
   3. `features_cliente_scoring.sql`

Los scripts son deterministas: todos obtienen exactamente el mismo resultado.
