"""RQ worker entry point."""

import os
import sys
import logging
import redis
import multiprocessing

# Fix macOS fork() crash with Obj-C runtime
if sys.platform == "darwin":
    os.environ["OBJC_DISABLE_INITIALIZE_FORK_SAFETY"] = "YES"

# Patch multiprocessing for Windows to prevent RQ import from crashing
if sys.platform == "win32":
    _original_get_context = multiprocessing.get_context
    def _patched_get_context(method=None):
        if method == "fork":
            return _original_get_context("spawn")
        return _original_get_context(method)
    multiprocessing.get_context = _patched_get_context

from rq import Worker
from rq.worker import SimpleWorker

# Load .env from project root
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "../../.env"))

from worker.config import REDIS_URL, QUEUE_NAME
from worker.callbacks import handle_job_failure

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass  # No console attached (e.g. Start-Process)

log_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "worker.log")
logging.basicConfig(
    level=logging.ERROR,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ],
    force=True
)
logger = logging.getLogger("worker")

if __name__ == "__main__":
    logger.info(f"REDIS_URL: {REDIS_URL}")
    logger.info(f"Queue: {QUEUE_NAME}")
    logger.info(f"OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES")

    conn = redis.from_url(REDIS_URL)
    
    worker_cls = SimpleWorker if sys.platform == "win32" else Worker
    worker = worker_cls(
        [QUEUE_NAME],
        connection=conn,
        exception_handlers=[handle_job_failure],
    )
    logger.info("Worker started, waiting for jobs...")
    worker.work(logging_level="DEBUG")
