# Hermes deployment

This reference deploys the portable portfolio workflow on Hermes Agent. The
policy remains in `portfolio-cycle`, `portfolio-brief`, and `work-cycle`; this
file contains only runtime wiring: schedules, delivery, toolsets, workdirs,
timezone handling, testing, and recovery.

Portfolio repository: shown throughout as `<portfolio-path>`. Substitute the
deployment's absolute path; nothing here depends on a particular location.

Times, timezone and delivery channel are likewise the reference deployment's,
not requirements. Pick a morning slot for the executor and a slot for the brief
that suits when the owner actually reads it.

## Topology

Use two recurring jobs and one priority source:

1. **Serial executor** — one recurring `work-cycle` invocation. It uses an
   explicit caller-declared budget measured only in fully closed goals and
   leaves routine output local. A deployment may apply an explicit lane
   allocation before queue-order selection; without one, follow queue order.
2. **Continuable brief** — one recurring `portfolio-brief` invocation,
   delivered to a chat channel shortly before a natural break in the owner's
   day. It condenses the latest executor result, decisions, runway, and anything
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
name: <executor-job>
schedule: <executor-cron>
workdir: <portfolio-path>
skills: [work-cycle]
deliver: local
enabled_toolsets: [file, terminal, skills, web, browser]
attach_to_session: false
```

Prompt:

```text
Run work-cycle against <portfolio-path> under a caller-declared budget of <N>
fully closed goals. Apply any explicit deployed lane allocation, preserve queue
order within its eligible set, and never create replacement work. Count an item
only after project work, lifecycle state, log, portfolio commit, and
clean-worktree verification are complete. Stop rather than selecting another
item when close-out is incomplete. Commit project and portfolio changes, but do
not push; the deployment's publication mechanism owns automatic pushes. Routine
results remain local for the later portfolio brief.
```

The worker is deterministic at the portfolio level: explicit lane allocation,
then queue order within each eligible set, with the budget counted only at
durable lifecycle boundaries. Without a declared allocation it follows the raw
queue. The selected project still controls implementation via its own
`AGENTS.md`, `CLAUDE.md`, tests, and repository state.

A local delivery is deliberate. Routine completion, partial progress, and
ordinary blockers wait for the brief rather than interrupting the owner at
work.
Safety incidents or unexpected external exposure are exceptions: stop, record
the issue durably, and rely on the next brief unless the active platform policy
provides an explicitly authorised urgent-alert path.

## Job 2: continuable portfolio brief

Configuration:

```text
name: <brief-job>
schedule: <brief-cron>
workdir: <portfolio-path>
skills: [portfolio-brief]
deliver: <chat-channel>
enabled_toolsets: [file, terminal, skills, cronjob]
attach_to_session: true
```

Prompt:

```text
Run portfolio-brief against <portfolio-path>. Reconcile repository evidence and
the most recent <executor-job> status into the recurring queue window: recent
completions, the first five open goals with owner and routing state, the actual
executor-selected next goal, anomalies, and up to two non-duplicated user items
outside the window. Deliver it even when little moved. Do not execute a goal,
re-order the queue, approve a proposal, or change scheduled jobs.
```

`attach_to_session` makes the delivered brief continuable: a reply can
retain the report context instead of starting from an isolated delivery. Any
subsequent strategy or queue change proceeds interactively under
`portfolio-cycle`; a reply does not grant the brief extra authority.

Always read the stored job back and confirm `attach_to_session: true`; a tool
update response is not proof that the scheduler persisted every field. Use a
supported locked API or CLI rather than editing scheduler storage directly. Do
not enable a global continuation setting merely to work around one brief job;
that changes behaviour for unrelated deliveries.

### Diagnose continuation by layer

A delivered brief and a continuable reply require three separate facts:

1. **Delivery:** the platform received the message.
2. **Attachment:** the stored job is continuable and the labelled cron turn was
   written into the intended chat transcript.
3. **Routing:** the chat routes to an active canonical session rather than stale
   session metadata.

Verify them in that order. Compare the attached session's canonical end state
with the gateway's routing entry, and corroborate daemon warnings against live
process or inbound-message evidence. Configuration-file state and the state
loaded by a long-running gateway are also distinct. Apply lifecycle changes and
gateway restarts only through a supported external mechanism; a worker inside
the gateway must not restart its own parent. After repair, send a clearly
labelled test brief and reply to it—successful delivery alone is not a
continuation test.

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

Do not infer that a capability is absent from the deployment merely because the
scheduled worker lacks a CLI. An interactive session with the `cronjob` tool and
a reachable gateway may be the administrative lane. Probe the current tool
before filing a user blocker, then record the narrower capability boundary.

## Verification

For each job:

1. List the job and inspect its full configuration.
2. Confirm the attached skill exists and the workdir is exactly the configured
   `<portfolio-path>`.
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

### Prove workflow migrations with pipecleaners

Configuration that looks plausible is not a completed migration. For each
distinct operating mode, use a disposable repository or sentinel item when
production work would otherwise be consumed. Verify from durable evidence:

- exact sentinel bytes or artifact behaviour;
- verifier/test exit status;
- task or goal transitions and separate commits;
- debrief or portfolio log;
- clean worktrees and lock release;
- persisted job configuration and stored run output.

Remove disposable jobs and repositories only after inspecting those outputs.
Read the production job back, but do not fire it merely to prove a migration if
that would consume real queued work.

### Observe the first real runs

After two or three real invocations, reconcile the causal chain rather than
trusting a successful scheduler status or polished brief: scheduler record,
claim, lock lifecycle, project commit and objective checks, portfolio close-out,
publication evidence where applicable, and the brief's resulting claims. Check
ordering failures as well as missing artifacts. In particular, do not remove a
project's publish eligibility while required commits are still ahead of the
remote. Treat remote parity, deployment health, and browser-visible behaviour as
separate claims.

Calibrate frequency from completed outcomes, including partial and no-op runs,
not from configured schedule capacity. Define how a released partial lock is
reacquired so the next worker resumes the existing claim before later work.

## Host-side pusher

Agents create ordinary commits where `PROJECTS.json` permits `commit`; they do
not push from `work-cycle`. The host-side pusher is the only automatic push path.
Its contract remains:

- read `agent_may` from `<portfolio-path>/PROJECTS.json`;
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

`legacy-slot-scheduling/` holds a previous frozen-slot model. The continuous
queue replaced it: work now proceeds up to the caller-declared closed-item
budget until the queue empties or a boundary blocks it. The archive remains only
for historical reference. Do not build new jobs from those templates.
