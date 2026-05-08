"""Analysis worker — background thread pool executing subprocess jobs."""
import json
import os
import subprocess
import sys
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
            # Use sys.executable to ensure subprocess uses the same Python as the worker
            if cmd and cmd[0] == "python":
                cmd[0] = sys.executable
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
                    {"name": out.name, "path": p, "size": os.path.getsize(p),
                     "format": getattr(out, "format", ""),
                     "display": getattr(out, "display", "download")}
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
    existing = _tools.get(tool.tool_id)
    if existing:
        existing.tool_version = tool.tool_version
        for attr in ['display_name', 'description', 'category', 'inputs', 'parameters', 'outputs',
                      'timeout_seconds', 'dependencies']:
            if hasattr(tool, attr):
                setattr(existing, attr, getattr(tool, attr))
        return existing
    _tools[tool.tool_id] = tool
    return tool

def get_tools(active_only: bool = True) -> list:
    tools = list(_tools.values())
    if active_only:
        tools = [t for t in tools if getattr(t, 'tool_status', 'active') == 'active']
    return tools

def get_all_tools() -> list:
    return list(_tools.values())

def _get_tool(tool_id: str):
    return _tools.get(tool_id)

def set_tool_status(tool_id: str, status: str) -> bool:
    tool = _tools.get(tool_id)
    if not tool:
        return False
    tool.tool_status = status
    return True

def unregister_tool(tool_id: str) -> bool:
    return _tools.pop(tool_id, None) is not None


# ── Plugin install / scan ──

def _validate_whl(whl_path: str) -> bool:
    """Check .whl metadata for fance.analysis_tools entry point."""
    import zipfile, configparser, os
    if not zipfile.is_zipfile(whl_path):
        return False
    with zipfile.ZipFile(whl_path) as z:
        # Look for entry_points.txt in the .dist-info directory
        for name in z.namelist():
            if name.endswith('.dist-info/entry_points.txt'):
                cp = configparser.ConfigParser()
                cp.read_string(z.read(name).decode('utf-8', errors='replace'))
                return cp.has_section('fance.analysis_tools')
    return False

def install_whl(whl_path: str) -> list[dict]:
    """pip install a .whl file and return newly discovered tools."""
    import subprocess, importlib, os
    if not _validate_whl(whl_path):
        raise RuntimeError("Not a valid FAN-CE analysis plugin: missing 'fance.analysis_tools' entry point")
    proc = subprocess.run(["pip", "install", whl_path], capture_output=True, text=True, timeout=120)
    if proc.returncode != 0:
        raise RuntimeError(f"pip install failed: {proc.stderr[:500]}")
    importlib.invalidate_caches()
    return _scan_entry_points()

def scan_plugin_dir(plugin_dir: str) -> list[dict]:
    """Scan a directory for .whl files and install any not yet registered."""
    import subprocess, importlib, os
    discovered = []
    for f in sorted(os.listdir(plugin_dir)):
        if not f.endswith('.whl'):
            continue
        full = os.path.join(plugin_dir, f)
        if not _validate_whl(full):
            continue
        proc = subprocess.run(["pip", "install", full], capture_output=True, text=True, timeout=120)
        if proc.returncode == 0:
            discovered.append(f)
    if discovered:
        importlib.invalidate_caches()
    return _scan_entry_points()

def _scan_entry_points() -> list[dict]:
    """Scan entry_points for new tools and register them as inactive."""
    from basis.analysis.registry import discover_plugins
    new_tools = []
    for tool in discover_plugins():
        t = register_tool(tool)
        if getattr(t, 'tool_status', None) is None:
            t.tool_status = "inactive"
        new_tools.append({"tool_id": t.tool_id, "version": t.tool_version, "status": t.tool_status})
    return new_tools


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
