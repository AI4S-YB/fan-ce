"""Analysis worker — background thread pool executing subprocess jobs."""
import json
import os
import subprocess
import threading
import time
import logging

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class AnalysisWorker:
    """Polls brd_analysis_job for pending jobs and executes them via subprocess."""

    def __init__(self, db_session_factory, num_workers: int = 2, poll_interval: float = 2.0):
        self.db_factory = db_session_factory
        self.poll_interval = poll_interval
        self.num_workers = num_workers
        self._threads = []
        self._running = False

    def start(self):
        self._running = True
        for i in range(self.num_workers):
            t = threading.Thread(target=self._loop, name=f"analysis-wkr-{i}", daemon=True)
            t.start()
            self._threads.append(t)
        logger.info(f"AnalysisWorker started with {self.num_workers} threads")

    def stop(self):
        self._running = False

    def _loop(self):
        while self._running:
            db = None
            try:
                db = self.db_factory()
                from apps.analysis.models import BrdAnalysisJob
                job = db.query(BrdAnalysisJob).filter_by(status="pending") \
                    .order_by(BrdAnalysisJob.created_at.asc()).first()
                if job:
                    self._execute(db, job)
            except Exception as e:
                logger.error(f"Worker error: {e}")
            finally:
                if db:
                    try:
                        db.close()
                    except Exception:
                        pass
            time.sleep(self.poll_interval)

    def _execute(self, db: Session, job):
        from apps.analysis.models import BrdAnalysisJob
        job.status = "running"
        job.started_at = int(time.time())
        db.commit()

        # Look up the tool instance
        tool = _get_tool(job.tool_id)
        if not tool:
            job.status = "failed"
            job.error_message = f"Unknown tool: {job.tool_id}"
            job.finished_at = int(time.time())
            db.commit()
            return

        work_dir = f"/tmp/fance-jobs/{job.id}"
        os.makedirs(work_dir, exist_ok=True)

        try:
            # Resolve input file paths from asset_file
            bindings = json.loads(job.input_bindings) if isinstance(job.input_bindings, str) else job.input_bindings
            params = json.loads(job.param_overrides) if isinstance(job.param_overrides, str) else job.param_overrides

            file_paths = {}
            for param_name, asset_file_id in bindings.items():
                from apps.datasets.models import AssetFile
                af = db.query(AssetFile).filter_by(id=asset_file_id).first()
                if not af:
                    raise FileNotFoundError(f"AssetFile id={asset_file_id} not found")
                # Use local_path if set, otherwise construct from storage_uri
                path = getattr(af, "local_path", None) or getattr(af, "storage_uri", None) or ""
                if not path or not os.path.exists(path):
                    raise FileNotFoundError(f"File not found: {path}")
                file_paths[param_name] = path

            # Build command
            cmd = tool.build_command(file_paths, params, work_dir)
            job.command_log = " ".join(cmd)

            # Execute
            proc = subprocess.run(
                cmd, capture_output=True, text=True,
                timeout=tool.timeout_seconds, cwd=work_dir,
            )

            job.exit_code = proc.returncode
            if proc.returncode == 0:
                output_paths = tool.validate_outputs(work_dir)
                job.output_files = json.dumps([
                    {"name": out.name, "path": p, "size": os.path.getsize(p)}
                    for out, p in zip(tool.outputs, output_paths)
                ], ensure_ascii=False)
                job.status = "success"
            else:
                job.status = "failed"
                job.error_message = (proc.stderr or proc.stdout or "")[:3000]

        except subprocess.TimeoutExpired:
            job.status = "timeout"
            job.error_message = f"Exceeded {tool.timeout_seconds}s limit"
        except Exception as e:
            job.status = "failed"
            job.error_message = str(e)[:3000]
        finally:
            job.finished_at = int(time.time())
            db.commit()


# ── Tool registry (in-memory for now) ──

_tools: dict = {}

def register_tool(tool):
    """Register an analysis tool instance."""
    _tools[tool.tool_id] = tool

def get_tools() -> list:
    return list(_tools.values())

def _get_tool(tool_id: str):
    return _tools.get(tool_id)


# ── Singleton ──

_worker: AnalysisWorker | None = None

def get_worker() -> AnalysisWorker | None:
    return _worker

def start_worker(db_session_factory):
    global _worker
    if _worker is not None:
        return
    _worker = AnalysisWorker(db_session_factory)
    _worker.start()

def stop_worker():
    global _worker
    if _worker:
        _worker.stop()
        _worker = None
