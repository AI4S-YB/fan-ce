# FRP 数据共享隧道 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让用户通过 Admin-Web 一键开启 frp 隧道，将自己本地 FAN-CE 实例的数据通过云服务器固定 IP 对外共享。

**Architecture:** 扩展 `pf_site_setting` 表（7 个新字段），新增 `frp_service.py` 管理 frpc 子进程，在 Admin-Web 平台设置页新增隧道控制卡片，portal-web 支持可配置 API 地址。

**Tech Stack:** Python 3.11+ (subprocess), FastAPI, SQLAlchemy 2.0, Vue 3 + Ant Design Vue, frp (MIT)

**Dependencies:** frp 二进制（运行时自动下载），不引入新的 Python/JS 依赖包。

---

## File Map

### Backend
| Action | File | Responsibility |
|--------|------|----------------|
| Create | `backend/api-server/alembic/versions/<hash>_add_frp_to_site_setting.py` | DB migration |
| Modify | `backend/api-server/apps/platform/models.py:31-49` | Add frp columns to PlatformSiteSetting |
| Modify | `backend/api-server/apps/platform/schemas.py` | Add frp request/response schemas |
| Create | `backend/api-server/apps/platform/frp_service.py` | frpc lifecycle (download/start/stop/status) |
| Modify | `backend/api-server/apps/platform/api/setting.py` | Add 4 frp endpoints |
| Create | `backend/api-server/static/install-frps.sh` | frps cloud server install script |

### Frontend (Admin-Web)
| Action | File | Responsibility |
|--------|------|----------------|
| Modify | `frontend/admin-web/apps/web-antd/src/api/platform/setting.ts` | Add frp API functions + types |
| Create | `frontend/admin-web/apps/web-antd/src/views/platform/components/FrpTunnelCard.vue` | Tunnel control card component |
| Modify | `frontend/admin-web/apps/web-antd/src/views/platform/setting.vue` | Import and render FrpTunnelCard |
| Modify | `frontend/admin-web/apps/web-antd/src/locales/langs/zh-CN/platform.json` | Chinese labels |
| Modify | `frontend/admin-web/apps/web-antd/src/locales/langs/en-US/platform.json` | English labels |

### Frontend (Portal-Web)
| Action | File | Responsibility |
|--------|------|----------------|
| Modify | `frontend/portal-web/vite.config.ts` | Proxy target 8001 → 8002 |
| Modify | `frontend/portal-web/src/App.vue` | Use configurable API_BASE_URL |

---

### Task 1: Database Migration — add frp columns to pf_site_setting

**Files:**
- Create: `backend/api-server/alembic/versions/<auto_hash>_add_frp_columns_to_site_setting.py`
- Modify: `backend/api-server/apps/platform/models.py:31-49`

- [ ] **Step 1: Add frp columns to PlatformSiteSetting model**

```python
# In apps/platform/models.py, inside PlatformSiteSetting class, add after extra_json:

    frp_enabled = Column(Boolean, default=False, comment="是否启用隧道共享")
    frp_server_addr = Column(String(255), nullable=True, comment="云服务器IP地址")
    frp_server_port = Column(Integer, default=7000, comment="frps绑定端口")
    frp_token = Column(String(255), nullable=True, comment="frps与frpc认证密钥")
    frp_public_port = Column(Integer, default=80, comment="对外HTTP端口")
    frp_status = Column(String(32), default="stopped", comment="隧道状态: stopped/running/error")
    frp_config_json = Column(Text, nullable=True, comment="高级自定义frpc配置JSON")
```

- [ ] **Step 2: Update to_dict() to include new fields**

In the `to_dict()` method of PlatformSiteSetting, add the new fields to the returned dict.

- [ ] **Step 3: Generate and run Alembic migration**

```bash
cd backend/api-server && alembic revision --autogenerate -m "add_frp_columns_to_site_setting"
alembic upgrade head
```

- [ ] **Step 4: Verify in database**

```bash
# Check columns exist
python -c "
from db.session import SessionLocal
from sqlalchemy import inspect
db = SessionLocal()
cols = [c['name'] for c in inspect(db.bind).get_columns('pf_site_setting')]
print([c for c in cols if c.startswith('frp_')])
"
```

Expected: `['frp_enabled', 'frp_server_addr', 'frp_server_port', 'frp_token', 'frp_public_port', 'frp_status', 'frp_config_json']`

- [ ] **Step 5: Commit**

```bash
git add backend/api-server/alembic/versions/*add_frp*.py backend/api-server/apps/platform/models.py
git commit -m "feat: add frp tunnel columns to pf_site_setting"
```

---

### Task 2: Backend Schemas — Pydantic request/response models

**Files:**
- Modify: `backend/api-server/apps/platform/schemas.py`

- [ ] **Step 1: Add FRP schemas to schemas.py**

```python
# FRP Tunnel schemas
from pydantic import BaseModel, Field

class FrpStartRequest(BaseModel):
    """Request to start frp tunnel. Reads config from pf_site_setting."""
    pass  # No extra params; reads from site setting

class FrpStartResponse(BaseModel):
    frp_status: str
    public_url: str
    api_url: str
    pid: int

class FrpStopResponse(BaseModel):
    frp_status: str

class FrpStatusResponse(BaseModel):
    frp_status: str
    pid: Optional[int] = None
    public_url: Optional[str] = None
    api_url: Optional[str] = None
    last_error: Optional[str] = None
    uptime_seconds: Optional[int] = None

class FrpConfigUpdateRequest(BaseModel):
    """Update frp config in site setting. All fields optional."""
    frp_server_addr: Optional[str] = Field(None, description="云服务器IP地址")
    frp_server_port: Optional[int] = Field(7000, description="frps绑定端口")
    frp_token: Optional[str] = Field(None, description="认证密钥")
    frp_public_port: Optional[int] = Field(80, description="对外HTTP端口")
    frp_config_json: Optional[str] = Field(None, description="高级自定义frpc配置")
```

- [ ] **Step 2: Commit**

```bash
git add backend/api-server/apps/platform/schemas.py
git commit -m "feat: add frp tunnel Pydantic schemas"
```

---

### Task 3: Backend frp_service — frpc lifecycle management

**Files:**
- Create: `backend/api-server/apps/platform/frp_service.py`

- [ ] **Step 1: Create frp_service.py with download logic**

```python
"""FRP tunnel service — manages frpc subprocess lifecycle."""
import os
import platform
import subprocess
import tempfile
import time
from pathlib import Path

import requests

from apps.platform.models import PlatformSiteSetting

FRPC_BIN_DIR = Path.home() / ".fan-ce"
FRPC_BIN = FRPC_BIN_DIR / "frpc"
FRPC_VERSION = "0.61.0"

FRPC_DOWNLOAD_URLS = [
    "https://gitee.com/fatedier/frp/releases/download/v{version}/frp_{version}_{platform}.tar.gz",
    "https://github.com/fatedier/frp/releases/download/v{version}/frp_{version}_{platform}.tar.gz",
]

# Runtime state in memory (not persisted to DB between restarts)
_frpc_process: subprocess.Popen | None = None
_frpc_started_at: float | None = None
_frpc_last_error: str | None = None
_frpc_pid_file: Path = FRPC_BIN_DIR / "frpc.pid"


def _get_platform_suffix() -> str:
    """Return platform suffix for frpc download (e.g. 'linux_amd64')."""
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
            import tarfile
            import io
            resp = requests.get(url, timeout=30, stream=True)
            resp.raise_for_status()
            with tarfile.open(fileobj=io.BytesIO(resp.content), mode="r:gz") as tar:
                for member in tar.getmembers():
                    if member.name.endswith("frpc"):
                        extracted = tar.extractfile(member)
                        if extracted:
                            FRPC_BIN.write_bytes(extracted.read())
                            FRPC_BIN.chmod(0o755)
                            return True
        except Exception:
            continue

    return False


def _generate_config(settings: PlatformSiteSetting) -> str:
    """Generate frpc.ini content from site settings. Returns file path."""
    config = f"""[common]
server_addr = {settings.frp_server_addr}
server_port = {settings.frp_server_port}
token = {settings.frp_token}

[portal-web]
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
    config_path = FRPC_BIN_DIR / "frpc.ini"
    config_path.write_text(config)
    return str(config_path)


def start_frpc(db_settings: PlatformSiteSetting) -> dict:
    """Start frpc tunnel. Returns status dict."""
    global _frpc_process, _frpc_started_at, _frpc_last_error

    # Validate
    if not db_settings.frp_server_addr or not db_settings.frp_token:
        _frpc_last_error = "云服务器IP和Token不能为空"
        return {"frp_status": "error", "error": _frpc_last_error}

    # Ensure frpc binary exists
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
    config_path = _generate_config(db_settings)
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

    public_url = f"http://{db_settings.frp_server_addr}"
    if db_settings.frp_public_port != 80:
        public_url += f":{db_settings.frp_public_port}"

    return {
        "frp_status": "running",
        "public_url": public_url,
        "api_url": f"http://{db_settings.frp_server_addr}:8002",
        "pid": _frpc_process.pid,
    }


def stop_frpc() -> dict:
    """Stop frpc process. Returns status dict."""
    global _frpc_process, _frpc_started_at

    if _frpc_process is None:
        # Try reading PID from file
        if _frpc_pid_file.exists():
            try:
                pid = int(_frpc_pid_file.read_text().strip())
                import signal
                os.kill(pid, signal.SIGTERM)
                _frpc_pid_file.unlink()
            except (ProcessLookupError, ValueError):
                pass
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


def get_frpc_status(db_settings: PlatformSiteSetting) -> dict:
    """Query current frpc status."""
    global _frpc_process, _frpc_started_at, _frpc_last_error

    public_url = f"http://{db_settings.frp_server_addr}"
    if db_settings.frp_public_port and db_settings.frp_public_port != 80:
        public_url += f":{db_settings.frp_public_port}"

    result = {
        "frp_status": db_settings.frp_status or "stopped",
        "pid": None,
        "public_url": public_url if db_settings.frp_server_addr else None,
        "api_url": f"http://{db_settings.frp_server_addr}:8002" if db_settings.frp_server_addr else None,
        "last_error": _frpc_last_error,
        "uptime_seconds": None,
    }

    if _frpc_process is not None:
        poll = _frpc_process.poll()
        if poll is None:
            result["pid"] = _frpc_process.pid
            if _frpc_started_at:
                result["uptime_seconds"] = int(time.time() - _frpc_started_at)
        else:
            # Process exited unexpectedly
            result["frp_status"] = "error"
            stderr = _frpc_process.stderr.read().decode(errors="replace") if _frpc_process.stderr else ""
            result["last_error"] = stderr[-500:] if stderr else f"Process exited with code {poll}"
            _frpc_last_error = result["last_error"]

    return result
```

- [ ] **Step 2: Verify imports work**

```bash
cd backend/api-server && python -c "from apps.platform.frp_service import _get_platform_suffix, _generate_config; print('imports OK')"
```

- [ ] **Step 3: Commit**

```bash
git add backend/api-server/apps/platform/frp_service.py
git commit -m "feat: add frp_service for frpc lifecycle management"
```

---

### Task 4: Backend API Endpoints — FRP management

**Files:**
- Modify: `backend/api-server/apps/platform/api/setting.py`

- [ ] **Step 1: Add FRP API endpoints to setting.py**

Add these imports at the top of `setting.py`:
```python
from apps.platform.frp_service import start_frpc, stop_frpc, get_frpc_status
from apps.platform.schemas import (
    FrpStartResponse, FrpStopResponse, FrpStatusResponse, FrpConfigUpdateRequest,
)
import os
```

Add these endpoints after the existing site setting endpoints:

```python
@setting_router.post("/frp/config/update", summary="更新frp隧道配置")
async def frp_config_update(
    req: FrpConfigUpdateRequest,
    current_user=Depends(check_permission("platform:admin")),
    db=Depends(get_db),
):
    """Update frp tunnel config in site setting."""
    site = db.query(PlatformSiteSetting).order_by(PlatformSiteSetting.id.asc()).first()
    if not site:
        site = PlatformSiteSetting()
        db.add(site)

    update_fields = req.model_dump(exclude_unset=True)
    for field, value in update_fields.items():
        setattr(site, field, value)
    site.update_time = int(time.time())

    db.commit()
    db.refresh(site)
    return response_2000(data=site.to_dict())


@setting_router.post("/frp/start", summary="开启frp隧道共享")
async def frp_start(
    current_user=Depends(check_permission("platform:admin")),
    db=Depends(get_db),
):
    """Start frpc tunnel. Downloads frpc if needed."""
    site = db.query(PlatformSiteSetting).order_by(PlatformSiteSetting.id.asc()).first()
    if not site:
        return response_2000(code=4000, msg="请先配置云服务器信息", data={})

    result = start_frpc(site)

    # Persist status to DB
    site.frp_status = result.get("frp_status", "error")
    site.update_time = int(time.time())
    db.commit()

    if result["frp_status"] == "error":
        return response_2000(code=4000, msg=result.get("error", "启动失败"), data=result)

    return response_2000(data=result)


@setting_router.post("/frp/stop", summary="关闭frp隧道共享")
async def frp_stop(
    current_user=Depends(check_permission("platform:admin")),
    db=Depends(get_db),
):
    """Stop frpc tunnel."""
    result = stop_frpc()

    site = db.query(PlatformSiteSetting).order_by(PlatformSiteSetting.id.asc()).first()
    if site:
        site.frp_status = "stopped"
        site.update_time = int(time.time())
        db.commit()

    return response_2000(data=result)


@setting_router.post("/frp/status", summary="查询frp隧道状态")
async def frp_status(
    db=Depends(get_db),
):
    """Get current frpc tunnel status."""
    site = db.query(PlatformSiteSetting).order_by(PlatformSiteSetting.id.asc()).first()
    if not site:
        return response_2000(data={"frp_status": "stopped"})

    result = get_frpc_status(site)
    return response_2000(data=result)


@setting_router.get("/frp/install-script", summary="获取云服务器frps安装脚本")
async def frp_install_script():
    """Return the frps install script for cloud server setup."""
    script_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "static", "install-frps.sh"
    )
    # Also check in the api-server static directory
    if not os.path.exists(script_path):
        # Try relative to the app
        script_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "..", "..", "..", "static", "install-frps.sh"
        )

    if not os.path.exists(script_path):
        from fastapi.responses import PlainTextResponse
        return PlainTextResponse(
            "#!/bin/bash\necho 'frps install script not found'\n",
            media_type="text/plain",
        )

    from fastapi.responses import FileResponse
    return FileResponse(script_path, media_type="text/plain", filename="install-frps.sh")
```

Note: The `check_permission("platform:admin")` call may differ from the existing `_require_platform_admin()` helper. To stay consistent with existing code, use `_require_platform_admin` in the dependency chain instead. Import it from the same module.

- [ ] **Step 2: Verify backend starts without import errors**

```bash
cd backend/api-server && python -c "from apps.platform.api.setting import setting_router; print('router OK')"
```

- [ ] **Step 3: Commit**

```bash
git add backend/api-server/apps/platform/api/setting.py
git commit -m "feat: add frp tunnel management API endpoints"
```

---

### Task 5: Cloud Server Install Script

**Files:**
- Create: `backend/api-server/static/install-frps.sh`

- [ ] **Step 1: Create install-frps.sh**

```bash
#!/usr/bin/env bash
set -euo pipefail

# FAN-CE frps 一键安装脚本
# 在云服务器上运行: curl -sSL <url> | sudo bash

FRP_VERSION="0.61.0"
INSTALL_DIR="/opt/fan-ce-frps"
FRPS_BIN="$INSTALL_DIR/frps"
FRPS_CONF="$INSTALL_DIR/frps.ini"

detect_arch() {
    local arch
    arch=$(uname -m)
    case "$arch" in
        x86_64|amd64) echo "amd64" ;;
        aarch64|arm64) echo "arm64" ;;
        *) echo "unsupported"; exit 1 ;;
    esac
}

detect_os() {
    case "$(uname -s)" in
        Linux) echo "linux" ;;
        *) echo "unsupported"; exit 1 ;;
    esac
}

install_frps() {
    local os arch suffix token
    os=$(detect_os)
    arch=$(detect_arch)
    suffix="${os}_${arch}"
    token=$(openssl rand -hex 16)

    mkdir -p "$INSTALL_DIR"

    echo "==> Downloading frps v$FRP_VERSION for $suffix..."
    curl -sSL "https://github.com/fatedier/frp/releases/download/v${FRP_VERSION}/frp_${FRP_VERSION}_${suffix}.tar.gz" \
        -o /tmp/frp.tar.gz

    cd /tmp
    tar xzf frp.tar.gz
    cp "frp_${FRP_VERSION}_${suffix}/frps" "$FRPS_BIN"
    chmod +x "$FRPS_BIN"
    rm -rf "frp_${FRP_VERSION}_${suffix}" frp.tar.gz

    echo "==> Generating config..."
    cat > "$FRPS_CONF" <<EOF
[common]
bind_port = 7000
token = $token
dashboard_port = 7500
dashboard_user = admin
dashboard_pwd = $(openssl rand -hex 8)
EOF

    echo "==> Setting up systemd service..."
    cat > /etc/systemd/system/fan-ce-frps.service <<SVC
[Unit]
Description=FAN-CE frps Server
After=network.target

[Service]
Type=simple
ExecStart=$FRPS_BIN -c $FRPS_CONF
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
SVC

    systemctl daemon-reload
    systemctl enable fan-ce-frps
    systemctl start fan-ce-frps

    echo ""
    echo "============================================"
    echo "  FAN-CE frps 安装完成!"
    echo "============================================"
    echo ""
    echo "  FRP Token: $token"
    echo "  Dashboard: http://$(curl -s ifconfig.me):7500"
    echo ""
    echo "  请将以下信息填入 Admin-Web 平台设置:"
    echo "    云服务器 IP: $(curl -s ifconfig.me)"
    echo "    frp 端口: 7000"
    echo "    Token: $token"
    echo ""
    echo "  云服务器防火墙请开放端口: 7000, 80, 8002"
    echo "============================================"
}

install_frps
```

- [ ] **Step 2: Make script executable and verify static dir**

```bash
chmod +x backend/api-server/static/install-frps.sh
ls -la backend/api-server/static/install-frps.sh
```

- [ ] **Step 3: Commit**

```bash
git add backend/api-server/static/install-frps.sh
git commit -m "feat: add frps cloud server one-click install script"
```

---

### Task 6: Frontend API Client — FRP functions

**Files:**
- Modify: `frontend/admin-web/apps/web-antd/src/api/platform/setting.ts`

- [ ] **Step 1: Add FRP TypeScript interfaces and API functions**

Add to `setting.ts`:

```typescript
// ── FRP Tunnel types ──

export interface FrpStatusResult {
  frp_status: 'stopped' | 'running' | 'error';
  pid: number | null;
  public_url: string | null;
  api_url: string | null;
  last_error: string | null;
  uptime_seconds: number | null;
}

export interface FrpConfigPayload {
  frp_server_addr?: string;
  frp_server_port?: number;
  frp_token?: string;
  frp_public_port?: number;
  frp_config_json?: string;
}

// ── FRP API functions ──

export async function updateFrpConfigApi(data: FrpConfigPayload) {
  return requestClient.post('/platform/frp/config/update', data);
}

export async function startFrpTunnelApi() {
  return requestClient.post<FrpStatusResult>('/platform/frp/start');
}

export async function stopFrpTunnelApi() {
  return requestClient.post<FrpStatusResult>('/platform/frp/stop');
}

export async function getFrpStatusApi() {
  return requestClient.post<FrpStatusResult>('/platform/frp/status');
}

export function getFrpInstallScriptUrl() {
  // Returns a direct download URL for the install script
  return '/api/v1/platform/frp/install-script';
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/admin-web/apps/web-antd/src/api/platform/setting.ts
git commit -m "feat: add frp tunnel API client functions"
```

---

### Task 7: Frontend FrpTunnelCard Component

**Files:**
- Create: `frontend/admin-web/apps/web-antd/src/views/platform/components/FrpTunnelCard.vue`

- [ ] **Step 1: Create FrpTunnelCard.vue**

```vue
<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from 'vue';
import {
  Card, Button, Input, InputNumber, Space, Tag, message, Alert, Spin,
} from 'ant-design-vue';
import {
  startFrpTunnelApi, stopFrpTunnelApi, getFrpStatusApi,
  updateFrpConfigApi, getFrpInstallScriptUrl,
  type FrpStatusResult,
} from '#/api/platform/setting';
import { $t } from '@vben/locales';

interface FrpConfig {
  frp_server_addr: string;
  frp_server_port: number;
  frp_token: string;
  frp_public_port: number;
  frp_config_json: string;
}

const props = defineProps<{
  siteSetting: Record<string, any>;
}>();

const emit = defineEmits<{
  (e: 'refresh'): void;
}>();

const statusLoading = ref(false);
const actionLoading = ref(false);
const configSaving = ref(false);
const status = ref<FrpStatusResult | null>(null);
let pollTimer: ReturnType<typeof setInterval> | null = null;

const config = ref<FrpConfig>({
  frp_server_addr: '',
  frp_server_port: 7000,
  frp_token: '',
  frp_public_port: 80,
  frp_config_json: '',
});

// Init from props
function initFromProps() {
  config.value.frp_server_addr = props.siteSetting?.frp_server_addr || '';
  config.value.frp_server_port = props.siteSetting?.frp_server_port || 7000;
  config.value.frp_token = props.siteSetting?.frp_token || '';
  config.value.frp_public_port = props.siteSetting?.frp_public_port || 80;
  config.value.frp_config_json = props.siteSetting?.frp_config_json || '';
}

const frpEnabled = computed(() => props.siteSetting?.frp_enabled);
const frpStatus = computed(() => status.value?.frp_status || 'stopped');

const statusColor = computed(() => {
  switch (frpStatus.value) {
    case 'running': return 'green';
    case 'error': return 'red';
    default: return 'default';
  }
});

const statusText = computed(() => $t(`platform.frpStatus.${frpStatus.value}`));

async function fetchStatus() {
  statusLoading.value = true;
  try {
    const res = await getFrpStatusApi();
    status.value = res;
  } catch {
    status.value = null;
  } finally {
    statusLoading.value = false;
  }
}

async function saveConfig() {
  configSaving.value = true;
  try {
    await updateFrpConfigApi(config.value);
    message.success($t('platform.frpConfigSaved'));
    emit('refresh');
  } catch {
    message.error($t('platform.frpConfigSaveFailed'));
  } finally {
    configSaving.value = false;
  }
}

async function handleStart() {
  actionLoading.value = true;
  try {
    const res = await startFrpTunnelApi();
    status.value = res;
    if (res.frp_status === 'running') {
      message.success($t('platform.frpTunnelStarted'));
      startPolling();
    } else {
      message.error(res.last_error || $t('platform.frpTunnelStartFailed'));
    }
    emit('refresh');
  } catch {
    message.error($t('platform.frpTunnelStartFailed'));
  } finally {
    actionLoading.value = false;
  }
}

async function handleStop() {
  actionLoading.value = true;
  try {
    await stopFrpTunnelApi();
    status.value = { frp_status: 'stopped', pid: null, public_url: null, api_url: null, last_error: null, uptime_seconds: null };
    message.success($t('platform.frpTunnelStopped'));
    stopPolling();
    emit('refresh');
  } catch {
    message.error($t('platform.frpTunnelStopFailed'));
  } finally {
    actionLoading.value = false;
  }
}

function generateToken() {
  const chars = 'abcdefghijklmnopqrstuvwxyz0123456789';
  let token = '';
  for (let i = 0; i < 32; i++) {
    token += chars.charAt(Math.floor(Math.random() * chars.length));
  }
  config.value.frp_token = token;
}

function startPolling() {
  stopPolling();
  pollTimer = setInterval(fetchStatus, 10000);
}

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer);
    pollTimer = null;
  }
}

onMounted(() => {
  initFromProps();
  fetchStatus();
  if (props.siteSetting?.frp_status === 'running') {
    startPolling();
  }
});

onUnmounted(() => stopPolling());
</script>

<template>
  <Card :title="$t('platform.frpTunnelCard')" style="margin-top: 16px;">
    <!-- Config Form -->
    <div style="display: flex; flex-wrap: wrap; gap: 16px; margin-bottom: 16px;">
      <div style="flex: 1; min-width: 200px;">
        <label style="display: block; margin-bottom: 4px; font-weight: 500;">
          {{ $t('platform.frpServerAddr') }} *
        </label>
        <Input v-model:value="config.frp_server_addr" :placeholder="$t('platform.frpServerAddrPlaceholder')" />
      </div>
      <div style="flex: 1; min-width: 120px;">
        <label style="display: block; margin-bottom: 4px; font-weight: 500;">
          {{ $t('platform.frpServerPort') }}
        </label>
        <InputNumber v-model:value="config.frp_server_port" :min="1" :max="65535" style="width: 100%;" />
      </div>
      <div style="flex: 1; min-width: 120px;">
        <label style="display: block; margin-bottom: 4px; font-weight: 500;">
          {{ $t('platform.frpPublicPort') }}
        </label>
        <InputNumber v-model:value="config.frp_public_port" :min="1" :max="65535" style="width: 100%;" />
      </div>
      <div style="flex: 2; min-width: 280px;">
        <label style="display: block; margin-bottom: 4px; font-weight: 500;">
          {{ $t('platform.frpToken') }} *
        </label>
        <Space style="width: 100%;">
          <Input v-model:value="config.frp_token" :placeholder="$t('platform.frpTokenPlaceholder')" style="flex: 1;" />
          <Button size="small" @click="generateToken">{{ $t('platform.frpGenerateToken') }}</Button>
        </Space>
      </div>
    </div>

    <Space style="margin-bottom: 16px;">
      <Button type="primary" ghost :loading="configSaving" @click="saveConfig">
        {{ $t('platform.frpSaveConfig') }}
      </Button>
      <Button @click="() => window.open(getFrpInstallScriptUrl(), '_blank')">
        {{ $t('platform.frpDownloadScript') }}
      </Button>
    </Space>

    <!-- Status & Controls -->
    <div style="display: flex; align-items: center; gap: 12px; padding: 12px; background: #fafafa; border-radius: 6px;">
      <span style="font-weight: 500;">{{ $t('platform.frpCurrentStatus') }}:</span>
      <Spin v-if="statusLoading" size="small" />
      <Tag v-else :color="statusColor">{{ statusText }}</Tag>

      <template v-if="status?.public_url && frpStatus === 'running'">
        <span style="color: #888; margin-left: 8px;">
          {{ $t('platform.frpPublicUrl') }}:
          <a :href="status.public_url" target="_blank">{{ status.public_url }}</a>
        </span>
      </template>

      <div style="flex: 1;" />

      <Button
        v-if="frpStatus !== 'running'"
        type="primary"
        :loading="actionLoading"
        @click="handleStart"
      >
        {{ $t('platform.frpStartSharing') }}
      </Button>
      <Button
        v-else
        danger
        :loading="actionLoading"
        @click="handleStop"
      >
        {{ $t('platform.frpStopSharing') }}
      </Button>
    </div>

    <!-- Error display -->
    <Alert
      v-if="frpStatus === 'error' && status?.last_error"
      type="error"
      :message="$t('platform.frpErrorTitle')"
      :description="status.last_error"
      show-icon
      style="margin-top: 12px;"
    />

    <!-- Notice for first-time users -->
    <Alert
      type="info"
      :message="$t('platform.frpFirstTimeTitle')"
      :description="$t('platform.frpFirstTimeDesc')"
      show-icon
      style="margin-top: 12px;"
    />
  </Card>
</template>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/admin-web/apps/web-antd/src/views/platform/components/FrpTunnelCard.vue
git commit -m "feat: add FrpTunnelCard component for frp tunnel control"
```

---

### Task 8: Integrate FrpTunnelCard into Settings Page

**Files:**
- Modify: `frontend/admin-web/apps/web-antd/src/views/platform/setting.vue`

- [ ] **Step 1: Import and render FrpTunnelCard**

Add the import:
```typescript
import FrpTunnelCard from './components/FrpTunnelCard.vue';
```

Add after the site settings card in the template (find `<Card :title="$t('platform.siteConfig')">` block and add after its closing `</Card>`):

```vue
<FrpTunnelCard :site-setting="siteForm" @refresh="fetchSiteSetting" />
```

The `fetchSiteSetting` function should already exist — it loads the site setting data. If the name differs, use the existing function name.

- [ ] **Step 2: Commit**

```bash
git add frontend/admin-web/apps/web-antd/src/views/platform/setting.vue
git commit -m "feat: integrate FrpTunnelCard into platform settings page"
```

---

### Task 9: i18n — Chinese and English labels

**Files:**
- Modify: `frontend/admin-web/apps/web-antd/src/locales/langs/zh-CN/platform.json`
- Modify: `frontend/admin-web/apps/web-antd/src/locales/langs/en-US/platform.json`

- [ ] **Step 1: Add Chinese labels**

Add to `zh-CN/platform.json`:

```json
{
  "frpTunnelCard": "数据共享隧道",
  "frpServerAddr": "云服务器 IP 地址",
  "frpServerAddrPlaceholder": "请输入云服务器公网 IP",
  "frpServerPort": "frp 端口",
  "frpPublicPort": "对外 HTTP 端口",
  "frpToken": "认证 Token",
  "frpTokenPlaceholder": "与云服务器 frps 的 token 保持一致",
  "frpGenerateToken": "随机生成",
  "frpSaveConfig": "保存配置",
  "frpDownloadScript": "下载云服务器安装脚本",
  "frpCurrentStatus": "当前状态",
  "frpPublicUrl": "公网地址",
  "frpStartSharing": "开启共享",
  "frpStopSharing": "关闭共享",
  "frpErrorTitle": "隧道异常",
  "frpFirstTimeTitle": "首次使用？",
  "frpFirstTimeDesc": "1. 购买一台便宜云服务器；2. SSH 登录后运行下载的安装脚本；3. 将生成的 Token 填入上方配置；4. 点击"开启共享"",
  "frpConfigSaved": "隧道配置已保存",
  "frpConfigSaveFailed": "配置保存失败",
  "frpTunnelStarted": "隧道已开启，数据可通过公网访问",
  "frpTunnelStartFailed": "隧道启动失败",
  "frpTunnelStopped": "隧道已关闭",
  "frpTunnelStopFailed": "隧道关闭失败",
  "frpStatus.stopped": "已停止",
  "frpStatus.running": "运行中",
  "frpStatus.error": "异常"
}
```

- [ ] **Step 2: Add English labels**

Add to `en-US/platform.json`:

```json
{
  "frpTunnelCard": "Data Sharing Tunnel",
  "frpServerAddr": "Cloud Server IP",
  "frpServerAddrPlaceholder": "Enter cloud server public IP",
  "frpServerPort": "FRP Port",
  "frpPublicPort": "Public HTTP Port",
  "frpToken": "Auth Token",
  "frpTokenPlaceholder": "Must match cloud server frps token",
  "frpGenerateToken": "Generate",
  "frpSaveConfig": "Save Config",
  "frpDownloadScript": "Download Cloud Install Script",
  "frpCurrentStatus": "Status",
  "frpPublicUrl": "Public URL",
  "frpStartSharing": "Enable Sharing",
  "frpStopSharing": "Disable Sharing",
  "frpErrorTitle": "Tunnel Error",
  "frpFirstTimeTitle": "First Time?",
  "frpFirstTimeDesc": "1. Rent a cheap cloud server; 2. SSH in and run the install script; 3. Fill in the generated token above; 4. Click \"Enable Sharing\"",
  "frpConfigSaved": "Tunnel config saved",
  "frpConfigSaveFailed": "Failed to save config",
  "frpTunnelStarted": "Tunnel enabled, data is publicly accessible",
  "frpTunnelStartFailed": "Failed to start tunnel",
  "frpTunnelStopped": "Tunnel disabled",
  "frpTunnelStopFailed": "Failed to stop tunnel",
  "frpStatus.stopped": "Stopped",
  "frpStatus.running": "Running",
  "frpStatus.error": "Error"
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/admin-web/apps/web-antd/src/locales/langs/zh-CN/platform.json frontend/admin-web/apps/web-antd/src/locales/langs/en-US/platform.json
git commit -m "feat: add i18n labels for frp tunnel card"
```

---

### Task 10: Portal-Web — Configurable API Base URL

**Files:**
- Modify: `frontend/portal-web/vite.config.ts`
- Modify: `frontend/portal-web/src/App.vue`

- [ ] **Step 1: Fix portal-web vite proxy port (8001 → 8002)**

Modify `vite.config.ts`:
```typescript
import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';

export default defineConfig({
  plugins: [vue()],
  server: {
    host: '127.0.0.1',
    port: 5677,
    proxy: {
      '/api/v1': {
        target: 'http://127.0.0.1:8002',
        changeOrigin: true,
      },
    },
  },
});
```

- [ ] **Step 2: Make App.vue API base URL configurable**

In `App.vue` `<script setup>`, add a constant near the top:
```typescript
// Use VITE_API_BASE_URL env var, or default to '/api/v1' (proxied in dev)
const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api/v1';
```

Replace all hardcoded `/api/v1/...` fetch URLs with template literals using `API_BASE`. For example:
```typescript
// Before:
fetch('/api/v1/public/dataset/list', { ... })
// After:
fetch(`${API_BASE}/public/dataset/list`, { ... })
```

Since App.vue is a large single file, search for all occurrences of `/api/v1/` in fetch() calls and replace with `${API_BASE}/...`.

- [ ] **Step 3: Verify portal-web builds**

```bash
cd frontend/portal-web && pnpm build
```

- [ ] **Step 4: Commit**

```bash
git add frontend/portal-web/vite.config.ts frontend/portal-web/src/App.vue
git commit -m "feat: make portal-web API base URL configurable via env var"
```

---

### Task 11: Integration Verification

- [ ] **Step 1: Verify backend starts cleanly**

```bash
cd backend/api-server && timeout 10 python main.py 2>&1 | head -5
# Should show normal startup, no import errors
```

- [ ] **Step 2: Verify frontend builds cleanly**

```bash
cd frontend/admin-web && pnpm build:antd 2>&1 | tail -5
# Should complete without errors
```

- [ ] **Step 3: End-to-end manual verification checklist**

1. Start backend: `uvicorn main:app --host 0.0.0.0 --port 8002 --reload`
2. Start admin-web: `pnpm dev:antd`
3. Navigate to `http://127.0.0.1:5666/platform/setting`
4. Verify "数据共享隧道" card appears below site config
5. Fill in server IP and token, click "Save Config"
6. Click "Download Cloud Install Script" — verify script downloads
7. Click "Enable Sharing" — verify status shows error (no real frps on that IP)
8. Stop and verify status returns to "stopped"

- [ ] **Step 4: Commit any fixes from verification**

```bash
git add -A
git commit -m "chore: integration verification fixes for frp tunnel"
```
