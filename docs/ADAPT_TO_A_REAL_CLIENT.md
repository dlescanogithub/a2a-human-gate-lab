# Adapt to a real client

Short version. Do not rename Nube Austral to a real company inside this repo.

1. Run the ten questions in [DISCOVERY.md](DISCOVERY.md). Write the answers down. If the amount does not come from a system of record, stop.
2. Replace the YAML thresholds with the client's bands. Keep zero and the over-cap band forbidden until someone argues otherwise.
3. Keep the requester from approving. If their policy says otherwise, that is a different product.
4. Point the effect at their ledger behind the same idempotency key. Add a reversing entry they already have. The kill switch still does not undo a post.
5. Leave the cassette gate in CI. Add their cases as invariants (no effect without the second person, rejection sticks). Do not freeze a tool-call transcript.
6. Identity, email, and hosting stay out until the gate is already green without them.
7. Do not turn on `LIVE_MODE` in CI. A measured model run is a separate note with a date, a command, and a public price URL.

This lab is the shape of the control. It is not the client's system.
