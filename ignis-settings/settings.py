#!/usr/bin/env python3
"""
IgnisOS Settings — 시스템 설정 앱
WiFi · Bluetooth · Display · Sound · DateTime · Language · Users · Power
"""
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GLib, Gdk, Gio
import subprocess, os, json, pwd, grp, threading

CONFIG_FILE = os.path.expanduser("~/.config/ignis/shell.json")

def _load_shell_cfg():
    try:
        with open(CONFIG_FILE) as f:
            return json.load(f)
    except Exception:
        return {"dark_mode": True}

def _save_shell_cfg(cfg):
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f)

def apply_theme(dark: bool):
    """Apply dark/light theme to the settings app."""
    sm = Adw.StyleManager.get_default()
    sm.set_color_scheme(
        Adw.ColorScheme.FORCE_DARK if dark else Adw.ColorScheme.FORCE_LIGHT)
    cfg = _load_shell_cfg()
    cfg["dark_mode"] = dark
    _save_shell_cfg(cfg)

CSS = b"""
.settings-sidebar {
    background: rgba(10,10,20,0.95);
    border-right: 1px solid rgba(232,93,4,0.3);
}
.settings-sidebar row {
    padding: 10px 14px;
    color: #cbd5e1;
    border-radius: 8px;
    margin: 2px 6px;
}
.settings-sidebar row:selected {
    background: rgba(232,93,4,0.25);
    color: #fff;
}
.settings-sidebar row label { font-size: 14px; }
.settings-content { background: #0d0d1f; }
.settings-section-title {
    font-size: 22px; font-weight: bold;
    color: #f1f5f9; margin-bottom: 8px;
}
.settings-card {
    background: rgba(255,255,255,0.05);
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 14px;
    padding: 16px;
    margin-bottom: 12px;
}
.settings-card label { color: #e2e8f0; }
.settings-card-title { font-size: 15px; font-weight: 600; color: #f1f5f9; }
.settings-card-desc { font-size: 12px; color: #94a3b8; }
.ignis-switch { }
.danger-btn {
    background: rgba(239,68,68,0.15);
    border: 1px solid rgba(239,68,68,0.4);
    color: #f87171;
    border-radius: 8px;
}
.danger-btn:hover { background: rgba(239,68,68,0.3); }
.accent-btn {
    background: rgba(232,93,4,0.2);
    border: 1px solid rgba(232,93,4,0.5);
    color: #fb923c;
    border-radius: 8px;
}
.accent-btn:hover { background: rgba(232,93,4,0.35); }
row, listbox { background: transparent; }
"""

PANELS = [
    ("📶", "Wi-Fi",         "wifi"),
    ("📡", "Bluetooth",     "bluetooth"),
    ("🖥️", "디스플레이",    "display"),
    ("🔊", "소리",          "sound"),
    ("🌐", "언어 및 지역",  "language"),
    ("🕐", "날짜 및 시간",  "datetime"),
    ("☀️", "밝기 및 전원",  "power"),
    ("⌨️", "키보드",        "keyboard"),
    ("🖱️", "마우스",        "mouse"),
    ("🔔", "알림",          "notifications"),
    ("🔒", "보안",          "security"),
    ("👤", "사용자",        "users"),
    ("🖨️", "프린터",        "printer"),
    ("💾", "저장소",        "storage"),
    ("🌐", "네트워크",      "network"),
    ("📦", "앱 및 업데이트","apps"),
    ("♿", "손쉬운 사용",   "accessibility"),
    ("ℹ️", "시스템 정보",   "about"),
]


def run(cmd, capture=True):
    try:
        if capture:
            return subprocess.check_output(cmd, shell=True, stderr=subprocess.DEVNULL).decode().strip()
        else:
            subprocess.Popen(cmd, shell=True)
    except Exception:
        return ""


def card(title="", desc="", widget=None):
    box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
    box.add_css_class("settings-card")

    text = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2, hexpand=True)
    if title:
        lbl = Gtk.Label(label=title, xalign=0)
        lbl.add_css_class("settings-card-title")
        text.append(lbl)
    if desc:
        d = Gtk.Label(label=desc, xalign=0, wrap=True)
        d.add_css_class("settings-card-desc")
        text.append(d)
    box.append(text)
    if widget:
        box.append(widget)
    return box


# ── 패널들 ─────────────────────────────────────────

class WifiPanel(Gtk.Box):
    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.set_margin_start(24)
        self.set_margin_end(24)

        sw = Gtk.Switch()
        sw.set_active(True)
        sw.connect("state-set", self._toggle)
        self.append(card("Wi-Fi", "네트워크에 연결합니다", sw))

        # 네트워크 목록
        self.list_box = Gtk.ListBox()
        self.list_box.add_css_class("settings-card")
        self.list_box.set_selection_mode(Gtk.SelectionMode.NONE)
        self.append(self.list_box)

        refresh = Gtk.Button(label="🔄 새로고침")
        refresh.add_css_class("accent-btn")
        refresh.connect("clicked", self._refresh)
        self.append(refresh)

        self._refresh()

    def _refresh(self, *_):
        while child := self.list_box.get_first_child():
            self.list_box.remove(child)
        networks = run("nmcli -t -f SSID,SIGNAL,SECURITY dev wifi list 2>/dev/null | head -10")
        if not networks:
            row = Gtk.ListBoxRow()
            row.set_child(Gtk.Label(label="네트워크를 찾을 수 없습니다", margin_top=10, margin_bottom=10))
            self.list_box.append(row)
            return
        for line in networks.splitlines():
            parts = line.split(":")
            if len(parts) < 2:
                continue
            ssid, signal = parts[0], parts[1]
            row = Gtk.ListBoxRow()
            box = Gtk.Box(spacing=8, margin_top=6, margin_bottom=6,
                         margin_start=8, margin_end=8)
            icon = "📶" if int(signal or "0") > 50 else "📡"
            box.append(Gtk.Label(label=f"{icon} {ssid or '(숨김 네트워크)'}",
                                xalign=0, hexpand=True))
            box.append(Gtk.Label(label=f"{signal}%", xalign=1))
            row.set_child(box)
            self.list_box.append(row)

    def _toggle(self, sw, state):
        run(f"nmcli radio wifi {'on' if state else 'off'}", capture=False)


class BluetoothPanel(Gtk.Box):
    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.set_margin_start(24)
        self.set_margin_end(24)

        sw = Gtk.Switch()
        sw.set_active(True)
        sw.connect("state-set", self._toggle)
        self.append(card("Bluetooth", "블루투스 기기와 연결합니다", sw))

        scan_btn = Gtk.Button(label="🔍 기기 검색")
        scan_btn.add_css_class("accent-btn")
        scan_btn.connect("clicked", self._scan)
        self.append(scan_btn)

        self.dev_list = Gtk.ListBox()
        self.dev_list.add_css_class("settings-card")
        self.dev_list.set_selection_mode(Gtk.SelectionMode.NONE)
        self.append(self.dev_list)
        self._load_devices()

    def _load_devices(self):
        devices = run("bluetoothctl devices 2>/dev/null")
        while child := self.dev_list.get_first_child():
            self.dev_list.remove(child)
        if not devices:
            row = Gtk.ListBoxRow()
            row.set_child(Gtk.Label(label="등록된 기기 없음", margin_top=8, margin_bottom=8))
            self.dev_list.append(row)
            return
        for line in devices.splitlines():
            parts = line.split(" ", 2)
            name = parts[2] if len(parts) >= 3 else "알 수 없는 기기"
            row = Gtk.ListBoxRow()
            box = Gtk.Box(spacing=8, margin_top=6, margin_bottom=6,
                         margin_start=8, margin_end=8)
            box.append(Gtk.Label(label=f"📱 {name}", xalign=0, hexpand=True))
            btn = Gtk.Button(label="연결")
            btn.add_css_class("accent-btn")
            box.append(btn)
            row.set_child(box)
            self.dev_list.append(row)

    def _scan(self, *_):
        threading.Thread(target=lambda: run("bluetoothctl scan on &; sleep 5; bluetoothctl scan off"),
                        daemon=True).start()

    def _toggle(self, sw, state):
        run(f"bluetoothctl power {'on' if state else 'off'}", capture=False)


class DisplayPanel(Gtk.Box):
    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.set_margin_start(24)
        self.set_margin_end(24)

        # 해상도
        res_combo = Gtk.DropDown()
        resolutions = ["3840×2160 (4K)", "2560×1440 (QHD)", "1920×1080 (FHD)",
                       "1600×900", "1366×768", "1280×720 (HD)"]
        model = Gtk.StringList.new(resolutions)
        res_combo.set_model(model)
        res_combo.set_selected(2)
        res_combo.connect("notify::selected", self._on_resolution)
        self.append(card("해상도", "화면 해상도를 선택합니다", res_combo))

        # 주사율
        rate_combo = Gtk.DropDown()
        rates = ["60 Hz", "75 Hz", "90 Hz", "120 Hz", "144 Hz", "165 Hz"]
        self.append(card("주사율", "화면 재생률", Gtk.DropDown.new_with_strings(rates)))

        # 스케일
        scale_combo = Gtk.DropDown()
        scales = ["100%", "125%", "150%", "175%", "200%"]
        m = Gtk.StringList.new(scales)
        scale_combo.set_model(m)
        scale_combo.set_selected(1)
        self.append(card("화면 배율 (HiDPI)", "UI 크기를 조정합니다", scale_combo))

        # 방향
        orient_combo = Gtk.DropDown()
        orients = ["정방향 (가로)", "90° 회전", "180° 회전", "270° 회전"]
        self.append(card("화면 방향", "화면 회전 방향", Gtk.DropDown.new_with_strings(orients)))

        # 야간 모드
        ns = Gtk.Switch()
        self.append(card("야간 모드", "화면 색온도를 따뜻하게 합니다", ns))

        # 다크 모드
        cfg = _load_shell_cfg()
        dm = Gtk.Switch()
        dm.set_active(cfg.get("dark_mode", True))
        dm.connect("state-set", lambda s, state: apply_theme(state))
        self.append(card("다크 모드", "어두운 테마를 사용합니다", dm))

    def _on_resolution(self, combo, *_):
        # xrandr로 실제 적용
        resmap = {0: "3840x2160", 1: "2560x1440", 2: "1920x1080",
                  3: "1600x900",  4: "1366x768",  5: "1280x720"}
        res = resmap.get(combo.get_selected(), "1920x1080")
        run(f"xrandr --output $(xrandr | grep ' connected' | head -1 | awk '{{print $1}}') --mode {res}",
            capture=False)


class SoundPanel(Gtk.Box):
    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.set_margin_start(24)
        self.set_margin_end(24)

        # 출력 볼륨
        vol_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 1)
        vol_scale.set_hexpand(True)
        vol_scale.set_value(70)
        vol_scale.connect("value-changed", self._on_volume)
        self.append(card("출력 볼륨", "스피커/헤드폰 음량", vol_scale))

        # 입력 볼륨
        mic_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 1)
        mic_scale.set_hexpand(True)
        mic_scale.set_value(80)
        mic_scale.connect("value-changed", self._on_mic)
        self.append(card("마이크 음량", "입력 장치 감도", mic_scale))

        # 음소거
        mute = Gtk.Switch()
        mute.connect("state-set", lambda s, state: run(
            f"amixer set Master {'mute' if state else 'unmute'}", capture=False))
        self.append(card("음소거", "모든 소리를 끕니다", mute))

        # 출력 장치
        out_combo = Gtk.DropDown()
        outputs = ["내장 스피커", "HDMI 출력", "헤드폰 (3.5mm)", "Bluetooth 스피커"]
        self.append(card("출력 장치", "소리 출력 장치를 선택합니다",
                        Gtk.DropDown.new_with_strings(outputs)))

        # 알림음
        notif = Gtk.Switch()
        notif.set_active(True)
        self.append(card("알림음", "시스템 알림 소리", notif))

    def _on_volume(self, scale):
        v = int(scale.get_value())
        run(f"amixer set Master {v}%", capture=False)

    def _on_mic(self, scale):
        v = int(scale.get_value())
        run(f"amixer set Capture {v}%", capture=False)


class LanguagePanel(Gtk.Box):
    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.set_margin_start(24)
        self.set_margin_end(24)

        # 언어
        lang_combo = Gtk.DropDown()
        langs = ["English (United States)", "한국어 (대한민국)", "日本語 (日本)",
                 "中文 (简体)", "Français (France)", "Deutsch (Deutschland)",
                 "Español (España)"]
        m = Gtk.StringList.new(langs)
        lang_combo.set_model(m)
        lang_combo.connect("notify::selected", self._on_lang)
        self.append(card("시스템 언어", "인터페이스 표시 언어를 선택합니다", lang_combo))

        # 입력기
        input_combo = Gtk.DropDown()
        inputs = ["영어 (US)", "한국어 (한글)", "日本語 (かな)", "Pinyin (中文)"]
        self.append(card("입력 방식", "키보드 입력 방법", Gtk.DropDown.new_with_strings(inputs)))

        # 시간대
        tz_combo = Gtk.DropDown()
        zones = ["Asia/Seoul (KST +9)", "Asia/Tokyo (JST +9)",
                 "America/New_York (EST -5)", "America/Los_Angeles (PST -8)",
                 "Europe/London (GMT)", "Europe/Paris (CET +1)"]
        m2 = Gtk.StringList.new(zones)
        tz_combo.set_model(m2)
        tz_combo.connect("notify::selected", self._on_timezone)
        self.append(card("시간대", "지역 시간대", tz_combo))

        # 숫자/날짜 형식
        fmt_combo = Gtk.DropDown()
        fmts = ["한국 (YYYY.MM.DD)", "미국 (MM/DD/YYYY)", "유럽 (DD/MM/YYYY)"]
        self.append(card("날짜 형식", "날짜 및 숫자 표기 방법",
                        Gtk.DropDown.new_with_strings(fmts)))

    def _on_lang(self, combo, *_):
        locales = {0: "en_US.UTF-8", 1: "ko_KR.UTF-8", 2: "ja_JP.UTF-8",
                   3: "zh_CN.UTF-8", 4: "fr_FR.UTF-8", 5: "de_DE.UTF-8", 6: "es_ES.UTF-8"}
        locale = locales.get(combo.get_selected(), "en_US.UTF-8")
        run(f"localectl set-locale LANG={locale}", capture=False)

    def _on_timezone(self, combo, *_):
        tzmap = {0: "Asia/Seoul", 1: "Asia/Tokyo", 2: "America/New_York",
                 3: "America/Los_Angeles", 4: "Europe/London", 5: "Europe/Paris"}
        tz = tzmap.get(combo.get_selected(), "UTC")
        run(f"timedatectl set-timezone {tz}", capture=False)


class DateTimePanel(Gtk.Box):
    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.set_margin_start(24)
        self.set_margin_end(24)

        # 자동 시간
        auto = Gtk.Switch()
        auto.set_active(True)
        auto.connect("state-set", lambda s, st: run(
            f"timedatectl set-ntp {'true' if st else 'false'}", capture=False))
        self.append(card("자동 시간 설정", "인터넷에서 시간을 자동으로 가져옵니다", auto))

        # 날짜 선택
        cal = Gtk.Calendar()
        cal.add_css_class("settings-card")
        self.append(cal)

        # 시간 입력
        time_box = Gtk.Box(spacing=8)
        h = Gtk.SpinButton.new_with_range(0, 23, 1)
        m = Gtk.SpinButton.new_with_range(0, 59, 1)
        s = Gtk.SpinButton.new_with_range(0, 59, 1)
        import datetime as dt
        now = dt.datetime.now()
        h.set_value(now.hour)
        m.set_value(now.minute)
        s.set_value(now.second)
        time_box.append(h)
        time_box.append(Gtk.Label(label=":"))
        time_box.append(m)
        time_box.append(Gtk.Label(label=":"))
        time_box.append(s)
        self.append(card("시간 설정", "시:분:초", time_box))

        # 24시간 형식
        h24 = Gtk.Switch()
        h24.set_active(True)
        self.append(card("24시간 형식", "오전/오후 대신 0~23시로 표시", h24))


class PowerPanel(Gtk.Box):
    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.set_margin_start(24)
        self.set_margin_end(24)

        # 밝기
        bright_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 1)
        bright_scale.set_hexpand(True)
        bright_scale.set_value(80)
        bright_scale.connect("value-changed", self._on_brightness)
        self.append(card("화면 밝기", "☀️ 화면 밝기 조절", bright_scale))

        # 절전 모드
        sleep_combo = Gtk.DropDown()
        sleeps = ["안 함", "1분", "5분", "10분", "15분", "30분"]
        m = Gtk.StringList.new(sleeps)
        sleep_combo.set_model(m)
        sleep_combo.set_selected(3)
        self.append(card("자동 절전", "화면 꺼짐 시간 설정", sleep_combo))

        # 덮개 닫기 동작 (노트북)
        lid_combo = Gtk.DropDown()
        lids = ["절전", "최대 절전", "아무것도 안 함"]
        self.append(card("덮개 닫기", "노트북 덮개 닫을 때 동작",
                        Gtk.DropDown.new_with_strings(lids)))

        # 배터리
        bat = run("cat /sys/class/power_supply/BAT*/capacity 2>/dev/null | head -1")
        if bat:
            bat_label = Gtk.Label(label=f"🔋 {bat}%", xalign=0)
            bat_label.add_css_class("settings-card-title")
            self.append(bat_label)

        # 전원 버튼 동작
        pwr_combo = Gtk.DropDown()
        pwrs = ["종료", "절전", "최대 절전", "아무것도 안 함"]
        self.append(card("전원 버튼", "전원 버튼 누를 때 동작",
                        Gtk.DropDown.new_with_strings(pwrs)))

    def _on_brightness(self, scale):
        v = int(scale.get_value())
        run(f"brightnessctl set {v}%", capture=False)


class UsersPanel(Gtk.Box):
    def __init__(self, win):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.set_margin_start(24)
        self.set_margin_end(24)
        self.win = win

        add_btn = Gtk.Button(label="➕ 사용자 추가")
        add_btn.add_css_class("accent-btn")
        add_btn.connect("clicked", self._add_user)
        self.append(add_btn)

        self.user_list = Gtk.ListBox()
        self.user_list.add_css_class("settings-card")
        self.user_list.set_selection_mode(Gtk.SelectionMode.NONE)
        self.append(self.user_list)
        self._load_users()

    def _load_users(self):
        while child := self.user_list.get_first_child():
            self.user_list.remove(child)
        for p in pwd.getpwall():
            if 1000 <= p.pw_uid < 65534:
                row = Gtk.ListBoxRow()
                box = Gtk.Box(spacing=8, margin_top=6, margin_bottom=6,
                             margin_start=8, margin_end=8)
                admin = "root" in [g.gr_name for g in grp.getgrall() if p.pw_name in g.gr_mem]
                info = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
                info.append(Gtk.Label(label=f"👤 {p.pw_name}", xalign=0))
                info.append(Gtk.Label(label=f"UID: {p.pw_uid}  {'관리자' if admin else '일반 사용자'}",
                                     xalign=0))
                box.append(info)
                box.append(Gtk.Box(hexpand=True))
                del_btn = Gtk.Button(label="삭제")
                del_btn.add_css_class("danger-btn")
                uname = p.pw_name
                del_btn.connect("clicked", lambda _b, u=uname: self._del_user(u))
                box.append(del_btn)
                row.set_child(box)
                self.user_list.append(row)

    def _add_user(self, *_):
        dialog = Gtk.AlertDialog()
        dialog.set_message("사용자 추가")
        dialog.set_detail("새 사용자 이름을 입력하세요:")
        dialog.add_button("취소")
        dialog.add_button("추가")
        dialog.set_default_button(1)
        dialog.set_cancel_button(0)
        dialog.choose(self.win, None, self._on_add_response, None)

    def _on_add_response(self, dialog, result, _):
        try:
            if dialog.choose_finish(result) == 1:
                run("useradd -m -s /bin/bash newuser", capture=False)
                GLib.timeout_add(500, self._load_users)
        except Exception:
            pass

    def _del_user(self, username):
        dialog = Gtk.AlertDialog()
        dialog.set_message(f"'{username}' 삭제")
        dialog.set_detail("정말 이 사용자를 삭제하시겠습니까?")
        dialog.add_button("취소")
        dialog.add_button("삭제")
        dialog.set_default_button(0)
        dialog.set_cancel_button(0)
        dialog.choose(self.win, None,
                     lambda d, r, _: run(f"userdel -r {username}", capture=False)
                     if d.choose_finish(r) == 1 else None, None)


class SecurityPanel(Gtk.Box):
    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.set_margin_start(24)
        self.set_margin_end(24)

        fw = Gtk.Switch()
        fw.connect("state-set", lambda s, st: run(
            f"ufw {'enable' if st else 'disable'}", capture=False))
        self.append(card("방화벽 (UFW)", "네트워크 방화벽 활성화", fw))

        auto_update = Gtk.Switch()
        auto_update.set_active(True)
        self.append(card("자동 보안 업데이트", "보안 패치를 자동으로 설치합니다", auto_update))

        lock = Gtk.Switch()
        lock.set_active(True)
        self.append(card("자동 화면 잠금", "일정 시간 후 화면을 잠급니다", lock))

        ssh = Gtk.Switch()
        self.append(card("SSH 원격 접속", "SSH 서버를 활성화합니다", ssh))
        ssh.connect("state-set", lambda s, st: run(
            f"systemctl {'enable --now' if st else 'disable --now'} ssh", capture=False))


class AboutPanel(Gtk.Box):
    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.set_margin_start(24)
        self.set_margin_end(24)

        banner = Gtk.Label()
        banner.set_markup('<span size="32000">🔥</span>')
        self.append(banner)

        info = {
            "OS 이름":    "IgnisOS 1.0.0 LTS",
            "코드명":     "Ember",
            "아키텍처":   run("uname -m") or "aarch64",
            "커널":       run("uname -r") or "Linux ARM64",
            "업타임 커널": "v1.0.0",
            "기반":       "Ubuntu 24.04 LTS (Noble)",
            "라이선스":   "MIT",
            "제작":       "100% AI Built (Claude Sonnet 4.6)",
            "GitHub":     "github.com/viviantest1004/IgnisOS",
        }
        for k, v in info.items():
            c = card(k, v)
            self.append(c)

        copy_btn = Gtk.Button(label="📋 시스템 정보 복사")
        copy_btn.add_css_class("accent-btn")
        copy_btn.connect("clicked", self._copy_info)
        self.append(copy_btn)

    def _copy_info(self, *_):
        info_text = "\n".join([
            "IgnisOS 1.0.0 LTS (Ember)",
            f"Kernel: {run('uname -r') or 'ARM64'}",
            f"Arch: {run('uname -m') or 'aarch64'}",
        ])
        display = Gdk.Display.get_default()
        display.get_clipboard().set(info_text)


class KeyboardPanel(Gtk.Box):
    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.set_margin_start(24); self.set_margin_end(24)

        repeat_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 1, 10, 1)
        repeat_scale.set_hexpand(True); repeat_scale.set_value(5)
        self.append(card("키 반복 속도", "키를 누르고 있을 때 반복 속도", repeat_scale))

        delay_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 1, 10, 1)
        delay_scale.set_hexpand(True); delay_scale.set_value(3)
        self.append(card("반복 지연", "키 반복 시작 전 대기 시간", delay_scale))

        layout_combo = Gtk.DropDown()
        layouts = ["영어 (US)", "한국어", "日本語", "QWERTY", "Dvorak", "Colemak"]
        layout_combo.set_model(Gtk.StringList.new(layouts))
        self.append(card("키보드 레이아웃", "키보드 입력 배열", layout_combo))

        shortcuts = Gtk.Switch(); shortcuts.set_active(True)
        self.append(card("키보드 단축키", "시스템 단축키 활성화", shortcuts))

        autocorrect = Gtk.Switch()
        self.append(card("자동 수정", "오타 자동 교정", autocorrect))


class MousePanel(Gtk.Box):
    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.set_margin_start(24); self.set_margin_end(24)

        speed_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 1, 10, 1)
        speed_scale.set_hexpand(True); speed_scale.set_value(5)
        speed_scale.connect("value-changed", lambda s:
            run(f"xinput set-prop 'pointer' 'libinput Accel Speed' {(s.get_value()-5)/5}", capture=False))
        self.append(card("포인터 속도", "마우스/터치패드 커서 속도", speed_scale))

        natural = Gtk.Switch()
        natural.connect("state-set", lambda s, st:
            run(f"xinput set-prop 'pointer' 'libinput Natural Scrolling Enabled' {1 if st else 0}", capture=False))
        self.append(card("자연 스크롤", "스크롤 방향 반전 (macOS 스타일)", natural))

        tap = Gtk.Switch(); tap.set_active(True)
        self.append(card("탭하여 클릭", "터치패드 탭을 클릭으로 인식", tap))

        accel = Gtk.Switch(); accel.set_active(True)
        self.append(card("포인터 가속", "속도에 따라 커서 가속", accel))

        buttons = Gtk.DropDown()
        buttons.set_model(Gtk.StringList.new(["오른손잡이", "왼손잡이"]))
        self.append(card("기본 버튼", "마우스 주 버튼 방향", buttons))


class NotificationsPanel(Gtk.Box):
    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.set_margin_start(24); self.set_margin_end(24)

        dnd = Gtk.Switch()
        self.append(card("방해 금지 모드", "모든 알림을 끕니다", dnd))

        sound = Gtk.Switch(); sound.set_active(True)
        self.append(card("알림음", "알림 수신 시 소리 재생", sound))

        preview = Gtk.Switch(); preview.set_active(True)
        self.append(card("잠금 화면 알림", "잠금 화면에서 알림 표시", preview))

        pos_combo = Gtk.DropDown()
        pos_combo.set_model(Gtk.StringList.new(["오른쪽 위", "오른쪽 아래", "왼쪽 위", "왼쪽 아래"]))
        self.append(card("알림 위치", "알림 팝업이 나타날 위치", pos_combo))

        timeout_combo = Gtk.DropDown()
        timeout_combo.set_model(Gtk.StringList.new(["3초", "5초", "10초", "계속 표시"]))
        timeout_combo.set_selected(1)
        self.append(card("알림 표시 시간", "알림이 사라지기까지의 시간", timeout_combo))


class PrinterPanel(Gtk.Box):
    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.set_margin_start(24); self.set_margin_end(24)

        printers = run("lpstat -p 2>/dev/null") or "연결된 프린터 없음"
        info = Gtk.Label(label=printers, xalign=0, wrap=True)
        info.add_css_class("settings-card")
        self.append(info)

        add_btn = Gtk.Button(label="➕ 프린터 추가")
        add_btn.add_css_class("accent-btn")
        add_btn.connect("clicked", lambda *_: run("system-config-printer", capture=False))
        self.append(add_btn)

        default_combo = Gtk.DropDown()
        default_combo.set_model(Gtk.StringList.new(["기본 프린터", "PDF 저장"]))
        self.append(card("기본 프린터", "기본으로 사용할 프린터", default_combo))

        quality_combo = Gtk.DropDown()
        quality_combo.set_model(Gtk.StringList.new(["초안", "보통", "높음", "최상"]))
        quality_combo.set_selected(1)
        self.append(card("인쇄 품질", "기본 인쇄 품질", quality_combo))


class StoragePanel(Gtk.Box):
    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.set_margin_start(24); self.set_margin_end(24)

        # 디스크 사용량
        try:
            import shutil
            total, used, free = shutil.disk_usage("/")
            pct = used / total * 100
            bar = Gtk.ProgressBar()
            bar.set_fraction(pct / 100)
            bar.set_show_text(True)
            bar.set_text(f"{used//1024//1024//1024:.1f}GB / {total//1024//1024//1024:.1f}GB 사용")
            self.append(card("내부 저장소", f"{free//1024//1024//1024:.1f}GB 남음", bar))
        except Exception:
            self.append(card("저장소", "정보를 불러올 수 없습니다"))

        # 마운트된 드라이브
        mounts = run("lsblk -o NAME,SIZE,MOUNTPOINT -n 2>/dev/null | head -10") or "드라이브 없음"
        mount_lbl = Gtk.Label(label=mounts, xalign=0)
        mount_lbl.add_css_class("settings-card")
        mount_lbl.set_selectable(True)
        self.append(mount_lbl)

        clean_btn = Gtk.Button(label="🗑 임시 파일 정리")
        clean_btn.add_css_class("accent-btn")
        clean_btn.connect("clicked", lambda *_: run("rm -rf /tmp/* ~/.cache/thumbnails 2>/dev/null", capture=False))
        self.append(clean_btn)


class NetworkPanel(Gtk.Box):
    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.set_margin_start(24); self.set_margin_end(24)

        ip = run("ip -4 addr show | grep inet | awk '{print $2}' | head -3") or "N/A"
        self.append(card("IP 주소", ip))

        dns_combo = Gtk.DropDown()
        dns_combo.set_model(Gtk.StringList.new([
            "자동 (DHCP)", "Google (8.8.8.8)", "Cloudflare (1.1.1.1)", "수동 설정"
        ]))
        dns_combo.connect("notify::selected", self._on_dns)
        self.append(card("DNS 서버", "이름 확인 서버", dns_combo))

        proxy = Gtk.Switch()
        self.append(card("프록시", "네트워크 프록시 사용", proxy))

        vpn_btn = Gtk.Button(label="🔐 VPN 설정")
        vpn_btn.add_css_class("accent-btn")
        self.append(vpn_btn)

        firewall = Gtk.Switch()
        firewall.connect("state-set", lambda s, st:
            run(f"ufw {'enable' if st else 'disable'}", capture=False))
        self.append(card("방화벽", "UFW 네트워크 방화벽", firewall))

    def _on_dns(self, combo, *_):
        dns_map = {1: "8.8.8.8\nnameserver 8.8.4.4",
                   2: "1.1.1.1\nnameserver 1.0.0.1"}
        idx = combo.get_selected()
        if idx in dns_map:
            run(f"echo 'nameserver {dns_map[idx]}' | sudo tee /etc/resolv.conf", capture=False)


# ── 메인 설정 앱 ───────────────────────────────────
class IgnisSettings(Adw.Application):
    def __init__(self):
        super().__init__(application_id="org.ignis.Settings",
                         flags=Gio.ApplicationFlags.FLAGS_NONE)
        self.connect("activate", self._on_activate)

    def _on_activate(self, app):
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(CSS)
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        win = Adw.ApplicationWindow(application=app)
        win.set_title("설정")
        win.set_default_size(960, 680)

        split = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        win.set_content(split)

        # ── 사이드바 ──────────────────────────────
        sidebar_scroll = Gtk.ScrolledWindow()
        sidebar_scroll.set_size_request(220, -1)
        sidebar_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        sidebar_scroll.add_css_class("settings-sidebar")

        sidebar_list = Gtk.ListBox()
        sidebar_list.add_css_class("settings-sidebar")
        sidebar_list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        sidebar_scroll.set_child(sidebar_list)
        split.append(sidebar_scroll)

        # ── 컨텐츠 영역 ───────────────────────────
        content_scroll = Gtk.ScrolledWindow(hexpand=True, vexpand=True)
        content_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        content_scroll.add_css_class("settings-content")

        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        content_box.set_margin_top(24)
        content_box.set_margin_bottom(24)
        content_scroll.set_child(content_box)
        split.append(content_scroll)

        # 패널 생성
        panels = {}
        for icon, name, key in PANELS:
            row = Gtk.ListBoxRow()
            row_box = Gtk.Box(spacing=10, margin_start=8, margin_top=4, margin_bottom=4)
            row_box.append(Gtk.Label(label=icon))
            row_box.append(Gtk.Label(label=name, xalign=0))
            row.set_child(row_box)
            sidebar_list.append(row)

            # 제목
            title_lbl = Gtk.Label(label=f"{icon}  {name}", xalign=0)
            title_lbl.add_css_class("settings-section-title")
            title_lbl.set_margin_start(24)
            title_lbl.set_margin_bottom(12)

            panel_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
            panel_box.append(title_lbl)

            if key == "wifi":              panel = WifiPanel()
            elif key == "bluetooth":       panel = BluetoothPanel()
            elif key == "display":         panel = DisplayPanel()
            elif key == "sound":           panel = SoundPanel()
            elif key == "language":        panel = LanguagePanel()
            elif key == "datetime":        panel = DateTimePanel()
            elif key == "power":           panel = PowerPanel()
            elif key == "keyboard":        panel = KeyboardPanel()
            elif key == "mouse":           panel = MousePanel()
            elif key == "notifications":   panel = NotificationsPanel()
            elif key == "users":           panel = UsersPanel(win)
            elif key == "security":        panel = SecurityPanel()
            elif key == "printer":         panel = PrinterPanel()
            elif key == "storage":         panel = StoragePanel()
            elif key == "network":         panel = NetworkPanel()
            elif key == "about":           panel = AboutPanel()
            else:
                panel = Gtk.Label(label=f"{name} 설정 (준비 중)")
                panel.add_css_class("settings-card-desc")
                panel.set_margin_start(24)

            panel_box.append(panel)
            panel_box.set_visible(False)
            panels[key] = panel_box
            content_box.append(panel_box)

        def on_row_selected(lb, row):
            if not row:
                return
            idx = row.get_index()
            key = PANELS[idx][2]
            for k, p in panels.items():
                p.set_visible(k == key)

        sidebar_list.connect("row-selected", on_row_selected)
        sidebar_list.select_row(sidebar_list.get_row_at_index(0))

        win.present()


def main():
    app = IgnisSettings()
    app.run([])


if __name__ == "__main__":
    main()
