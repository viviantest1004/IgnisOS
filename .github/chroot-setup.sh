#!/bin/bash
# IgnisOS chroot setup — runs inside the rootfs
set -e
export DEBIAN_FRONTEND=noninteractive

# apt sources
cat > /etc/apt/sources.list << 'EOF'
deb http://ports.ubuntu.com/ubuntu-ports noble main universe restricted multiverse
deb http://ports.ubuntu.com/ubuntu-ports noble-updates main universe restricted multiverse
deb http://ports.ubuntu.com/ubuntu-ports noble-security main universe restricted multiverse
EOF

apt-get update -qq

# Core packages
apt-get install -y --no-install-recommends \
    linux-image-generic \
    casper \
    xorg openbox \
    lightdm lightdm-gtk-greeter \
    python3 python3-gi python3-gi-cairo \
    gir1.2-gtk-4.0 gir1.2-adw-1 \
    network-manager \
    fonts-noto fonts-ubuntu \
    sudo ca-certificates locales tzdata \
    libnotify-bin build-essential

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
