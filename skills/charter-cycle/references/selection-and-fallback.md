# Selection

`QUEUE.json` is the sole fresh execution source. Charters are ranked; requirements
use array order and declared dependencies. The user names `eligible_workers` when
a charter is authorized. A worker is eligible only when its `WORKERS.json` profile
is named and its verified capabilities cover the requirement's `requires` list.
Only active, user-authorized charters are selectable.

Themes sit above execution: they preserve direction and context but neither create
work nor route it to a worker. Drafts, paused charters, deferred requirements and
unresolved dependencies remain unavailable. An empty queue is a no-op. There is
no historical-queue or theme-derived fallback.

User steering can change order, scope or worker eligibility with a recorded
instruction; no additional ratification ritual is needed. An agent may not lift
a user deferral, assign itself to a charter or activate a draft.
