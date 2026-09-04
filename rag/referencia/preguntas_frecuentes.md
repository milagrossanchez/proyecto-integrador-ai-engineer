# Preguntas frecuentes del analista

> Documento de referencia para el asistente. Simulado, fines académicos.

## ¿Un cliente de riesgo medio puede recibir una recompensa alta?

No. Los clientes de riesgo medio solo pueden recibir recompensa baja o media.
Las recompensas altas se reservan para clientes de riesgo bajo.

## ¿Qué pasa con los clientes de riesgo alto?

No reciben ninguna recompensa ni comunicación promocional. Se genera una alerta
para el equipo de juego responsable, que los contacta con información de límites de
juego y autoexclusión.

## ¿Cómo se elige a quién premiar si el presupuesto no alcanza para todos?

Se ordena a los clientes elegibles por eficiencia (valor esperado por cada sol
gastado) y se asigna de arriba hacia abajo hasta agotar el presupuesto.

## ¿Qué significa "probabilidad de respuesta"?

Es la probabilidad estimada (de 0 a 1) de que el cliente vuelva a visitar o juegue
tras recibir el incentivo. La entrega el modelo de propensión.

## ¿Qué significa "valor esperado" en la tabla de asignación?

Es la ganancia neta esperada de darle la recompensa a ese cliente:
probabilidad de respuesta por el valor incremental estimado, menos el costo de la
recompensa. Si es negativo, no se asigna.

## ¿El sistema reemplaza al analista?

No. El sistema recomienda; el analista revisa y aprueba. Toda decisión sobre
clientes de riesgo alto la maneja el equipo de juego responsable.

## ¿Puedo cambiar el presupuesto de la campaña?

Sí, en la pestaña Cartera de la aplicación. El plan de asignación se recalcula al
instante.

## ¿De dónde salen los nombres y ciudades de los clientes?

En este caso de estudio son datos simulados y deterministas. En producción vendrían
del sistema de fidelización del casino.
