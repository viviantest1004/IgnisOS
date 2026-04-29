#!/usr/bin/env python3
"""IgnisOS 캘린더"""
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GLib, Gdk, Gio
import datetime, json, os

DATA_FILE = os.path.expanduser("~/.ignis-calendar.json")

CSS = b"""
.cal-win { background: #0d0d1f; }
.cal-header {
    background: rgba(10,10,20,0.95);
    border-bottom: 1px solid rgba(232,93,4,0.25);
    padding: 12px 16px;
}
.cal-month { font-size: 22px; font-weight: 700; color: #f1f5f9; }
.cal-nav {
    background: rgba(232,93,4,0.15);
    border: 1px solid rgba(232,93,4,0.4);
    border-radius: 8px; color: #fb923c;
    padding: 4px 14px; font-size: 14px;
}
.cal-nav:hover { background: rgba(232,93,4,0.3); }
.day-header { font-size: 12px; font-weight: 600; color: #64748b; padding: 6px; }
.day-btn {
    background: transparent; border: none;
    border-radius: 8px; color: #e2e8f0;
    font-size: 14px; padding: 8px; min-width: 36px;
}
.day-btn:hover { background: rgba(232,93,4,0.15); color: #fb923c; }
.day-btn.today {
    background: rgba(232,93,4,0.25);
    border: 1px solid rgba(232,93,4,0.6);
    color: #fb923c; font-weight: 700;
}
.day-btn.other-month { color: #334155; }
.day-btn.has-event { color: #fb923c; }
.event-row {
    background: rgba(232,93,4,0.1);
    border: 1px solid rgba(232,93,4,0.25);
    border-radius: 10px; padding: 10px 14px; margin: 4px 0;
}
.event-row label { font-size: 13px; color: #f1f5f9; }
"""

class CalendarApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id="org.ignis.Calendar",
                         flags=Gio.ApplicationFlags.FLAGS_NONE)
        self.connect("activate", self._activate)
        self._today = datetime.date.today()
        self._view = datetime.date(self._today.year, self._today.month, 1)
        self._selected = self._today
        self._events = self._load_events()

    def _load_events(self):
        try:
            with open(DATA_FILE) as f:
                return json.load(f)
        except Exception:
            return {}

    def _save_events(self):
        try:
            with open(DATA_FILE, "w") as f:
                json.dump(self._events, f)
        except Exception:
            pass

    def _activate(self, app):
        css = Gtk.CssProvider()
        css.load_from_data(CSS)
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        self.win = Adw.ApplicationWindow(application=app)
        self.win.set_title("캘린더")
        self.win.set_default_size(700, 560)
        self.win.add_css_class("cal-win")

        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.win.set_content(hbox)

        # 왼쪽 캘린더 그리드
        left = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        left.set_size_request(380, -1)

        # 헤더
        header = Gtk.Box(spacing=8)
        header.add_css_class("cal-header")
        prev_btn = Gtk.Button(label="◀")
        prev_btn.add_css_class("cal-nav")
        prev_btn.connect("clicked", lambda *_: self._navigate(-1))
        next_btn = Gtk.Button(label="▶")
        next_btn.add_css_class("cal-nav")
        next_btn.connect("clicked", lambda *_: self._navigate(1))
        self.month_lbl = Gtk.Label(hexpand=True)
        self.month_lbl.add_css_class("cal-month")
        today_btn = Gtk.Button(label="오늘")
        today_btn.add_css_class("cal-nav")
        today_btn.connect("clicked", self._go_today)
        header.append(prev_btn)
        header.append(self.month_lbl)
        header.append(today_btn)
        header.append(next_btn)
        left.append(header)

        # 그리드
        self.grid = Gtk.Grid()
        self.grid.set_margin_start(8)
        self.grid.set_margin_end(8)
        self.grid.set_margin_top(8)
        self.grid.set_margin_bottom(8)
        self.grid.set_row_spacing(2)
        self.grid.set_column_spacing(2)
        left.append(self.grid)
        hbox.append(left)

        # 오른쪽 이벤트 패널
        right = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8,
                        margin_start=16, margin_end=16, margin_top=16,
                        vexpand=True, hexpand=True)
        self.sel_lbl = Gtk.Label(xalign=0)
        self.sel_lbl.add_css_class("cal-month")
        right.append(self.sel_lbl)

        # 이벤트 추가
        add_box = Gtk.Box(spacing=8)
        self.event_entry = Gtk.Entry()
        self.event_entry.set_placeholder_text("새 일정 입력...")
        self.event_entry.set_hexpand(True)
        self.event_entry.connect("activate", self._add_event)
        add_btn = Gtk.Button(label="➕")
        add_btn.add_css_class("cal-nav")
        add_btn.connect("clicked", self._add_event)
        add_box.append(self.event_entry)
        add_box.append(add_btn)
        right.append(add_box)

        scroll = Gtk.ScrolledWindow(vexpand=True)
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.event_list = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        scroll.set_child(self.event_list)
        right.append(scroll)
        hbox.append(right)

        self._render_calendar()
        self._render_events()
        self.win.present()

    def _navigate(self, delta):
        m = self._view.month + delta
        y = self._view.year
        if m > 12: m, y = 1, y + 1
        elif m < 1: m, y = 12, y - 1
        self._view = datetime.date(y, m, 1)
        self._render_calendar()

    def _go_today(self, *_):
        self._today = datetime.date.today()
        self._view = datetime.date(self._today.year, self._today.month, 1)
        self._selected = self._today
        self._render_calendar()
        self._render_events()

    def _render_calendar(self):
        self.month_lbl.set_text(self._view.strftime("%Y년 %m월"))
        while self.grid.get_first_child():
            self.grid.remove(self.grid.get_first_child())

        for col, day in enumerate(["일","월","화","수","목","금","토"]):
            lbl = Gtk.Label(label=day)
            lbl.add_css_class("day-header")
            self.grid.attach(lbl, col, 0, 1, 1)

        first_day = self._view.weekday()  # 0=Mon
        first_col = (first_day + 1) % 7   # 0=Sun

        import calendar
        days_in_month = calendar.monthrange(self._view.year, self._view.month)[1]
        prev_month_days = calendar.monthrange(
            self._view.year if self._view.month > 1 else self._view.year - 1,
            self._view.month - 1 if self._view.month > 1 else 12)[1]

        col, row = first_col, 1
        for d in range(first_col - 1, -1, -1):
            self._add_day_btn(prev_month_days - d, row, col - (first_col - 1 - d) - 1,
                              other_month=True)

        for d in range(1, days_in_month + 1):
            date = datetime.date(self._view.year, self._view.month, d)
            self._add_day_btn(d, row, col, date=date)
            col += 1
            if col > 6:
                col = 0
                row += 1

        extra = 1
        while col <= 6:
            self._add_day_btn(extra, row, col, other_month=True)
            col += 1
            extra += 1

    def _add_day_btn(self, day, row, col, date=None, other_month=False):
        btn = Gtk.Button(label=str(day))
        btn.add_css_class("day-btn")
        if other_month:
            btn.add_css_class("other-month")
        elif date:
            key = str(date)
            if date == self._today:
                btn.add_css_class("today")
            if key in self._events and self._events[key]:
                btn.add_css_class("has-event")
            btn.connect("clicked", lambda _, d=date: self._select_day(d))
        self.grid.attach(btn, col, row, 1, 1)

    def _select_day(self, date):
        self._selected = date
        self._render_calendar()
        self._render_events()

    def _render_events(self):
        while self.event_list.get_first_child():
            self.event_list.remove(self.event_list.get_first_child())
        self.sel_lbl.set_text(self._selected.strftime("%Y년 %m월 %d일"))
        key = str(self._selected)
        for i, ev in enumerate(self._events.get(key, [])):
            row = Gtk.Box(spacing=8)
            row.add_css_class("event-row")
            lbl = Gtk.Label(label=f"• {ev}", xalign=0, hexpand=True)
            lbl.add_css_class("event-row")
            del_btn = Gtk.Button(label="🗑")
            del_btn.connect("clicked", lambda _, k=key, idx=i: self._del_event(k, idx))
            row.append(lbl)
            row.append(del_btn)
            self.event_list.append(row)

    def _add_event(self, *_):
        text = self.event_entry.get_text().strip()
        if not text:
            return
        key = str(self._selected)
        self._events.setdefault(key, []).append(text)
        self._save_events()
        self.event_entry.set_text("")
        self._render_calendar()
        self._render_events()

    def _del_event(self, key, idx):
        try:
            self._events[key].pop(idx)
            if not self._events[key]:
                del self._events[key]
            self._save_events()
            self._render_calendar()
            self._render_events()
        except Exception:
            pass


def main():
    CalendarApp().run([])

if __name__ == "__main__":
    main()
