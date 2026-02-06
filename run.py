#!/usr/bin/env python3
"""
Raspberry Pi Claude Installer
==============================
One command:   sudo python3 run.py setup

Installs and configures:
  - System updates & essentials
  - Docker & Docker Compose
  - Node.js 20 & npm
  - Claude Code CLI
  - Anthropic Python SDK
  - docker-compose.yml + launcher script
"""

import subprocess
import sys
import os
import shutil
import textwrap

# ── Colours ──────────────────────────────────────────────────────
G  = "\033[92m"   # green
Y  = "\033[93m"   # yellow
R  = "\033[91m"   # red
C  = "\033[96m"   # cyan
B  = "\033[1m"    # bold
X  = "\033[0m"    # reset


# ── Helpers ──────────────────────────────────────────────────────
def ok(msg):   print(f"{G}{B}[OK]{X} {msg}")
def warn(msg): print(f"{Y}[!!]{X} {msg}")
def err(msg):  print(f"{R}[XX]{X} {msg}")
def info(msg): print(f"{C}  -> {X}{msg}")

def run(cmd, desc=None, check=True):
    if desc:
        info(desc)
    try:
        subprocess.run(cmd, shell=True, check=check,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        return True
    except subprocess.CalledProcessError as e:
        err(f"Failed: {cmd}")
        if e.stdout:
            print(e.stdout[-600:])
        if check:
            sys.exit(1)
        return False

def has(cmd):
    return shutil.which(cmd) is not None

def node_major():
    try:
        out = subprocess.run("node --version", shell=True,
                             capture_output=True, text=True)
        return int(out.stdout.strip().lstrip("v").split(".")[0])
    except Exception:
        return 0

def real_user():
    return os.environ.get("SUDO_USER", "pi")

def real_home():
    return os.path.expanduser(f"~{real_user()}")


# ── Pre-flight checks ───────────────────────────────────────────
def preflight():
    print(f"\n{B}Pre-flight checks{X}")
    print("-" * 45)

    # root
    if os.geteuid() != 0:
        err("Must be run as root.  Use:  sudo python3 run.py setup")
        sys.exit(1)
    ok("Running as root")

    # architecture
    arch = os.uname().machine
    if arch == "aarch64":
        ok(f"Arch: {arch} (64-bit)")
    elif arch == "armv7l":
        warn(f"Arch: {arch} (32-bit) — 64-bit Pi OS recommended")
    else:
        ok(f"Arch: {arch}")

    # Pi model
    try:
        with open("/proc/device-tree/model") as f:
            model = f.read().strip().replace("\x00", "")
        ok(f"Device: {model}")
    except FileNotFoundError:
        warn("Could not detect Pi model")

    # RAM
    with open("/proc/meminfo") as f:
        for line in f:
            if line.startswith("MemTotal"):
                ram_mb = int(line.split()[1]) // 1024
                break
    if ram_mb < 2048:
        warn(f"RAM: {ram_mb}MB (low — may be tight)")
    else:
        ok(f"RAM: {ram_mb}MB")

    # Disk
    st = os.statvfs("/")
    free_gb = (st.f_bavail * st.f_frsize) // (1024 ** 3)
    if free_gb < 4:
        err(f"Disk: only {free_gb}GB free — need at least 4GB")
        sys.exit(1)
    ok(f"Disk: {free_gb}GB free")

    # Internet
    if run("ping -c1 -W3 google.com", check=False):
        ok("Internet: connected")
    else:
        err("No internet connection")
        sys.exit(1)

    print()


# ── Installers ───────────────────────────────────────────────────
def install_updates():
    print(f"\n{B}[1/7] System update{X}")
    run("apt-get update -y -qq", "apt update")
    run("apt-get upgrade -y -qq", "apt upgrade")
    run("apt-get install -y -qq curl wget git ca-certificates gnupg lsb-release",
        "Installing essentials")
    ok("System up to date")


def install_docker():
    print(f"\n{B}[2/7] Docker{X}")
    if has("docker"):
        warn("Docker already installed")
    else:
        run("curl -fsSL https://get.docker.com -o /tmp/get-docker.sh", "Downloading installer")
        run("sh /tmp/get-docker.sh", "Installing Docker")
    run("systemctl enable docker && systemctl start docker", "Enabling service")
    run(f"usermod -aG docker {real_user()}", f"Adding {real_user()} to docker group")
    ok("Docker ready")


def install_compose():
    print(f"\n{B}[3/7] Docker Compose{X}")
    if run("docker compose version", check=False):
        warn("Docker Compose already installed")
    else:
        run("apt-get install -y -qq docker-compose-plugin", "Installing compose plugin")
    ok("Docker Compose ready")


def install_node():
    print(f"\n{B}[4/7] Node.js & npm{X}")
    if has("node") and node_major() >= 18:
        warn(f"Node v{node_major()} already installed")
    else:
        if has("node"):
            run("apt-get remove -y -qq nodejs", "Removing old node")
        run("curl -fsSL https://deb.nodesource.com/setup_20.x | bash -", "Adding NodeSource repo")
        run("apt-get install -y -qq nodejs", "Installing Node 20")
    ok("Node & npm ready")


def install_claude_cli():
    print(f"\n{B}[5/7] Claude Code CLI{X}")
    run("npm install -g @anthropic-ai/claude-code --loglevel=warn", "Installing via npm")
    ok("Claude Code CLI installed")


def install_python_sdk():
    print(f"\n{B}[6/7] Anthropic Python SDK{X}")
    run("apt-get install -y -qq python3-pip python3-venv", "Ensuring pip")
    u = real_user()
    run(f'sudo -u {u} pip3 install --user --break-system-packages anthropic 2>/dev/null '
        f'|| sudo -u {u} pip3 install --user anthropic',
        "Installing SDK", check=False)
    ok("Python SDK installed")


def scaffold():
    print(f"\n{B}[7/7] Creating project files{X}")

    base = os.path.join(real_home(), "claude-workspace")
    ws   = os.path.join(base, "workspace")
    os.makedirs(ws, exist_ok=True)

    # ── docker-compose.yml ────────────────────────────
    with open(os.path.join(base, "docker-compose.yml"), "w") as f:
        f.write(textwrap.dedent('''\
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
                    echo "Installing Claude Code …"
                    npm install -g @anthropic-ai/claude-code --loglevel=warn
                    echo "Launching …"
                    exec claude

            volumes:
              claude-config:
              npm-cache:
        '''))

    # ── .env ──────────────────────────────────────────
    env_path = os.path.join(base, ".env")
    if not os.path.exists(env_path) or "your-api-key-here" in open(env_path).read():
        with open(env_path, "w") as f:
            f.write('# Paste your Anthropic API key below\n')
            f.write('ANTHROPIC_API_KEY=your-api-key-here\n')

    # ── start-claude.sh ──────────────────────────────
    launcher = os.path.join(base, "start-claude.sh")
    with open(launcher, "w") as f:
        f.write(textwrap.dedent('''\
            #!/usr/bin/env bash
            set -e
            DIR="$(cd "$(dirname "$0")" && pwd)"
            if [ -z "$ANTHROPIC_API_KEY" ]; then
              source "$DIR/.env" 2>/dev/null || true
              export ANTHROPIC_API_KEY
            fi
            if [ "$ANTHROPIC_API_KEY" = "your-api-key-here" ] || [ -z "$ANTHROPIC_API_KEY" ]; then
              echo ""; echo "  No API key set.  Edit $DIR/.env first."; echo ""; exit 1
            fi
            echo ""
            echo "  1) Native  (claude CLI)"
            echo "  2) Docker  (container)"
            echo ""
            read -rp "  Pick [1/2]: " choice
            case "$choice" in
              2) cd "$DIR" && docker compose up ;;
              *) cd "$DIR/workspace" && claude ;;
            esac
        '''))
    os.chmod(launcher, 0o755)

    # fix ownership
    run(f"chown -R {real_user()}:{real_user()} {base}")

    ok(f"Files created at {base}")
    return base


# ── API key prompt ───────────────────────────────────────────────
def ask_key(base):
    print(f"\n{C}{B}-- API Key --{X}")
    print("  Get yours at: https://console.anthropic.com")
    key = input("\n  Paste your API key (Enter to skip): ").strip()

    if not key:
        warn("Skipped — edit .env later before running Claude")
        return

    # save to .env
    env_path = os.path.join(base, ".env")
    with open(env_path, "w") as f:
        f.write(f'ANTHROPIC_API_KEY={key}\n')

    # save to bashrc
    bashrc = os.path.join(real_home(), ".bashrc")
    try:
        existing = open(bashrc).read()
    except FileNotFoundError:
        existing = ""
    if "ANTHROPIC_API_KEY" not in existing:
        with open(bashrc, "a") as f:
            f.write(f'\n# Anthropic API Key\nexport ANTHROPIC_API_KEY="{key}"\n')

    ok("API key saved to .env and ~/.bashrc")


# ── Final summary ────────────────────────────────────────────────
def summary(base):
    print(f"""
{G}{B}
╔═══════════════════════════════════════════════════════╗
║              SETUP COMPLETE!                          ║
╚═══════════════════════════════════════════════════════╝{X}

  {B}Installed:{X}
    Docker, Docker Compose, Node.js, npm,
    Claude Code CLI, Anthropic Python SDK

  {B}Your workspace:{X}
    {base}/
    ├── docker-compose.yml
    ├── .env               <- API key goes here
    ├── start-claude.sh    <- quick launcher
    └── workspace/         <- your project files

  {B}To launch Claude:{X}
    cd {base}
    ./start-claude.sh

  {B}Or directly:{X}
    claude                  <- native
    docker compose up       <- in Docker

  {Y}Reboot or run 'newgrp docker' for docker permissions.{X}
""")


# ── Entry point ──────────────────────────────────────────────────
def setup():
    print(f"""
{C}{B}
╔═══════════════════════════════════════════════════════╗
║  Raspberry Pi  —  Claude Code  Full Auto-Installer    ║
╚═══════════════════════════════════════════════════════╝{X}
""")
    preflight()
    install_updates()
    install_docker()
    install_compose()
    install_node()
    install_claude_cli()
    install_python_sdk()
    base = scaffold()
    ask_key(base)
    summary(base)


def usage():
    print(f"""
{B}Usage:{X}
  sudo python3 run.py setup     Install everything
  sudo python3 run.py help      Show this message
""")


if __name__ == "__main__":
    cmd = sys.argv[1].lower() if len(sys.argv) > 1 else ""
    if cmd == "setup":
        setup()
    else:
        usage()
