# SD Card Flash Guide - Raspberry Pi Claude Code

Step-by-step record of how we built a ready-to-boot SD card with Raspberry Pi OS,
pre-configured WiFi/SSH, and the raspie Claude Code installer baked into the boot partition.

Done on: Windows 10, using Git Bash, PowerShell (elevated), and Python (Anaconda).

---

## Requirements

- Windows PC with Git Bash and Python (Anaconda) installed
- `pyfatfs` Python library (`pip install pyfatfs`)
- Micro SD card (16GB+ recommended) in a USB card reader
- Internet connection (to download the Pi OS image)
- The `raspie` project folder (from `D:\raspie` or cloned from GitHub)

## Overview

1. Download Raspberry Pi OS Lite (64-bit)
2. Decompress the image
3. Extract the FAT32 boot partition from the image
4. Inject WiFi config, SSH, raspie files, and install script into the boot partition
5. Write the modified boot partition back into the image
6. Flash the complete image to the SD card (elevated PowerShell)
7. Verify the MBR on-disk

---

## Step 1: Download and decompress Raspberry Pi OS

```bash
# Download (takes a few minutes)
curl -L -o /tmp/raspios.img.xz "https://downloads.raspberrypi.com/raspios_lite_arm64_latest"

# Decompress
unxz -k /tmp/raspios.img.xz

# Verify (~2.8GB)
ls -lh /tmp/raspios.img
```

## Step 2: Identify the SD card disk number

```powershell
# Run in PowerShell
Get-Disk | Format-Table Number, FriendlyName, Size, PartitionStyle -AutoSize
```

Look for the USB/SD card reader entry (e.g. "Generic STORAGE DEVICE"). Note the **disk number** (ours was `4`). Double-check the size matches your SD card.

## Step 3: Modify the image (add WiFi, SSH, raspie)

Save this as a Python script and run it with `python` (Anaconda, where pyfatfs is installed).

**IMPORTANT:** Edit the WiFi SSID and password before running.

```python
import os
import struct
from pyfatfs.PyFatFS import PyFatFS

IMG = r"C:\Users\ohjos\AppData\Local\Temp\raspios.img"
BOOT_START = 16384 * 512       # boot partition byte offset
BOOT_SIZE  = 1048576 * 512     # boot partition size (512MB)
BOOT_IMG   = r"C:\Users\ohjos\AppData\Local\Temp\bootfs.img"

# ===== EDIT THESE =====
WIFI_SSID     = "TP-Link_FORTRESS 2.4G"
WIFI_PASSWORD = "Zayne55936910"
WIFI_COUNTRY  = "US"
RASPIE_DIR    = r"D:\raspie"     # path to your raspie project folder
# =======================

# --- Extract boot partition from image ---
print("[1/4] Extracting boot partition...")
with open(IMG, "rb") as f:
    f.seek(BOOT_START)
    data = f.read(BOOT_SIZE)
with open(BOOT_IMG, "wb") as f:
    f.write(data)

# --- Add files to boot partition ---
print("[2/4] Adding WiFi, SSH, raspie files...")
fs = PyFatFS(filename=BOOT_IMG, read_only=False)

# WiFi config
wpa_conf = (
    "ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev\n"
    "update_config=1\n"
    f"country={WIFI_COUNTRY}\n"
    "\n"
    "network={\n"
    f'    ssid="{WIFI_SSID}"\n'
    f'    psk="{WIFI_PASSWORD}"\n'
    "    key_mgmt=WPA-PSK\n"
    "}\n"
)
fs.create("/wpa_supplicant.conf")
with fs.open("/wpa_supplicant.conf", "w") as f:
    f.write(wpa_conf)

# Enable SSH
fs.create("/ssh")
with fs.open("/ssh", "w") as f:
    f.write("")

# Install script (runs on the Pi to kick off the full setup)
setup_script = (
    "#!/bin/bash\n"
    "set -e\n"
    'echo ""\n'
    'echo "  ============================================"\n'
    'echo "  Raspberry Pi - Claude Code Installer"\n'
    'echo "  ============================================"\n'
    'echo ""\n'
    'RASPIE_SRC="/boot/firmware/raspie"\n'
    'RASPIE_DST="$HOME/raspie"\n'
    'if [ -d "$RASPIE_SRC" ]; then\n'
    '    echo "  Copying raspie to $RASPIE_DST..."\n'
    '    cp -r "$RASPIE_SRC" "$RASPIE_DST"\n'
    '    chmod -R u+rwX "$RASPIE_DST"\n'
    '    echo "  [OK] Copied!"\n'
    '    echo ""\n'
    '    cd "$RASPIE_DST"\n'
    '    sudo python3 run.py setup\n'
    "else\n"
    '    echo "  [ERROR] Cannot find $RASPIE_SRC"\n'
    "    exit 1\n"
    "fi\n"
)
fs.create("/install-claude.sh")
with fs.open("/install-claude.sh", "w") as f:
    f.write(setup_script)

# Raspie project files
fs.makedir("/raspie")
files_to_copy = [
    "run.py", "bootstrap.sh", "setup_raspberry_pi.py",
    "docker-compose.yml", "cli-commands.txt",
    "claude-setup-guide.txt", "README.md",
]
for fname in files_to_copy:
    src = os.path.join(RASPIE_DIR, fname)
    if os.path.exists(src):
        with open(src, "r", encoding="utf-8", errors="replace") as sf:
            content = sf.read()
        dst = f"/raspie/{fname}"
        fs.create(dst)
        with fs.open(dst, "w") as df:
            df.write(content)
        print(f"  Added: {dst}")

# Clean .env (no real API keys on the card)
fs.create("/raspie/.env")
with fs.open("/raspie/.env", "w") as f:
    f.write("# Paste your Anthropic API key here\nANTHROPIC_API_KEY=your-api-key-here\n")
fs.create("/raspie/.env.example")
with fs.open("/raspie/.env.example", "w") as f:
    f.write("# Copy this file to .env and paste your real API key\n# cp .env.example .env\nANTHROPIC_API_KEY=your-api-key-here\n")

fs.close()

# --- Write modified boot partition back into the image file ---
print("[3/4] Patching image with modified boot partition...")
with open(BOOT_IMG, "rb") as bf:
    boot_data = bf.read()
with open(IMG, "r+b") as f:
    f.seek(BOOT_START)
    f.write(boot_data)

# --- Verify MBR ---
print("[4/4] Verifying MBR in image...")
with open(IMG, "rb") as f:
    f.seek(510)
    sig = f.read(2)
    print(f"  MBR signature: {sig.hex()} (expect 55aa)")
    f.seek(446)
    for i in range(4):
        entry = f.read(16)
        ptype = entry[4]
        lba = struct.unpack_from('<I', entry, 8)[0]
        sectors = struct.unpack_from('<I', entry, 12)[0]
        if ptype != 0:
            print(f"  Partition {i+1}: type=0x{ptype:02x}, LBA={lba}, sectors={sectors}")

print("\nImage ready for flashing!")
```

## Step 4: Flash the image to the SD card

Save this as a `.ps1` file and run it **as Administrator** (right-click > Run as Administrator),
or launch it with `Start-Process -Verb RunAs`.

**IMPORTANT:** Change `$diskNumber` to match your SD card's disk number from Step 2.

```powershell
$ErrorActionPreference = "Stop"
$imgPath    = "C:\Users\ohjos\AppData\Local\Temp\raspios.img"
$diskNumber = 4    # <--- CHANGE THIS to your SD card disk number

# Clean the disk
Write-Host "[1/3] Cleaning disk $diskNumber..."
@"
select disk $diskNumber
clean
"@ | diskpart

# Write the image
Write-Host "[2/3] Writing image to disk..."
$source = [System.IO.File]::OpenRead($imgPath)
$target = New-Object System.IO.FileStream(
    "\\.\PHYSICALDRIVE$diskNumber",
    [System.IO.FileMode]::Open,
    [System.IO.FileAccess]::Write,
    [System.IO.FileShare]::None
)
$target.Seek(0, [System.IO.SeekOrigin]::Begin) | Out-Null

$bufferSize = 1MB
$buffer     = New-Object byte[] $bufferSize
$totalBytes = $source.Length
$written    = 0

while (($bytesRead = $source.Read($buffer, 0, $bufferSize)) -gt 0) {
    $target.Write($buffer, 0, $bytesRead)
    $written += $bytesRead
    $pct = [math]::Round(($written / $totalBytes) * 100, 1)
    if ($written % (50MB) -lt $bufferSize) {
        Write-Host "  Progress: $pct% ($([math]::Round($written/1MB))MB / $([math]::Round($totalBytes/1MB))MB)"
    }
}
$target.Flush()
$source.Close()
$target.Close()
Write-Host "[OK] Image written!"

# Verify MBR
Write-Host "[3/3] Verifying MBR on disk..."
Start-Sleep -Seconds 1
$verify = New-Object System.IO.FileStream(
    "\\.\PHYSICALDRIVE$diskNumber",
    [System.IO.FileMode]::Open,
    [System.IO.FileAccess]::Read,
    [System.IO.FileShare]::ReadWrite
)
$verify.Seek(0, [System.IO.SeekOrigin]::Begin) | Out-Null
$mbr = New-Object byte[] 512
$verify.Read($mbr, 0, 512) | Out-Null
$verify.Close()

$sig    = "{0:X2}{1:X2}" -f $mbr[510], $mbr[511]
$p1type = "{0:X2}" -f $mbr[450]
$p2type = "{0:X2}" -f $mbr[466]
Write-Host "  MBR Signature:    $sig (expect 55AA)"
Write-Host "  Partition 1 type: 0x$p1type (expect 0C = FAT32 boot)"
Write-Host "  Partition 2 type: 0x$p2type (expect 83 = Linux root)"

if ($sig -eq "55AA" -and $p1type -eq "0C" -and $p2type -eq "83") {
    Write-Host "  VERIFICATION PASSED!" -ForegroundColor Green
} else {
    Write-Host "  VERIFICATION FAILED!" -ForegroundColor Red
}
```

## Step 5: Boot the Pi

1. Remove the SD card from the USB reader
2. Insert it into the Pi's micro SD slot
3. Power on the Pi
4. Complete first-boot setup (create username/password)
5. The Pi will auto-connect to the WiFi network you configured

## Step 6: Run the Claude installer

From the Pi (directly or via SSH):

```bash
# SSH from another machine (optional)
ssh <your-username>@raspberrypi.local

# Run the installer
sudo bash /boot/firmware/install-claude.sh

# Reboot for Docker permissions
sudo reboot

# Launch Claude
claude
```

---

## What gets baked into the SD card

| File on boot partition       | Purpose                                     |
|------------------------------|---------------------------------------------|
| `wpa_supplicant.conf`        | Auto-connects to your WiFi on first boot    |
| `ssh` (empty file)           | Enables SSH server on first boot            |
| `install-claude.sh`          | One-command Claude Code installer launcher  |
| `raspie/run.py`              | Full auto-installer (Docker, Node, Claude)  |
| `raspie/bootstrap.sh`        | Bash alternative installer                  |
| `raspie/setup_raspberry_pi.py` | Standalone Python installer               |
| `raspie/docker-compose.yml`  | Docker config for running Claude            |
| `raspie/cli-commands.txt`    | CLI command reference                       |
| `raspie/claude-setup-guide.txt` | Manual setup guide                       |
| `raspie/README.md`           | Project documentation                       |
| `raspie/.env`                | API key placeholder (edit after setup)      |
| `raspie/.env.example`        | API key template                            |

## Notes

- The `pyfatfs` library is installed in Anaconda Python (`python`), not the Windows Store Python (`python3`). Use `python` to run the modification script.
- The flash script **must run as Administrator** since it writes directly to a physical disk.
- Always verify the disk number before flashing to avoid wiping the wrong drive.
- The `.env` file on the card has a placeholder key. The installer will prompt for a real key, or you can edit `~/claude-workspace/.env` after setup.
- Windows cannot mount the Pi's partitions after flashing (it doesn't recognize Linux ext4 or multi-partition removable drives). This is normal. The Pi will read them fine.
- To flash another card: just repeat Steps 2 and 4 (the modified image from Step 3 can be reused).
