# 🔥 IgnisOS

> **An AI-built, open-source ARM64 Linux operating system**
> Built entirely by AI · Based on Ubuntu 24.04 · MIT License

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Architecture](https://img.shields.io/badge/arch-ARM64-blue.svg)]()
[![Base](https://img.shields.io/badge/base-Ubuntu%2024.04%20LTS-orange.svg)]()
[![Kernel](https://img.shields.io/badge/Uptime%20Kernel-v1.0.0-red.svg)]()

---

## ✨ Features

- 🔥 **IgnisOS Desktop** — Full GNOME desktop based on Ubuntu 24.04 LTS
- ⚡ **Uptime Kernel** — Custom boot-time shell environment (written in C)
- 🏗️ **ARM64 Native** — Built for ARM64 (aarch64) architecture
- 🤖 **100% AI-Made** — Entirely designed and built by AI

## 🚀 Boot Menu

On startup, GRUB presents two options:

```
┌─────────────────────────────────────────┐
│  🔥 IgnisOS — Uptime Kernel             │  ← Custom shell
│  🖥️  IgnisOS — Desktop (GNOME)          │  ← Full desktop
│  🛠️  IgnisOS — Recovery Mode            │
└─────────────────────────────────────────┘
```

## ⚡ Uptime Kernel

The **Uptime Kernel** is a custom interactive shell that runs at boot time.

```
  ██╗ ██████╗ ███╗   ██╗██╗███████╗ ██████╗ ███████╗
  ██║██╔════╝ ████╗  ██║██║██╔════╝██╔═══██╗██╔════╝
  ██║██║  ███╗██╔██╗ ██║██║███████╗██║   ██║███████╗
  ██║██║   ██║██║╚██╗██║██║╚════██║██║   ██║╚════██║
  ██║╚██████╔╝██║ ╚████║██║███████║╚██████╔╝███████║
  ╚═╝ ╚═════╝ ╚═╝  ╚═══╝╚═╝╚══════╝ ╚═════╝ ╚══════╝

  Uptime Kernel v1.0.0  ·  ARM64  ·  MIT License
```

### Commands

| Category | Command | Description |
|----------|---------|-------------|
| **Files** | `ls [path]` | List files/directories |
| | `cd <path>` | Change directory |
| | `pwd` | Print working directory |
| | `mkdir <dir>` | Create directory |
| | `rmdir <dir>` | Remove empty directory |
| | `rm <file>` | Remove file |
| | `touch <file>` | Create empty file |
| | `cat <file>` | Print file contents |
| | `cp <src> <dst>` | Copy file |
| | `mv <src> <dst>` | Move/rename file |
| **System** | `uptime` | System uptime, memory, load |
| | `uname` | System info |
| | `clear` | Clear screen |
| **Calculator** | `calc <expr>` | Arithmetic calculator |
| | | Supports `+ - * / %` and `()` |
| **Exit** | `exit` | Leave Uptime Kernel → boot desktop |

### Calculator Examples

```
root@ignis:~❯ calc 2+3
  2+3 = 5

root@ignis:~❯ calc (10+5)*2
  (10+5)*2 = 30

root@ignis:~❯ calc 100/7
  100/7 = 14.28571429
```

## 🛠️ Build from Source

### Requirements

- Ubuntu/Debian host (x86_64 or ARM64)
- `debootstrap`, `qemu-user-static` (for cross-build)
- `grub-efi-arm64`, `xorriso`, `squashfs-tools`
- `gcc-aarch64-linux-gnu` (for Uptime Kernel cross-compile)

```bash
# Install dependencies
sudo apt install debootstrap qemu-user-static binfmt-support \
  grub-efi-arm64 grub-efi-arm64-bin dosfstools mtools \
  squashfs-tools xorriso gcc-aarch64-linux-gnu

# Build IgnisOS ISO
git clone https://github.com/viviantest1004/IgnisOS
cd IgnisOS
sudo ./build.sh

# Flash to USB (replace /dev/sdX with your USB drive)
sudo dd if=build/IgnisOS-1.0.0-arm64.iso of=/dev/sdX bs=4M status=progress
```

### Build Uptime Kernel only

```bash
cd uptime-kernel

# Native (for testing)
make

# ARM64 cross-compile
make arm
```

## 📋 System Requirements

| Component | Minimum |
|-----------|---------|
| Architecture | ARM64 (aarch64) |
| RAM | 2 GB |
| Storage | 16 GB |
| Display | 1280×720 |
| Boot | UEFI |

## 📁 Project Structure

```
IgnisOS/
├── uptime-kernel/
│   ├── uptime_kernel.c   # Uptime Kernel source (C)
│   └── Makefile
├── config/
│   └── grub/
│       └── grub.cfg      # GRUB boot configuration
├── rootfs/
│   └── etc/
│       ├── os-release    # IgnisOS branding
│       └── motd          # Login message
├── build.sh              # Full ISO build script
├── LICENSE               # MIT License
└── README.md
```

## 🤖 About

IgnisOS was **entirely designed and built by AI** (Claude Sonnet 4.6).

- OS name: **IgnisOS** (*Ignis* = Latin for *Fire* 🔥)
- Custom shell: **Uptime Kernel** — written in C from scratch
- Base: Ubuntu 24.04 LTS (noble)
- Architecture: ARM64

## 📄 License

MIT License — see [LICENSE](LICENSE)

---

*IgnisOS — 🔥 Open source. ARM64. AI-built.*
