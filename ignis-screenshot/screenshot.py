#!/usr/bin/env python3
"""IgnisOS 스크린샷 & 화면 녹화 — Print Screen 단축키 지원"""
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GLib, Gdk, Gio
import subprocess, sys
sys.path.insert(0, '/usr/share/ignis/ignis-i18n')
try:
    from i18n import t
except ImportError:
    def t(k): return k, os, datetime, threading

SAVE_DIR = os.path.expanduser("~/Pictures/Screenshots")
RECORD_DIR = os.path.expanduser("~/Videos/Recordings")

CSS = b"""
.ss-win { background: #0d0d1f; }
.ss-card {
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 16px; padding: 20px;
}
.ss-title { font-size: 16px; font-weight: 700; color: #f1f5f9; margin-bottom: 4px; }
.ss-desc { font-size: 13px; color: #64748b; }
.ss-btn {
    background: linear-gradient(135deg, #e85d04, #fb923c);
    border: none; border-radius: 10px; color: white;
    padding: 12px 24px; font-size: 14px; font-weight: 700;
}
.ss-btn:hover { opacity: 0.88; }
.ss-btn.danger {
    background: linear-gradient(135deg, #dc2626, #f87171);
}
.ss-status { font-size: 12px; color: #64748b; }
.ss-kbd {
    background: rgba(255,255,255,0.08);
    border: 1px solid rgba(255,255,255,0.15);
    border-radius: 6px; padding: 2px 8px;
    font-family: monospace; font-size: 12px; color: #e2e8f0;
}
"""

class ScreenshotApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id="org.ignis.Screenshot",
                         flags=Gio.ApplicationFlags.FLAGS_NONE)
        self.connect("activate", self._activate)
        self._rec_proc = None
        self._recording = False
        self._delay = 3

    def _activate(self, app):
        css = Gtk.CssProvider()
        css.load_from_data(CSS)
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        self.win = Adw.ApplicationWindow(application=app)
        self.win.set_title("스크린샷 & 화면 녹화")
        self.win.set_default_size(440, 540)
        self.win.add_css_class("ss-win")

        # 키보드 단축키 (Print Screen)
        ctrl = Gtk.EventControllerKey()
        ctrl.connect("key-pressed", self._on_key)
        self.win.add_controller(ctrl)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16,
                       margin_start=20, margin_end=20,
                       margin_top=20, margin_bottom=20)
        self.win.set_content(vbox)

        # 단축키 안내
        kb_box = Gtk.Box(spacing=8, halign=Gtk.Align.CENTER)
        for key, desc in [("Print Screen","전체 화면"), ("Alt+Print","창 캡처"), ("Shift+Print","영역 선택")]:
            chip = Gtk.Box(spacing=6, margin_start=6, margin_end=6)
            k = Gtk.Label(label=key)
            k.add_css_class("ss-kbd")
            chip.append(k)
            chip.append(Gtk.Label(label=desc))
            kb_box.append(chip)
        vbox.append(kb_box)

        # 전체 스크린샷 카드
        vbox.append(self._make_card(
            "🖥️ 전체 화면 캡처",
            "Print Screen — 전체 화면을 즉시 캡처합니다",
            [("📷 지금 캡처", self._capture_full),
             (f"⏱ {self._delay}초 후 캡처", self._capture_delayed)]
        ))

        # 영역 캡처 카드
        vbox.append(self._make_card(
            "✂️ 영역 선택 캡처",
            "마우스로 영역을 드래그해 캡처합니다",
            [("✂️ 영역 선택", self._capture_area)]
        ))

        # 화면 녹화 카드
        rec_card = self._make_card(
            "🎥 화면 녹화",
            "화면 전체를 MP4로 녹화합니다",
            []
        )
        self.rec_btn = Gtk.Button(label="● 녹화 시작")
        self.rec_btn.add_css_class("ss-btn")
        self.rec_btn.connect("clicked", self._toggle_record)
        rec_card.get_last_child().append(self.rec_btn) if hasattr(rec_card.get_last_child(), 'append') else None
        # 버튼을 카드에 직접 추가
        rec_card.append(self.rec_btn)
        vbox.append(rec_card)

        # 딜레이 설정
        delay_box = Gtk.Box(spacing=8, halign=Gtk.Align.CENTER)
        delay_box.append(Gtk.Label(label="캡처 딜레이:"))
        delay_spin = Gtk.SpinButton.new_with_range(0, 10, 1)
        delay_spin.set_value(self._delay)
        delay_spin.connect("value-changed", lambda w: setattr(self, '_delay', int(w.get_value())))
        delay_box.append(delay_spin)
        delay_box.append(Gtk.Label(label="초"))
        vbox.append(delay_box)

        # 상태 / 저장 경로
        self.status_lbl = Gtk.Label(label=f"저장 위치: {SAVE_DIR}", xalign=0, wrap=True)
        self.status_lbl.add_css_class("ss-status")
        vbox.append(self.status_lbl)

        os.makedirs(SAVE_DIR, exist_ok=True)
        os.makedirs(RECORD_DIR, exist_ok=True)

        self.win.present()

    def _make_card(self, title, desc, buttons):
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        card.add_css_class("ss-card")
        t = Gtk.Label(label=title, xalign=0)
        t.add_css_class("ss-title")
        d = Gtk.Label(label=desc, xalign=0, wrap=True)
        d.add_css_class("ss-desc")
        card.append(t)
        card.append(d)
        btn_box = Gtk.Box(spacing=8)
        for label, cb in buttons:
            btn = Gtk.Button(label=label)
            btn.add_css_class("ss-btn")
            btn.connect("clicked", cb)
            btn_box.append(btn)
        card.append(btn_box)
        return card

    def _on_key(self, ctrl, keyval, keycode, state):
        if keyval == Gdk.KEY_Print:
            if state & Gdk.ModifierType.ALT_MASK:
                self._capture_window()
            elif state & Gdk.ModifierType.SHIFT_MASK:
                self._capture_area()
            else:
                self._capture_full()
            return True
        return False

    def _timestamp(self):
        return datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

    def _capture_full(self, *_):
        self.win.hide()
        GLib.timeout_add(200, self._do_capture_full)

    def _do_capture_full(self):
        path = os.path.join(SAVE_DIR, f"screenshot_{self._timestamp()}.png")
        try:
            subprocess.run(["scrot", path], check=True)
        except FileNotFoundError:
            try:
                subprocess.run(["import", "-window", "root", path], check=True)
            except Exception as e:
                path = f"오류: {e}"
        self.win.present()
        self._set_status(path)
        return False

    def _capture_delayed(self, *_):
        self.status_lbl.set_text(f"{self._delay}초 후 캡처...")
        GLib.timeout_add(self._delay * 1000, self._do_capture_full)

    def _capture_area(self, *_):
        path = os.path.join(SAVE_DIR, f"screenshot_{self._timestamp()}.png")
        try:
            subprocess.Popen(["scrot", "-s", path])
            GLib.timeout_add(500, lambda: self._set_status(path) or False)
        except FileNotFoundError:
            try:
                subprocess.Popen(["gnome-screenshot", "-a", "-f", path])
            except Exception as e:
                self._set_status(f"오류: {e}")

    def _capture_window(self, *_):
        path = os.path.join(SAVE_DIR, f"screenshot_{self._timestamp()}.png")
        try:
            subprocess.run(["scrot", "-u", path], check=True)
            self._set_status(path)
        except FileNotFoundError:
            self._set_status("scrot이 필요합니다: sudo apt install scrot")

    def _toggle_record(self, *_):
        if self._recording:
            self._stop_record()
        else:
            self._start_record()

    def _start_record(self):
        path = os.path.join(RECORD_DIR, f"recording_{self._timestamp()}.mp4")
        try:
            # ffmpeg로 화면 녹화
            display = os.environ.get("DISPLAY", ":0")
            self._rec_proc = subprocess.Popen([
                "ffmpeg", "-y",
                "-f", "x11grab", "-r", "30", "-i", display,
                "-f", "pulse", "-i", "default",
                "-c:v", "libx264", "-preset", "ultrafast",
                "-c:a", "aac", path
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self._recording = True
            self._rec_path = path
            self.rec_btn.set_label("⏹ 녹화 중지")
            self.rec_btn.add_css_class("danger")
            self.status_lbl.set_text(f"녹화 중: {path}")
        except FileNotFoundError:
            self.status_lbl.set_text("ffmpeg이 필요합니다: sudo apt install ffmpeg")

    def _stop_record(self):
        if self._rec_proc:
            self._rec_proc.terminate()
            self._rec_proc = None
        self._recording = False
        self.rec_btn.set_label("● 녹화 시작")
        self.rec_btn.remove_css_class("danger")
        self._set_status(getattr(self, '_rec_path', ''))

    def _set_status(self, path):
        if path and os.path.exists(path):
            self.status_lbl.set_text(f"저장됨: {path}")
        else:
            self.status_lbl.set_text(str(path))


def main():
    ScreenshotApp().run([])

if __name__ == "__main__":
    main()
