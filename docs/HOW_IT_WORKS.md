# Cómo funciona

Este texto es para contarlo en una entrevista, en voz alta. El laboratorio es local. La empresa Nube Austral es inventada. El "modelo" es un planificador falso. No hay un cliente real atrás.

## La analogía

Mirá el sistema como una **firma de cheque con dos firmas**. Fijate que la primera firma no paga sola.

La primera persona (el agente) puede llenar el cheque: a quién, por qué concepto, con qué importe. Eso es barato y reversible. El banco (el sistema alrededor del modelo) no entrega la plata si falta la segunda firma. La misma persona no puede firmar dos veces. Si el cheque se anuló, sigue anulado aunque alguien lo vuelva a presentar. Y si el gerente de la sucursal baja la persiana (el kill switch), la caja no paga más, aunque el cheque ya tuviera las dos firmas listas y todavía no hubiera salido.

El modelo razona. El sistema alrededor decide si eso toca el mundo.

## El recorrido, paso a paso

1. Un cliente local crea una tarea. Manda un mensaje ("nota de credito") y el id de un registro sintético (`INV-1001`).
2. La tarea pasa por `submitted` y `working`.
3. El planificador propone acciones. El falso mira palabras del mensaje (`leer`, `borrador`, `credito`, `banco`). No lee la nota del cliente como si fuera una orden.
4. La política clasifica cada acción: auto, necesita aprobación, o prohibida. El importe de una nota de crédito sale del registro, no del texto del modelo.
5. Leer y redactar un borrador corren solos. No tocan el libro downstream.
6. Una nota de crédito chica (menos de 5000 centavos de una unidad inventada) corre sola. De 5000 a 500000 espera a otra persona. Por encima de 500000, o en cero, se rechaza. Cambiar el banco de un proveedor siempre espera.
7. La tarea queda en `input-required` con motivo `approval-pending`.
8. Si aprueba la misma persona que pidió, el sistema responde 403 y no aplica nada.
9. Si aprueba alguien con rol `finance_approver` o `admin`, y no venció el plazo, el efecto entra al libro falso una sola vez.
10. Si rechaza, la tarea queda `rejected`. Un replay devuelve esa misma tarea. No hay segundo efecto.
11. Cada línea del log incluye el hash de la anterior. `verify-evidence` recomputa la cadena.
12. Un admin con el token que salió del entorno puede bajar la persiana. Después de eso, un efecto nuevo no se aplica.

## Qué está medido

El 2026-10-18, con Python 3.12.3 y el paquete 0.1.0, `python -m a2a_gate.evalkit run` pasó 37 de 37 casos. El comando de regresión forzada salió con código 1. Eso está en el README con el comando exacto. No es un número de producción.

## Glosario

| Palabra | Qué quiere decir acá |
|---|---|
| Tarea | Una unidad de trabajo con id y estado. Inspirada en A2A, no es el schema oficial completo |
| Planificador | El componente que propone acciones. Por defecto es falso |
| Cassette | Un plan congelado. La eval lo reproduce para no llamar a un modelo pago |
| Política | El archivo YAML que dice auto, aprobación o prohibido |
| Efecto | Una escritura en el libro falso: nota de crédito o cambio de banco |
| Idempotencia | La misma clave devuelve el mismo resultado y no escribe dos veces |
| Evidencia | Un JSONL que solo agrega líneas y las encadena por hash |
| Kill switch | Una orden de admin que frena efectos nuevos |
| Invariante | Una condición que tiene que ser verdad al final, sin importar el camino del modelo |

## Límites, en serio

- No habla el protocolo A2A completo. El 2026-10-18 miramos la spec pública (enlace en `docs/architecture.md`). Este lab usa unos nombres de estado y una tarjeta en `/.well-known/agent-card.json`. El binding se llama `LAB-HTTP` a propósito, para no decir que cumplimos JSON-RPC ni el HTTP+JSON oficial.
- No firma la tarjeta. No hay streaming ni push.
- No hay login de verdad. El bearer del lab no es un IdP.
- No manda mails ni paga.
- El kill switch no deshace lo que ya se aplicó. Frena lo que viene.
- La cadena de hash detecta si alguien editó el archivo. No impide que alguien con acceso al disco lo edite.
- Los tokens de los cassettes (24 y 12) son simulados. Con un modelo real no medimos nada: la tabla dice "none yet".
