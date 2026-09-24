# Worker profiles and close-outs

`WORKERS.json` is installation configuration beside `QUEUE.json`. Its machine-readable
shape is `../assets/workers.schema.json`; the helper additionally enforces that the
reserve is smaller than the total budget and that configured paths resolve inside
the portfolio. It records facts about available scheduled workers; it never assigns
strategic priority.
A profile has a stable id and holder prefix, verified capabilities, an explicit
wind-down budget, a structured report sink, and an independently inspectable
health source. Paths are relative to the portfolio and may not escape it. An
optional `max_job_hours` says the worker's host keeps a detached job running
after the session for up to that long; without it the worker cannot start one.

Example (invented):

```json
{
  "version": 1,
  "timezone": "Etc/UTC",
  "workers": [{
    "id": "general-morning",
    "holder_prefix": "general-morning",
    "capabilities": ["general", "network"],
    "wind_down": {"minutes": 50, "reserve_minutes": 10},
    "report_sink": ".briefing/daily",
    "health": {"kind": "hermes-cron", "job_id": "example-job"}
  }]
}
```

The charter records `eligible_workers`; each requirement records `requires`.
Selection preserves charter and requirement order after checking explicit worker
eligibility, capabilities, dependencies, claims, repository permissions and
availability. Themes do not choose a worker. An active requirement that no named
worker can execute is invalid configuration.

After lifecycle close-out and `check-exit`, a scheduled worker calls `report` once.
The queue retains immutable transition records keyed by holder, so a later worker
cannot invalidate an earlier run's close-out. A transition must also name a
configured worker's holder prefix, so the record is attributable rather than a free
string. The helper requires the control repository transition to be committed,
serializes the append, writes a human-readable daily Markdown document, embeds a
machine-readable entry, and rejects duplicate run ids. `reports --since <ISO
timestamp>` supports diagnostics.

Scheduled briefs use `brief-window --previous-delivery <status> --through <ISO>`
with an optional `--earliest` floor. Its gitignored cursor advances only when the
prior delivery is confirmed successful; failed or unknown delivery replays the
unsent interval across calendar files, and the floor bounds the window only while
nothing has ever been confirmed delivered.

Close-outs are transport, not canonical evidence. Keep them bounded: terminal
state, item, result, direct evidence references and an exact continuation or
blocker. A missing close-out does not prove a scheduler missed its run; the brief
checks the profile's health source independently and distinguishes scheduler
state, worker self-report and repository evidence.
