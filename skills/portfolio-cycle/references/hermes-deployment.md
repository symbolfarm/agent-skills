# Hermes deployment

Keep scheduler configuration separate from workflow policy. Use one fresh charter
queue and the `charter-cycle` skill for execution; `portfolio-brief` reports between
reviews. A scheduler prompt names the portfolio and worker profile in plain language,
plus any deployment boundary not already represented there. `WORKERS.json` supplies
capabilities, wind-down budget, health source and report sink; authorized charters
name eligible workers. Never copy queue policy into cron prompts or fall back to
historical work.

Preserve existing schedule, timezone, model and delivery settings unless the user
changes them. Inspect actual stored jobs rather than inferring from documentation.
Update an existing job for the same responsibility; do not create a duplicate.
Use the supported administration tool in the runtime that owns the scheduler.
Repository edits alone do not deploy a job or an installed host script.

Verify persisted prompt, attached skill, workdir, enabled state and next occurrence
with its timezone offset. Confirm shared skills resolve to the current checkout.
If configuration cannot load, pause the affected job and report the problem.
An empty fresh queue can test routing without consuming production work; do not
manufacture experiments or contact external recipients to prove deployment.

For an existing brief, preserve the authorized channel and continuation settings.
Update its data source alongside the executor so it does not solicit retired work.
Sending a message and retaining reply context are separate verification outcomes.

Keep host-only publication credentials and installation boundaries intact. Mark
source preparation, live installation and observed execution separately in the
private deployment record. Do not report a scheduler updated until it is read back.
