#!/usr/bin/env python3
"""
IgnisOS Shell — Desktop environment
Top bar + Right dock + App launcher overlay
"""
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GLib, Gdk, Gio, GdkPixbuf
import subprocess, os, threading, datetime, json, signal

# ── 색상 테마 (Ignis Fire) ─────────────────────────
CSS = b"""
* { font-family: 'Ubuntu', 'Segoe UI', sans-serif; }

.ignis-topbar {
    background: rgba(10, 10, 20, 0.92);
    border-bottom: 1px solid rgba(232, 93, 4, 0.3);
}
.ignis-topbar label { color: #f1f5f9; font-size: 13px; }
.ignis-topbar button {
    background: transparent;
    border: none;
    color: #f1f5f9;
    padding: 2px 8px;
    border-radius: 6px;
    font-size: 13px;
}
.ignis-topbar button:hover { background: rgba(255,255,255,0.1); }

.ignis-dock {
    background: rgba(10, 10, 20, 0.92);
    border-left: 1px solid rgba(232, 93, 4, 0.3);
    padding: 8px 4px;
}
.dock-btn {
    background: transparent;
    border: none;
    border-radius: 12px;
    padding: 8px;
    margin: 3px;
    color: #f1f5f9;
    font-size: 10px;
}
.dock-btn:hover {
    background: rgba(232, 93, 4, 0.2);
    border: 1px solid rgba(232, 93, 4, 0.5);
}
.dock-btn.active {
    background: rgba(232, 93, 4, 0.3);
    border: 1px solid #e85d04;
}
.dock-running-dot {
    color: #e85d04;
    font-size: 8px;
    margin-top: 0px;
    margin-bottom: 0px;
}
.dock-launcher {
    background: rgba(232, 93, 4, 0.15);
    border: 1px solid rgba(232, 93, 4, 0.4);
    border-radius: 12px;
    padding: 10px;
    margin: 4px;
    color: #e85d04;
    font-size: 18px;
}
.dock-launcher:hover { background: rgba(232, 93, 4, 0.3); }

.ignis-launcher {
    background: rgba(5, 5, 15, 0.96);
}
.launcher-search {
    background: rgba(255,255,255,0.08);
    border: 1px solid rgba(232, 93, 4, 0.4);
    border-radius: 12px;
    color: #f1f5f9;
    font-size: 16px;
    padding: 10px 16px;
}
.launcher-search:focus {
    border-color: #e85d04;
    box-shadow: 0 0 0 2px rgba(232,93,4,0.2);
}
.app-grid-btn {
    background: rgba(255,255,255,0.05);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 14px;
    padding: 14px;
    color: #f1f5f9;
    font-size: 11px;
}
.app-grid-btn:hover {
    background: rgba(232, 93, 4, 0.15);
    border-color: rgba(232, 93, 4, 0.4);
}
.launcher-section { color: #94a3b8; font-size: 11px; font-weight: bold; }
.power-btn {
    background: rgba(255,60,60,0.1);
    border: 1px solid rgba(255,60,60,0.3);
    border-radius: 10px;
    color: #f87171;
    padding: 8px 14px;
    font-size: 13px;
}
.power-btn:hover { background: rgba(255,60,60,0.25); }

.ignis-clock { font-size: 13px; font-weight: 600; color: #f1f5f9; }
.ignis-indicator { font-size: 13px; color: #e2e8f0; padding: 2px 6px; }
.topbar-left button { color: #f1f5f9; font-size: 13px; font-weight: 600; }
"""

APPS = [
    {"name": "Terminal",    "icon": "🖥️",  "cmd": "ignis-terminal", "fixed": True},
    {"name": "Calculator",  "icon": "🧮",  "cmd": "ignis-calc",     "fixed": True},
    {"name": "Browser",     "icon": "🌐",  "cmd": "firefox",        "fixed": True},
    {"name": "Settings",    "icon": "⚙️",  "cmd": "ignis-settings", "fixed": True},
    {"name": "Files",       "icon": "📂",  "cmd": "ignis-files",    "fixed": True},
    {"name": "Text Editor", "icon": "📝",  "cmd": "gedit",          "fixed": False},
    {"name": "Image View",  "icon": "🖼️",  "cmd": "eog",            "fixed": False},
    {"name": "System Mon.", "icon": "📊",  "cmd": "gnome-system-monitor", "fixed": False},
    {"name": "Archive Mgr", "icon": "🗜️",  "cmd": "file-roller",   "fixed": False},
    {"name": "Uptime Kern", "icon": "⚡",  "cmd": "uptime-kernel",  "fixed": False},
    {"name": "Recovery",    "icon": "🛠️",  "cmd": "ignis-recovery", "fixed": False},
]


def run_app(cmd):
    try:
        subprocess.Popen(cmd, shell=True,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as e:
        print(f"[shell] Failed to launch {cmd}: {e}")


# ── 상단바 ─────────────────────────────────────────
class TopBar(Gtk.ApplicationWindow):
    def __init__(self, app, launcher_toggle_cb):
        super().__init__(application=app)
        self.launcher_toggle_cb = launcher_toggle_cb
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

        # ── 왼쪽: 앱 제목 + 창 배치 ──────────────
        left = Gtk.Box(spacing=4)
        left.add_css_class("topbar-left")

        lbl_app = Gtk.Label(label="IgnisOS")
        lbl_app.add_css_class("ignis-clock")
        left.append(lbl_app)

        sep = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
        sep.set_margin_start(6)
        sep.set_margin_end(6)
        left.append(sep)

        for lbl, cb in [("Terminal", lambda *_: run_app("ignis-terminal")),
                        ("Tile ⊞",   self.on_tile)]:
            b = Gtk.Button(label=lbl)
            b.connect("clicked", cb)
            left.append(b)

        box.append(left)

        # ── 가운데 spacer ──────────────────────────
        box.append(Gtk.Box(hexpand=True))

        # ── 오른쪽: 시스템 표시 ──────────────────
        right = Gtk.Box(spacing=2)
        right.set_halign(Gtk.Align.END)

        self.lbl_lang = Gtk.Button(label="EN")
        self.lbl_lang.add_css_class("ignis-indicator")
        self.lbl_lang.connect("clicked", self.toggle_lang)
        right.append(self.lbl_lang)
        self._lang = "EN"

        self.lbl_bright = Gtk.Button(label="☀ 80%")
        self.lbl_bright.add_css_class("ignis-indicator")
        right.append(self.lbl_bright)

        self.lbl_vol = Gtk.Button(label="🔊 70%")
        self.lbl_vol.add_css_class("ignis-indicator")
        right.append(self.lbl_vol)

        self.lbl_wifi = Gtk.Button(label="📶")
        self.lbl_wifi.add_css_class("ignis-indicator")
        right.append(self.lbl_wifi)

        self.lbl_bat = Gtk.Label(label="")
        self.lbl_bat.add_css_class("ignis-indicator")
        self._update_battery()
        right.append(self.lbl_bat)

        self.lbl_clock = Gtk.Label()
        self.lbl_clock.add_css_class("ignis-clock")
        self.lbl_clock.set_margin_start(6)
        right.append(self.lbl_clock)

        box.append(right)

        self._update_clock()
        GLib.timeout_add_seconds(1, self._update_clock)
        GLib.timeout_add_seconds(30, self._update_battery)

    def _update_clock(self):
        now = datetime.datetime.now()
        self.lbl_clock.set_text(now.strftime("%a %b %d  %H:%M"))
        return True

    def _update_battery(self):
        try:
            out = subprocess.check_output(
                "cat /sys/class/power_supply/BAT*/capacity 2>/dev/null | head -1",
                shell=True).decode().strip()
            status = subprocess.check_output(
                "cat /sys/class/power_supply/BAT*/status 2>/dev/null | head -1",
                shell=True).decode().strip()
            if out:
                icon = "🔋" if status != "Charging" else "⚡"
                self.lbl_bat.set_text(f"{icon} {out}%")
            else:
                self.lbl_bat.set_text("")
        except Exception:
            self.lbl_bat.set_text("")
        return True

    def toggle_lang(self, *_):
        self._lang = "KO" if self._lang == "EN" else ("JA" if self._lang == "KO" else "EN")
        self.lbl_lang.set_label(self._lang)
        try:
            codes = {"EN": "us", "KO": "kr", "JA": "jp"}
            subprocess.Popen(["setxkbmap", codes[self._lang]])
        except Exception:
            pass

    def on_tile(self, *_):
        dialog = Gtk.AlertDialog()
        dialog.set_message("창 배치")
        dialog.set_detail("창 배치 기능은 현재 개발 중입니다.\n단축키: Super+←/→ (절반 배치)")
        dialog.show(self)


# ── 우측 독 ────────────────────────────────────────
def is_running(cmd):
    """앱이 실행 중인지 확인 (프로세스 이름으로)"""
    try:
        name = cmd.split()[0].split("/")[-1]
        result = subprocess.run(
            ["pgrep", "-f", name],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return result.returncode == 0
    except Exception:
        return False


class Dock(Gtk.ApplicationWindow):
    def __init__(self, app, launcher_toggle_cb):
        super().__init__(application=app)
        self.launcher_toggle_cb = launcher_toggle_cb
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

        # 실행 중 표시 점 레이블 저장 {cmd: dot_label}
        self._dot_labels = {}

        # 고정 앱 아이콘
        for app_info in APPS:
            if not app_info["fixed"]:
                continue
            btn = self._make_dock_btn(app_info)
            self._box.append(btn)

        # spacer
        self._box.append(Gtk.Box(vexpand=True))

        # 런처 버튼
        self.launcher_btn = Gtk.Button(label="⊞")
        self.launcher_btn.add_css_class("dock-launcher")
        self.launcher_btn.connect("clicked", self._on_launcher)
        self._box.append(self.launcher_btn)

        # 전원 버튼
        pwr = Gtk.Button(label="⏻")
        pwr.add_css_class("dock-launcher")
        pwr.connect("clicked", self._on_power)
        self._box.append(pwr)

        # 실행 중 앱 감지 — 2초마다 업데이트
        GLib.timeout_add(2000, self._update_running_dots)

    def _make_dock_btn(self, app_info):
        """독 버튼 생성 — 아이콘 + 이름 + 실행 중 표시 점"""
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
        inner.add_css_class("dock-btn")

        icon = Gtk.Label()
        icon.set_markup(f'<span size="20000">{app_info["icon"]}</span>')
        name_lbl = Gtk.Label(label=app_info["name"][:6])
        name_lbl.set_ellipsize(3)

        inner.append(icon)
        inner.append(name_lbl)

        # 실행 중 표시 점 (macOS 스타일 ●)
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
        btn.connect("clicked", lambda *_: run_app(cmd))
        return btn

    def _update_running_dots(self):
        """백그라운드에서 실행 중 앱 확인 후 점 업데이트"""
        def check():
            states = {}
            for app_info in APPS:
                if app_info["fixed"]:
                    states[app_info["cmd"]] = is_running(app_info["cmd"])
            GLib.idle_add(self._apply_dots, states)
        threading.Thread(target=check, daemon=True).start()
        return True  # 반복 유지

    def _apply_dots(self, states):
        for cmd, running in states.items():
            if cmd in self._dot_labels:
                self._dot_labels[cmd].set_text("●" if running else "")

    def _on_launcher(self, *_):
        self.launcher_toggle_cb()

    def _on_power(self, *_):
        dialog = Gtk.AlertDialog()
        dialog.set_message("전원 옵션")
        dialog.set_detail("종료 / 재시작 / 절전")
        dialog.add_button("취소")
        dialog.add_button("재시작")
        dialog.add_button("종료")
        dialog.set_default_button(0)
        dialog.set_cancel_button(0)
        dialog.choose(self, None, self._on_power_response, None)

    def _on_power_response(self, dialog, result, _):
        try:
            idx = dialog.choose_finish(result)
            if idx == 1:
                subprocess.Popen(["systemctl", "reboot"])
            elif idx == 2:
                subprocess.Popen(["systemctl", "poweroff"])
        except Exception:
            pass


# ── 앱 런처 오버레이 ───────────────────────────────
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

        self._all_apps = APPS
        self._build_ui()

    def _build_ui(self):
        main = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        main.set_margin_top(24)
        main.set_margin_start(32)
        main.set_margin_end(32)
        main.set_margin_bottom(16)
        self.set_child(main)

        # 검색창
        search = Gtk.SearchEntry()
        search.set_placeholder_text("앱 검색...")
        search.add_css_class("launcher-search")
        search.connect("search-changed", self._on_search)
        main.append(search)

        # 앱 그리드
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

        # 하단 전원 버튼
        bot = Gtk.Box(spacing=8)
        bot.set_halign(Gtk.Align.CENTER)
        for label, cmd in [("🔄 재시작", "systemctl reboot"),
                           ("⏻ 종료",    "systemctl poweroff"),
                           ("💤 절전",   "systemctl suspend"),
                           ("🔒 잠금",   "loginctl lock-session")]:
            b = Gtk.Button(label=label)
            b.add_css_class("power-btn")
            b.connect("clicked", lambda _b, c=cmd: run_app(c))
            bot.append(b)
        main.append(bot)

    def _populate(self, apps):
        while child := self.flow.get_first_child():
            self.flow.remove(child)

        for app_info in apps:
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
            box.set_margin_top(8)
            box.set_margin_bottom(8)
            box.set_margin_start(6)
            box.set_margin_end(6)

            icon = Gtk.Label()
            icon.set_markup(f'<span size="28000">{app_info["icon"]}</span>')
            name = Gtk.Label(label=app_info["name"])
            name.set_ellipsize(3)

            box.append(icon)
            box.append(name)

            btn = Gtk.Button()
            btn.set_child(box)
            btn.add_css_class("app-grid-btn")
            cmd = app_info["cmd"]
            btn.connect("clicked", lambda *_, c=cmd: (run_app(c), self.hide()))
            self.flow.append(btn)

    def _on_search(self, entry):
        q = entry.get_text().lower()
        filtered = [a for a in APPS if q in a["name"].lower()] if q else APPS
        self._populate(filtered)

    def toggle(self):
        if self.is_visible():
            self.hide()
        else:
            self.present()


# ── 메인 앱 ────────────────────────────────────────
class IgnisShell(Adw.Application):
    def __init__(self):
        super().__init__(application_id="org.ignis.Shell",
                         flags=Gio.ApplicationFlags.FLAGS_NONE)
        self.connect("activate", self._on_activate)

    def _on_activate(self, app):
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(CSS)
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

        self.launcher = Launcher(app)
        self.topbar = TopBar(app, self.launcher.toggle)
        self.dock = Dock(app, self.launcher.toggle)

        display = Gdk.Display.get_default()
        monitor = display.get_monitors()[0]
        geo = monitor.get_geometry()

        # 상단바: 화면 최상단
        self.topbar.present()
        self.topbar.set_position(geo.x, geo.y)

        # 독: 우측
        self.dock.present()
        self.dock.set_position(geo.x + geo.width - 68, geo.y)

        # 런처: 독/상단바 제외 영역
        self.launcher.present()
        self.launcher.set_position(geo.x, geo.y + 36)
        self.launcher.hide()

        signal.signal(signal.SIGTERM, lambda *_: self.quit())
        signal.signal(signal.SIGINT,  lambda *_: self.quit())


def main():
    app = IgnisShell()
    app.run([])


if __name__ == "__main__":
    main()
