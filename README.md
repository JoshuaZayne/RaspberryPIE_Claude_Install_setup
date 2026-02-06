# Raspberry Pi - Claude Code Installer

One-command setup to get **Claude Code**, **Docker**, **Node.js**, and the **Anthropic Python SDK** running on a Raspberry Pi.

```bash
sudo python3 run.py setup
```

That's it. The script checks your Pi, installs everything, and sets up your workspace.

---

## What Gets Installed

| Tool | Purpose |
|------|---------|
| **Docker** | Run Claude in an isolated container |
| **Docker Compose** | Manage the Claude container with one command |
| **Node.js 20 + npm** | Required by Claude Code CLI |
| **Claude Code CLI** | Anthropic's official CLI for Claude |
| **Anthropic Python SDK** | Use Claude from Python scripts |

## Requirements

- Raspberry Pi 4 or 5 (4GB+ RAM recommended)
- Raspberry Pi OS (64-bit recommended)
- Internet connection
- An [Anthropic API key](https://console.anthropic.com)

## Quick Start

### 1. Clone this repo on your Pi

```bash
git clone https://github.com/JoshuaZayne/RaspberryPIE_Claude_Install_setup.git
cd RaspberryPIE_Claude_Install_setup
```

### 2. Run the installer

```bash
sudo python3 run.py setup
```

The script will:
- Check your Pi (model, architecture, RAM, disk, internet)
- Install Docker, Docker Compose, Node.js, npm
- Install Claude Code CLI and the Python SDK
- Create a workspace at `~/claude-workspace/`
- Prompt you for your API key

### 3. Launch Claude

**Native (direct CLI):**
```bash
claude
```

**Interactive launcher (pick native or Docker):**
```bash
cd ~/claude-workspace
./start-claude.sh
```

**Docker:**
```bash
cd ~/claude-workspace
docker compose up
```

## Project Structure

```
raspie/
├── run.py                    # Full auto-installer (sudo python3 run.py setup)
├── docker-compose.yml        # Runs Claude in a Docker container
├── .env                      # Your API key (edit before using Docker)
├── bootstrap.sh              # Bash alternative to run.py
├── setup_raspberry_pi.py     # Standalone Python installer
├── cli-commands.txt          # Full CLI command reference
├── claude-setup-guide.txt    # Step-by-step manual setup guide
└── workspace/                # Mounted into the Docker container
```

## Running Claude in Docker

The included `docker-compose.yml` runs Claude Code inside a container with persistent config.

```bash
# Edit your API key
nano .env

# Start (foreground)
docker compose up

# Start (background)
docker compose up -d

# Attach to a running session
docker attach claude-code

# Detach without stopping: Ctrl+P then Ctrl+Q

# Stop
docker compose down
```

## Common Commands

| Action | Command |
|--------|---------|
| Full install | `sudo python3 run.py setup` |
| Launch Claude | `claude` |
| Launch in Docker | `docker compose up` |
| Update Claude CLI | `sudo npm update -g @anthropic-ai/claude-code` |
| Set API key | `export ANTHROPIC_API_KEY="sk-..."` |
| Check Docker | `docker ps` |
| View logs | `docker logs claude-code` |
| Pi temperature | `vcgencmd measure_temp` |

See [`cli-commands.txt`](cli-commands.txt) for the full command reference.

## Updating

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Update Claude Code CLI
sudo npm update -g @anthropic-ai/claude-code

# Update Python SDK
pip3 install --user --upgrade anthropic

# Update Docker image
cd ~/claude-workspace && docker compose pull && docker compose up -d
```

## Uninstalling

```bash
# Remove Claude CLI
sudo npm uninstall -g @anthropic-ai/claude-code

# Remove Python SDK
pip3 uninstall anthropic

# Remove container and volumes
cd ~/claude-workspace && docker compose down -v

# Remove Docker
sudo apt remove docker-ce docker-ce-cli containerd.io

# Delete workspace
rm -rf ~/claude-workspace
```

## Troubleshooting

- **Permission denied on Docker** — Log out and back in (or reboot) after setup so the docker group takes effect, or run `newgrp docker`.
- **npm install fails** — Try with `sudo`: `sudo npm install -g @anthropic-ai/claude-code`
- **GLIBC errors** — You're likely on 32-bit Pi OS. Switch to 64-bit.
- **Low memory** — Pi models with <2GB RAM may struggle. Use the Python SDK or curl approach instead of the full CLI.
- **API key not working** — Verify at [console.anthropic.com](https://console.anthropic.com) that your key is active and has credits.

## License

MIT
