# Base de datos — `CasinoPalacioReal`

Ejecutar en **SQL Server 2022+** (SSMS), en orden:

| # | Script | Crea |
|---|---|---|
| 1 | `01_cargar_FctPlayerSession.sql` | BD `CasinoPalacioReal` + tabla `dbo.FctPlayerSession` y carga del CSV |
| 2 | `02_crear_dimensiones_y_vista.sql` | Modelo estrella (`DimCliente`, `DimMaquina`, `DimSala`, `DimEmpresa`, `DimUbicacion`, `DimMoneda`, `DimNegocio`, `DimTipoSesion`, `DimCalendario`) + claves foráneas + vistas `vw_SesionesDetalle`, `vw_ResumenCliente`, `vw_ResumenMaquina`, `vw_ResumenDiario` |
| 3 | `03_features_cliente_scoring.sql` | `vw_FeaturesCliente` (tabla analítica, 1 fila por cliente) y `vw_ClientesScoring` (baseline por reglas: `NivelRiesgo`, `DecilPropension`, `AccionRecomendada`) |
| 4 | `04_preparar_abt_riesgo_supervisado.sql` | ABT temporal supervisada de riesgo y controles de calidad (requiere `ext.*`, ver abajo) |
| 5 | `05_modelo_riesgo_supervisado.sql` | Corridas, predicciones y vista vigente del modelo de riesgo |
| 6 | `06_modelo_respuesta_nbo.sql` | Evidencia, campañas calibradas y opciones cliente-recompensa (requiere `ext.*`) |
| 7 | `07_optimizador_recompensas.sql` | Corridas, decisiones trazables y vistas vigentes del optimizador |
| 8 | `08_catalogo_y_relaciones.sql` | (opcional) inventario de tablas/vistas, relaciones (FK), diccionario de columnas y resumen ejecutivo — SQL puro, sin Python |

## Antes de empezar

1. Copiar `../data/raw/playersession_ficticio_100k.csv` a `C:\Data\` (el servicio
   de SQL Server no lee dentro de OneDrive).
2. Verificar la versión: `SELECT @@VERSION;` — debe ser 16.x o superior.

## Datos externos para los scripts 4, 5 y 6 (`ext.*`)

Los scripts `04`-`06` (riesgo supervisado y respuesta NBO calibrada, ver
`docs/etapa1_riesgo_supervisado.md` a `etapa3_modelo_respuesta_nbo.md`) leen de
tablas `ext.HillstromEmail`, `ext.CriteoUpliftV21` y las fuentes externas de
juego responsable (`ext.Transparency*`, `ext.UCIBank*`, `ext.UKGCRiskAlgorithmsRaw`).
No hay script `CREATE TABLE ext.*` ni `BULK INSERT` commiteado en el repo para
esas tablas — se cargan restaurando el backup completo (ver abajo).

Una vez restaurado ese backup, correr en orden para regenerar los artefactos
locales (`models_store/*.joblib`) a partir de la base:

```bash
python scripts/prepare_risk_data.py       # etapa 1: ABT de riesgo supervisado
python scripts/train_supervised_risk.py   # etapa 2: modelo_riesgo_supervisado.joblib
python scripts/train_response_nbo.py      # etapa 3: modelo_respuesta_nbo_calibrado.joblib
python scripts/run_allocation.py --presupuesto 15000   # etapa 4: optimizador sobre datos reales
```

La app (`streamlit_app.py`) detecta solo si existe
`modelo_respuesta_nbo_calibrado.joblib` y lo usa; si no, sigue con el NBO
semi-sintético (`modelo_respuesta_nbo.joblib`) sin romperse.

## Compartir la base ya cargada

Dos backups, no versionados en git (`*.bak` en `.gitignore`):

| Archivo | Contiene | Peso aprox. |
|---|---|---|
| `entregables/CasinoPalacioReal.bak` | solo `dbo.*` (sesiones, dimensiones, `vw_FeaturesCliente`) | ~41 MB |
| `data/CasinoPalacioReal.bak` | lo anterior **+** `ext.*` (Hillstrom, Criteo, datasets de juego responsable) **+** `ml.*` (corridas y predicciones de las etapas 1-4 ya publicadas) | ~365 MB |

Para tener todo (incluyendo lo necesario para entrenar NBO calibrado y riesgo
supervisado), restaurar `data/CasinoPalacioReal.bak`. Instrucciones generales
de restauración en `../entregables/LEEME_restaurar_base.md` (mismo
procedimiento `RESTORE DATABASE ... WITH MOVE, REPLACE`, apuntando a este
archivo en vez del de `entregables/`).

## Notas de los datos

- El CSV es UTF-8 con saltos de línea LF ⇒ `BULK INSERT ... ROWTERMINATOR='0x0a'`.
- `ManualEdit` llega como texto `'True'/'False'` ⇒ se carga como `VARCHAR(5)`.
- `PointMultiplier` viene siempre vacío ⇒ `NULL`.
- `TripNumber` y algunas columnas de puntos son constantes en la muestra simulada.
- Los atributos de `DimCliente` / `DimMaquina` (nombres, ciudades, fabricantes)
  son ficticios pero **deterministas**: re-ejecutar da el mismo resultado.
