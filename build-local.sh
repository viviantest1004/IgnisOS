#!/usr/bin/env bash
# IgnisOS 로컬 빌드 스크립트 (Apple Silicon Mac용)
# 사용법: ./build-local.sh [버전]
set -euo pipefail

VERSION="${1:-1.0.0}"
OUT="IgnisOS-${VERSION}-arm64.iso"
WORK="$(pwd)/_build_tmp"

echo "==> IgnisOS ${VERSION} 빌드 시작"
echo "    출력: ${OUT}"

# Docker 확인
if ! command -v docker &>/dev/null; then
    echo "ERROR: Docker가 필요합니다. https://www.docker.com/products/docker-desktop 설치"
    exit 1
fi

# 빌드 디렉토리
rm -rf "${WORK}"
mkdir -p "${WORK}"

# 인라인 Dockerfile 작성
cat > "${WORK}/Dockerfile" << 'DOCKERFILE'
FROM ubuntu:24.04
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update -qq && apt-get install -y --no-install-recommends \
    wget squashfs-tools xorriso \
    grub-efi-arm64-bin mtools \
    debootstrap \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /build
COPY chroot-setup.sh /build/
COPY ignis-shell      /build/ignis/ignis-shell/
COPY ignis-settings   /build/ignis/ignis-settings/
COPY ignis-files      /build/ignis/ignis-files/
COPY ignis-calc       /build/ignis/ignis-calc/
COPY ignis-terminal   /build/ignis/ignis-terminal/
COPY ignis-notepad    /build/ignis/ignis-notepad/
COPY ignis-clock      /build/ignis/ignis-clock/
COPY ignis-taskmanager /build/ignis/ignis-taskmanager/
COPY ignis-recovery   /build/ignis/ignis-recovery/
COPY ignis-oobe       /build/ignis/ignis-oobe/
COPY config/grub/grub.cfg /build/grub.cfg
COPY build-iso-inner.sh /build/

RUN chmod +x /build/build-iso-inner.sh /build/chroot-setup.sh
DOCKERFILE

# 내부 빌드 스크립트
cat > "${WORK}/build-iso-inner.sh" << 'INNERSCRIPT'
#!/bin/bash
set -e

VER="${VERSION:-1.0.0}"
ROOTFS=/build/rootfs
ISO_DIR=/build/iso

echo "[1/5] ubuntu-base 다운로드..."
mkdir -p "${ROOTFS}"
wget -q "https://cdimage.ubuntu.com/ubuntu-base/releases/24.04/release/ubuntu-base-24.04-base-arm64.tar.gz" \
    -O /tmp/ubuntu-base.tar.gz
tar -xzf /tmp/ubuntu-base.tar.gz -C "${ROOTFS}"
rm /tmp/ubuntu-base.tar.gz
echo "    기본 rootfs: $(du -sh ${ROOTFS} | cut -f1)"

echo "[2/5] IgnisOS 앱 복사..."
mkdir -p "${ROOTFS}/usr/share/ignis"
cp -r /build/ignis/ignis-* "${ROOTFS}/usr/share/ignis/"

echo "[3/5] 패키지 설치 (chroot)..."
cp /build/chroot-setup.sh "${ROOTFS}/tmp/setup.sh"
chmod +x "${ROOTFS}/tmp/setup.sh"
mount --bind /proc   "${ROOTFS}/proc"
mount --bind /sys    "${ROOTFS}/sys"
mount --bind /dev    "${ROOTFS}/dev"
mount --bind /dev/pts "${ROOTFS}/dev/pts"
chroot "${ROOTFS}" /tmp/setup.sh
umount "${ROOTFS}/dev/pts" "${ROOTFS}/dev" \
       "${ROOTFS}/sys"     "${ROOTFS}/proc" 2>/dev/null || true
echo "    최종 rootfs: $(du -sh ${ROOTFS} | cut -f1)"

echo "[4/5] squashfs + ISO 생성..."
mkdir -p "${ISO_DIR}/boot/grub" "${ISO_DIR}/EFI/BOOT" "${ISO_DIR}/casper"

# 커널 + initrd
VMLINUZ=$(ls "${ROOTFS}/boot/" | grep '^vmlinuz-' | tail -1)
INITRD=$(ls  "${ROOTFS}/boot/" | grep '^initrd.img-' | tail -1)
cp "${ROOTFS}/boot/${VMLINUZ}" "${ISO_DIR}/casper/vmlinuz"
cp "${ROOTFS}/boot/${INITRD}"  "${ISO_DIR}/casper/initrd"

# squashfs
mksquashfs "${ROOTFS}" "${ISO_DIR}/casper/filesystem.squashfs" \
    -comp gzip -e boot -e proc -e sys -noappend
echo "    squashfs: $(du -sh ${ISO_DIR}/casper/filesystem.squashfs | cut -f1)"

# rootfs 삭제 (디스크 확보)
rm -rf "${ROOTFS}"

# GRUB 설정
sed 's|/boot/vmlinuz|/casper/vmlinuz|g; s|/boot/initrd.img|/casper/initrd|g' \
    /build/grub.cfg > "${ISO_DIR}/boot/grub/grub.cfg"

# UEFI EFI 바이너리
grub-mkstandalone \
    --format=arm64-efi \
    --output="${ISO_DIR}/EFI/BOOT/BOOTAA64.EFI" \
    --modules="part_gpt fat iso9660 linux normal boot configfile \
      loopback chain efifwsetup efi_gop ls search search_label \
      search_fs_uuid search_fs_file gfxterm all_video loadenv ext2" \
    "boot/grub/grub.cfg=${ISO_DIR}/boot/grub/grub.cfg"

# EFI 파티션 이미지
EFI_IMG="${ISO_DIR}/boot/grub/efi.img"
dd if=/dev/zero of="${EFI_IMG}" bs=1M count=4 2>/dev/null
mkfs.vfat "${EFI_IMG}"
mmd  -i "${EFI_IMG}" ::/EFI ::/EFI/BOOT
mcopy -i "${EFI_IMG}" "${ISO_DIR}/EFI/BOOT/BOOTAA64.EFI" ::/EFI/BOOT/BOOTAA64.EFI

# ISO 빌드
xorriso -as mkisofs \
    -r -V "IgnisOS_${VER}" \
    -J -joliet-long \
    -no-emul-boot \
    -e boot/grub/efi.img \
    -isohybrid-gpt-basdat \
    -o "/output/IgnisOS-${VER}-arm64.iso" "${ISO_DIR}"
echo "    ISO: $(du -sh /output/IgnisOS-${VER}-arm64.iso | cut -f1)"
echo "[5/5] 완료!"
INNERSCRIPT
chmod +x "${WORK}/build-iso-inner.sh"

# 소스 파일 복사
echo "==> 소스 파일 준비 중..."
for d in ignis-shell ignis-settings ignis-files ignis-calc ignis-terminal \
          ignis-notepad ignis-clock ignis-taskmanager ignis-recovery ignis-oobe; do
    [ -d "$d" ] && cp -r "$d" "${WORK}/"
done
cp -r config "${WORK}/"
cp .github/chroot-setup.sh "${WORK}/"

# Docker 이미지 빌드 및 실행
echo "==> Docker 이미지 빌드 중..."
docker build --platform linux/arm64 -t ignisOS-builder "${WORK}" -q

echo "==> ISO 빌드 중 (20~30분 소요)..."
mkdir -p "$(pwd)/dist"
docker run --rm --privileged \
    --platform linux/arm64 \
    -e VERSION="${VERSION}" \
    -v "$(pwd)/dist:/output" \
    ignisOS-builder \
    bash /build/build-iso-inner.sh

docker rmi ignisOS-builder 2>/dev/null || true
rm -rf "${WORK}"

echo ""
echo "완료! → dist/IgnisOS-${VERSION}-arm64.iso"
echo "UTM에서 열기: open dist/"
