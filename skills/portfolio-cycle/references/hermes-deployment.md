# Hermes deployment (stub — G-009)

Scheduling and delivery are runtime-specific. `portfolio-cycle` and
`portfolio-brief` are fully functional without any of it.

**Not yet written.** Filed as G-009: split `portfolio-cycle` into interactive
planning plus this reference, and write `goal-cycle`.

What belongs here when it is written:

- creating recurring Hermes cron jobs for `portfolio-brief` and `goal-cycle`;
- WhatsApp delivery and `attach_to_session` for continuable jobs;
- IANA timezone configuration (`Australia/Adelaide`), not fixed UTC;
- the host-side non-destructive pusher (fast-forward only, never `--force`,
  never ref deletion, key stays on the host).

## Superseded

`legacy-slot-scheduling/` holds the previous model: frozen dated plans of up to
twelve two-hourly slots, rendered into one-shot cron payloads. It was replaced
by the continuous goal queue — work now runs until the queue empties or
something blocks, so there is nothing to freeze or allocate.

Kept because the dated plans and deployment manifests in the portfolio
repository's `archive/` refer to it. Do not build on it.
