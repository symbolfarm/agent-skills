# Selection

`QUEUE.json` is the sole fresh execution source. Charters are ranked; requirements
use array order and declared dependencies. A lane selects its own lane or `any`,
with verified capabilities. Only active, user-authorized charters are selectable.
Drafts, paused charters, deferred requirements and unresolved dependencies remain
unavailable. An empty queue is a no-op. There is no historical-queue fallback.

User steering can change order or scope with a recorded instruction; no additional
ratification ritual is needed. An agent may not lift a user deferral itself.
