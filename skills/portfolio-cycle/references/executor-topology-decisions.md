# Executor topology decisions

Load this reference during `portfolio-cycle` when deciding how approved portfolio
work should be allocated to unattended workers. It compares mechanisms; reading
it is not authorization to create or change jobs.

## Shared contract

Interactive planning owns strategy: project state, queue order, lane allocation,
and which outcomes are approved. Executors own mechanics: validate their
assignment, select deterministically, enter one repository, read its local
instructions, run `work-cycle`, verify, commit, and close the lifecycle.

The portfolio queue remains the sole strategic priority. A deployment may define
an explicit lane allocation or eligible set—for example by capability or work
class—but must name it as routing rather than claiming the raw queue was
reordered. Within an eligible set, preserve queue order. The brief should show
both the raw queue window and the actual routed selection.

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

Keep a bounded number of recurring workers and assign each an explicit lane or
eligible set.

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
- lane allocation: which subset a worker serves first or exclusively;
- capability: whether the worker can execute an item at all;
- run budget: how many fully closed items one invocation may consume;
- repository availability: whether the selected worktree can safely be edited.

Every deployed selection algorithm must state its order of operations. A useful
baseline is: resume this worker's claim; apply explicit lane allocation; scan
that eligible set in queue order; apply assignee, gate, capability, claim, and
repository-availability checks; then use any declared fallback set in queue
order. If there is no explicit allocation, scan the canonical queue directly.

## Migration and first-run proof

State readiness on four independent axes before launching work:

- **policy:** scope, authority, routing, budget, and stop rules are settled;
- **repository:** worktree, lock, instructions, and objective checks are ready;
- **queue:** an approved eligible item actually exists;
- **scheduler:** the job/runtime is installed, enabled, and verified.

"The setup supports execution" may describe policy and repository readiness while
no task is filed and no job is running. Keep the distinction explicit.

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
