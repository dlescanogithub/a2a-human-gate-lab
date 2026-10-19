# Final script used: a2a_human_gate_lab_demo_en.mp4 (gate)

Voice: xAI TTS leo, speed 1.08. EN burned in; ES as soft subtitle track (disabled by default).


## A_hook (starts 0.80 s)

- EN: An agent proposes a credit note, or a supplier bank change.
  ES: Un agente propone una nota de crédito, o un cambio de cuenta bancaria de un proveedor.
- EN: Can it just do it? No: a policy decides, and a second person approves.
  ES: ¿Puede hacerlo solo? No: una política decide y una segunda persona aprueba.

## B_walk (starts 10.23 s)

- EN: The credit note waits: input-required. Self-approval: denied.
  ES: La nota de crédito espera: input-required. Autoaprobación: denegada.
- EN: A second person approves, and it completes.
  ES: Una segunda persona aprueba y se completa.
- EN: Replay the same request: no second effect.
  ES: Se repite el mismo pedido: no hay un segundo efecto.
- EN: The bank change? A human rejects it, and it stays rejected.
  ES: ¿El cambio de banco? Una persona lo rechaza y queda rechazado.
- EN: Then the kill switch: the next action fails.
  ES: Después el interruptor de emergencia: la siguiente acción falla.
- EN: Applied effects: one.
  ES: Efectos aplicados: uno.

## C1_log (starts 29.54 s)

- EN: Every step goes into a hash-chained log.
  ES: Cada paso queda en un registro encadenado por hash.
- EN: Here: the self-approval denied, then the effect applied once.
  ES: Acá: la autoaprobación denegada y después el efecto aplicado una sola vez.

## C2_tamper (starts 38.08 s)

- EN: Now I edit one amount after the fact.
  ES: Ahora edito un monto después del hecho.
- EN: Verification fails, at that exact line.
  ES: La verificación falla, en esa línea exacta.

## D_eval (starts 44.85 s)

- EN: Offline, thirty-seven cases pass.
  ES: Sin conexión, pasan treinta y siete casos.
- EN: Then I force a regression. The gate catches a risky effect without approval, and exits with one.
  ES: Después fuerzo una regresión. El gate detecta un efecto riesgoso sin aprobación y sale con uno.

## E_live (starts 54.29 s)

- EN: Then a real model, planner only.
  ES: Después un modelo real, solo el planificador.
- EN: Three runs and a probe: invariants clean, thirty-seven of thirty-seven, every time.
  ES: Tres corridas y una sonda: invariantes limpias, treinta y siete de treinta y siete, siempre.
- EN: Expected outcomes matched thirty-five on run one. Strictly, thirty-four.
  ES: Los resultados esperados coincidieron treinta y cinco en la primera corrida. Estrictamente, treinta y cuatro.

## F_caveat (starts 67.86 s)

- EN: Caveats. Only the planner was measured. Approvals were scripted.
  ES: Salvedades. Solo se midió el planificador. Las aprobaciones fueron guionadas.
- EN: One model, one prompt, three runs. A good sign, not a proof.
  ES: Un modelo, un prompt, tres corridas. Una buena señal, no una prueba.

## G_close (starts 78.62 s)

- EN: Next would be shadow mode. Everything past the lab is design only.
  ES: Lo siguiente sería el modo shadow. Todo lo que pasa del laboratorio es solo diseño.
- EN: Not covered: real login, tenants, a real ledger.
  ES: No cubierto: login real, tenants, un libro contable real.
- EN: ROI: E-S-T, about eleven hours a week. An estimate, not a promise.
  ES: ROI: [EST], unas once horas por semana. Una estimación, no una promesa.
