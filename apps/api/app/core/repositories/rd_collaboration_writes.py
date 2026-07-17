from __future__ import annotations

from app.core.repositories.rd_collaboration_experience_writes import (
    RdCollaborationExperienceWriteMixin,
)
from app.core.repositories.rd_collaboration_policy_writes import (
    RdCollaborationPolicyWriteMixin,
)
from app.core.repositories.rd_collaboration_scope_writes import (
    RdCollaborationScopeWriteMixin,
)
from app.core.repositories.rd_collaboration_shared import (
    RdCollaborationRepositoryError,
    RdCollaborationVersionConflictError,
    RdCollaborationWriteBase,
)
from app.core.repositories.rd_collaboration_work_writes import (
    RdCollaborationWorkWriteMixin,
)

__all__ = [
    "RdCollaborationRepositoryError",
    "RdCollaborationVersionConflictError",
    "RdCollaborationWriteRepository",
]


class RdCollaborationWriteRepository(
    RdCollaborationPolicyWriteMixin,
    RdCollaborationScopeWriteMixin,
    RdCollaborationWorkWriteMixin,
    RdCollaborationExperienceWriteMixin,
    RdCollaborationWriteBase,
):
    """Facade composing focused aggregate repositories over one transaction base."""
