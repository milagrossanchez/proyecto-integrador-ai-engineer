# Etapa 3 — Modelo de respuesta por recompensa

## Objetivo

Estimar `P(respuesta | cliente, recompensa)` para recompensas `baja`, `media` y
`alta`, además de valor incremental, costo y valor esperado.

## Naturaleza de los datos

Casino Palacio Real no dispone todavía de campañas históricas con los tres tipos
de recompensa y resultado observado. Por autorización del proyecto, se utiliza
una campaña **semi-sintética calibrada con evidencia real**:

- Control: tasa de visita del grupo `No E-Mail` de Hillstrom.
- Baja: uplift relativo de visita del tratamiento Criteo aplicado al control.
- Media: tasa de visita de `Womens E-Mail` de Hillstrom.
- Alta: tasa de visita de `Mens E-Mail` de Hillstrom.

La correspondencia baja/media/alta es una hipótesis de simulación. Los tratamientos
originales no son recompensas monetarias equivalentes y nunca se presentan como
si lo fueran.

## Diseño

- Ocho campañas, una exposición por cliente y campaña.
- Rotación balanceada: cada cliente aparece dos veces en control, baja, media y alta.
- La respuesta se genera con semilla 42 y probabilidades medias ancladas en los RCT.
- La heterogeneidad usa únicamente atributos reales del cliente ya disponibles.
- El valor económico se deriva de `ValorTeoricoCasa`, tendencia y la configuración
  existente `factor_uplift`/costos.
- Train, validación y test se separan por cliente; un cliente nunca cruza splits.

## Modelado

- Baseline: regresión logística calibrada.
- Candidato: HistGradientBoosting calibrado.
- Selección: PR-AUC de validación y Brier como desempate.
- Modelo adicional de valor si responde: HistGradientBoostingRegressor.

## Salida por cliente–recompensa

- `ControlProbability`
- `ResponseProbability`
- `UpliftProbability`
- `ValueIncremental`
- `Cost`
- `ExpectedValue = ResponseProbability × ValueIncremental − Cost`
- `IncrementalExpectedValue = UpliftProbability × ValueIncremental − Cost`

## Artefactos

- SQL: `ml.ResponseModelRun`, `ml.ResponseEvidenceAnchor`,
  `ml.ResponseCampaignSynthetic`, `ml.ResponseOption` y vistas actuales.
- Modelo: `models_store/modelo_respuesta_nbo_calibrado.joblib`.
- Histórico: `data/processed/historico_campanas_rct_calibrado.parquet`.
- Opciones: `data/processed/opciones_respuesta_nbo.parquet`.
- Métricas: `reports/metrics/metrics_respuesta_nbo_calibrado.json`.
- EDA: `reports/figures/respuesta_nbo_evaluacion.png`.

Este modelo es adecuado para demostrar y probar el optimizador. Debe reemplazarse
o recalibrarse cuando existan campañas reales del casino con tratamiento, costo,
respuesta y ventana de atribución documentados.

## Integración causal con el optimizador

`IncrementalExpectedValue` y `UpliftProbability` ya se calculaban en
`predict_options()`, pero `predict_wide()` solo exponía `ProbRespuesta`,
`ValorIncremental` y `ValorEsperado` (el `ExpectedValue` bruto,
`P(respuesta) × valor − costo`) — el optimizador nunca llegaba a verlos.

`predict_wide()` ahora también pivota `UpliftProbability_<tipo>` e
`IncrementalExpectedValue_<tipo>` por recompensa, más `ControlProbability`
(constante por cliente). `evaluar_recompensas()` (`optimization/allocate.py`)
usa `IncrementalExpectedValue_<tipo>` como `ValorEsperado` —y por lo tanto
como criterio de `Eficiencia`/ranking— cuando esas columnas existen; conserva
el cálculo bruto en `ValorEsperadoBruto` solo para comparación. Sin esas
columnas (NBO V1 semi-sintético, sin brazo de control) el comportamiento es
idéntico al anterior: no hay regresión para el modelo V1.

Con datos reales (presupuesto S/ 15 000): 492 clientes asignados con el
criterio causal, frente a los que resultarían de rankear por `ProbRespuesta ×
valor − costo` sin restar el control — la diferencia son clientes que el
NBO calibrado estima que habrían respondido casi igual sin campaña (poco
uplift), aunque su probabilidad bruta fuera alta.

**Pendiente (fuera de alcance de esta iteración):** el modelo sigue siendo un
hurdle de dos etapas simple sobre `Responded` binario dentro de la campaña
simulada, no sobre ventanas de retorno observables (7/14/30 días), no modela
`DaysToReturn` con supervivencia/censura, y el uplift es la diferencia de dos
modelos de probabilidad (enfoque tipo two-model/T-learner), no un
T/S/X-learner o doubly-robust learner dedicado, ni se evalúa con Qini/AUUC.
Son extensiones razonables para una siguiente iteración con campañas reales,
no una limitación oculta de lo que aquí se reporta.

