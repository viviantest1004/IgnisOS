#!/usr/bin/env python3
"""
IgnisOS Shell — Desktop environment
Top bar + Right dock + App launcher + App switcher + Dark/Light mode
"""
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GLib, Gdk, Gio
import subprocess, os, threading, datetime, json, signal

CONFIG_FILE = os.path.expanduser("~/.config/ignis/shell.json")

def load_config():
    try:
        with open(CONFIG_FILE) as f:
            return json.load(f)
    except Exception:
        return {"dark_mode": True}

def save_config(cfg):
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f)

CONFIG = load_config()

# ── CSS ─────────────────────────────────────────────
CSS_DARK = b"""
* { font-family: 'Ubuntu', 'Segoe UI', sans-serif; }
window, .ignis-topbar, .ignis-dock, .ignis-launcher, .switcher-win {
    transition: background 0.25s ease, border-color 0.25s ease;
}
button {
    transition: background 0.15s ease, border-color 0.15s ease,
                transform 0.1s ease, box-shadow 0.15s ease;
}
button:active { transform: scale(0.95); }
.ignis-topbar {
    background: rgba(10,10,20,0.93);
    border-bottom: 1px solid rgba(232,93,4,0.3);
}
.ignis-topbar label { color: #f1f5f9; font-size: 13px; }
.ignis-topbar button {
    background: transparent; border: none;
    color: #f1f5f9; padding: 2px 8px; border-radius: 6px; font-size: 13px;
}
.ignis-topbar button:hover {
    background: rgba(255,255,255,0.12);
    box-shadow: 0 2px 8px rgba(0,0,0,0.3);
}
.ignis-dock {
    background: rgba(10,10,20,0.93);
    border-left: 1px solid rgba(232,93,4,0.3);
    padding: 8px 4px;
}
.dock-btn {
    background: transparent; border: 1px solid transparent; border-radius: 14px;
    padding: 8px; margin: 3px; color: #f1f5f9; font-size: 10px;
    transition: background 0.18s ease, border-color 0.18s ease,
                transform 0.12s cubic-bezier(0.34,1.56,0.64,1), box-shadow 0.18s ease;
}
.dock-btn:hover {
    background: rgba(232,93,4,0.22); border-color: rgba(232,93,4,0.55);
    transform: scale(1.1);
    box-shadow: 0 4px 16px rgba(232,93,4,0.25);
}
.dock-btn:active { transform: scale(0.96); }
.dock-btn.running { background: rgba(232,93,4,0.12); }
.dock-running-dot { color: #e85d04; font-size: 9px; }
.dock-launcher {
    background: rgba(232,93,4,0.15); border: 1px solid rgba(232,93,4,0.4);
    border-radius: 12px; padding: 10px; margin: 4px; color: #e85d04; font-size: 18px;
    transition: background 0.18s ease, transform 0.12s cubic-bezier(0.34,1.56,0.64,1);
}
.dock-launcher:hover { background: rgba(232,93,4,0.32); transform: scale(1.08); }
.ignis-launcher { background: rgba(5,5,15,0.97); }
.launcher-search {
    background: rgba(255,255,255,0.08); border: 1px solid rgba(232,93,4,0.4);
    border-radius: 12px; color: #f1f5f9; font-size: 16px; padding: 10px 16px;
    transition: border-color 0.2s ease, background 0.2s ease, box-shadow 0.2s ease;
}
.launcher-search:focus {
    border-color: #e85d04;
    background: rgba(255,255,255,0.11);
    box-shadow: 0 0 0 3px rgba(232,93,4,0.18);
}
.app-grid-btn {
    background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.08);
    border-radius: 16px; padding: 14px; color: #f1f5f9; font-size: 11px;
    transition: background 0.18s ease, border-color 0.18s ease,
                transform 0.12s cubic-bezier(0.34,1.56,0.64,1), box-shadow 0.18s ease;
}
.app-grid-btn:hover {
    background: rgba(232,93,4,0.16); border-color: rgba(232,93,4,0.45);
    transform: translateY(-2px) scale(1.03);
    box-shadow: 0 6px 20px rgba(232,93,4,0.2);
}
.app-grid-btn:active { transform: scale(0.97); }
.power-btn {
    background: rgba(255,60,60,0.1); border: 1px solid rgba(255,60,60,0.3);
    border-radius: 10px; color: #f87171; padding: 8px 14px; font-size: 13px;
    transition: background 0.15s ease, transform 0.1s ease;
}
.power-btn:hover { background: rgba(255,60,60,0.25); transform: scale(1.04); }
.ignis-clock { font-size: 13px; font-weight: 600; color: #f1f5f9; }
.ignis-indicator { font-size: 13px; color: #e2e8f0; padding: 2px 6px; }
.topbar-left button { color: #f1f5f9; font-size: 13px; font-weight: 600; }
.switcher-win { background: rgba(5,5,15,0.97); }
.switcher-card {
    background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.1);
    border-radius: 16px; padding: 14px;
    transition: background 0.18s ease, border-color 0.18s ease,
                transform 0.12s ease, box-shadow 0.18s ease;
}
.switcher-card:hover {
    background: rgba(232,93,4,0.13); border-color: rgba(232,93,4,0.35);
    transform: translateY(-2px);
    box-shadow: 0 6px 20px rgba(232,93,4,0.15);
}
.switcher-name { color: #f1f5f9; font-size: 13px; font-weight: 600; }
.switcher-pid  { color: #64748b; font-size: 11px; }
.switcher-close { background: rgba(239,68,68,0.15); border: 1px solid rgba(239,68,68,0.3);
    border-radius: 8px; color: #f87171; padding: 4px 10px; font-size: 12px;
    transition: background 0.15s ease; }
.switcher-close:hover { background: rgba(239,68,68,0.32); }
.ctx-menu-btn { background: transparent; border: none; border-radius: 6px;
    color: #e2e8f0; padding: 6px 14px; font-size: 13px; text-align: left;
    transition: background 0.12s ease; }
.ctx-menu-btn:hover { background: rgba(232,93,4,0.2); }
.ctx-menu-del { color: #f87171; }
"""

CSS_LIGHT = b"""
* { font-family: 'Ubuntu', 'Segoe UI', sans-serif; }
window, .ignis-topbar, .ignis-dock, .ignis-launcher, .switcher-win {
    transition: background 0.25s ease, border-color 0.25s ease;
}
button {
    transition: background 0.15s ease, border-color 0.15s ease,
                transform 0.1s ease, box-shadow 0.15s ease;
}
button:active { transform: scale(0.95); }
.ignis-topbar {
    background: rgba(245,245,252,0.96);
    border-bottom: 1px solid rgba(232,93,4,0.25);
    box-shadow: 0 1px 8px rgba(0,0,0,0.08);
}
.ignis-topbar label { color: #1e293b; font-size: 13px; }
.ignis-topbar button {
    background: transparent; border: none;
    color: #1e293b; padding: 2px 8px; border-radius: 6px; font-size: 13px;
}
.ignis-topbar button:hover {
    background: rgba(0,0,0,0.08);
    box-shadow: 0 2px 6px rgba(0,0,0,0.08);
}
.ignis-dock {
    background: rgba(240,240,252,0.96);
    border-left: 1px solid rgba(232,93,4,0.2);
    padding: 8px 4px;
    box-shadow: -2px 0 12px rgba(0,0,0,0.06);
}
.dock-btn {
    background: transparent; border: 1px solid transparent; border-radius: 14px;
    padding: 8px; margin: 3px; color: #1e293b; font-size: 10px;
    transition: background 0.18s ease, border-color 0.18s ease,
                transform 0.12s cubic-bezier(0.34,1.56,0.64,1), box-shadow 0.18s ease;
}
.dock-btn:hover {
    background: rgba(232,93,4,0.13); border-color: rgba(232,93,4,0.42);
    transform: scale(1.1);
    box-shadow: 0 4px 14px rgba(232,93,4,0.18);
}
.dock-btn:active { transform: scale(0.96); }
.dock-btn.running { background: rgba(232,93,4,0.09); }
.dock-running-dot { color: #e85d04; font-size: 9px; }
.dock-launcher {
    background: rgba(232,93,4,0.1); border: 1px solid rgba(232,93,4,0.32);
    border-radius: 12px; padding: 10px; margin: 4px; color: #e85d04; font-size: 18px;
    transition: background 0.18s ease, transform 0.12s cubic-bezier(0.34,1.56,0.64,1);
}
.dock-launcher:hover { background: rgba(232,93,4,0.22); transform: scale(1.08); }
.ignis-launcher { background: rgba(245,245,252,0.98); }
.launcher-search {
    background: rgba(0,0,0,0.05); border: 1px solid rgba(232,93,4,0.35);
    border-radius: 12px; color: #1e293b; font-size: 16px; padding: 10px 16px;
    transition: border-color 0.2s ease, background 0.2s ease, box-shadow 0.2s ease;
}
.launcher-search:focus {
    border-color: #e85d04;
    background: rgba(0,0,0,0.07);
    box-shadow: 0 0 0 3px rgba(232,93,4,0.14);
}
.app-grid-btn {
    background: rgba(255,255,255,0.85); border: 1px solid rgba(0,0,0,0.07);
    border-radius: 16px; padding: 14px; color: #1e293b; font-size: 11px;
    box-shadow: 0 2px 6px rgba(0,0,0,0.06);
    transition: background 0.18s ease, border-color 0.18s ease,
                transform 0.12s cubic-bezier(0.34,1.56,0.64,1), box-shadow 0.18s ease;
}
.app-grid-btn:hover {
    background: rgba(232,93,4,0.1); border-color: rgba(232,93,4,0.38);
    transform: translateY(-2px) scale(1.03);
    box-shadow: 0 6px 18px rgba(232,93,4,0.14);
}
.app-grid-btn:active { transform: scale(0.97); }
.power-btn {
    background: rgba(220,38,38,0.07); border: 1px solid rgba(220,38,38,0.22);
    border-radius: 10px; color: #dc2626; padding: 8px 14px; font-size: 13px;
    transition: background 0.15s ease, transform 0.1s ease;
}
.power-btn:hover { background: rgba(220,38,38,0.16); transform: scale(1.04); }
.ignis-clock { font-size: 13px; font-weight: 600; color: #1e293b; }
.ignis-indicator { font-size: 13px; color: #334155; padding: 2px 6px; }
.topbar-left button { color: #1e293b; font-size: 13px; font-weight: 600; }
.switcher-win { background: rgba(245,245,252,0.98); }
.switcher-card {
    background: rgba(255,255,255,0.9); border: 1px solid rgba(0,0,0,0.08);
    border-radius: 16px; padding: 14px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.05);
    transition: background 0.18s ease, border-color 0.18s ease,
                transform 0.12s ease, box-shadow 0.18s ease;
}
.switcher-card:hover {
    background: rgba(232,93,4,0.08); border-color: rgba(232,93,4,0.28);
    transform: translateY(-2px);
    box-shadow: 0 6px 18px rgba(232,93,4,0.1);
}
.switcher-name { color: #1e293b; font-size: 13px; font-weight: 600; }
.switcher-pid  { color: #94a3b8; font-size: 11px; }
.switcher-close { background: rgba(220,38,38,0.07); border: 1px solid rgba(220,38,38,0.22);
    border-radius: 8px; color: #dc2626; padding: 4px 10px; font-size: 12px;
    transition: background 0.15s ease; }
.switcher-close:hover { background: rgba(220,38,38,0.2); }
.ctx-menu-btn { background: transparent; border: none; border-radius: 6px;
    color: #334155; padding: 6px 14px; font-size: 13px; text-align: left;
    transition: background 0.12s ease; }
.ctx-menu-btn:hover { background: rgba(232,93,4,0.1); }
.ctx-menu-del { color: #dc2626; }
"""

APPS = [
    {"name": "Terminal",     "icon": "🖥️",  "cmd": "ignis-terminal",     "fixed": True},
    {"name": "Calculator",   "icon": "🧮",  "cmd": "ignis-calc",         "fixed": True},
    {"name": "Browser",      "icon": "🌐",  "cmd": "firefox",            "fixed": True},
    {"name": "Settings",     "icon": "⚙️",  "cmd": "ignis-settings",     "fixed": True},
    {"name": "Files",        "icon": "📂",  "cmd": "ignis-files",        "fixed": True},
    {"name": "메모장",        "icon": "📝",  "cmd": "ignis-notepad",      "fixed": True},
    {"name": "시계",          "icon": "🕐",  "cmd": "ignis-clock",        "fixed": False},
    {"name": "작업 관리자",   "icon": "📊",  "cmd": "ignis-taskmanager",  "fixed": False},
    {"name": "Python",       "icon": "🐍",  "cmd": "ignis-terminal",     "fixed": False},
    {"name": "Image Viewer", "icon": "🖼️",  "cmd": "eog",                "fixed": False},
    {"name": "Text Editor",  "icon": "✏️",  "cmd": "gedit",              "fixed": False},
    {"name": "Recovery",     "icon": "🛠️",  "cmd": "ignis-recovery",     "fixed": False},
]


def run_app(cmd):
    try:
        subprocess.Popen(cmd, shell=True,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as e:
        print(f"[shell] {cmd}: {e}")


def is_running(cmd):
    try:
        name = cmd.split()[0].split("/")[-1]
        r = subprocess.run(["pgrep", "-f", name],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return r.returncode == 0
    except Exception:
        return False


def get_running_apps():
    """현재 실행 중인 GUI 앱 목록 반환 [{name, pid, cmd}]"""
    try:
        out = subprocess.check_output(
            "ps aux | grep -E '(python3|firefox|gedit|eog|gnome)' | grep -v grep",
            shell=True, stderr=subprocess.DEVNULL).decode()
        apps = []
        for line in out.strip().splitlines():
            parts = line.split(None, 10)
            if len(parts) < 11:
                continue
            pid = parts[1]
            cmd = parts[10][:60]
            # 알려진 앱 매핑
            name = "알 수 없음"
            icon = "📦"
            for a in APPS:
                if a["cmd"].split()[0] in cmd:
                    name = a["name"]
                    icon = a["icon"]
                    break
            if "python3" in cmd and "ignis" in cmd:
                for part in cmd.split():
                    if "ignis-" in part:
                        name = part.split("/")[-1].replace("ignis-", "Ignis ").title()
                        break
            apps.append({"name": name, "icon": icon, "pid": pid, "cmd": cmd})
        return apps
    except Exception:
        return []


def apply_theme(dark: bool):
    sm = Adw.StyleManager.get_default()
    sm.set_color_scheme(
        Adw.ColorScheme.FORCE_DARK if dark else Adw.ColorScheme.FORCE_LIGHT)
    css = Gtk.CssProvider()
    css.load_from_data(CSS_DARK if dark else CSS_LIGHT)
    Gtk.StyleContext.add_provider_for_display(
        Gdk.Display.get_default(), css,
        Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)


# ── 열린 앱 전환기 ─────────────────────────────────
class AppSwitcher(Gtk.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app)
        self.set_decorated(False)
        self.set_resizable(False)
        self.add_css_class("switcher-win")

        display = Gdk.Display.get_default()
        monitor = display.get_monitors()[0]
        geo = monitor.get_geometry()
        self.set_default_size(geo.width - 68, geo.height - 36)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16,
                      margin_top=24, margin_start=32, margin_end=32, margin_bottom=24)
        self.set_child(vbox)

        hdr = Gtk.Box(spacing=12)
        title = Gtk.Label(xalign=0, hexpand=True)
        title.set_markup('<span size="18000" weight="bold">열린 앱</span>')
        hdr.append(title)

        close_btn = Gtk.Button(label="✕ 닫기")
        close_btn.add_css_class("dock-launcher")
        close_btn.connect("clicked", lambda *_: self.hide())
        hdr.append(close_btn)

        refresh_btn = Gtk.Button(label="🔄")
        refresh_btn.add_css_class("dock-launcher")
        refresh_btn.connect("clicked", lambda *_: self._refresh())
        hdr.append(refresh_btn)
        vbox.append(hdr)

        scroll = Gtk.ScrolledWindow(vexpand=True)
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        vbox.append(scroll)

        self.flow = Gtk.FlowBox()
        self.flow.set_max_children_per_line(6)
        self.flow.set_min_children_per_line(3)
        self.flow.set_selection_mode(Gtk.SelectionMode.NONE)
        self.flow.set_homogeneous(True)
        self.flow.set_row_spacing(10)
        self.flow.set_column_spacing(10)
        scroll.set_child(self.flow)

        self.empty_lbl = Gtk.Label(label="실행 중인 앱이 없습니다")
        self.empty_lbl.set_visible(False)
        vbox.append(self.empty_lbl)

    def _refresh(self):
        while child := self.flow.get_first_child():
            self.flow.remove(child)

        apps = get_running_apps()
        self.empty_lbl.set_visible(len(apps) == 0)

        for a in apps:
            card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6,
                          margin_top=8, margin_bottom=8,
                          margin_start=8, margin_end=8)
            card.add_css_class("switcher-card")

            icon = Gtk.Label()
            icon.set_markup(f'<span size="24000">{a["icon"]}</span>')
            card.append(icon)

            name = Gtk.Label(label=a["name"], ellipsize=3)
            name.add_css_class("switcher-name")
            card.append(name)

            pid_lbl = Gtk.Label(label=f"PID {a['pid']}")
            pid_lbl.add_css_class("switcher-pid")
            card.append(pid_lbl)

            btns = Gtk.Box(spacing=6, halign=Gtk.Align.CENTER)

            focus_btn = Gtk.Button(label="▶ 전환")
            focus_btn.add_css_class("dock-launcher")
            pid = a["pid"]
            focus_btn.connect("clicked", lambda *_, p=pid: (
                subprocess.Popen(["wmctrl", "-ia", p],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL),
                self.hide()
            ))
            btns.append(focus_btn)

            kill_btn = Gtk.Button(label="✕ 종료")
            kill_btn.add_css_class("switcher-close")
            kill_btn.connect("clicked", lambda *_, p=pid: (
                subprocess.Popen(["kill", p]),
                GLib.timeout_add(500, self._refresh)
            ))
            btns.append(kill_btn)

            card.append(btns)

            self.flow.append(card)

    def toggle(self):
        if self.is_visible():
            self.hide()
        else:
            self._refresh()
            self.present()


# ── 상단바 ─────────────────────────────────────────
class TopBar(Gtk.ApplicationWindow):
    def __init__(self, app, launcher_cb, switcher_cb, toggle_theme_cb):
        super().__init__(application=app)
        self.toggle_theme_cb = toggle_theme_cb
        self.set_decorated(False)
        self.set_resizable(False)
        self.add_css_class("ignis-topbar")

        display = Gdk.Display.get_default()
        monitor = display.get_monitors()[0]
        geo = monitor.get_geometry()
        self.set_default_size(geo.width, 36)
        self.set_size_request(geo.width, 36)

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        box.set_margin_start(8)
        box.set_margin_end(8)
        self.set_child(box)

        # 왼쪽
        left = Gtk.Box(spacing=4)
        left.add_css_class("topbar-left")

        lbl = Gtk.Label(label="🔥 IgnisOS")
        lbl.add_css_class("ignis-clock")
        left.append(lbl)

        sep = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
        sep.set_margin_start(6); sep.set_margin_end(6)
        left.append(sep)

        for label, cb in [
            ("Terminal", lambda *_: run_app("ignis-terminal")),
            ("창 전환 ⊟",  lambda *_: switcher_cb()),
        ]:
            b = Gtk.Button(label=label)
            b.connect("clicked", cb)
            left.append(b)

        box.append(left)
        box.append(Gtk.Box(hexpand=True))

        # 오른쪽
        right = Gtk.Box(spacing=2)

        # 다크/라이트 토글
        self._dark = CONFIG.get("dark_mode", True)
        self.theme_btn = Gtk.Button(label="🌙" if self._dark else "☀️")
        self.theme_btn.add_css_class("ignis-indicator")
        self.theme_btn.connect("clicked", self._on_theme_toggle)
        right.append(self.theme_btn)

        self.lbl_lang = Gtk.Button(label="EN")
        self.lbl_lang.add_css_class("ignis-indicator")
        self.lbl_lang.connect("clicked", self.toggle_lang)
        right.append(self.lbl_lang)
        self._lang = "EN"

        self.lbl_vol = Gtk.Button(label="🔊")
        self.lbl_vol.add_css_class("ignis-indicator")
        right.append(self.lbl_vol)

        self.lbl_wifi = Gtk.Button(label="📶")
        self.lbl_wifi.add_css_class("ignis-indicator")
        right.append(self.lbl_wifi)

        self.lbl_bat = Gtk.Label(label="")
        self.lbl_bat.add_css_class("ignis-indicator")
        right.append(self.lbl_bat)

        self.lbl_clock = Gtk.Label()
        self.lbl_clock.add_css_class("ignis-clock")
        self.lbl_clock.set_margin_start(6)
        right.append(self.lbl_clock)

        box.append(right)

        self._update_clock()
        self._update_battery()
        GLib.timeout_add_seconds(1, self._update_clock)
        GLib.timeout_add_seconds(30, self._update_battery)

    def _on_theme_toggle(self, *_):
        self._dark = not self._dark
        self.theme_btn.set_label("🌙" if self._dark else "☀️")
        CONFIG["dark_mode"] = self._dark
        save_config(CONFIG)
        self.toggle_theme_cb(self._dark)

    def _update_clock(self):
        self.lbl_clock.set_text(datetime.datetime.now().strftime("%a %b %d  %H:%M"))
        return True

    def _update_battery(self):
        try:
            cap = subprocess.check_output(
                "cat /sys/class/power_supply/BAT*/capacity 2>/dev/null | head -1",
                shell=True).decode().strip()
            sta = subprocess.check_output(
                "cat /sys/class/power_supply/BAT*/status 2>/dev/null | head -1",
                shell=True).decode().strip()
            self.lbl_bat.set_text(f"{'⚡' if sta=='Charging' else '🔋'} {cap}%" if cap else "")
        except Exception:
            self.lbl_bat.set_text("")
        return True

    def toggle_lang(self, *_):
        self._lang = {"EN": "KO", "KO": "JA", "JA": "EN"}[self._lang]
        self.lbl_lang.set_label(self._lang)
        try:
            subprocess.Popen(["setxkbmap", {"EN":"us","KO":"kr","JA":"jp"}[self._lang]])
        except Exception:
            pass


# ── 독 ─────────────────────────────────────────────
class Dock(Gtk.ApplicationWindow):
    def __init__(self, app, launcher_cb, switcher_cb):
        super().__init__(application=app)
        self.set_decorated(False)
        self.set_resizable(False)
        self.add_css_class("ignis-dock")

        display = Gdk.Display.get_default()
        monitor = display.get_monitors()[0]
        geo = monitor.get_geometry()
        DOCK_W = 68
        self.set_default_size(DOCK_W, geo.height)
        self.set_size_request(DOCK_W, geo.height)

        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.set_child(scroll)

        self._box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self._box.set_margin_top(36)
        self._box.set_margin_bottom(8)
        scroll.set_child(self._box)

        self._dot_labels = {}
        self._launcher_cb = launcher_cb
        self._switcher_cb = switcher_cb

        for a in APPS:
            if a["fixed"]:
                self._box.append(self._make_btn(a))

        self._box.append(Gtk.Box(vexpand=True))

        self.launcher_btn = Gtk.Button(label="⊞")
        self.launcher_btn.add_css_class("dock-launcher")
        self.launcher_btn.connect("clicked", lambda *_: launcher_cb())
        self._box.append(self.launcher_btn)

        pwr = Gtk.Button(label="⏻")
        pwr.add_css_class("dock-launcher")
        pwr.connect("clicked", self._on_power)
        self._box.append(pwr)

        GLib.timeout_add(2000, self._update_dots)

    def _make_btn(self, app_info):
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
        inner.add_css_class("dock-btn")

        icon = Gtk.Label()
        icon.set_markup(f'<span size="20000">{app_info["icon"]}</span>')
        name_lbl = Gtk.Label(label=app_info["name"][:6])
        name_lbl.set_ellipsize(3)
        inner.append(icon)
        inner.append(name_lbl)

        dot = Gtk.Label(label="")
        dot.add_css_class("dock-running-dot")
        dot.set_halign(Gtk.Align.CENTER)
        self._dot_labels[app_info["cmd"]] = dot

        outer.append(inner)
        outer.append(dot)

        btn = Gtk.Button()
        btn.set_child(outer)
        btn.add_css_class("dock-btn")
        cmd = app_info["cmd"]
        name = app_info["name"]

        # 좌클릭 — 앱 실행
        btn.connect("clicked", lambda *_: run_app(cmd))

        # 우클릭 — 컨텍스트 메뉴
        rc = Gtk.GestureClick()
        rc.set_button(3)
        rc.connect("pressed", lambda g, n, x, y, c=cmd, nm=name, b=btn:
                   self._show_ctx_menu(b, c, nm))
        btn.add_controller(rc)

        return btn

    def _show_ctx_menu(self, parent_btn, cmd, name):
        popover = Gtk.Popover()
        popover.set_parent(parent_btn)
        popover.set_has_arrow(False)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2,
                      margin_top=6, margin_bottom=6, margin_start=4, margin_end=4)

        title = Gtk.Label(label=name, xalign=0)
        title.set_markup(f'<b>{name}</b>')
        title.set_margin_start(8)
        title.set_margin_bottom(4)
        vbox.append(title)
        vbox.append(Gtk.Separator())

        for label, action in [
            ("▶  열기",        lambda: run_app(cmd)),
            ("🔄  다시 시작",  lambda: (self._kill_app(cmd), GLib.timeout_add(500, lambda: run_app(cmd)))),
            ("✕  닫기",       lambda: self._kill_app(cmd)),
            ("ℹ️  앱 정보",    lambda: self._show_info(cmd, name)),
        ]:
            b = Gtk.Button(label=label)
            b.add_css_class("ctx-menu-btn")
            if "닫기" in label:
                b.add_css_class("ctx-menu-del")
            b.set_hexpand(True)
            act = action
            b.connect("clicked", lambda _b, a=act: (a(), popover.popdown()))
            vbox.append(b)

        popover.set_child(vbox)
        popover.popup()

    def _kill_app(self, cmd):
        name = cmd.split()[0].split("/")[-1]
        subprocess.Popen(["pkill", "-f", name],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def _show_info(self, cmd, name):
        try:
            pid_out = subprocess.check_output(
                f"pgrep -f {cmd.split()[0]}", shell=True).decode().strip()
            mem_out = subprocess.check_output(
                f"ps -o pid,rss,pcpu -p {pid_out.splitlines()[0]} 2>/dev/null | tail -1",
                shell=True).decode().strip() if pid_out else "N/A"
        except Exception:
            pid_out = "실행 중이 아님"
            mem_out = ""

        dialog = Gtk.AlertDialog()
        dialog.set_message(f"앱 정보: {name}")
        dialog.set_detail(
            f"명령어: {cmd}\n"
            f"PID: {pid_out or '실행 중이 아님'}\n"
            f"메모리/CPU: {mem_out}"
        )
        dialog.show(self)

    def _update_dots(self):
        def check():
            states = {a["cmd"]: is_running(a["cmd"]) for a in APPS if a["fixed"]}
            GLib.idle_add(self._apply_dots, states)
        threading.Thread(target=check, daemon=True).start()
        return True

    def _apply_dots(self, states):
        for cmd, running in states.items():
            if cmd in self._dot_labels:
                lbl = self._dot_labels[cmd]
                lbl.set_text("●" if running else "")
                btn = lbl.get_parent()
                if btn:
                    inner = btn.get_first_child()
                    if inner:
                        if running:
                            inner.add_css_class("running")
                        else:
                            inner.remove_css_class("running")

    def _on_power(self, *_):
        dialog = Gtk.AlertDialog()
        dialog.set_message("전원 옵션")
        dialog.set_detail("작업을 선택하세요")
        dialog.add_button("취소")
        dialog.add_button("재시작")
        dialog.add_button("종료")
        dialog.set_default_button(0)
        dialog.set_cancel_button(0)
        dialog.choose(self, None, self._power_response, None)

    def _power_response(self, dialog, result, _):
        try:
            idx = dialog.choose_finish(result)
            if idx == 1: subprocess.Popen(["systemctl", "reboot"])
            elif idx == 2: subprocess.Popen(["systemctl", "poweroff"])
        except Exception:
            pass


# ── 앱 런처 ────────────────────────────────────────
class Launcher(Gtk.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app)
        self.set_decorated(False)
        self.set_resizable(False)
        self.add_css_class("ignis-launcher")

        display = Gdk.Display.get_default()
        monitor = display.get_monitors()[0]
        geo = monitor.get_geometry()
        self.set_default_size(geo.width - 68, geo.height - 36)

        main = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16,
                      margin_top=24, margin_start=32, margin_end=32, margin_bottom=16)
        self.set_child(main)

        search = Gtk.SearchEntry()
        search.set_placeholder_text("앱 검색...")
        search.add_css_class("launcher-search")
        search.connect("search-changed", self._on_search)
        main.append(search)

        scroll = Gtk.ScrolledWindow(vexpand=True)
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        main.append(scroll)

        self.flow = Gtk.FlowBox()
        self.flow.set_max_children_per_line(8)
        self.flow.set_min_children_per_line(4)
        self.flow.set_selection_mode(Gtk.SelectionMode.NONE)
        self.flow.set_homogeneous(True)
        self.flow.set_row_spacing(8)
        self.flow.set_column_spacing(8)
        scroll.set_child(self.flow)

        self._populate(APPS)

        bot = Gtk.Box(spacing=8, halign=Gtk.Align.CENTER)
        for label, cmd in [("🔄 재시작","systemctl reboot"),
                           ("⏻ 종료","systemctl poweroff"),
                           ("💤 절전","systemctl suspend"),
                           ("🔒 잠금","loginctl lock-session")]:
            b = Gtk.Button(label=label)
            b.add_css_class("power-btn")
            b.connect("clicked", lambda _b, c=cmd: run_app(c))
            bot.append(b)
        main.append(bot)

    def _populate(self, apps):
        while child := self.flow.get_first_child():
            self.flow.remove(child)
        for a in apps:
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6,
                         margin_top=8, margin_bottom=8, margin_start=6, margin_end=6)
            icon = Gtk.Label()
            icon.set_markup(f'<span size="28000">{a["icon"]}</span>')
            name = Gtk.Label(label=a["name"])
            name.set_ellipsize(3)
            box.append(icon)
            box.append(name)
            btn = Gtk.Button()
            btn.set_child(box)
            btn.add_css_class("app-grid-btn")
            cmd = a["cmd"]
            btn.connect("clicked", lambda *_, c=cmd: (run_app(c), self.hide()))
            self.flow.append(btn)

    def _on_search(self, entry):
        q = entry.get_text().lower()
        self._populate([a for a in APPS if q in a["name"].lower()] if q else APPS)

    def toggle(self):
        if self.is_visible(): self.hide()
        else: self.present()


# ── 메인 앱 ────────────────────────────────────────
class IgnisShell(Adw.Application):
    def __init__(self):
        super().__init__(application_id="org.ignis.Shell",
                         flags=Gio.ApplicationFlags.FLAGS_NONE)
        self.connect("activate", self._on_activate)

    def _on_activate(self, app):
        dark = CONFIG.get("dark_mode", True)
        apply_theme(dark)

        self.launcher  = Launcher(app)
        self.switcher  = AppSwitcher(app)
        self.topbar    = TopBar(app, self.launcher.toggle,
                                self.switcher.toggle, apply_theme)
        self.dock      = Dock(app, self.launcher.toggle, self.switcher.toggle)

        display = Gdk.Display.get_default()
        monitor = display.get_monitors()[0]
        geo = monitor.get_geometry()

        self.topbar.present()
        self.topbar.set_position(geo.x, geo.y)
        self.dock.present()
        self.dock.set_position(geo.x + geo.width - 68, geo.y)
        self.launcher.present()
        self.launcher.set_position(geo.x, geo.y + 36)
        self.launcher.hide()
        self.switcher.present()
        self.switcher.set_position(geo.x, geo.y + 36)
        self.switcher.hide()

        signal.signal(signal.SIGTERM, lambda *_: self.quit())
        signal.signal(signal.SIGINT,  lambda *_: self.quit())


def main():
    IgnisShell().run([])


if __name__ == "__main__":
    main()
