from __future__ import annotations

import os
from datetime import UTC, datetime
from itertools import count

_SLUG_COUNTER = count()


def regression_slug(prefix: str = "full-chain") -> str:
    timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S%f")
    return f"{prefix}-{timestamp}-{os.getpid()}-{next(_SLUG_COUNTER)}"
