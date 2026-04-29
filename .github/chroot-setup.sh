#!/bin/bash
# IgnisOS chroot setup — runs inside the rootfs
set -e
export DEBIAN_FRONTEND=noninteractive

# apt sources (Ubuntu 24.04 uses deb822 format in sources.list.d)
rm -f /etc/apt/sources.list.d/*.sources /etc/apt/sources.list.d/*.list 2>/dev/null || true
cat > /etc/apt/sources.list << 'EOF'
deb http://ports.ubuntu.com/ubuntu-ports noble main universe restricted multiverse
deb http://ports.ubuntu.com/ubuntu-ports noble-updates main universe restricted multiverse
deb http://ports.ubuntu.com/ubuntu-ports noble-security main universe restricted multiverse
EOF

apt-get update -qq 2>&1 | tail -5

# chroot 내에서 서비스 시작 방지
cat > /usr/sbin/policy-rc.d << 'POLICY'
#!/bin/sh
exit 101
POLICY
chmod +x /usr/sbin/policy-rc.d

# Core packages (최소 구성)
apt-get install -y --no-install-recommends \
    linux-image-generic \
    casper \
    xorg \
    openbox \
    lightdm \
    python3 python3-gi python3-gi-cairo \
    gir1.2-gtk-4.0 gir1.2-adw-1 \
    fonts-noto \
    sudo ca-certificates locales tzdata \
    libnotify-bin build-essential

# policy-rc.d 제거 (정상 부팅 허용)
rm -f /usr/sbin/policy-rc.d

# Locale
locale-gen en_US.UTF-8 ko_KR.UTF-8
update-locale LANG=en_US.UTF-8

# User
useradd -m -s /bin/bash -G sudo ignis 2>/dev/null || true
echo "ignis:ignis" | chpasswd
echo "root:ignis"   | chpasswd
echo "ignis ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

# Launcher scripts
for app in shell settings files calc terminal notepad clock taskmanager oobe; do
    cat > /usr/local/bin/ignis-${app} << LAUNCHER
#!/bin/bash
exec python3 /usr/share/ignis/ignis-${app}/${app}.py "\$@"
LAUNCHER
    chmod +x /usr/local/bin/ignis-${app}
done

# Recovery
if [ -f /usr/share/ignis/ignis-recovery/recovery.sh ]; then
    install -m755 /usr/share/ignis/ignis-recovery/recovery.sh \
        /usr/local/bin/ignis-recovery
fi

# Build uptime-kernel
if [ -f /usr/share/ignis/uptime-kernel/uptime_kernel.c ]; then
    gcc -O2 -o /usr/local/bin/uptime-kernel \
        /usr/share/ignis/uptime-kernel/uptime_kernel.c -lm || true
fi

# Autostart
mkdir -p /etc/xdg/autostart
cat > /etc/xdg/autostart/ignis-shell.desktop << 'EOF'
[Desktop Entry]
Type=Application
Name=Ignis Shell
Exec=/usr/local/bin/ignis-shell
X-GNOME-Autostart-enabled=true
EOF

# LightDM autologin
mkdir -p /etc/lightdm
cat > /etc/lightdm/lightdm.conf << 'EOF'
[Seat:*]
autologin-user=ignis
autologin-user-timeout=0
user-session=openbox
EOF

# OS branding
cat > /etc/os-release << 'EOF'
NAME="IgnisOS"
VERSION="1.0"
ID=ignisOS
ID_LIKE=ubuntu
PRETTY_NAME="IgnisOS"
HOME_URL="https://viviantest1004.github.io/IgnisOS"
EOF

# Cleanup
apt-get clean
rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*
