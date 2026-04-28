# 🔥 IgnisOS — ARM64 Linux OS

> **A fully AI-built, open-source ARM64 Linux operating system**
> 100% designed and written by AI · Ubuntu 24.04 base · MIT License

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Architecture](https://img.shields.io/badge/arch-ARM64%20%2F%20aarch64-blue.svg)]()
[![Base](https://img.shields.io/badge/base-Ubuntu%2024.04%20LTS-orange.svg)]()
[![Uptime Kernel](https://img.shields.io/badge/Uptime%20Kernel-v1.0.0-red.svg)]()
[![Status](https://img.shields.io/badge/status-active-brightgreen.svg)]()

---

## 📥 Download ISO (ARM64)

> **[🌐 ISO Download Website](https://viviantest1004.github.io/IgnisOS/)** ← direct download page

| Edition | Size | Download |
|---------|------|----------|
| **IgnisOS 1.0.0 Live ARM64** *(boot without install)* | ~2.1 GB | [🔗 Download Page](https://viviantest1004.github.io/IgnisOS/) · [GitHub Releases](https://github.com/viviantest1004/IgnisOS/releases/tag/v1.0.0) |
| **IgnisOS 1.0.0 Install ARM64** *(full installer)* | ~2.8 GB | [🔗 Download Page](https://viviantest1004.github.io/IgnisOS/) · [GitHub Releases](https://github.com/viviantest1004/IgnisOS/releases/tag/v1.0.0) |

> ⚠️ **ARM64 only.** These ISOs run on ARM64 (aarch64) hardware such as Raspberry Pi 4/5, Apple M1/M2/M3/M4 (via UTM), QEMU ARM64, AWS Graviton, etc.

### Flash to USB
```bash
# Linux / macOS
sudo dd if=IgnisOS-1.0.0-live-arm64.iso of=/dev/sdX bs=4M status=progress

# Or use Balena Etcher (Windows/macOS/Linux)
```

---

## ✨ What is IgnisOS?

IgnisOS is a **custom ARM64 Linux distribution** built on Ubuntu 24.04 LTS with a fully custom desktop environment and a unique boot-time shell called the **Uptime Kernel**.

- 🔥 **Custom Desktop** — GNOME-based with Ignis Shell (top bar + right dock)
- ⚡ **Uptime Kernel** — Custom C-written boot shell (file management, calculator, uptime)
- 🌐 **Multilingual** — English (default), 한국어, 日本語
- 🏗️ **ARM64 Native** — aarch64 architecture
- 🤖 **100% AI-Made** — Entirely built by Claude Sonnet 4.6

---

## 🖥️ Desktop Features

### Ignis Shell
| Component | Description |
|-----------|-------------|
| **Top Bar (left)** | App name, Terminal shortcut, Window tiling controls |
| **Top Bar (right)** | Clock, Language switcher (EN/KO/JA), Volume, Brightness, WiFi, Battery |
| **Right Dock** | Pinned apps (Terminal, Calculator, Browser, Settings, Files) + App Launcher button |
| **App Launcher** | Searchable grid of all apps + Power menu (Shutdown/Restart/Sleep/Lock) |

### Built-in Apps
| App | Description |
|-----|-------------|
| **ignis-terminal** | VTE-based terminal with tabs + fallback shell |
| **ignis-calc** | Calculator with standard + scientific modes |
| **ignis-files** | File manager with copy/paste/rename/move/delete + sidebar |
| **ignis-settings** | Full system settings (see below) |
| Firefox | Web browser |

### Settings Panels
- 📶 **Wi-Fi** — Network list, connect/disconnect
- 📡 **Bluetooth** — Device pairing
- 🖥️ **Display** — Resolution, refresh rate, HiDPI scale, orientation, night mode
- 🔊 **Sound** — Output/input volume, device selection
- 🌐 **Language & Region** — System language (EN/KO/JA/etc.), timezone, date format
- 🕐 **Date & Time** — NTP auto-sync, manual time set
- ☀️ **Brightness & Power** — Brightness slider, sleep timer, lid close action
- 👤 **Users** — Add/delete user accounts
- 🔒 **Security** — Firewall (UFW), SSH, screen lock
- ℹ️ **System Info** — OS version, kernel, architecture, memory, disk

---

## ⚡ Uptime Kernel

The **Uptime Kernel** is IgnisOS's signature boot-time environment — a custom interactive shell written in C from scratch.

```
  ██╗ ██████╗ ███╗   ██╗██╗███████╗ ██████╗ ███████╗
  ██║██╔════╝ ████╗  ██║██║██╔════╝██╔═══██╗██╔════╝
  ...
  Uptime Kernel v1.0.0  ·  ARM64  ·  MIT License

root@ignis:~❯ uptime
  System Time : 18:42:05
  Uptime      : 03:14:22
  Memory      : 1240 MB used / 4096 MB total

root@ignis:~❯ calc (100+50)/3
  (100+50)/3 = 50

root@ignis:~❯ ls
Documents  Downloads  Music  Pictures  Videos

root@ignis:~❯ exit
  IgnisOS Desktop booting...
```

### Uptime Kernel Commands
| Category | Commands |
|----------|----------|
| **File Management** | `ls`, `cd`, `pwd`, `mkdir`, `rmdir`, `rm`, `touch`, `cat`, `cp`, `mv` |
| **Calculator** | `calc <expr>` — supports `+ - * / %` and parentheses `()` |
| **System** | `uptime`, `uname`, `clear`, `help` |
| **Exit** | `exit` — returns to IgnisOS desktop boot |

---

## 🛠️ Recovery Mode

Access from GRUB boot menu → **Recovery & Tools**:

| Option | Description |
|--------|-------------|
| 🛠️ Recovery Mode | Interactive recovery menu |
| ⚡ Uptime Kernel (Recovery) | Boot into Uptime Kernel from recovery |
| 🔍 Filesystem Check | Run `fsck` on root partition |
| 🖥️ Recovery Shell | Root bash shell |
| 🔄 Factory Reset | Reset all user data to defaults |
| 🌐 Network Recovery | Fix network (DHCP, DNS, NetworkManager) |
| 🔑 Password Reset | Reset user account password |
| 💾 Memory Test | Run `memtest86+` |

---

## 🚀 How to Build from Source

### Requirements

**Host system**: Ubuntu 22.04+ or Debian 12+ (x86_64 or ARM64)

```bash
# Install build dependencies
sudo apt update
sudo apt install -y \
  debootstrap qemu-user-static binfmt-support \
  grub-efi-arm64 grub-efi-arm64-bin \
  dosfstools mtools \
  squashfs-tools xorriso \
  gcc-aarch64-linux-gnu \
  gcc make
```

### Clone & Build

```bash
# 1. Clone repository
git clone https://github.com/viviantest1004/IgnisOS.git
cd IgnisOS

# 2. Build complete ARM64 ISO (requires root)
sudo ./build.sh

# Output: build/IgnisOS-1.0.0-arm64.iso
```

### Build Uptime Kernel Only

```bash
cd uptime-kernel

# Build for your current machine (for testing)
make
./uptime-kernel        # Run and test

# Cross-compile for ARM64
make arm
# Output: uptime-kernel-arm64 (static binary, runs on any ARM64 Linux)
```

### Install on Existing Ubuntu ARM64

```bash
git clone https://github.com/viviantest1004/IgnisOS.git
cd IgnisOS
sudo ./scripts/setup.sh
```

---

## 🍎 Run on Apple M1/M2/M3/M4 (via UTM)

> **UTM** is a free VM app for macOS. Download from [mac.getutm.app](https://mac.getutm.app/)

### Step-by-step (UTM)

1. **Download** UTM from [mac.getutm.app](https://mac.getutm.app/) and open it.
2. Click **"+"** → **"Virtualize"** (NOT emulate — M-series Macs run ARM64 natively at full speed).
3. Select **"Linux"** as the operating system.
4. Click **"Browse"** and select the `IgnisOS-1.0.0-live-arm64.iso` file.
5. Set RAM to **at least 2048 MB** (4096 MB recommended).
6. Set disk size to **20 GB** or more.
7. Leave CPU cores at default (or set to 4+).
8. Click **"Save"** then **"Play"** to boot IgnisOS.

> **Note:** If you see a blank screen, wait 10–15 seconds — the Uptime Kernel loads first, then the desktop appears.

### UTM Settings (recommended)
| Setting | Value |
|---------|-------|
| Virtualization | Enabled (ARM64 native) |
| RAM | 4096 MB |
| CPU Cores | 4 |
| Storage | 20 GB |
| Display | VirtIO GPU |
| Network | Shared Network (NAT) |

---

## 💻 Run in QEMU (ARM64 VM)

```bash
# Install QEMU
sudo apt install qemu-system-aarch64

# Download EFI firmware
sudo apt install qemu-efi-aarch64

# Run IgnisOS Live ISO
qemu-system-aarch64 \
  -M virt \
  -cpu cortex-a72 \
  -m 2048 \
  -bios /usr/share/qemu-efi-aarch64/QEMU_EFI.fd \
  -drive if=virtio,format=raw,file=IgnisOS-1.0.0-live-arm64.iso \
  -device virtio-gpu-pci \
  -display sdl \
  -device usb-kbd -device usb-mouse \
  -usb
```

---

## 📋 System Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| **Architecture** | ARM64 (aarch64) | ARM64 |
| **RAM** | 2 GB | 4 GB+ |
| **Storage** | 16 GB | 32 GB+ |
| **Display** | 1280×720 | 1920×1080 |
| **Boot** | UEFI | UEFI |

### Compatible Hardware
- Raspberry Pi 4 / 5
- Apple M1/M2/M3/M4 (via [UTM](https://mac.getutm.app/))
- AWS Graviton instances
- Any QEMU ARM64 VM
- Ampere Altra, Neoverse N1/N2

---

## 📁 Project Structure

```
IgnisOS/
├── uptime-kernel/
│   ├── uptime_kernel.c     # Uptime Kernel — written in C
│   └── Makefile
├── ignis-shell/
│   └── shell.py            # Desktop shell (top bar + dock + launcher)
├── ignis-settings/
│   └── settings.py         # Full system settings app
├── ignis-files/
│   └── files.py            # File manager (copy/paste/rename/move)
├── ignis-calc/
│   └── calc.py             # Calculator (standard + scientific)
├── ignis-terminal/
│   └── terminal.py         # Terminal emulator (VTE + fallback)
├── ignis-recovery/
│   └── recovery.sh         # Recovery mode menu
├── config/
│   └── grub/grub.cfg       # GRUB boot configuration
├── rootfs/
│   └── etc/                # OS branding files
├── scripts/
│   └── setup.sh            # Install on existing Ubuntu ARM64
├── build.sh                # Full ISO build script
├── LICENSE                 # MIT License
└── README.md
```

---

## 🌐 Internationalization

IgnisOS supports **3 languages** out of the box:

| Language | Code | Status |
|----------|------|--------|
| English | `en_US` | ✅ Default |
| 한국어 | `ko_KR` | ✅ Supported |
| 日本語 | `ja_JP` | ✅ Supported |

Switch language: **Settings → Language & Region → System Language**

Or click the language indicator in the top-right corner of the screen (EN / KO / JA).

---

## 🤖 About IgnisOS

IgnisOS was **entirely designed and built by AI** (Claude Sonnet 4.6 by Anthropic).

- **Name**: *Ignis* = Latin for *Fire* 🔥
- **Base**: Ubuntu 24.04 LTS Noble
- **Architecture**: ARM64 (aarch64) — **not x86, not x86_64**
- **License**: MIT — free to use, modify, distribute

### What was AI-built
- ✅ Uptime Kernel (C language, ~400 lines)
- ✅ Ignis Shell (Python/GTK4 desktop)
- ✅ Settings app (12 panels)
- ✅ File manager (full featured)
- ✅ Calculator (standard + scientific)
- ✅ Terminal emulator (VTE + fallback)
- ✅ Recovery system (9 recovery options)
- ✅ GRUB boot configuration
- ✅ Build system (debootstrap-based)
- ✅ All documentation

---

## 📄 License

MIT License — see [LICENSE](LICENSE)

Free to use, modify, and distribute. Attribution appreciated.

---

## 🐛 Issues & Contributing

- **Bug reports**: [GitHub Issues](https://github.com/viviantest1004/IgnisOS/issues)
- **Feature requests**: [GitHub Discussions](https://github.com/viviantest1004/IgnisOS/discussions)
- **Source code**: [github.com/viviantest1004/IgnisOS](https://github.com/viviantest1004/IgnisOS)

---

*🔥 IgnisOS — ARM64 · Open Source · AI-Built*
