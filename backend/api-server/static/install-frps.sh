#!/usr/bin/env bash
set -euo pipefail

# FAN-CE frps 一键安装脚本
# 用法: curl -sSL <url> | sudo bash

FRP_VERSION="0.61.0"
INSTALL_DIR="/opt/fan-ce-frps"

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

# Check root
if [ "$(id -u)" -ne 0 ]; then
    echo "请使用 sudo 运行此脚本: curl ... | sudo bash"
    exit 1
fi

OS=$(detect_os)
ARCH=$(detect_arch)
SUFFIX="${OS}_${ARCH}"
TOKEN=$(openssl rand -hex 16)
DASHBOARD_PWD=$(openssl rand -hex 8)

echo "============================================"
echo "  FAN-CE frps 一键安装"
echo "  平台: ${SUFFIX}"
echo "============================================"

mkdir -p "$INSTALL_DIR"

# Download frps
echo "==> 下载 frps v${FRP_VERSION} (${SUFFIX})..."
DOWNLOAD_URL="https://github.com/fatedier/frp/releases/download/v${FRP_VERSION}/frp_${FRP_VERSION}_${SUFFIX}.tar.gz"
curl -sSL "$DOWNLOAD_URL" -o /tmp/frp.tar.gz

cd /tmp
tar xzf frp.tar.gz
cp "frp_${FRP_VERSION}_${SUFFIX}/frps" "${INSTALL_DIR}/frps"
chmod +x "${INSTALL_DIR}/frps"
rm -rf "frp_${FRP_VERSION}_${SUFFIX}" frp.tar.gz
echo "==> frps 已安装到 ${INSTALL_DIR}/frps"

# Generate config
echo "==> 生成配置文件..."
cat > "${INSTALL_DIR}/frps.ini" <<EOF
[common]
bind_port = 7000
token = ${TOKEN}
dashboard_port = 7500
dashboard_user = admin
dashboard_pwd = ${DASHBOARD_PWD}
EOF

# Setup systemd service
echo "==> 注册 systemd 服务..."
cat > /etc/systemd/system/fan-ce-frps.service <<SVC
[Unit]
Description=FAN-CE frps Server
After=network.target

[Service]
Type=simple
ExecStart=${INSTALL_DIR}/frps -c ${INSTALL_DIR}/frps.ini
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
SVC

systemctl daemon-reload
systemctl enable fan-ce-frps
systemctl start fan-ce-frps

# Check status
sleep 2
if systemctl is-active --quiet fan-ce-frps; then
    echo "==> frps 服务已启动"
else
    echo "==> WARNING: frps 服务未正常启动，请检查: systemctl status fan-ce-frps"
fi

PUBLIC_IP=$(curl -s ifconfig.me 2>/dev/null || echo "YOUR_SERVER_IP")

echo ""
echo "============================================"
echo "  FAN-CE frps 安装完成!"
echo "============================================"
echo ""
echo "  请在 Admin-Web 平台设置中填写以下信息:"
echo "  ┌─────────────────────────────────────"
echo "  │ 云服务器 IP : ${PUBLIC_IP}"
echo "  │ frp 端口    : 7000"
echo "  │ Token       : ${TOKEN}"
echo "  └─────────────────────────────────────"
echo ""
echo "  Dashboard: http://${PUBLIC_IP}:7500"
echo "  用户名: admin  密码: ${DASHBOARD_PWD}"
echo ""
echo "  请确保云服务器防火墙已开放端口:"
echo "    7000 (frp 控制), 80 (HTTP), 8002 (API)"
echo "============================================"
