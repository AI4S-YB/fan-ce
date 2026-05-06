"""FRP tunnel service — manages frpc subprocess lifecycle."""
import os
import platform
import signal
import subprocess
import time
from pathlib import Path

import requests

FRPC_BIN_DIR = Path.home() / ".fan-ce"
FRPC_BIN = FRPC_BIN_DIR / "frpc"
FRPC_VERSION = "0.61.0"

# Download mirrors: domestic CDN first, GitHub fallback
FRPC_DOWNLOAD_URLS = [
    "https://ghproxy.com/https://github.com/fatedier/frp/releases/download/v{version}/frp_{version}_{platform}.tar.gz",
    "https://gh.con.sh/https://github.com/fatedier/frp/releases/download/v{version}/frp_{version}_{platform}.tar.gz",
    "https://github.com/fatedier/frp/releases/download/v{version}/frp_{version}_{platform}.tar.gz",
]

# Runtime state (in-memory, not persisted across restarts)
_frpc_process: subprocess.Popen | None = None
_frpc_started_at: float | None = None
_frpc_last_error: str | None = None
_frpc_pid_file: Path = FRPC_BIN_DIR / "frpc.pid"


def _get_platform_suffix() -> str:
    """Return 'darwin_amd64', 'linux_amd64', or 'windows_amd64'."""
    system = platform.system().lower()
    if system == "darwin":
        return "darwin_amd64"
    elif system == "linux":
        return "linux_amd64"
    elif system == "windows":
        return "windows_amd64"
    raise RuntimeError(f"Unsupported platform: {system}")


def _download_frpc() -> bool:
    """Download frpc binary to ~/.fan-ce/frpc. Returns True on success."""
    FRPC_BIN_DIR.mkdir(parents=True, exist_ok=True)
    plat = _get_platform_suffix()

    for url_template in FRPC_DOWNLOAD_URLS:
        url = url_template.format(version=FRPC_VERSION, platform=plat)
        try:
            import io
            import tarfile
            resp = requests.get(url, timeout=15, stream=True)
            resp.raise_for_status()
            with tarfile.open(fileobj=io.BytesIO(resp.content), mode="r:gz") as tar:
                for member in tar.getmembers():
                    if member.name.endswith("frpc") and not member.isdir():
                        extracted = tar.extractfile(member)
                        if extracted:
                            FRPC_BIN.write_bytes(extracted.read())
                            FRPC_BIN.chmod(0o755)
                            return True
        except Exception:
            continue

    return False


def _generate_config(settings) -> str:
    """Generate frpc.ini content from PlatformSiteSetting. Returns config file path."""
    config = f"""[common]
server_addr = {settings.frp_server_addr}
server_port = {settings.frp_server_port}
token = {settings.frp_token}

[public-web]
type = tcp
local_ip = 127.0.0.1
local_port = 80
remote_port = {settings.frp_public_port}

[backend-api]
type = tcp
local_ip = 127.0.0.1
local_port = 8002
remote_port = 8002
"""
    FRPC_BIN_DIR.mkdir(parents=True, exist_ok=True)
    config_path = FRPC_BIN_DIR / "frpc.ini"
    config_path.write_text(config)
    return str(config_path)


def start_frpc(settings) -> dict:
    """Start frpc tunnel. settings is a PlatformSiteSetting ORM object.
    Returns dict with frp_status, public_url, api_url, pid on success,
    or frp_status='error' with error message.
    """
    global _frpc_process, _frpc_started_at, _frpc_last_error

    # Validate required fields
    if not settings.frp_server_addr or not settings.frp_token:
        _frpc_last_error = "云服务器IP和Token不能为空"
        return {"frp_status": "error", "error": _frpc_last_error}

    # Download frpc if needed
    if not FRPC_BIN.exists():
        ok = _download_frpc()
        if not ok:
            _frpc_last_error = (
                "frpc 二进制下载失败。请手动下载 frpc 到 "
                + str(FRPC_BIN)
                + "，下载地址: https://github.com/fatedier/frp/releases"
            )
            return {"frp_status": "error", "error": _frpc_last_error}

    # Stop existing process if running
    if _frpc_process is not None:
        stop_frpc()

    # Generate config and start
    config_path = _generate_config(settings)
    try:
        _frpc_process = subprocess.Popen(
            [str(FRPC_BIN), "-c", config_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        _frpc_started_at = time.time()
        _frpc_pid_file.write_text(str(_frpc_process.pid))
        _frpc_last_error = None
    except Exception as e:
        _frpc_last_error = str(e)
        return {"frp_status": "error", "error": str(e)}

    public_url = f"http://{settings.frp_server_addr}"
    if settings.frp_public_port and settings.frp_public_port != 80:
        public_url += f":{settings.frp_public_port}"

    return {
        "frp_status": "running",
        "public_url": public_url,
        "api_url": f"http://{settings.frp_server_addr}:8002",
        "pid": _frpc_process.pid,
    }


def stop_frpc() -> dict:
    """Stop frpc process gracefully (SIGTERM then SIGKILL after 5s)."""
    global _frpc_process, _frpc_started_at

    if _frpc_process is None:
        # Try reading PID from file (survived process restart but state lost)
        if _frpc_pid_file.exists():
            try:
                pid = int(_frpc_pid_file.read_text().strip())
                os.kill(pid, signal.SIGTERM)
                _frpc_pid_file.unlink()
            except (ProcessLookupError, ValueError):
                if _frpc_pid_file.exists():
                    _frpc_pid_file.unlink()
        return {"frp_status": "stopped"}

    try:
        _frpc_process.terminate()
        _frpc_process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        _frpc_process.kill()
        _frpc_process.wait()

    _frpc_process = None
    _frpc_started_at = None
    if _frpc_pid_file.exists():
        _frpc_pid_file.unlink()

    return {"frp_status": "stopped"}


def get_frpc_status(settings) -> dict:
    """Query current frpc tunnel status. settings is a PlatformSiteSetting ORM object."""
    global _frpc_process, _frpc_started_at, _frpc_last_error

    public_url = None
    api_url = None
    if settings.frp_server_addr:
        public_url = f"http://{settings.frp_server_addr}"
        if settings.frp_public_port and settings.frp_public_port != 80:
            public_url += f":{settings.frp_public_port}"
        api_url = f"http://{settings.frp_server_addr}:8002"

    result = {
        "frp_status": settings.frp_status or "stopped",
        "pid": None,
        "public_url": public_url,
        "api_url": api_url,
        "last_error": _frpc_last_error,
        "uptime_seconds": None,
    }

    if _frpc_process is not None:
        poll = _frpc_process.poll()
        if poll is None:
            # Process still running
            result["pid"] = _frpc_process.pid
            if _frpc_started_at:
                result["uptime_seconds"] = int(time.time() - _frpc_started_at)
        else:
            # Process exited unexpectedly
            result["frp_status"] = "error"
            try:
                stderr = _frpc_process.stderr.read().decode(errors="replace") if _frpc_process.stderr else ""
                result["last_error"] = stderr[-500:] if stderr else f"frpc exited with code {poll}"
            except Exception:
                result["last_error"] = f"frpc exited with code {poll}"
            _frpc_last_error = result["last_error"]

    return result
