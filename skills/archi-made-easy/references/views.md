# Views from one model

L1: users, systems and business capabilities. L2: deployable containers and external stores. L3: components and integration responsibilities. Share semantic IDs across views; selecting a view must not rewrite the model.

Deployment/network: show the relevant administrative/network/security boundaries. Sequence: declare the ordered interactions; static import order and graph topology do not establish temporal order. Capability matrices suppress runtime edges deliberately and link to a deployment view.

ERD/class: add attributes and key roles; retain physical versus conceptual distinction. The current renderer displays attributes but does not claim complete UML or ER cardinality notation. State/activity: author transitions, guards and terminal behavior explicitly; generic arrows do not imply UML compliance.

Choose the primary story before layout. For large graphs, supply curated view membership rather than relying on automatic batches. Include interface/context nodes at slice boundaries; record omitted relationships. Automatic batches are a starting point, not a substitute for architectural abstraction.
