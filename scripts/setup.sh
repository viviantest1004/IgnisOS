#!/usr/bin/env bash
# IgnisOS — Post-install Setup Script
# Run this after installing Ubuntu 24.04 ARM64 base

set -euo pipefail

GRN='\033[1;32m' CYN='\033[1;36m' RST='\033[0m'
ok()  { echo -e "${GRN}[OK]${RST} $*"; }
log() { echo -e "${CYN}[>>]${RST} $*"; }

log "Installing dependencies..."
apt-get update -qq
apt-get install -y --no-install-recommends \
  python3 python3-gi python3-gi-cairo gir1.2-gtk-4.0 gir1.2-adw-1 \
  gir1.2-vte-3.91 python3-vte \
  nmcli bluetooth bluez \
  brightnessctl alsa-utils pulseaudio \
  xdg-utils mimetypes

ok "Dependencies installed"

INSTALL_DIR="/usr/share/ignis"
BIN_DIR="/usr/local/bin"

log "Installing IgnisOS apps..."
mkdir -p "$INSTALL_DIR"
cp -r ignis-shell    "$INSTALL_DIR/"
cp -r ignis-settings "$INSTALL_DIR/"
cp -r ignis-files    "$INSTALL_DIR/"
cp -r ignis-calc     "$INSTALL_DIR/"
cp -r ignis-terminal "$INSTALL_DIR/"
cp -r ignis-recovery "$INSTALL_DIR/"
cp -r ignis-icons    "$INSTALL_DIR/"

log "Creating launcher scripts..."
for app in shell settings files calc terminal; do
    cat > "${BIN_DIR}/ignis-${app}" <<EOF
#!/usr/bin/env bash
exec python3 ${INSTALL_DIR}/ignis-${app}/${app}.py "\$@"
EOF
    chmod +x "${BIN_DIR}/ignis-${app}"
done

# recovery
install -m 755 ignis-recovery/recovery.sh "${BIN_DIR}/ignis-recovery"

# Uptime Kernel
log "Building Uptime Kernel (ARM64)..."
cd uptime-kernel
if command -v aarch64-linux-gnu-gcc &>/dev/null; then
    aarch64-linux-gnu-gcc -O2 -static -o uptime-kernel-arm64 uptime_kernel.c -lm
    install -m 755 uptime-kernel-arm64 "${BIN_DIR}/uptime-kernel"
else
    gcc -O2 -o uptime-kernel-native uptime_kernel.c -lm
    install -m 755 uptime-kernel-native "${BIN_DIR}/uptime-kernel"
fi
cd ..
ok "Uptime Kernel installed"

log "Setting up autostart..."
mkdir -p /etc/xdg/autostart
cat > /etc/xdg/autostart/ignis-shell.desktop <<EOF
[Desktop Entry]
Type=Application
Name=Ignis Shell
Exec=/usr/local/bin/ignis-shell
X-GNOME-Autostart-enabled=true
EOF

log "Installing .desktop files..."
mkdir -p /usr/share/applications
for app in \
    "ignis-terminal;터미널;🖥️;ignis-terminal" \
    "ignis-calc;계산기;🧮;ignis-calc" \
    "ignis-files;파일;📂;ignis-files" \
    "ignis-settings;설정;⚙️;ignis-settings"; do
    IFS=';' read -r id name icon cmd <<< "$app"
    cat > "/usr/share/applications/${id}.desktop" <<EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=${name}
Icon=${icon}
Exec=${cmd}
Categories=System;
EOF
done

log "Applying IgnisOS branding..."
cp rootfs/etc/os-release  /etc/os-release
cp rootfs/etc/motd        /etc/motd

log "Configuring GRUB..."
cp config/grub/grub.cfg /etc/grub.d/99_ignis 2>/dev/null || true
update-grub 2>/dev/null || grub-mkconfig -o /boot/grub/grub.cfg 2>/dev/null || true

ok "IgnisOS setup complete!"
echo ""
echo "  Reboot to start IgnisOS Desktop"
echo "  ignis-terminal  → 터미널"
echo "  ignis-settings  → 설정"
echo "  ignis-files     → 파일 관리자"
echo "  ignis-calc      → 계산기"

# OOBE (첫 실행 설정 마법사)
log "Installing OOBE (first-run wizard)..."
cp -r ignis-oobe "$INSTALL_DIR/"
cat > "${BIN_DIR}/ignis-oobe" <<BEOF
#!/usr/bin/env bash
exec python3 ${INSTALL_DIR}/ignis-oobe/oobe.py "\$@"
BEOF
chmod +x "${BIN_DIR}/ignis-oobe"

# OOBE 자동 시작 (첫 부팅에만)
cat > /etc/xdg/autostart/ignis-oobe.desktop <<DEOF
[Desktop Entry]
Type=Application
Name=IgnisOS Setup
Exec=/usr/local/bin/ignis-oobe
X-GNOME-Autostart-enabled=true
DEOF
ok "OOBE installed"
