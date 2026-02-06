#!/usr/bin/env python3
"""
Raspberry Pi Setup Script
=========================
Automates installation of:
  - System updates
  - Docker & Docker Compose
  - Node.js & npm
  - Claude Code CLI
  - Anthropic Python SDK

Run with: sudo python3 setup_raspberry_pi.py
"""

import subprocess
import sys
import os
import shutil
import time


# ── Colours for terminal output ──────────────────────────────────────────────
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"


def banner():
    print(f"""
{CYAN}{BOLD}
 ╔══════════════════════════════════════════════════════╗
 ║   Raspberry Pi  –  Docker + Claude  Setup Script     ║
 ╚══════════════════════════════════════════════════════╝
{RESET}""")


def log_step(msg):
    print(f"\n{BOLD}{GREEN}[✓] {msg}{RESET}")


def log_warn(msg):
    print(f"{YELLOW}[!] {msg}{RESET}")


def log_error(msg):
    print(f"{RED}[✗] {msg}{RESET}")


def log_info(msg):
    print(f"{CYAN}    → {msg}{RESET}")


def run(cmd, description="", check=True, shell=True):
    """Run a shell command with live output."""
    if description:
        log_info(description)
    try:
        result = subprocess.run(
            cmd, shell=shell, check=check,
            text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
        )
        return result.returncode == 0
    except subprocess.CalledProcessError as e:
        log_error(f"Command failed: {cmd}")
        if e.stdout:
            print(e.stdout[-500:])  # print last 500 chars of output
        return False


def check_root():
    """Ensure the script is running as root."""
    if os.geteuid() != 0:
        log_error("This script must be run as root.")
        print("  Re-run with:  sudo python3 setup_raspberry_pi.py")
        sys.exit(1)


def get_real_user():
    """Get the non-root user who invoked sudo."""
    return os.environ.get("SUDO_USER", "pi")


def is_installed(cmd):
    """Check if a command is available on PATH."""
    return shutil.which(cmd) is not None


# ─────────────────────────────────────────────────────────────────────────────
#  STEP 1: System Update
# ─────────────────────────────────────────────────────────────────────────────
def update_system():
    log_step("STEP 1/6  –  Updating & upgrading system packages")
    run("apt-get update -y", "Running apt-get update …")
    run("apt-get upgrade -y", "Running apt-get upgrade …")
    run("apt-get install -y curl wget git ca-certificates gnupg lsb-release",
        "Installing essential utilities …")


# ─────────────────────────────────────────────────────────────────────────────
#  STEP 2: Docker
# ─────────────────────────────────────────────────────────────────────────────
def install_docker():
    log_step("STEP 2/6  –  Installing Docker")

    if is_installed("docker"):
        log_warn("Docker is already installed – skipping.")
        run("docker --version", "Current Docker version:")
    else:
        log_info("Downloading Docker install script …")
        run("curl -fsSL https://get.docker.com -o /tmp/get-docker.sh")
        run("sh /tmp/get-docker.sh", "Running official Docker installer …")

        if not is_installed("docker"):
            log_error("Docker installation failed. Check output above.")
            sys.exit(1)

    # Add the real user to the docker group so they can run without sudo
    user = get_real_user()
    run(f"usermod -aG docker {user}",
        f"Adding '{user}' to the docker group …")

    # Enable & start Docker service
    run("systemctl enable docker", "Enabling Docker on boot …")
    run("systemctl start docker", "Starting Docker service …")

    log_info("Docker installed successfully.")
    run("docker --version")


# ─────────────────────────────────────────────────────────────────────────────
#  STEP 3: Docker Compose
# ─────────────────────────────────────────────────────────────────────────────
def install_docker_compose():
    log_step("STEP 3/6  –  Installing Docker Compose plugin")

    if is_installed("docker-compose") or run(
        "docker compose version", check=False
    ):
        log_warn("Docker Compose is already available – skipping.")
    else:
        run("apt-get install -y docker-compose-plugin",
            "Installing docker-compose-plugin …")

    run("docker compose version", "Docker Compose version:", check=False)


# ─────────────────────────────────────────────────────────────────────────────
#  STEP 4: Node.js & npm
# ─────────────────────────────────────────────────────────────────────────────
def install_node():
    log_step("STEP 4/6  –  Installing Node.js & npm")

    needs_install = True

    if is_installed("node"):
        out = subprocess.run(
            "node --version", shell=True, capture_output=True, text=True
        )
        version_str = out.stdout.strip().lstrip("v")
        try:
            major = int(version_str.split(".")[0])
            if major >= 18:
                log_warn(f"Node.js v{version_str} already installed – skipping.")
                needs_install = False
            else:
                log_warn(f"Node.js v{version_str} is too old (need ≥18). Upgrading …")
                run("apt-get remove -y nodejs", "Removing old Node.js …")
        except ValueError:
            pass

    if needs_install:
        run("curl -fsSL https://deb.nodesource.com/setup_20.x | bash -",
            "Adding NodeSource repo (Node 20 LTS) …")
        run("apt-get install -y nodejs",
            "Installing Node.js …")

    run("node --version", "Node version:")
    run("npm --version", "npm version:")


# ─────────────────────────────────────────────────────────────────────────────
#  STEP 5: Claude Code CLI
# ─────────────────────────────────────────────────────────────────────────────
def install_claude_code():
    log_step("STEP 5/6  –  Installing Claude Code CLI")

    if is_installed("claude"):
        log_warn("Claude Code CLI already installed – updating …")
        run("npm update -g @anthropic-ai/claude-code",
            "Updating Claude Code …")
    else:
        run("npm install -g @anthropic-ai/claude-code",
            "Installing Claude Code via npm …")

    if is_installed("claude"):
        log_info("Claude Code CLI is ready. Run 'claude' to start.")
    else:
        log_warn("Claude Code CLI could not be verified on PATH.")
        log_info("You may need to open a new terminal or run: hash -r")


# ─────────────────────────────────────────────────────────────────────────────
#  STEP 6: Anthropic Python SDK
# ─────────────────────────────────────────────────────────────────────────────
def install_python_sdk():
    log_step("STEP 6/6  –  Installing Anthropic Python SDK")

    run("apt-get install -y python3-pip python3-venv",
        "Ensuring pip & venv are available …")

    user = get_real_user()
    home = os.path.expanduser(f"~{user}")

    # Install for the real user (not root)
    run(f"sudo -u {user} pip3 install --user --break-system-packages anthropic 2>/dev/null "
        f"|| sudo -u {user} pip3 install --user anthropic",
        "Installing anthropic SDK for user …", check=False)

    log_info("Anthropic Python SDK installed.")


# ─────────────────────────────────────────────────────────────────────────────
#  API Key helper
# ─────────────────────────────────────────────────────────────────────────────
def configure_api_key():
    user = get_real_user()
    home = os.path.expanduser(f"~{user}")
    bashrc = os.path.join(home, ".bashrc")

    # Check if already configured
    try:
        with open(bashrc, "r") as f:
            if "ANTHROPIC_API_KEY" in f.read():
                log_warn("ANTHROPIC_API_KEY already present in .bashrc – skipping.")
                return
    except FileNotFoundError:
        pass

    print(f"""
{CYAN}{BOLD}── API Key Setup ──────────────────────────────────────────{RESET}
  To use Claude you need an Anthropic API key.
  Get one at: {BOLD}https://console.anthropic.com{RESET}
""")

    key = input("  Paste your API key (or press Enter to skip): ").strip()

    if key:
        with open(bashrc, "a") as f:
            f.write(f'\n# Anthropic API Key\nexport ANTHROPIC_API_KEY="{key}"\n')
        # Also set for current session
        os.environ["ANTHROPIC_API_KEY"] = key
        log_info("API key saved to ~/.bashrc")
    else:
        log_warn("Skipped. Set it later with:")
        print(f'  echo \'export ANTHROPIC_API_KEY="sk-..."\' >> ~/.bashrc && source ~/.bashrc')


# ─────────────────────────────────────────────────────────────────────────────
#  Summary
# ─────────────────────────────────────────────────────────────────────────────
def print_summary():
    user = get_real_user()
    print(f"""
{GREEN}{BOLD}
 ╔══════════════════════════════════════════════════════╗
 ║              SETUP COMPLETE!                         ║
 ╚══════════════════════════════════════════════════════╝{RESET}

  {BOLD}Installed:{RESET}
    • Docker           → docker --version
    • Docker Compose   → docker compose version
    • Node.js & npm    → node --version / npm --version
    • Claude Code CLI  → claude
    • Anthropic SDK    → python3 -c "import anthropic"

  {BOLD}Quick Start:{RESET}
    1. Open a new terminal (or run: {CYAN}newgrp docker{RESET})
    2. Verify Docker:   {CYAN}docker run hello-world{RESET}
    3. Launch Claude:   {CYAN}claude{RESET}

  {BOLD}Run Claude in Docker (optional):{RESET}
    docker run -it --rm \\
      -e ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY \\
      node:20-slim bash -c "npm i -g @anthropic-ai/claude-code && claude"

  {YELLOW}NOTE: Log out & back in (or reboot) for docker group
  permissions to take effect for user '{user}'.{RESET}
""")


# ─────────────────────────────────────────────────────────────────────────────
#  Main
# ─────────────────────────────────────────────────────────────────────────────
def main():
    banner()
    check_root()

    update_system()
    install_docker()
    install_docker_compose()
    install_node()
    install_claude_code()
    install_python_sdk()
    configure_api_key()
    print_summary()


if __name__ == "__main__":
    main()
