#!/usr/bin/env bash
# IgnisOS Build Script — ARM64
# Builds a bootable IgnisOS image based on Ubuntu 24.04 (noble)
#
# Requirements (Ubuntu/Debian host):
#   sudo apt install debootstrap qemu-user-static binfmt-support
#   sudo apt install grub-efi-arm64 grub-efi-arm64-bin dosfstools mtools
#   sudo apt install squashfs-tools xorriso isolinux
#
# Usage:
#   sudo ./build.sh [--clean]

set -euo pipefail

# ── 설정 ────────────────────────────────────────────
IGNIS_NAME="IgnisOS"
IGNIS_VERSION="1.0.0"
IGNIS_CODENAME="Ember"
UBUNTU_BASE="noble"         # Ubuntu 24.04 LTS
ARCH="arm64"
MIRROR="http://ports.ubuntu.com/ubuntu-ports"
WORK_DIR="$(pwd)/build"
ROOTFS_DIR="${WORK_DIR}/rootfs"
ISO_DIR="${WORK_DIR}/iso"
OUTPUT_ISO="${WORK_DIR}/${IGNIS_NAME}-${IGNIS_VERSION}-${ARCH}.iso"

RED='\033[1;31m'
GREEN='\033[1;32m'
YELLOW='\033[1;33m'
CYAN='\033[1;36m'
RESET='\033[0m'

log()  { echo -e "${CYAN}[IgnisOS]${RESET} $*"; }
ok()   { echo -e "${GREEN}[  OK  ]${RESET} $*"; }
warn() { echo -e "${YELLOW}[ WARN ]${RESET} $*"; }
err()  { echo -e "${RED}[ERROR ]${RESET} $*"; exit 1; }

# ── 권한 확인 ────────────────────────────────────────
[[ $EUID -ne 0 ]] && err "Run as root: sudo $0"

# ── 클린 빌드 ────────────────────────────────────────
if [[ "${1:-}" == "--clean" ]]; then
  log "Cleaning build directory..."
  rm -rf "${WORK_DIR}"
  ok "Cleaned."
fi

mkdir -p "${ROOTFS_DIR}" "${ISO_DIR}/boot/grub" "${ISO_DIR}/EFI/BOOT"

# ── 1. debootstrap — Ubuntu ARM64 base ──────────────
log "Step 1/7: Bootstrapping Ubuntu ${UBUNTU_BASE} (ARM64)..."
if [[ ! -f "${ROOTFS_DIR}/bin/bash" ]]; then
  debootstrap --arch=${ARCH} --foreign ${UBUNTU_BASE} "${ROOTFS_DIR}" "${MIRROR}"
  cp /usr/bin/qemu-aarch64-static "${ROOTFS_DIR}/usr/bin/"
  chroot "${ROOTFS_DIR}" /debootstrap/debootstrap --second-stage
else
  warn "rootfs already exists, skipping debootstrap"
fi
ok "Base system bootstrapped."

# ── 2. IgnisOS 브랜딩 적용 ──────────────────────────
log "Step 2/7: Applying IgnisOS branding..."
cp rootfs/etc/os-release  "${ROOTFS_DIR}/etc/os-release"
cp rootfs/etc/motd        "${ROOTFS_DIR}/etc/motd"
echo "ignis" > "${ROOTFS_DIR}/etc/hostname"
cat > "${ROOTFS_DIR}/etc/hosts" <<EOF
127.0.0.1   localhost
127.0.1.1   ignis
::1         localhost ip6-localhost ip6-loopback
EOF
ok "Branding applied."

# ── 3. Uptime Kernel 빌드 & 설치 ───────────────────
log "Step 3/7: Building Uptime Kernel..."
# ARM64 크로스 컴파일
if command -v aarch64-linux-gnu-gcc &>/dev/null; then
  aarch64-linux-gnu-gcc -O2 -static -o "${ISO_DIR}/boot/uptime-kernel-init" \
    uptime-kernel/uptime_kernel.c -lm
  install -m 755 "${ISO_DIR}/boot/uptime-kernel-init" \
    "${ROOTFS_DIR}/usr/bin/uptime-kernel"
  ok "Uptime Kernel compiled (ARM64 static)."
else
  warn "aarch64-linux-gnu-gcc not found, skipping ARM64 compile"
  warn "Install: sudo apt install gcc-aarch64-linux-gnu"
fi

# ── 4. 패키지 설치 (chroot) ─────────────────────────
log "Step 4/7: Installing desktop packages (chroot)..."
cp /etc/resolv.conf "${ROOTFS_DIR}/etc/resolv.conf"

chroot "${ROOTFS_DIR}" /bin/bash <<'CHROOT_EOF'
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq

# 기본 시스템
apt-get install -y --no-install-recommends \
  ubuntu-minimal \
  linux-image-generic \
  linux-firmware \
  grub-efi-arm64 \
  network-manager \
  sudo \
  curl \
  wget \
  vim \
  nano \
  htop \
  git \
  ca-certificates \
  locales \
  tzdata

# 데스크톱 (GNOME minimal)
apt-get install -y --no-install-recommends \
  ubuntu-desktop-minimal \
  gnome-terminal \
  nautilus \
  gedit \
  eog \
  firefox

# 언어 설정
locale-gen ko_KR.UTF-8 en_US.UTF-8
update-locale LANG=en_US.UTF-8

# 기본 사용자 생성
useradd -m -s /bin/bash -G sudo ignis 2>/dev/null || true
echo "ignis:ignis" | chpasswd
echo "root:ignis" | chpasswd

# 자동 로그인 설정 (GDM)
mkdir -p /etc/gdm3
cat > /etc/gdm3/custom.conf <<GDM
[daemon]
AutomaticLoginEnable=true
AutomaticLogin=ignis
GDM

apt-get clean
CHROOT_EOF
ok "Packages installed."

# ── 5. 커스텀 init 스크립트 (Uptime Kernel 부팅) ────
log "Step 5/7: Setting up Uptime Kernel boot entry..."
cat > "${ROOTFS_DIR}/usr/bin/ignis-uptime-boot" <<'BOOT_EOF'
#!/bin/bash
# IgnisOS Uptime Kernel boot wrapper
/usr/bin/uptime-kernel
exec /sbin/init
BOOT_EOF
chmod +x "${ROOTFS_DIR}/usr/bin/ignis-uptime-boot"
ok "Boot wrapper created."

# ── 6. GRUB 설정 ────────────────────────────────────
log "Step 6/7: Configuring GRUB..."
cp config/grub/grub.cfg "${ISO_DIR}/boot/grub/grub.cfg"

# GRUB EFI 이미지 생성
grub-mkimage \
  -d /usr/lib/grub/arm64-efi \
  -o "${ISO_DIR}/EFI/BOOT/BOOTAA64.EFI" \
  -O arm64-efi \
  -p /boot/grub \
  fat part_gpt part_msdos normal boot linux \
  configfile loopback chain efifwsetup efi_gop \
  squash4 search search_label search_fs_uuid
ok "GRUB configured."

# ── 7. SquashFS + ISO 생성 ──────────────────────────
log "Step 7/7: Creating ISO image..."
mksquashfs "${ROOTFS_DIR}" "${ISO_DIR}/boot/filesystem.squashfs" \
  -comp xz -e boot 2>/dev/null

# 커널/initrd 복사
KERNEL=$(ls "${ROOTFS_DIR}/boot/vmlinuz-"* 2>/dev/null | tail -1)
INITRD=$(ls "${ROOTFS_DIR}/boot/initrd.img-"* 2>/dev/null | tail -1)
[[ -f "$KERNEL" ]] && cp "$KERNEL" "${ISO_DIR}/boot/vmlinuz"
[[ -f "$INITRD" ]] && cp "$INITRD" "${ISO_DIR}/boot/initrd.img"

xorriso -as mkisofs \
  -r \
  -V "IgnisOS_${IGNIS_VERSION}" \
  --efi-boot EFI/BOOT/BOOTAA64.EFI \
  -efi-boot-part --efi-boot-image \
  -o "${OUTPUT_ISO}" \
  "${ISO_DIR}"

ok "ISO created: ${OUTPUT_ISO}"
echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo -e "${GREEN}  IgnisOS ${IGNIS_VERSION} build complete!${RESET}"
echo -e "${GREEN}  ISO: ${OUTPUT_ISO}${RESET}"
echo -e "${GREEN}  Flash with: sudo dd if=${OUTPUT_ISO} of=/dev/sdX bs=4M status=progress${RESET}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
