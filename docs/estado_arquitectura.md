# Estado de implementación de la arquitectura

Revisión del código local: **1 de octubre de 2026**. Referencias:
[prototipo](arquitectura.md) y [objetivo de producción](arquitectura_produccion.md).
El diagrama representa el objetivo; una caja dibujada no acredita un servicio desplegado.
Esta revisión comprueba el repositorio y la aplicación local, no una suscripción de Azure.

## Cuánto está aplicado

Se agruparon los requisitos en **22 capacidades**: **6 implementadas en el
prototipo, 4 parciales y 12 pendientes**. No es un porcentaje de avance del
proyecto: las capacidades tienen esfuerzos y criterios de aceptación distintos.
El núcleo local está implementado; la plataforma distribuida de producción todavía no.

| Capacidad del diseño | Estado | Evidencia y límite actual |
|---|---|---|
| 1. SQL local, extracción y features | Implementada local | `sql/`, `data/extract.py`, `features/build.py`: vistas SQL y alternativa CSV; no acredita infraestructura administrada. |
| 2. Modelo de riesgo | Implementada local | `models/risk.py`: clasificador con etiquetas derivadas de reglas y detector de anomalías; falta validación con etiquetas reales. |
| 3. Respuesta V1 y NBO V2 | Implementada local | `models/response.py`: probabilidades y valor por recompensa; entrenamiento V2 con campañas semisintéticas. |
| 4. Optimizador y guardrails | Implementada local | `optimization/allocate.py`: presupuesto, exclusión de riesgo alto, solo baja para riesgo medio, mínimo de sesiones y topes por segmento/recompensa. |
| 5. Explicaciones y mensajes | Implementada local | `genai/explainer.py`: integración LLM, controles y plantillas de respaldo. La existencia de configuración no verifica disponibilidad del proveedor. |
| 6. Panel interno y chat flotante | Implementada local | `app/streamlit_app.py`: Cartera, Cliente e historial en sesión. Panel corregido con fondo opaco y contraste; no equivale al frontend público. |
| 7. Servicio compartido de chat | Parcial | Web y Telegram reutilizan `AsistentePoliticas`; son llamadas a la misma clase, no un servicio de API independiente. Recupera documentos con TF-IDF; faltan embeddings/índice vectorial y consultas autorizadas a cartera. |
| 8. Canal Telegram | Parcial | `genai/telegram_bot.py`: envío y procesamiento de mensajes/botones, con modo dry-run. Faltan endpoint HTTPS, validación del secreto, vinculación de identidad y persistencia de eventos pendientes. |
| 9. Resultados y métricas reales | Parcial | `metrics/respuesta_real.py`: Parquet y métricas de respuesta/calibración. Faltan tabla SQL, concurrencia, costos/ROI, vencimiento de ofertas y medición del resultado económico real. |
| 10. Validación y pruebas | Parcial | `tests/` y métricas guardadas. Faltan pruebas de carga, integración de todos los canales, evaluación formal del RAG y validación temporal sin fuga para todos los modelos. |
| 11. Frontend público React/Next.js | Pendiente | No hay proyecto frontend ni integración por API. Streamlit sigue siendo la interfaz. |
| 12. Orquestador FastAPI/Functions | Pendiente | La app y los scripts llaman directamente a modelos/optimizador; no existe el servicio coordinador. |
| 13. Cola y workers de scoring | Pendiente | Sin Service Bus/Kafka, consumidores, reintentos, deduplicación ni cola de mensajes fallidos. |
| 14. Caché Redis | Pendiente | `st.cache_data`/`st.cache_resource` son cachés locales de Streamlit; no hay caché distribuida de features. |
| 15. Azure SQL y réplica | Pendiente | Existe conexión SQL Server; no hay despliegue, réplica de lectura ni migración de resultados a Azure SQL. |
| 16. Blob Storage / Data Lake | Pendiente | Datos y artefactos en archivos locales; falta almacenamiento compartido y versionado. |
| 17. Reentrenamiento con feedback real | Pendiente | `scripts/train_models.py` siempre simula campañas; faltan construcción del dataset real, ejecución periódica y promoción/versionado de modelos. |
| 18. Recomendación adaptativa | Pendiente | El optimizador usa ranking greedy; no hay aprendizaje en línea ni contextual bandit. |
| 19. Red y escalado | Pendiente | Sin configuración versionada de CDN/WAF, Gateway, balanceador, autoescalado o VPN/Private Link. |
| 20. Identidad y secretos de producción | Pendiente | Configuración local mediante entorno/`.env`; faltan autenticación, roles, aislamiento por cliente y Key Vault. |
| 21. Observabilidad y alertas | Pendiente | Logging local en módulos; faltan trazas con identificador común, colector central, alertas de latencia/errores/drift. |
| 22. Contenedores y despliegue reproducible | Pendiente | No hay Dockerfile, Compose, infraestructura como código ni pipeline de despliegue en el repositorio. |

Las rutas de módulos Python de la tabla son relativas a `src/casino_ia/`.

## Diferencias importantes entre el documento y el código

- **El RAG no consulta la cartera:** `rag.py` indexa archivos Markdown de
  `rag/`; no recibe la tabla de clientes ni el historial de ofertas. Tampoco
  pasa el historial conversacional al LLM. La interfaz ya describe únicamente
  sus consultas sobre políticas y recompensas.
- **No hay webhook de Telegram:** `TELEGRAM_WEBHOOK_SECRET` está configurado,
  pero no existe un endpoint que lo valide. Los pendientes se guardan en un
  diccionario por chat: se pierden al reiniciar y una segunda oferta sustituye
  la referencia anterior. Hace falta identificar cada oferta en el botón y
  procesar respuestas de forma persistente e idempotente.
- **El dataset real no sustituye directamente al simulado:** el registro
  guarda `ValorGenerado` y predicciones; NBO exige `ValorIncremental` y las
  features de entrenamiento. Hace falta un dataset con las features observadas
  al enviar cada oferta y una definición/medición del valor incremental; no
  basta con renombrar una columna ni usar la predicción como resultado real.
- **La validación temporal no es general:** riesgo y respuesta V1 usan
  `train_test_split`; NBO separa campañas ordenando `IdCampana`, lo que sigue
  el tiempo para los IDs simulados actuales, pero no lo garantiza para campañas
  reales. Hay que partir por fecha y ajustar las transformaciones solo con
  entrenamiento antes de afirmar validación temporal sin fuga.

## Orden para llevar el diseño a implementación

1. **Servicio local integrado:** extraer la coordinación de la app a un
   servicio común y exponer una API de scoring, asignación y chat. Comprobar
   igualdad de decisiones y guardrails entre panel y API.
2. **Feedback persistente:** migrar resultados a SQL con identificadores de
   oferta y estados de envío/respuesta; probar reinicios, duplicados y dos
   ofertas en el mismo chat. Después conectar webhook autenticado y vínculo
   cliente–chat. Aceptar una oferta y generar valor económico son eventos distintos.
3. **RAG y evaluación:** incorporar consultas de cartera con permisos,
   pruebas de fidelidad y fuentes; construir el dataset real y corregir las
   particiones temporales antes del reentrenamiento.
4. **Ejecución distribuida:** contenedores, cola, workers, Redis, trazas y
   reintentos. Validar persistencia y límites de presupuesto bajo concurrencia.
5. **Frontend y Azure:** conectar el frontend a la API y desplegar identidad,
   secretos, almacenamiento, red y escalado con configuración reproducible.
   Se necesitan suscripción/entorno de destino, dominio y parámetros operativos;
   no están definidos en este repositorio.
6. **Operación y aprendizaje:** alertas, pruebas de carga, seguimiento de
   resultados reales, reentrenamiento controlado y evaluación de una política
   adaptativa manteniendo los guardrails y el presupuesto.

Cada etapa debe cerrarse con evidencia de ejecución. Ni el diagrama ni esta
lista sustituyen esa validación.

## Verificación de esta revisión

- Las **27 pruebas existentes** pasaron con las APIs externas desactivadas y
  el registro de resultados redirigido a un directorio temporal; no se enviaron
  mensajes reales de Telegram ni se mezclaron eventos de prueba con campañas.
- Se comprobó el chat en Chromium contra `http://localhost:8501`: fondo
  opaco y contraste en temas claro y oscuro, apertura/cierre, permanencia al
  cambiar de pestaña y dimensiones de escritorio (1440 × 1000) y móvil
  (390 × 844). Capturas locales en `reports/figures/chat_corporativo_*.png`.
- Compilación del módulo de la app y `git diff --check` correctos.
- Estas comprobaciones no acreditan un despliegue de Azure, un webhook
  público ni la calidad predictiva sobre campañas reales.
