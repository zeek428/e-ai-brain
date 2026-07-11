from __future__ import annotations

import logging

from app.workers.execution_worker import run_execution_worker_forever

logging.basicConfig(level=logging.INFO)
run_execution_worker_forever()
