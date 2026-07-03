#!/usr/bin/env bash
# ══════════════════════════════════════════════════════════════
#  Raspberry Pi – Claude Code Bootstrap (thin wrapper)
#
#  All installation logic lives in the canonical installer, run.py,
#  so there is a single source of truth (including the OOM-guard
#  NODE_OPTIONS used when installing the Claude Code CLI on the Pi).
#  This wrapper is kept for backward compatibility.
#
#  Usage:
#    sudo bash bootstrap.sh
# ══════════════════════════════════════════════════════════════
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

exec python3 "$SCRIPT_DIR/run.py" setup
