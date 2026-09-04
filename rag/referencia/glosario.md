# Glosario

> Documento de referencia para el asistente. Simulado, fines académicos.

## Nivel de riesgo

Clasificación del cliente en Bajo, Medio o Alto según señales de intensidad de
juego (persecución de pérdidas, sesiones largas, juego de madrugada, gasto por hora,
escalada de apuesta) y de rentabilidad del incentivo.

## Probabilidad de respuesta (propensión)

Probabilidad estimada de que el cliente reaccione positivamente a una recompensa.
Se expresa de 0 a 1 y también como decil (1 = menos propenso, 10 = más propenso).

## Valor incremental estimado

Ganancia adicional que el casino obtendría del cliente si responde al incentivo.
Se aproxima desde el valor teórico de la casa por sesión y la tendencia reciente.

## Valor esperado

probabilidad_de_respuesta * valor_incremental_estimado - costo_de_la_recompensa.
Es el criterio para decidir si conviene dar una recompensa y cuál.

## Eficiencia

valor_esperado / costo_de_la_recompensa. Retorno esperado por cada sol invertido.
La tabla de asignación se ordena por este valor.

## CoinIn

Dinero total apostado por el cliente. No es lo que pierde ni lo que gana el casino.

## TheoWin / valor teórico de la casa

Ganancia teórica del casino sobre lo apostado (CoinIn por la ventaja de la máquina).
Se usa como medida del valor del cliente para el negocio.

## Comps

Beneficios de cortesía otorgados al cliente (bebidas, comidas, estacionamiento).

## Baseline

Método de comparación: la asignación de recompensas por reglas de segmento que usa
hoy el casino. El sistema debe superarlo en retorno esperado.

## Guardrail de juego responsable

Regla dura del sistema: los clientes de riesgo alto quedan excluidos de toda
recomendación de recompensa, sin excepción y sin depender del criterio del modelo.

## RAG

Técnica por la cual el asistente responde solo con la información de estos
documentos, citando la fuente, en lugar de responder de memoria.
