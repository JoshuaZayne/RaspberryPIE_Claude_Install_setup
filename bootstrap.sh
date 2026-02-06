#!/usr/bin/env bash
# ══════════════════════════════════════════════════════════════
#  Raspberry Pi – Claude Code Full Bootstrap Script
#  One command to rule them all.
#
#  Usage:
#    curl -fsSL <your-hosted-url>/bootstrap.sh | sudo bash
#    — or —
#    sudo bash bootstrap.sh
# ══════════════════════════════════════════════════════════════
set -e

GREEN="\033[92m"
YELLOW="\033[93m"
RED="\033[91m"
CYAN="\033[96m"
BOLD="\033[1m"
RESET="\033[0m"

INSTALL_DIR="/home/${SUDO_USER:-pi}/claude-workspace"

banner() {
  echo -e "${CYAN}${BOLD}"
  echo "╔════════════════════════════════════════════════════════╗"
  echo "║  Raspberry Pi  –  Claude Code  Full Auto-Installer    ║"
  echo "╚════════════════════════════════════════════════════════╝"
  echo -e "${RESET}"
}

ok()   { echo -e "${GREEN}${BOLD}[✓]${RESET} $1"; }
warn() { echo -e "${YELLOW}[!]${RESET} $1"; }
fail() { echo -e "${RED}[✗]${RESET} $1"; }
info() { echo -e "${CYAN}  → ${RESET}$1"; }

# ── Pre-flight checks ───────────────────────────────────────────
preflight() {
  echo ""
  echo -e "${BOLD}Running pre-flight checks …${RESET}"

  # Must be root
  if [ "$EUID" -ne 0 ]; then
    fail "This script must be run with sudo."
    echo "  Run:  curl -fsSL <url>/bootstrap.sh | sudo bash"
    exit 1
  fi
  ok "Running as root"

  # Check architecture
  ARCH=$(uname -m)
  if [[ "$ARCH" == "aarch64" ]]; then
    ok "Architecture: $ARCH (64-bit) — perfect"
  elif [[ "$ARCH" == "armv7l" ]]; then
    warn "Architecture: $ARCH (32-bit) — some things may not work"
    warn "64-bit Raspberry Pi OS is strongly recommended"
  else
    ok "Architecture: $ARCH"
  fi

  # Check model
  if [ -f /proc/device-tree/model ]; then
    MODEL=$(tr -d '\0' < /proc/device-tree/model)
    ok "Device: $MODEL"
  else
    warn "Could not detect Raspberry Pi model (not on a Pi?)"
  fi

  # Check RAM
  TOTAL_RAM_KB=$(grep MemTotal /proc/meminfo | awk '{print $2}')
  TOTAL_RAM_MB=$((TOTAL_RAM_KB / 1024))
  if [ "$TOTAL_RAM_MB" -lt 2048 ]; then
    warn "RAM: ${TOTAL_RAM_MB}MB — low memory, may struggle with Docker + Claude"
  else
    ok "RAM: ${TOTAL_RAM_MB}MB"
  fi

  # Check disk space
  AVAIL_KB=$(df / | tail -1 | awk '{print $4}')
  AVAIL_GB=$((AVAIL_KB / 1024 / 1024))
  if [ "$AVAIL_GB" -lt 4 ]; then
    fail "Disk: only ${AVAIL_GB}GB free — need at least 4GB"
    exit 1
  else
    ok "Disk: ${AVAIL_GB}GB available"
  fi

  # Check internet
  if ping -c 1 -W 3 google.com &>/dev/null; then
    ok "Internet: connected"
  else
    fail "No internet connection detected."
    exit 1
  fi

  echo ""
}

# ── 1. System update ────────────────────────────────────────────
step_update() {
  echo -e "\n${BOLD}[1/7] Updating system packages …${RESET}"
  apt-get update -y -qq
  apt-get upgrade -y -qq
  apt-get install -y -qq curl wget git ca-certificates gnupg lsb-release
  ok "System updated"
}

# ── 2. Docker ───────────────────────────────────────────────────
step_docker() {
  echo -e "\n${BOLD}[2/7] Installing Docker …${RESET}"

  if command -v docker &>/dev/null; then
    warn "Docker already installed — $(docker --version)"
  else
    curl -fsSL https://get.docker.com -o /tmp/get-docker.sh
    sh /tmp/get-docker.sh
    rm -f /tmp/get-docker.sh
  fi

  systemctl enable docker
  systemctl start docker

  REAL_USER="${SUDO_USER:-pi}"
  usermod -aG docker "$REAL_USER"

  ok "Docker ready — $(docker --version)"
}

# ── 3. Docker Compose ──────────────────────────────────────────
step_compose() {
  echo -e "\n${BOLD}[3/7] Installing Docker Compose …${RESET}"

  if docker compose version &>/dev/null; then
    warn "Docker Compose already installed — $(docker compose version)"
  else
    apt-get install -y -qq docker-compose-plugin
  fi

  ok "Docker Compose ready"
}

# ── 4. Node.js + npm ──────────────────────────────────────────
step_node() {
  echo -e "\n${BOLD}[4/7] Installing Node.js & npm …${RESET}"

  NEED_NODE=true

  if command -v node &>/dev/null; then
    NODE_VER=$(node --version | sed 's/v//' | cut -d. -f1)
    if [ "$NODE_VER" -ge 18 ] 2>/dev/null; then
      warn "Node.js $(node --version) already installed — skipping"
      NEED_NODE=false
    else
      info "Node.js v$NODE_VER is too old — upgrading …"
      apt-get remove -y -qq nodejs || true
    fi
  fi

  if $NEED_NODE; then
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
    apt-get install -y -qq nodejs
  fi

  ok "Node $(node --version)  /  npm $(npm --version)"
}

# ── 5. Claude Code CLI ─────────────────────────────────────────
step_claude() {
  echo -e "\n${BOLD}[5/7] Installing Claude Code CLI …${RESET}"

  npm install -g @anthropic-ai/claude-code --loglevel=warn
  ok "Claude Code CLI installed"
}

# ── 6. Python SDK ──────────────────────────────────────────────
step_python() {
  echo -e "\n${BOLD}[6/7] Installing Anthropic Python SDK …${RESET}"

  apt-get install -y -qq python3 python3-pip python3-venv

  REAL_USER="${SUDO_USER:-pi}"
  sudo -u "$REAL_USER" pip3 install --user --break-system-packages anthropic 2>/dev/null \
    || sudo -u "$REAL_USER" pip3 install --user anthropic 2>/dev/null \
    || pip3 install anthropic

  ok "Anthropic Python SDK installed"
}

# ── 7. Scaffold project files ─────────────────────────────────
step_scaffold() {
  echo -e "\n${BOLD}[7/7] Creating project files …${RESET}"

  REAL_USER="${SUDO_USER:-pi}"
  mkdir -p "$INSTALL_DIR/workspace"

  # ── docker-compose.yml ──
  cat > "$INSTALL_DIR/docker-compose.yml" << 'COMPOSEFILE'
version: "3.9"

services:
  claude:
    image: node:20-slim
    container_name: claude-code
    stdin_open: true
    tty: true
    restart: unless-stopped
    working_dir: /workspace
    environment:
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
    volumes:
      - ./workspace:/workspace
      - claude-config:/root/.claude
      - npm-cache:/root/.npm
    entrypoint: ["/bin/sh", "-c"]
    command:
      - |
        echo "Installing Claude Code CLI …"
        npm install -g @anthropic-ai/claude-code --loglevel=warn
        echo "Launching Claude Code …"
        exec claude

volumes:
  claude-config:
  npm-cache:
COMPOSEFILE

  # ── .env ──
  cat > "$INSTALL_DIR/.env" << 'ENVFILE'
# Paste your Anthropic API key below
ANTHROPIC_API_KEY=your-api-key-here
ENVFILE

  # ── helper launch script ──
  cat > "$INSTALL_DIR/start-claude.sh" << 'LAUNCHER'
#!/usr/bin/env bash
# Quick-launch script — run Claude natively or in Docker
set -e

DIR="$(cd "$(dirname "$0")" && pwd)"

if [ -z "$ANTHROPIC_API_KEY" ]; then
  source "$DIR/.env" 2>/dev/null || true
  export ANTHROPIC_API_KEY
fi

if [ "$ANTHROPIC_API_KEY" = "your-api-key-here" ] || [ -z "$ANTHROPIC_API_KEY" ]; then
  echo ""
  echo "  ⚠  No API key set."
  echo "  Edit $DIR/.env  or run:"
  echo "    export ANTHROPIC_API_KEY=\"sk-...\""
  echo ""
  exit 1
fi

echo ""
echo "  How do you want to run Claude?"
echo "    1) Native   (claude CLI directly)"
echo "    2) Docker   (inside a container)"
echo ""
read -rp "  Pick [1/2]: " choice

case "$choice" in
  2)
    echo "  Starting Docker container …"
    cd "$DIR"
    docker compose up
    ;;
  *)
    echo "  Launching Claude Code …"
    cd "$DIR/workspace"
    claude
    ;;
esac
LAUNCHER

  chmod +x "$INSTALL_DIR/start-claude.sh"
  chown -R "$REAL_USER":"$REAL_USER" "$INSTALL_DIR"

  ok "Project files created at $INSTALL_DIR"
}

# ── API Key prompt ─────────────────────────────────────────────
ask_api_key() {
  echo ""
  echo -e "${CYAN}${BOLD}── API Key ───────────────────────────────────────────${RESET}"
  echo "  Get your key at: https://console.anthropic.com"
  echo ""
  read -rp "  Paste your API key (or Enter to skip): " KEY

  if [ -n "$KEY" ]; then
    sed -i "s|your-api-key-here|$KEY|g" "$INSTALL_DIR/.env"

    REAL_USER="${SUDO_USER:-pi}"
    BASHRC="/home/$REAL_USER/.bashrc"
    if ! grep -q "ANTHROPIC_API_KEY" "$BASHRC" 2>/dev/null; then
      echo "" >> "$BASHRC"
      echo "# Anthropic API Key" >> "$BASHRC"
      echo "export ANTHROPIC_API_KEY=\"$KEY\"" >> "$BASHRC"
    fi
    ok "API key saved to .env and ~/.bashrc"
  else
    warn "Skipped — edit $INSTALL_DIR/.env before launching"
  fi
}

# ── Summary ────────────────────────────────────────────────────
summary() {
  REAL_USER="${SUDO_USER:-pi}"
  echo -e "
${GREEN}${BOLD}
╔════════════════════════════════════════════════════════╗
║               ALL DONE — YOU'RE READY!                ║
╚════════════════════════════════════════════════════════╝${RESET}

  ${BOLD}Everything is installed:${RESET}
    Docker ............. $(docker --version 2>/dev/null || echo 'n/a')
    Docker Compose ..... $(docker compose version 2>/dev/null || echo 'n/a')
    Node.js ............ $(node --version 2>/dev/null || echo 'n/a')
    npm ................ $(npm --version 2>/dev/null || echo 'n/a')
    Claude Code ........ $(claude --version 2>/dev/null || echo 'installed')

  ${BOLD}Your files:${RESET}
    $INSTALL_DIR/
    ├── docker-compose.yml
    ├── .env                ← your API key
    ├── start-claude.sh     ← quick launcher
    └── workspace/          ← put your code here

  ${BOLD}Quick start:${RESET}
    ${CYAN}cd $INSTALL_DIR${RESET}
    ${CYAN}./start-claude.sh${RESET}

  ${BOLD}Or run directly:${RESET}
    ${CYAN}claude${RESET}                        ← native
    ${CYAN}docker compose up${RESET}             ← Docker

  ${YELLOW}NOTE: Log out & back in (or reboot) so docker group
  permissions take effect for '$REAL_USER'.${RESET}
"
}

# ── Main ───────────────────────────────────────────────────────
main() {
  banner
  preflight
  step_update
  step_docker
  step_compose
  step_node
  step_claude
  step_python
  step_scaffold
  ask_api_key
  summary
}

main
