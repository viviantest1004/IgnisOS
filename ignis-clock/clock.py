#!/usr/bin/env python3
"""IgnisOS 시계 — 시계 + 타이머 + 스톱워치 + 알람"""
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GLib, Gdk, Gio
import datetime, threading

CSS = b"""
.clock-win { background: #0d0d1f; }
.clock-face {
    font-size: 72px; font-weight: 800;
    color: #f1f5f9; letter-spacing: -2px;
    font-family: 'Ubuntu', monospace;
}
.clock-date { font-size: 16px; color: #94a3b8; }
.clock-tab {
    background: transparent; border: none;
    color: #94a3b8; padding: 8px 24px; font-size: 14px;
    border-bottom: 2px solid transparent;
    transition: color 0.15s, border-color 0.15s;
}
.clock-tab.active { color: #e85d04; border-bottom-color: #e85d04; }
.timer-display {
    font-size: 56px; font-weight: 700;
    color: #f1f5f9; font-family: monospace;
}
.ctrl-btn {
    background: rgba(232,93,4,0.15); border: 1px solid rgba(232,93,4,0.4);
    border-radius: 50px; color: #fb923c;
    padding: 12px 32px; font-size: 15px; font-weight: 600;
    transition: background 0.15s, transform 0.1s;
}
.ctrl-btn:hover { background: rgba(232,93,4,0.3); transform: scale(1.04); }
.ctrl-btn.danger {
    background: rgba(239,68,68,0.12); border-color: rgba(239,68,68,0.35);
    color: #f87171;
}
.alarm-row { background: rgba(255,255,255,0.04); border-radius: 12px; padding: 14px 18px; }
"""

class ClockApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id="org.ignis.Clock",
                         flags=Gio.ApplicationFlags.FLAGS_NONE)
        self.connect("activate", self._activate)
        self._stopwatch_running = False
        self._stopwatch_elapsed = 0.0
        self._timer_running = False
        self._timer_remaining = 0
        self._alarms = []

    def _activate(self, app):
        css = Gtk.CssProvider()
        css.load_from_data(CSS)
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), css,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        self.win = Adw.ApplicationWindow(application=app)
        self.win.set_title("시계")
        self.win.set_default_size(440, 560)
        self.win.add_css_class("clock-win")

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.win.set_content(vbox)

        # 탭 바
        tab_bar = Gtk.Box(halign=Gtk.Align.CENTER, spacing=0)
        tab_bar.set_margin_top(12)
        self._pages = {}
        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
        self.stack.set_vexpand(True)

        for key, label in [("clock","🕐 시계"),("stopwatch","⏱ 스톱워치"),
                            ("timer","⏳ 타이머"),("alarm","🔔 알람")]:
            btn = Gtk.Button(label=label)
            btn.add_css_class("clock-tab")
            btn.connect("clicked", lambda _, k=key: self._show_page(k))
            tab_bar.append(btn)
            self._pages[key] = btn

        vbox.append(tab_bar)
        vbox.append(self.stack)

        self.stack.add_named(self._make_clock_page(), "clock")
        self.stack.add_named(self._make_stopwatch_page(), "stopwatch")
        self.stack.add_named(self._make_timer_page(), "timer")
        self.stack.add_named(self._make_alarm_page(), "alarm")

        self._show_page("clock")
        GLib.timeout_add(1000, self._tick_clock)
        self.win.present()

    def _show_page(self, key):
        self.stack.set_visible_child_name(key)
        for k, btn in self._pages.items():
            if k == key: btn.add_css_class("active")
            else: btn.remove_css_class("active")

    # ── 시계 ──
    def _make_clock_page(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8,
                      halign=Gtk.Align.CENTER, valign=Gtk.Align.CENTER)
        self.clock_lbl = Gtk.Label()
        self.clock_lbl.add_css_class("clock-face")
        self.date_lbl = Gtk.Label()
        self.date_lbl.add_css_class("clock-date")
        box.append(self.clock_lbl)
        box.append(self.date_lbl)
        self._update_clock_lbl()
        return box

    def _update_clock_lbl(self):
        now = datetime.datetime.now()
        self.clock_lbl.set_text(now.strftime("%H:%M:%S"))
        self.date_lbl.set_text(now.strftime("%Y년 %m월 %d일 %A"))

    def _tick_clock(self):
        self._update_clock_lbl()
        self._check_alarms()
        return True

    # ── 스톱워치 ──
    def _make_stopwatch_page(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20,
                      halign=Gtk.Align.CENTER, valign=Gtk.Align.CENTER)
        self.sw_lbl = Gtk.Label(label="00:00.00")
        self.sw_lbl.add_css_class("timer-display")
        box.append(self.sw_lbl)

        btns = Gtk.Box(spacing=12, halign=Gtk.Align.CENTER)
        self.sw_start_btn = Gtk.Button(label="▶ 시작")
        self.sw_start_btn.add_css_class("ctrl-btn")
        self.sw_start_btn.connect("clicked", self._sw_toggle)
        reset_btn = Gtk.Button(label="↺ 초기화")
        reset_btn.add_css_class("ctrl-btn danger")
        reset_btn.connect("clicked", self._sw_reset)
        btns.append(self.sw_start_btn)
        btns.append(reset_btn)
        box.append(btns)
        return box

    def _sw_toggle(self, *_):
        self._stopwatch_running = not self._stopwatch_running
        self.sw_start_btn.set_label("⏸ 일시정지" if self._stopwatch_running else "▶ 시작")
        if self._stopwatch_running:
            self._sw_last = datetime.datetime.now()
            GLib.timeout_add(50, self._sw_tick)

    def _sw_tick(self):
        if not self._stopwatch_running:
            return False
        now = datetime.datetime.now()
        self._stopwatch_elapsed += (now - self._sw_last).total_seconds()
        self._sw_last = now
        m = int(self._stopwatch_elapsed // 60)
        s = self._stopwatch_elapsed % 60
        self.sw_lbl.set_text(f"{m:02d}:{s:05.2f}")
        return True

    def _sw_reset(self, *_):
        self._stopwatch_running = False
        self._stopwatch_elapsed = 0
        self.sw_lbl.set_text("00:00.00")
        self.sw_start_btn.set_label("▶ 시작")

    # ── 타이머 ──
    def _make_timer_page(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20,
                      halign=Gtk.Align.CENTER, valign=Gtk.Align.CENTER)

        self.timer_lbl = Gtk.Label(label="00:00:00")
        self.timer_lbl.add_css_class("timer-display")
        box.append(self.timer_lbl)

        spin_box = Gtk.Box(spacing=8, halign=Gtk.Align.CENTER)
        self.t_h = Gtk.SpinButton.new_with_range(0, 23, 1)
        self.t_m = Gtk.SpinButton.new_with_range(0, 59, 1)
        self.t_s = Gtk.SpinButton.new_with_range(0, 59, 1)
        for w, lbl in [(self.t_h,"시"),(self.t_m,"분"),(self.t_s,"초")]:
            spin_box.append(w)
            spin_box.append(Gtk.Label(label=lbl))
        box.append(spin_box)

        btns = Gtk.Box(spacing=12, halign=Gtk.Align.CENTER)
        self.timer_btn = Gtk.Button(label="▶ 시작")
        self.timer_btn.add_css_class("ctrl-btn")
        self.timer_btn.connect("clicked", self._timer_toggle)
        stop_btn = Gtk.Button(label="■ 정지")
        stop_btn.add_css_class("ctrl-btn danger")
        stop_btn.connect("clicked", self._timer_stop)
        btns.append(self.timer_btn)
        btns.append(stop_btn)
        box.append(btns)
        return box

    def _timer_toggle(self, *_):
        if not self._timer_running:
            secs = int(self.t_h.get_value())*3600 + int(self.t_m.get_value())*60 + int(self.t_s.get_value())
            if secs == 0: return
            self._timer_remaining = secs
            self._timer_running = True
            self.timer_btn.set_label("⏸ 일시정지")
            GLib.timeout_add(1000, self._timer_tick)
        else:
            self._timer_running = False
            self.timer_btn.set_label("▶ 계속")

    def _timer_tick(self):
        if not self._timer_running: return False
        self._timer_remaining -= 1
        h = self._timer_remaining // 3600
        m = (self._timer_remaining % 3600) // 60
        s = self._timer_remaining % 60
        self.timer_lbl.set_text(f"{h:02d}:{m:02d}:{s:02d}")
        if self._timer_remaining <= 0:
            self._timer_running = False
            self.timer_btn.set_label("▶ 시작")
            self._notify("타이머 완료!", "설정한 시간이 완료됐습니다.")
            return False
        return True

    def _timer_stop(self, *_):
        self._timer_running = False
        self._timer_remaining = 0
        self.timer_lbl.set_text("00:00:00")
        self.timer_btn.set_label("▶ 시작")

    # ── 알람 ──
    def _make_alarm_page(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12,
                      margin_top=20, margin_start=24, margin_end=24)

        add_box = Gtk.Box(spacing=8)
        self.alarm_h = Gtk.SpinButton.new_with_range(0, 23, 1)
        self.alarm_m = Gtk.SpinButton.new_with_range(0, 59, 1)
        add_box.append(Gtk.Label(label="알람 시간:"))
        add_box.append(self.alarm_h)
        add_box.append(Gtk.Label(label=":"))
        add_box.append(self.alarm_m)
        add_btn = Gtk.Button(label="➕ 추가")
        add_btn.add_css_class("ctrl-btn")
        add_btn.connect("clicked", self._add_alarm)
        add_box.append(add_btn)
        box.append(add_box)

        self.alarm_list = Gtk.ListBox()
        self.alarm_list.set_selection_mode(Gtk.SelectionMode.NONE)
        box.append(self.alarm_list)
        return box

    def _add_alarm(self, *_):
        h = int(self.alarm_h.get_value())
        m = int(self.alarm_m.get_value())
        self._alarms.append({"h": h, "m": m, "active": True})
        row = Gtk.ListBoxRow()
        row_box = Gtk.Box(spacing=8, margin_top=8, margin_bottom=8,
                          margin_start=8, margin_end=8)
        row_box.add_css_class("alarm-row")
        lbl = Gtk.Label(label=f"🔔 {h:02d}:{m:02d}", xalign=0, hexpand=True)
        sw = Gtk.Switch(active=True)
        del_btn = Gtk.Button(label="🗑")
        del_btn.connect("clicked", lambda *_, r=row: self.alarm_list.remove(r))
        row_box.append(lbl)
        row_box.append(sw)
        row_box.append(del_btn)
        row.set_child(row_box)
        self.alarm_list.append(row)

    def _check_alarms(self):
        now = datetime.datetime.now()
        for a in self._alarms:
            if a["active"] and a["h"] == now.hour and a["m"] == now.minute and now.second == 0:
                self._notify("알람!", f"{a['h']:02d}:{a['m']:02d} 알람입니다.")

    def _notify(self, title, body):
        try:
            import subprocess
            subprocess.Popen(["notify-send", title, body])
        except Exception:
            pass
        dialog = Gtk.AlertDialog()
        dialog.set_message(title)
        dialog.set_detail(body)
        dialog.show(self.win)


def main():
    ClockApp().run([])

if __name__ == "__main__":
    main()
