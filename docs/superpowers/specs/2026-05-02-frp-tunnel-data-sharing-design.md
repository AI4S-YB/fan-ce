# FAN-CE 数据共享隧道 (frp Tunnel) 设计文档

> **状态:** 设计阶段 | **日期:** 2026-05-02

**目标:** 让用户以最小代价将自己本地运行的 FAN-CE 实例中的数据通过公网分享。用户在云服务器上运行 frps，本地 FAN-CE 自动管理 frpc 进程，实现一键开启/关闭隧道共享。

**技术选型:** frp (Fast Reverse Proxy) — MIT 开源，Go 单二进制，国内社区成熟。

---

## 架构

```
┌─────────────────────────────────┐      ┌──────────────────────┐
│  用户本地服务器/PC                │      │  便宜云服务器 (固定 IP)  │
│                                 │      │                      │
│  Admin-Web (:5666) ─ 本地访问   │      │  frps (:7000)        │
│  Portal-Web (:5677)             │      │  ├─ :80 → portal-web │
│  Backend API (:8002)            │ frp  │  └─ :8002 → backend  │
│  PostgreSQL (:5433)             │隧道  │                      │
│  frpc (动态管理)                 │─────▶│  nginx (可选)        │
└─────────────────────────────────┘      └──────────────────────┘
                                               │
                                               ▼
                                         🌍 外部用户浏览器
                                         http://<云IP>
```

**关键设计决策：**
- Admin-Web 仅本地访问，不通过隧道暴露
- Portal-Web 构建为静态文件，由本地 nginx 在 80 端口托管，frp 将本地 80 映射到云端 80（外部用户直接看到 portal-web）
- Backend API (:8002) 同样通过 frp 映射到云端 8002，portal-web 的 API 调用指向 `http://<云IP>:8002`
- frpc 进程由后端 Python subprocess 管理，用户通过 Admin-Web 界面一键启停

**本地端口映射关系：**
```
本地 nginx :80  (portal-web 静态文件)  ──frp──▶  云端 :80
本地 Backend :8002  (API)             ──frp──▶  云端 :8002
```
Admin-Web (:5666) 不映射，仅供本地访问。

---

## 数据模型变更

### pf_site_setting 表新增字段

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `frp_enabled` | Boolean | false | 用户是否启用隧道共享 |
| `frp_server_addr` | String(255) | null | 云服务器 IP 地址 |
| `frp_server_port` | Integer | 7000 | frps 绑定端口 |
| `frp_token` | String(255) | null | frps 与 frpc 认证密钥 |
| `frp_public_port` | Integer | 80 | 对外 HTTP 端口 |
| `frp_status` | String(32) | "stopped" | stopped / running / error |
| `frp_config_json` | Text | null | 高级自定义 frpc 配置 (JSON) |

---

## 后端 API

### FRP 管理端点

所有端点挂载在 `/api/v1/platform/frp/` 下，需要平台管理员权限。

#### `POST /platform/frp/start`
启动 frpc 隧道进程。

流程：
1. 检查 `pf_site_setting` 中 frp 配置是否完整（server_addr, token 必填）
2. 检查 frpc 二进制是否存在，不存在则尝试下载（国内镜像优先 → GitHub 兜底）
3. 根据配置生成 `/tmp/fan-ce-frpc.ini`
4. `subprocess.Popen([frpc_path, '-c', config_path])` 启动 frpc
5. 记录 PID，更新 `frp_status = "running"`

返回：`{ frp_status, public_url, api_url, pid }`

#### `POST /platform/frp/stop`
停止 frpc 进程。

流程：
1. 向已记录的 frpc PID 发送 SIGTERM
2. 等待进程退出（最多 5 秒），超时则 SIGKILL
3. 更新 `frp_status = "stopped"`

#### `POST /platform/frp/status`
查询当前隧道状态。

返回：`{ frp_status, pid, public_url, api_url, last_error, uptime_seconds }`

若 frp_status 为 "running"，额外调用 frp Dashboard API 获取连接状态。

#### `GET /platform/frp/install-script`
返回云服务器 frps 一键安装脚本（纯文本）。

脚本功能：
- 检测服务器架构 (amd64/arm64)
- 从 GitHub 下载 frps 二进制
- 生成 frps.ini 配置文件
- 设置 systemd 服务实现开机自启
- 开放防火墙端口

### frpc 二进制下载策略

下载地址优先级（依次尝试）：
1. 国内镜像 1（如 Gitee Release 或自建 CDN）
2. 国内镜像 2（备用地址）
3. GitHub Releases（兜底）

每个地址超时 15 秒，失败则尝试下一个。全部失败则返回错误并给出手动下载指引。

---

## 前端变更

### Admin-Web: 平台设置页面扩展

在 `views/platform/setting.vue` 中新增 "数据共享隧道" 卡片：

**配置表单：**
- 云服务器 IP 地址（必填）
- frp 端口（默认 7000）
- 认证 Token（必填，带随机生成按钮）
- 对外 HTTP 端口（默认 80）
- 保存配置按钮

**控制区：**
- "开启共享" / "关闭共享" 按钮（根据 frp_status 切换）
- 状态指示灯：🟢 运行中 / ⚫ 已停止 / 🔴 异常
- 公网访问地址展示（状态为 running 时显示）
- "下载云服务器安装脚本" 链接
- 最近日志摘要（状态为 error 时展开显示）

### Portal-Web: API 地址可配置

`.env` 和 `.env.production` 中新增：
```
VITE_API_BASE_URL=/api/v1
```

构建时可通过环境变量覆盖。当用户开启 frp 后，portal-web 使用 `http://<云IP>:8002/api/v1` 作为 API 基础地址。

portal-web 的 API client 从环境变量读取 baseURL，不再硬编码。

---

## 错误处理与边界情况

| 场景 | 行为 |
|------|------|
| frpc 二进制下载失败（所有源） | 提示用户手动下载并放到指定目录 |
| 云服务器端口被占用 | 提示具体端口号 |
| frps 不可达 | 状态显示 "error"，展示近 10 行 frpc 日志 |
| frpc 进程意外退出 | 状态自动更新为 "error"，不自动重启 |
| 用户关机/断网 | frpc 随系统退出，重启后需手动再次点击"开启共享" |
| 用户在未停隧道时修改配置 | 自动先 stop 再 start（或提示用户先停再改） |
| Token 为空 | start 时校验，返回明确错误提示 |

---

## 不在此版本范围内的功能

- 模式 1（纯 frp/ngrok 用户自建）— 用户可自行配置，不在界面内集成
- 模式 3/4（中心化公共节点 / P2P 做种）— 未来版本
- 自动重启 frpc（systemd 管理）— 当前由应用层管理，保持简单
- HTTPS / TLS 证书自动管理 — 用户可在云服务器 nginx 层自行配置
- Portal-Web 部署到云端 — 当前所有服务跑本地，隧道映射

---

## 与现有 Dataset 发布流程的关系

现有的 Dataset 发布流程（draft → ready → publishing → public）专注于**数据层面的可见性控制**。frp 隧道是**网络层面的可达性**。两者正交：

- 用户先通过 frp 让站点在公网可达
- 然后在 Admin-Web 中将具体 Dataset 发布为 public
- 外部用户通过 portal-web 浏览公开数据，portal-web 调用 public API（无需认证）
- 关闭 frp 隧道后，所有外部访问立即中断，但 Dataset 的 visibility 状态不变
