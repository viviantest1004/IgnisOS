#!/usr/bin/env python3
"""IgnisOS 시스템 정보"""
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GLib, Gdk, Gio
import subprocess, os, platform

CSS = b"""
.si-win { background: #0d0d1f; }
.si-section-title {
    font-size: 12px; font-weight: 700; color: #64748b;
    text-transform: uppercase; letter-spacing: 1px;
    padding: 12px 16px 4px;
}
.si-row {
    background: rgba(255,255,255,0.03);
    border-bottom: 1px solid rgba(255,255,255,0.05);
    padding: 10px 16px;
}
.si-key { font-size: 13px; color: #64748b; }
.si-val { font-size: 13px; color: #f1f5f9; font-weight: 500; }
.si-logo { font-size: 72px; }
.si-os-name { font-size: 24px; font-weight: 800; color: #f1f5f9; }
.si-os-ver { font-size: 14px; color: #94a3b8; }
"""

def _read(path, default="알 수 없음"):
    try:
        with open(path) as f: return f.read().strip()
    except Exception: return default

def _cmd(args, default="알 수 없음"):
    try:
        return subprocess.check_output(args, stderr=subprocess.DEVNULL).decode().strip()
    except Exception: return default

class SysInfo(Adw.Application):
    def __init__(self):
        super().__init__(application_id="org.ignis.SysInfo",
                         flags=Gio.ApplicationFlags.FLAGS_NONE)
        self.connect("activate", self._activate)

    def _activate(self, app):
        css = Gtk.CssProvider()
        css.load_from_data(CSS)
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        self.win = Adw.ApplicationWindow(application=app)
        self.win.set_title("시스템 정보")
        self.win.set_default_size(560, 640)
        self.win.add_css_class("si-win")

        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.win.set_content(scroll)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        scroll.set_child(vbox)

        # 로고
        hero = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6,
                       halign=Gtk.Align.CENTER, margin_top=32, margin_bottom=20)
        logo = Gtk.Label()
        logo.set_markup('<span font="64">🔥</span>')
        hero.append(logo)
        name_lbl = Gtk.Label(label="IgnisOS")
        name_lbl.add_css_class("si-os-name")
        hero.append(name_lbl)

        # OS 버전
        os_release = {}
        try:
            for line in _read("/etc/os-release", "").splitlines():
                if "=" in line:
                    k, v = line.split("=", 1)
                    os_release[k] = v.strip('"')
        except Exception: pass
        ver_lbl = Gtk.Label(label=os_release.get("VERSION", platform.version()[:40]))
        ver_lbl.add_css_class("si-os-ver")
        hero.append(ver_lbl)
        vbox.append(hero)

        # Copy 버튼
        copy_btn = Gtk.Button(label="📋 정보 복사")
        copy_btn.set_halign(Gtk.Align.CENTER)
        copy_btn.set_margin_bottom(16)
        copy_btn.connect("clicked", self._copy_info)
        vbox.append(copy_btn)

        info = self._collect_info()
        for section, rows in info.items():
            sec_lbl = Gtk.Label(label=section, xalign=0)
            sec_lbl.add_css_class("si-section-title")
            vbox.append(sec_lbl)
            for key, val in rows:
                row = Gtk.Box(spacing=0)
                row.add_css_class("si-row")
                k = Gtk.Label(label=key, xalign=0, width_chars=20, hexpand=False)
                k.add_css_class("si-key")
                v = Gtk.Label(label=val, xalign=0, hexpand=True, wrap=True)
                v.add_css_class("si-val")
                row.append(k)
                row.append(v)
                vbox.append(row)

        self._info = info
        self.win.present()

    def _collect_info(self):
        # OS
        uname = platform.uname()
        hostname = _cmd(["hostname"])
        uptime_raw = _read("/proc/uptime", "0").split()[0]
        try:
            secs = float(uptime_raw)
            uptime = f"{int(secs//3600)}시간 {int((secs%3600)//60)}분"
        except Exception:
            uptime = uptime_raw

        # CPU
        cpu_name = "알 수 없음"
        try:
            for line in _read("/proc/cpuinfo","").splitlines():
                if "model name" in line or "Hardware" in line:
                    cpu_name = line.split(":", 1)[1].strip()
                    break
        except Exception: pass
        cpu_cores = _cmd(["nproc"])
        cpu_arch = uname.machine

        # 메모리
        mem_info = {}
        try:
            for line in _read("/proc/meminfo","").splitlines():
                k, v = line.split(":", 1)
                mem_info[k.strip()] = int(v.split()[0])
        except Exception: pass
        total_mb = mem_info.get("MemTotal", 0) // 1024
        avail_mb = mem_info.get("MemAvailable", 0) // 1024
        used_mb = total_mb - avail_mb

        # 디스크
        disk = _cmd(["df", "-h", "/"]).splitlines()
        disk_info = disk[1].split() if len(disk) > 1 else ["?","?","?","?","?"]

        # GPU
        gpu = _cmd(["lspci"], "").split("\n")
        gpu_name = next((l.split(":", 2)[-1].strip() for l in gpu
                        if "VGA" in l or "3D" in l or "Display" in l), "알 수 없음")

        # 네트워크
        ip = _cmd(["hostname", "-I"]).split()[0] if _cmd(["hostname","-I"]) else "알 수 없음"

        return {
            "운영체제": [
                ("이름", "IgnisOS"),
                ("커널", f"{uname.system} {uname.release}"),
                ("아키텍처", cpu_arch),
                ("호스트명", hostname),
                ("업타임", uptime),
            ],
            "하드웨어": [
                ("CPU", cpu_name),
                ("코어 수", f"{cpu_cores} 코어"),
                ("GPU", gpu_name[:60] if gpu_name else "알 수 없음"),
            ],
            "메모리": [
                ("전체", f"{total_mb:,} MB"),
                ("사용 중", f"{used_mb:,} MB"),
                ("사용 가능", f"{avail_mb:,} MB"),
            ],
            "저장소": [
                ("디바이스", disk_info[0] if len(disk_info) > 0 else "?"),
                ("전체 용량", disk_info[1] if len(disk_info) > 1 else "?"),
                ("사용 중", disk_info[2] if len(disk_info) > 2 else "?"),
                ("사용 가능", disk_info[3] if len(disk_info) > 3 else "?"),
                ("사용률", disk_info[4] if len(disk_info) > 4 else "?"),
            ],
            "네트워크": [
                ("IP 주소", ip),
            ],
        }

    def _copy_info(self, *_):
        lines = []
        for section, rows in self._info.items():
            lines.append(f"[{section}]")
            for k, v in rows:
                lines.append(f"  {k}: {v}")
            lines.append("")
        text = "\n".join(lines)
        clipboard = Gdk.Display.get_default().get_clipboard()
        clipboard.set(text)


def main():
    SysInfo().run([])

if __name__ == "__main__":
    main()
