# Hermes deployment

This reference deploys the portable portfolio workflow on Hermes Agent. The
policy remains in `portfolio-cycle`, `portfolio-brief`, and `work-cycle`; this
file contains only runtime wiring: schedules, delivery, toolsets, workdirs,
timezone handling, testing, and recovery.

Portfolio repository: shown throughout as `/workspace/portfolio`. Substitute
your own path; nothing here depends on that particular location.

Times, timezone and delivery channel are likewise the reference deployment's,
not requirements. Pick a morning slot for the executor and a slot for the brief
that suits when the owner actually reads it.

## Topology

Use two recurring jobs and one priority source:

1. **Serial executor** — one `work-cycle` invocation at 07:30 local time. It
   takes at most one goal from `GOALS.md` and leaves routine output local.
2. **Continuable brief** — one `portfolio-brief` invocation at 12:20 local
   time, delivered to a chat channel shortly before a natural break in the
   owner's day. It condenses the morning result, decisions, runway, and anything
   needing attention.

Do not create one cron job per goal. That duplicates queue state in the
scheduler and lets schedules drift from `GOALS.md`. Do not let the brief create
executor jobs: `portfolio-brief` reports and proposes but does not dispatch.

Start with one executor run per day. Add another only after the serial flow has
shown useful throughput and the claim/lock path has been exercised.

## Timezone prerequisite

Recurring cron expressions use Hermes's configured IANA timezone. Verify:

```bash
hermes config set timezone <Area/City>
```

If the timezone changed, restart the long-running gateway through its supported
external mechanism **before** creating or testing the jobs; the scheduler caches
timezone state. Never encode the zone as a fixed UTC offset — a zone with
daylight saving will silently drift by an hour.

After creation and after every manual test, verify that `next_run_at` still has
the correct local wall-clock time and seasonal offset. Successful delivery
alone does not prove recurrence was recomputed in the intended timezone.

Authoritative Hermes documentation:
https://hermes-agent.nousresearch.com/docs/user-guide/features/cron

## Job 1: serial goal executor

Configuration:

```text
name: portfolio-work-cycle-morning
schedule: 30 7 * * *
workdir: /workspace/portfolio
skills: [work-cycle]
deliver: local
enabled_toolsets: [file, terminal, skills, web, browser]
attach_to_session: false
```

Prompt:

```text
Run one work-cycle against /workspace/portfolio. Execute at most one goal. The
queue is the sole priority source: do not create replacement work, re-rank it,
or enter a project not named by the selected goal. Commit project and portfolio
changes, but do not push; the host-side pusher owns automatic pushes. Routine
results remain local for the 12:20 portfolio brief. Record partial work,
blockers, failures, and ask-class decisions in the portfolio log so the brief
can condense them. Never interact with an unrelated dirty or locked repository.
```

The worker is deterministic at the portfolio level: highest-priority eligible
goal, one goal, one run. The selected project still controls implementation via
its own `AGENTS.md`, `CLAUDE.md`, tests, and repository state.

A local delivery is deliberate. Routine completion, partial progress, and
ordinary blockers wait for the brief rather than interrupting the owner at
work.
Safety incidents or unexpected external exposure are exceptions: stop, record
the issue durably, and rely on the next brief unless the active platform policy
provides an explicitly authorised urgent-alert path.

## Job 2: continuable portfolio brief

Configuration:

```text
name: portfolio-brief-daily
schedule: 20 12 * * *
workdir: /workspace/portfolio
skills: [portfolio-brief]
deliver: <chat-channel>
enabled_toolsets: [file, terminal, skills, cronjob]
attach_to_session: true
```

Prompt:

```text
Run portfolio-brief against /workspace/portfolio. Reconcile repository evidence
and the most recent portfolio-work-cycle-morning status into one concise brief.
Deliver the normal brief even when little moved. Condense anything needing the owner
rather than emitting separate routine executor notifications. Do not execute a
goal, re-order the queue, approve a proposal, or change scheduled jobs.
```

`attach_to_session` makes the delivered brief continuable: a reply can
retain the report context instead of starting from an isolated delivery. Any
subsequent strategy or queue change proceeds interactively under
`portfolio-cycle`; a reply does not grant the brief extra authority.

**Hermes v0.19.0 verification note:** that release's cron tool schema and
scheduler support `attach_to_session`, but its registered tool handler omits the
argument when forwarding calls. A tool update can therefore report success
without persisting the field. Always read the stored job back and confirm
`attach_to_session: true`. Until the handler is fixed, set it through Hermes's
locked `cron.jobs.update_job` API rather than editing `jobs.json` directly. Do
not enable global `cron.mirror_delivery` merely to work around one brief job;
that changes continuation behaviour for unrelated deliveries.

The `cronjob` toolset is read-only by policy in this job. It exists so the brief
can inspect whether the morning executor ran or failed. The prompt and
`portfolio-brief` authority explicitly prohibit scheduler mutation.

## Creating or updating jobs

Use Hermes's `cronjob` tool or supported CLI. Prefer updating an existing job
when it represents the same responsibility; remove obsolete jobs rather than
leaving paused duplicates that can later be resumed accidentally.

When using the tool, set the complete prompt, schedule, skill list, delivery,
toolsets, workdir, and continuation flag explicitly. Cron runs in a fresh
session, so the prompt must be self-contained, but workflow policy should remain
in the attached skill rather than being copied into a long scheduler prompt.

## Verification

For each job:

1. List the job and inspect its full configuration.
2. Confirm the attached skill exists and the workdir is exactly
   `/workspace/portfolio`.
3. Confirm `next_run_at` represents each intended time in the configured zone.
4. Trigger one manual run.
5. Confirm execution status and delivery status.
6. Re-list the job and verify the recomputed next occurrence retains the correct
   local wall-clock time and UTC offset.

A safe executor test may legitimately no-op when the queue, claim, lock, dirty
worktree, or decision boundary says it should. The test is successful when it
follows the protocol and records the reason; do not substitute unrelated work to
manufacture activity.

For the brief, verify both delivery and continuation by replying to the test
delivery. A manual test should be clearly labelled as a test so it cannot be
mistaken for a scheduled brief.

## Host-side pusher

Agents create ordinary commits where `PROJECTS.json` permits `commit`; they do
not push from `work-cycle`. The host-side pusher is the only automatic push path.
Its contract remains:

- read `agent_may` from `/workspace/portfolio/PROJECTS.json`;
- fast-forward pushes only;
- never `--force` and never delete refs;
- keep the dedicated key on the host, outside agent containers;
- write its gitignored `.pusher-*.md` record for the next brief to fold into a
  committed portfolio log entry.

This separation limits credential exposure and prevents every executor from
becoming its own deployment mechanism.

## Recovery

- **Skill missing:** pause the affected job or update its attached skill before
  the next run. Do not rely on fallback behavior.
- **Workdir missing:** treat the run as invalid. Correct the job; never continue
  detached from the portfolio repository.
- **Stale timezone after a test:** reapply the schedule from a fresh process,
  restart the gateway, and verify `next_run_at` again.
- **Executor repeatedly blocked:** leave the goal and evidence intact. Discuss
  queue shape under `portfolio-cycle`; do not make the worker skip strategically.
- **Old job superseded:** remove it after the replacement passes its manual test.

## Superseded model

`legacy-slot-scheduling/` holds the previous frozen plan of up to twelve
one-shot slots. The continuous queue replaced it: work now proceeds one goal per
executor invocation until the queue empties or a boundary blocks it. The archive
remains only because historical portfolio records refer to it. Do not build new
jobs from those templates.
