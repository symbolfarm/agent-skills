> Historical topology discussion. Fresh charter execution uses the shared
> QUEUE.json helper and serial active claims. Older goal-selection and commit-as-lock
> claims below are superseded; consult charter-cycle for current behavior.

# Executor topology decisions

Load this reference during `portfolio-cycle` when deciding how approved portfolio
work should be allocated to unattended workers. It compares mechanisms; reading
it is not authorization to create or change jobs.

## Shared contract

Interactive planning owns strategy: project state, queue order, charter authority,
and eligible-worker assignment. Executors own mechanics: validate their assignment,
select deterministically, enter one repository, read its local instructions, and
close or preserve an exact continuation.

The portfolio queue remains the sole strategic priority. Worker profiles record
factual capabilities and operating limits, not preferences. The user names each
charter's eligible workers at authorization; within that eligible set preserve
queue order. Themes provide context above execution and never route work.

## Per-project workers

One recurring worker per active project, each with a fixed workdir and narrow
permissions.

Strengths:

- strong context, tool, and credential isolation;
- local instructions are injected naturally;
- failures and schedules are easy to attribute;
- disjoint repositories can run concurrently.

Costs:

- scheduler configuration grows with the project set;
- idle workers still wake;
- changing allocation requires scheduler changes;
- independent workers need durable claims and an explicit fairness policy.

## One serial portfolio worker

One recurring worker reads the portfolio, selects through the deployed routing
contract, and enters one project at a time.

Strengths:

- one stable scheduler job;
- central queue and capability handling;
- natural same-worktree serialisation;
- allocation changes can remain portfolio data rather than job proliferation.

Costs:

- it must explicitly load the selected repository's instructions;
- it needs permissions broad enough for several projects;
- throughput is serial and the worker is a single failure point;
- one model/tool policy must cover several work classes.

This is the default starting point when throughput has not yet proved it
insufficient.

## Fixed slot workers

Keep a bounded number of recurring workers, give each a factual worker profile,
and assign charters explicitly to one or more eligible workers.

Strengths:

- bounded concurrency independent of project count;
- one blocked worker need not stop another repository;
- allocation can change without creating a job per project.

Costs:

- two workers can race on the portfolio claim or collide in a repository;
- dynamic project context remains explicit;
- fallback rules can smuggle strategic judgement into execution;
- slots need precise budget-consumption and recovery semantics.

Do not point concurrent workers at one worktree without atomic claims plus
repository locks, or isolated worktrees and a merge protocol.

## Selection and capacity

Keep these concepts separate:

- queue position: strategic priority;
- charter eligibility: which named workers the user authorized;
- capability: whether an eligible worker can execute a requirement at all;
- wind-down budget: when a worker must preserve continuation and close out;
- repository availability: whether the selected worktree can safely be edited.

A deployed worker resumes its own claim first, then scans authorized charters in
queue order, applying explicit worker eligibility, capability, dependency, claim
and repository-availability checks. There is no theme-derived or historical
fallback set.

## Migration and first-run proof

State readiness on four independent axes before launching work:

- **policy:** scope, authority, routing, budget, and stop rules are settled;
- **repository:** worktree, lock, instructions, and objective checks are ready;
- **queue:** an approved eligible item actually exists;
- **scheduler:** the job/runtime is installed, enabled, and verified.

"The setup supports execution" may describe policy and repository readiness while
no task is filed and no job is running. Keep the distinction explicit.

### Immediate bounded execution

Do not route an explicit "run this now" request through delayed scheduling only
for procedural symmetry. An interactive immediate cycle is eligible when the
user has approved the exact outcome or finite batch, the repository is clean and
unlocked, objective checks exist, the queue items are filed or can be
mechanically transcribed from that approval, and no protected or irreversible
decision is crossed.

State the four readiness axes, claim the finite items, execute them sequentially
through `work-cycle`, and close every lifecycle before starting the next. When
the declared budget is exhausted, stop at the human review boundary. Leave
project state unchanged unless the already-approved contract explicitly says to
pause or park it on exhaustion; capacity is never permission to invent another
item. Preserve the same task transitions, commits, debriefs, validation, locks,
and portfolio reconciliation as a scheduled cycle.

Start with the simplest topology that meets the need. Before calling a migration
complete:

1. exercise every distinct mode with a disposable repository or sentinel item;
2. verify claim commits, lock creation/release, project commits, tests, lifecycle
   close-out, and clean worktrees from durable evidence;
3. verify scheduler configuration and stored output separately;
4. prove a truncated multi-item run leaves earlier items fully closed;
5. confirm partial claims have an explicit lock-reacquisition path;
6. observe two or three real runs before increasing concurrency or frequency.

A configured worker is not an executed outcome, and schedule frequency is not
completion rate. Expand only after recovery, collision handling, and the user's
review bandwidth have behaved acceptably.
