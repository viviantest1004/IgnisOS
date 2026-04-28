#!/usr/bin/env python3
"""
IgnisOS OOBE — Out Of Box Experience
첫 부팅 시 실행되는 초기 설정 마법사
: 언어 선택 → 시간대 설정 → Wi-Fi 연결 → 완료
"""
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, Gdk, Gio, GLib
import subprocess, os, json

OOBE_DONE_FILE = os.path.expanduser("~/.config/ignis/oobe-done")

CSS = b"""
.oobe-win {
    background: linear-gradient(135deg, #070714 0%, #0d0d2f 50%, #0a0a1a 100%);
}
.oobe-card {
    background: rgba(255,255,255,0.05);
    border: 1px solid rgba(232,93,4,0.3);
    border-radius: 20px;
    padding: 32px;
}
.oobe-title {
    font-size: 28px; font-weight: 700; color: #f1f5f9;
}
.oobe-subtitle { font-size: 15px; color: #94a3b8; }
.oobe-step-title { font-size: 22px; font-weight: 600; color: #f1f5f9; }
.oobe-step-desc  { font-size: 13px; color: #64748b; }
.oobe-next {
    background: #e85d04; color: #fff; font-size: 15px;
    font-weight: 600; border-radius: 12px; padding: 10px 28px; border: none;
}
.oobe-next:hover { background: #c74c00; }
.oobe-back {
    background: rgba(255,255,255,0.07); color: #94a3b8;
    font-size: 14px; border-radius: 10px; padding: 8px 20px; border: none;
}
.oobe-back:hover { background: rgba(255,255,255,0.13); }
.oobe-skip { color: #475569; font-size: 13px; border: none; background: transparent; }
.oobe-skip:hover { color: #64748b; }
.lang-row { padding: 10px 14px; border-radius: 10px; margin: 2px; }
.lang-row:selected { background: rgba(232,93,4,0.25); }
.lang-row label { font-size: 14px; color: #e2e8f0; }
.wifi-row { padding: 8px 12px; border-radius: 8px; margin: 2px; }
.wifi-row:hover { background: rgba(255,255,255,0.05); }
.step-dot {
    min-width: 10px; min-height: 10px;
    border-radius: 50%;
}
.step-dot-active  { background: #e85d04; }
.step-dot-done    { background: #22c55e; }
.step-dot-pending { background: rgba(255,255,255,0.2); }
row, listbox { background: transparent; }
"""

LANGUAGES = [
    ("🇺🇸", "English",          "en_US.UTF-8", "us"),
    ("🇰🇷", "한국어",           "ko_KR.UTF-8", "kr"),
    ("🇯🇵", "日本語",           "ja_JP.UTF-8", "jp"),
    ("🇨🇳", "中文 (简体)",      "zh_CN.UTF-8", "cn"),
    ("🇫🇷", "Français",         "fr_FR.UTF-8", "fr"),
    ("🇩🇪", "Deutsch",          "de_DE.UTF-8", "de"),
    ("🇪🇸", "Español",          "es_ES.UTF-8", "es"),
    ("🇧🇷", "Português",        "pt_BR.UTF-8", "br"),
]

TIMEZONES = [
    ("🇰🇷", "Seoul (KST +9)",        "Asia/Seoul"),
    ("🇯🇵", "Tokyo (JST +9)",         "Asia/Tokyo"),
    ("🇺🇸", "New York (EST -5)",      "America/New_York"),
    ("🇺🇸", "Los Angeles (PST -8)",   "America/Los_Angeles"),
    ("🇬🇧", "London (GMT)",           "Europe/London"),
    ("🇫🇷", "Paris (CET +1)",         "Europe/Paris"),
    ("🇸🇬", "Singapore (SGT +8)",     "Asia/Singapore"),
    ("🇦🇺", "Sydney (AEDT +11)",      "Australia/Sydney"),
    ("🌍", "UTC",                    "UTC"),
]


def run(cmd, capture=True):
    try:
        if capture:
            return subprocess.check_output(cmd, shell=True,
                                           stderr=subprocess.DEVNULL).decode().strip()
        else:
            subprocess.Popen(cmd, shell=True,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        return ""


class OOBE(Adw.Application):
    def __init__(self):
        super().__init__(application_id="org.ignis.OOBE",
                         flags=Gio.ApplicationFlags.FLAGS_NONE)
        self.connect("activate", self._on_activate)
        self._step = 0   # 0=welcome 1=language 2=timezone 3=wifi 4=done
        self._sel_lang = LANGUAGES[0]
        self._sel_tz   = TIMEZONES[0]

    def _on_activate(self, app):
        css = Gtk.CssProvider()
        css.load_from_data(CSS)
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), css,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        self.win = Adw.ApplicationWindow(application=app)
        self.win.set_title("IgnisOS 설정")
        self.win.set_default_size(680, 520)
        self.win.set_resizable(False)
        self.win.add_css_class("oobe-win")

        self._outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.win.set_content(self._outer)

        self._render_step()
        self.win.present()

    def _render_step(self):
        while child := self._outer.get_first_child():
            self._outer.remove(child)

        # 진행 점 표시
        dot_box = Gtk.Box(spacing=8, halign=Gtk.Align.CENTER,
                         margin_top=20, margin_bottom=0)
        STEPS = 4  # welcome/lang/tz/wifi
        for i in range(STEPS):
            dot = Gtk.Label(label="")
            dot.set_size_request(10, 10)
            dot.add_css_class("step-dot")
            if i < self._step:
                dot.add_css_class("step-dot-done")
            elif i == self._step:
                dot.add_css_class("step-dot-active")
            else:
                dot.add_css_class("step-dot-pending")
            dot_box.append(dot)
        self._outer.append(dot_box)

        # 콘텐츠
        scroll = Gtk.ScrolledWindow(vexpand=True)
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL,
                       spacing=0, halign=Gtk.Align.CENTER,
                       valign=Gtk.Align.CENTER, vexpand=True,
                       margin_start=60, margin_end=60,
                       margin_top=20, margin_bottom=20)
        scroll.set_child(inner)
        self._outer.append(scroll)

        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        card.add_css_class("oobe-card")
        inner.append(card)

        if self._step == 0:
            self._build_welcome(card)
        elif self._step == 1:
            self._build_language(card)
        elif self._step == 2:
            self._build_timezone(card)
        elif self._step == 3:
            self._build_wifi(card)
        elif self._step >= 4:
            self._build_done(card)

    # ── 0. 환영 ────────────────────────────────────
    def _build_welcome(self, box):
        logo = Gtk.Label()
        logo.set_markup('<span size="56000">🔥</span>')
        logo.set_halign(Gtk.Align.CENTER)
        box.append(logo)

        title = Gtk.Label(label="IgnisOS에 오신 것을 환영합니다")
        title.add_css_class("oobe-title")
        title.set_halign(Gtk.Align.CENTER)
        box.append(title)

        sub = Gtk.Label(label="몇 가지 기본 설정을 완료하면 바로 시작할 수 있어요")
        sub.add_css_class("oobe-subtitle")
        sub.set_halign(Gtk.Align.CENTER)
        box.append(sub)

        btn = Gtk.Button(label="시작하기 →")
        btn.add_css_class("oobe-next")
        btn.set_halign(Gtk.Align.CENTER)
        btn.connect("clicked", lambda *_: self._next())
        box.append(btn)

    # ── 1. 언어 ────────────────────────────────────
    def _build_language(self, box):
        title = Gtk.Label(label="🌐  언어를 선택하세요")
        title.add_css_class("oobe-step-title")
        box.append(title)

        sub = Gtk.Label(label="Select your language / 언어 선택 / 言語を選択")
        sub.add_css_class("oobe-step-desc")
        box.append(sub)

        scroll = Gtk.ScrolledWindow()
        scroll.set_size_request(-1, 220)
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        lb = Gtk.ListBox()
        lb.add_css_class("lang-list")
        lb.set_selection_mode(Gtk.SelectionMode.SINGLE)
        scroll.set_child(lb)

        for i, (flag, name, locale, kb) in enumerate(LANGUAGES):
            row = Gtk.ListBoxRow()
            row.add_css_class("lang-row")
            row_box = Gtk.Box(spacing=10)
            row_box.append(Gtk.Label(label=flag))
            row_box.append(Gtk.Label(label=name, xalign=0, hexpand=True))
            row.set_child(row_box)
            lb._data = getattr(lb, "_data", [])
            lb._data.append((flag, name, locale, kb))
            lb.append(row)
            if i == 0:
                lb.select_row(row)

        lb.connect("row-selected", self._on_lang_select)
        box.append(scroll)

        self._lang_lb = lb
        self._add_nav(box, skip=True)

    def _on_lang_select(self, lb, row):
        if row and hasattr(lb, "_data"):
            self._sel_lang = lb._data[row.get_index()]

    # ── 2. 시간대 ──────────────────────────────────
    def _build_timezone(self, box):
        title = Gtk.Label(label="🕐  시간대를 선택하세요")
        title.add_css_class("oobe-step-title")
        box.append(title)

        sub = Gtk.Label(label="Select your timezone")
        sub.add_css_class("oobe-step-desc")
        box.append(sub)

        scroll = Gtk.ScrolledWindow()
        scroll.set_size_request(-1, 260)
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        lb = Gtk.ListBox()
        lb.set_selection_mode(Gtk.SelectionMode.SINGLE)
        scroll.set_child(lb)

        for i, (flag, label, tz) in enumerate(TIMEZONES):
            row = Gtk.ListBoxRow()
            row.add_css_class("wifi-row")
            row_box = Gtk.Box(spacing=10, margin_top=4, margin_bottom=4,
                             margin_start=6, margin_end=6)
            row_box.append(Gtk.Label(label=flag))
            row_box.append(Gtk.Label(label=label, xalign=0, hexpand=True))
            row.set_child(row_box)
            lb.append(row)
            if i == 0:
                lb.select_row(row)

        lb._tz_data = TIMEZONES
        lb.connect("row-selected", self._on_tz_select)
        box.append(scroll)
        self._tz_lb = lb
        self._add_nav(box, skip=True)

    def _on_tz_select(self, lb, row):
        if row and hasattr(lb, "_tz_data"):
            self._sel_tz = lb._tz_data[row.get_index()]

    # ── 3. Wi-Fi ───────────────────────────────────
    def _build_wifi(self, box):
        title = Gtk.Label(label="📶  Wi-Fi 연결")
        title.add_css_class("oobe-step-title")
        box.append(title)

        sub = Gtk.Label(label="Connect to a Wi-Fi network (optional)")
        sub.add_css_class("oobe-step-desc")
        box.append(sub)

        self.wifi_list = Gtk.ListBox()
        self.wifi_list.set_selection_mode(Gtk.SelectionMode.SINGLE)

        scroll = Gtk.ScrolledWindow()
        scroll.set_size_request(-1, 180)
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_child(self.wifi_list)
        box.append(scroll)

        self._load_wifi()

        btn_box = Gtk.Box(spacing=8)
        refresh = Gtk.Button(label="🔄 새로고침")
        refresh.add_css_class("oobe-back")
        refresh.connect("clicked", lambda *_: self._load_wifi())
        btn_box.append(refresh)

        connect = Gtk.Button(label="🔗 연결")
        connect.add_css_class("oobe-next")
        connect.connect("clicked", self._connect_wifi)
        btn_box.append(connect)
        box.append(btn_box)

        self._add_nav(box, skip=True, skip_label="건너뛰기")

    def _load_wifi(self):
        while child := self.wifi_list.get_first_child():
            self.wifi_list.remove(child)

        networks = run("nmcli -t -f SSID,SIGNAL,SECURITY dev wifi list 2>/dev/null | head -12")
        if not networks:
            row = Gtk.ListBoxRow()
            row.set_child(Gtk.Label(label="Wi-Fi 네트워크를 찾을 수 없습니다",
                                   margin_top=12, margin_bottom=12))
            self.wifi_list.append(row)
            return

        for line in networks.splitlines():
            parts = line.split(":")
            if not parts[0]:
                continue
            ssid   = parts[0]
            signal = parts[1] if len(parts) > 1 else "?"
            sec    = parts[2] if len(parts) > 2 else ""
            icon = "📶" if int(signal or "0") > 60 else ("📡" if int(signal or "0") > 30 else "〰️")
            lock = "🔒" if sec and sec not in ("", "--") else "🔓"

            row = Gtk.ListBoxRow()
            row.add_css_class("wifi-row")
            row._ssid = ssid
            box = Gtk.Box(spacing=8, margin_top=5, margin_bottom=5,
                         margin_start=8, margin_end=8)
            box.append(Gtk.Label(label=f"{icon} {ssid}", xalign=0, hexpand=True))
            box.append(Gtk.Label(label=f"{lock} {signal}%", xalign=1))
            row.set_child(box)
            self.wifi_list.append(row)

    def _connect_wifi(self, *_):
        row = self.wifi_list.get_selected_row()
        if not row or not hasattr(row, "_ssid"):
            return
        ssid = row._ssid

        # 비밀번호 입력 다이얼로그
        dialog = Adw.MessageDialog(transient_for=self.win,
                                   heading=f"'{ssid}' 연결",
                                   body="Wi-Fi 비밀번호를 입력하세요 (공개망이면 비워두세요):")
        entry = Gtk.Entry()
        entry.set_input_purpose(Gtk.InputPurpose.PASSWORD)
        entry.set_visibility(False)
        dialog.set_extra_child(entry)
        dialog.add_response("cancel", "취소")
        dialog.add_response("connect", "연결")
        dialog.set_default_response("connect")

        def on_response(d, r):
            if r == "connect":
                pw = entry.get_text()
                if pw:
                    run(f"nmcli dev wifi connect '{ssid}' password '{pw}'", capture=False)
                else:
                    run(f"nmcli dev wifi connect '{ssid}'", capture=False)
        dialog.connect("response", on_response)
        dialog.present()

    # ── 4. 완료 ────────────────────────────────────
    def _build_done(self, box):
        logo = Gtk.Label()
        logo.set_markup('<span size="56000">✅</span>')
        logo.set_halign(Gtk.Align.CENTER)
        box.append(logo)

        title = Gtk.Label(label="설정 완료!")
        title.add_css_class("oobe-title")
        title.set_halign(Gtk.Align.CENTER)
        box.append(title)

        # 선택 내용 요약
        _, lang_name, _, _ = self._sel_lang
        _, tz_label, _     = self._sel_tz
        sub = Gtk.Label(label=f"언어: {lang_name}  ·  시간대: {tz_label}")
        sub.add_css_class("oobe-subtitle")
        sub.set_halign(Gtk.Align.CENTER)
        box.append(sub)

        sub2 = Gtk.Label(label="IgnisOS가 준비됐습니다. 즐겁게 사용하세요 🔥")
        sub2.add_css_class("oobe-step-desc")
        sub2.set_halign(Gtk.Align.CENTER)
        box.append(sub2)

        btn = Gtk.Button(label="🔥  IgnisOS 시작")
        btn.add_css_class("oobe-next")
        btn.set_halign(Gtk.Align.CENTER)
        btn.connect("clicked", self._finish)
        box.append(btn)

    # ── 네비게이션 ──────────────────────────────────
    def _add_nav(self, box, skip=False, skip_label="나중에"):
        nav = Gtk.Box(spacing=8, halign=Gtk.Align.END, margin_top=8)

        if skip:
            skip_btn = Gtk.Button(label=skip_label)
            skip_btn.add_css_class("oobe-skip")
            skip_btn.connect("clicked", lambda *_: self._next())
            nav.append(skip_btn)

        if self._step > 0:
            back = Gtk.Button(label="← 뒤로")
            back.add_css_class("oobe-back")
            back.connect("clicked", lambda *_: self._prev())
            nav.append(back)

        nxt = Gtk.Button(label="다음 →")
        nxt.add_css_class("oobe-next")
        nxt.connect("clicked", lambda *_: self._next())
        nav.append(nxt)

        box.append(nav)

    def _next(self):
        self._apply_current()
        self._step += 1
        self._render_step()

    def _prev(self):
        self._step = max(0, self._step - 1)
        self._render_step()

    def _apply_current(self):
        """현재 스텝 설정 적용"""
        if self._step == 1:
            _, _, locale, kb = self._sel_lang
            run(f"localectl set-locale LANG={locale}", capture=False)
            run(f"localectl set-keymap {kb}", capture=False)
        elif self._step == 2:
            _, _, tz = self._sel_tz
            run(f"timedatectl set-timezone {tz}", capture=False)
            run("timedatectl set-ntp true", capture=False)

    def _finish(self, *_):
        """OOBE 완료 — 플래그 파일 생성 후 종료"""
        os.makedirs(os.path.dirname(OOBE_DONE_FILE), exist_ok=True)
        with open(OOBE_DONE_FILE, "w") as f:
            _, lang_name, locale, _ = self._sel_lang
            _, tz_label, tz = self._sel_tz
            json.dump({"lang": locale, "tz": tz, "completed": True}, f)
        self.quit()


def should_run_oobe():
    return not os.path.exists(OOBE_DONE_FILE)


def main():
    if not should_run_oobe():
        return
    app = OOBE()
    app.run([])


if __name__ == "__main__":
    main()
