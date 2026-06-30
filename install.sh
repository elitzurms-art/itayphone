#!/usr/bin/env bash
#
# ItayPhone installer for Raspberry Pi OS (64-bit, Bookworm).
# Works on Raspberry Pi 5 and Pi 4 Model B. Run on the Pi itself:
#   sudo ./install.sh
#
# It is safe to re-run. Steps that need a reboot are flagged at the end.

set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
  echo "Please run as root:  sudo ./install.sh" >&2
  exit 1
fi

REAL_USER="${SUDO_USER:-pi}"
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
echo "==> ItayPhone install (user: ${REAL_USER}, dir: ${PROJECT_DIR})"

# --- 0. Sanity checks (Pi model + architecture) -----------------------------
PI_MODEL="$(tr -d '\0' < /proc/device-tree/model 2>/dev/null || echo unknown)"
ARCH="$(dpkg --print-architecture)"
echo "==> Detected: ${PI_MODEL}  (arch: ${ARCH})"
if [[ "${ARCH}" != "arm64" ]]; then
  echo "!! This is a ${ARCH} (32-bit) OS. The ItayPhone UI/dialer/SMS will run,"
  echo "   but Waydroid (Android apps like WhatsApp) needs a 64-bit (arm64) OS."
  echo "   Re-flash with Raspberry Pi OS 64-bit to get Android apps."
fi
# Pi 4 with little RAM + Waydroid is tight; nudge toward swap.
MEM_MB="$(awk '/MemTotal/{print int($2/1024)}' /proc/meminfo 2>/dev/null || echo 0)"
if [[ "${MEM_MB}" -gt 0 && "${MEM_MB}" -lt 3500 ]]; then
  echo "!! Only ${MEM_MB}MB RAM. Waydroid may struggle; consider more swap/zram."
fi

# --- 1. System packages -----------------------------------------------------
echo "==> Installing system packages"
apt-get update
apt-get install -y \
  python3 python3-pip python3-venv \
  python3-kivy \
  python3-serial \
  python3-bidi \
  usb-modeswitch \
  zram-tools \
  git curl \
  fonts-dejavu fonts-noto-hinted fonts-noto-color-emoji

# --- 2. Python dependencies -------------------------------------------------
echo "==> Installing Python requirements"
pip3 install --break-system-packages -r "${PROJECT_DIR}/requirements.txt"

# --- 2b. zram compressed swap -----------------------------------------------
# Waydroid + the UI on a 4GB Pi can run out of RAM. zram gives a compressed
# in-RAM swap (zstd) — far faster than swapping to the SD card and easier on its
# flash. PERCENT=50 scales to the box (≈2GB on a 4GB Pi, ≈4GB on an 8GB one).
echo "==> Configuring zram swap (zstd, 50% of RAM)"
cat > /etc/default/zramswap <<'EOF'
# Managed by ItayPhone install.sh
ALGO=zstd
PERCENT=50
PRIORITY=100
EOF
systemctl enable --now zramswap 2>/dev/null || \
  echo "!! Could not start zramswap now; it will come up on next boot."

# --- 3. Serial / display config ---------------------------------------------
# The SIM7600 HAT is reached over USB (ttyUSB*) by default, so the GPIO UART is
# left free. If you wire the modem to the 40-pin UART instead, the serial steps
# below free /dev/serial0 for it.
#
# config.txt moved to /boot/firmware/ on Bookworm; older images use /boot/.
if [[ -f /boot/firmware/config.txt ]]; then
  CONFIG_TXT="/boot/firmware/config.txt"
elif [[ -f /boot/config.txt ]]; then
  CONFIG_TXT="/boot/config.txt"
else
  CONFIG_TXT="/boot/firmware/config.txt"
fi
echo "==> Using ${CONFIG_TXT}"
# HDMI needs no extra config. A DSI panel (e.g. Waveshare 5") ships its own
# overlay/driver — add it here per the panel's instructions when you switch.

# Disable the serial login console so a UART-attached modem isn't disturbed.
raspi-config nonint do_serial_hw 0 || true
raspi-config nonint do_serial_cons 1 || true

# ModemManager fights with us over the AT port; disable it.
echo "==> Disabling ModemManager (it grabs the AT port)"
systemctl disable --now ModemManager 2>/dev/null || true

# --- 4. Waydroid (Android apps in a container) ------------------------------
if ! command -v waydroid >/dev/null 2>&1; then
  echo "==> Installing Waydroid"
  curl -s https://repo.waydro.id | bash || \
    echo "!! Waydroid repo script failed; install manually later."
  apt-get install -y waydroid || true
else
  echo "==> Waydroid already installed"
fi

# Waydroid needs the Android 'binder' driver with three device nodes. On
# Raspberry Pi OS this comes from the binder_linux module — load it with the
# names Waydroid expects and persist the config across reboots.
echo "==> Configuring binder for Waydroid"
echo "binder_linux" > /etc/modules-load.d/binder.conf
echo "options binder_linux devices=binder,hwbinder,vndbinder" \
  > /etc/modprobe.d/binder.conf
if modprobe binder_linux devices=binder,hwbinder,vndbinder 2>/dev/null; then
  echo "   binder_linux loaded."
else
  echo "!! binder_linux not in this kernel. Waydroid won't start until it is —"
  echo "   install a kernel with CONFIG_ANDROID_BINDER_IPC (or binder dkms)."
fi
# First-time Android image download (safe to re-run; needs network).
if [[ ! -d /var/lib/waydroid/images ]]; then
  echo "==> Initialising Waydroid (downloads the Android image)"
  waydroid init || echo "!! 'waydroid init' failed; run it manually after a reboot."
fi

# --- 5. Autostart the ItayPhone UI ------------------------------------------
# Installed but NOT enabled: with no SIM7600 plugged in, real mode fails and the
# service would crash-loop. Enable it once the modem is connected (see notes).
echo "==> Installing systemd service (left disabled for now)"
cat > /etc/systemd/system/itayphone.service <<EOF
[Unit]
Description=ItayPhone UI
After=graphical.target

[Service]
User=${REAL_USER}
WorkingDirectory=${PROJECT_DIR}/src
Environment=PYTHONPATH=${PROJECT_DIR}/src
ExecStart=/usr/bin/python3 -m itayphone.main --port /dev/ttyUSB2
Restart=on-failure

[Install]
WantedBy=graphical.target
EOF
systemctl daemon-reload

# --- 6. VoLTE note ----------------------------------------------------------
# Israel turned off 2G/3G, so voice calls must use VoLTE. We don't force it at
# install time (the modem may not be plugged in yet) — run the helper once the
# SIM7600 is connected; it sets network mode and prints IMS/VoLTE diagnostics.
echo "==> VoLTE: after the modem is connected run:"
echo "     cd ${PROJECT_DIR}/src && python3 -m itayphone.main --volte --port /dev/ttyUSB2"

cat <<EOF

==> Done.
Next steps:
  1. Try the UI right now — no modem needed (great for the HDMI bring-up):
       cd ${PROJECT_DIR}/src && python3 -m itayphone.main --mock
  2. Headless smoke-test of the modem layer:
       python3 -m itayphone.main --mock --demo
  3. Reboot (applies serial/Waydroid changes):  sudo reboot
  4. Once the SIM7600 HAT + SIM are connected, run against real hardware:
       python3 -m itayphone.main --port /dev/ttyUSB2
  5. VoLTE setup / diagnostics (needed since Israel's 2G/3G are off):
       python3 -m itayphone.main --volte --port /dev/ttyUSB2
  6. Android apps:  waydroid session start   (then install APKs)
  7. Autostart on boot (only after the modem works in step 4):
       sudo systemctl enable --now itayphone.service

If voice calls still fail to connect after step 5, the carrier likely needs to
provision VoLTE for the SIM, or the modem firmware needs a VoLTE build. See PLAN.md.
EOF
