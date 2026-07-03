#!/usr/bin/env python3
"""
Raspberry Pi Setup Script (thin wrapper)
========================================
All installation logic lives in the canonical installer, run.py, so
there is a single source of truth (including the OOM-guard NODE_OPTIONS
used when installing the Claude Code CLI on the Pi). This wrapper is
kept for backward compatibility.

Run with: sudo python3 setup_raspberry_pi.py
"""

import os
import sys

if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    run_py = os.path.join(here, "run.py")
    os.execv(sys.executable, [sys.executable, run_py, "setup"])
