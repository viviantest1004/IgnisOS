#!/usr/bin/env python3
"""IgnisOS 작업 관리자 — CPU/메모리/프로세스 모니터"""
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GLib, Gdk, Gio
import subprocess, threading, os

CSS = b"""
.tm-win { background: #0d0d1f; }
.tm-header {
    background: rgba(10,10,20,0.95);
    border-bottom: 1px solid rgba(232,93,4,0.25);
    padding: 8px 16px;
}
.tm-stat-card {
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 14px; padding: 14px 18px;
}
.tm-stat-title { font-size: 12px; color: #64748b; }
.tm-stat-value { font-size: 24px; font-weight: 700; color: #f1f5f9; }
.tm-stat-bar {
    background: rgba(255,255,255,0.08);
    border-radius: 4px; min-height: 6px;
}
.tm-col-header {
    font-size: 12px; font-weight: 600; color: #64748b;
    padding: 6px 8px; border-bottom: 1px solid rgba(255,255,255,0.07);
}
.tm-row { border-bottom: 1px solid rgba(255,255,255,0.04); }
.tm-row label { font-size: 13px; color: #e2e8f0; padding: 6px 8px; }
.kill-btn {
    background: rgba(239,68,68,0.12); border: 1px solid rgba(239,68,68,0.3);
    border-radius: 6px; color: #f87171; padding: 2px 8px; font-size: 12px;
}
.kill-btn:hover { background: rgba(239,68,68,0.25); }
"""

def read_file(path, default="0"):
    try:
        with open(path) as f:
            return f.read().strip()
    except Exception:
        return default

class TaskManager(Adw.Application):
    def __init__(self):
        super().__init__(application_id="org.ignis.TaskManager",
                         flags=Gio.ApplicationFlags.FLAGS_NONE)
        self.connect("activate", self._activate)

    def _activate(self, app):
        css = Gtk.CssProvider()
        css.load_from_data(CSS)
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), css,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        self.win = Adw.ApplicationWindow(application=app)
        self.win.set_title("작업 관리자")
        self.win.set_default_size(800, 620)
        self.win.add_css_class("tm-win")

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.win.set_content(vbox)

        # 상단 요약
        header = Gtk.Box(spacing=12, margin_top=16, margin_bottom=8,
                         margin_start=16, margin_end=16)

        self.cpu_lbl = Gtk.Label(label="0%")
        self.cpu_lbl.add_css_class("tm-stat-value")
        self.mem_lbl = Gtk.Label(label="0%")
        self.mem_lbl.add_css_class("tm-stat-value")
        self.cpu_bar = Gtk.ProgressBar()
        self.mem_bar = Gtk.ProgressBar()

        for title, val_lbl, bar in [
            ("CPU 사용률", self.cpu_lbl, self.cpu_bar),
            ("메모리 사용률", self.mem_lbl, self.mem_bar),
        ]:
            card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6,
                           hexpand=True)
            card.add_css_class("tm-stat-card")
            t = Gtk.Label(label=title, xalign=0)
            t.add_css_class("tm-stat-title")
            card.append(t)
            card.append(val_lbl)
            card.append(bar)
            header.append(card)

        # 업타임
        self.uptime_lbl = Gtk.Label(label="")
        self.uptime_lbl.add_css_class("tm-stat-value")
        uptime_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6,
                               hexpand=True)
        uptime_card.add_css_class("tm-stat-card")
        ut = Gtk.Label(label="업타임", xalign=0)
        ut.add_css_class("tm-stat-title")
        uptime_card.append(ut)
        uptime_card.append(self.uptime_lbl)
        header.append(uptime_card)

        vbox.append(header)

        # 툴바
        toolbar = Gtk.Box(spacing=8, margin_start=16, margin_end=16,
                          margin_bottom=8)
        refresh_btn = Gtk.Button(label="🔄 새로고침")
        refresh_btn.connect("clicked", lambda *_: self._refresh())
        toolbar.append(refresh_btn)
        self.search = Gtk.SearchEntry()
        self.search.set_placeholder_text("프로세스 검색...")
        self.search.set_hexpand(True)
        self.search.connect("search-changed", lambda *_: self._refresh())
        toolbar.append(self.search)
        vbox.append(toolbar)

        # 프로세스 목록
        scroll = Gtk.ScrolledWindow(vexpand=True)
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_margin_start(16); scroll.set_margin_end(16)
        scroll.set_margin_bottom(16)

        self.list_box = Gtk.ListBox()
        self.list_box.set_selection_mode(Gtk.SelectionMode.NONE)

        # 헤더
        col_header = Gtk.Box()
        for text, expand in [("PID", False),("프로세스", True),
                               ("CPU%", False),("메모리", False),("", False)]:
            lbl = Gtk.Label(label=text, xalign=0, hexpand=expand,
                           width_chars=8 if not expand else -1)
            lbl.add_css_class("tm-col-header")
            col_header.append(lbl)
        self.list_box.prepend(Gtk.ListBoxRow())

        scroll.set_child(self.list_box)
        vbox.append(scroll)

        self._prev_cpu = None
        self._refresh()
        GLib.timeout_add(2000, self._auto_refresh)
        self.win.present()

    def _get_cpu(self):
        try:
            with open("/proc/stat") as f:
                line = f.readline().split()
            vals = list(map(int, line[1:]))
            idle = vals[3]
            total = sum(vals)
            if self._prev_cpu:
                p_idle, p_total = self._prev_cpu
                d_idle = idle - p_idle
                d_total = total - p_total
                pct = 100 * (1 - d_idle / d_total) if d_total else 0
            else:
                pct = 0
            self._prev_cpu = (idle, total)
            return pct
        except Exception:
            return 0

    def _get_mem(self):
        try:
            info = {}
            with open("/proc/meminfo") as f:
                for line in f:
                    k, v = line.split(":")
                    info[k.strip()] = int(v.split()[0])
            total = info["MemTotal"]
            avail = info.get("MemAvailable", info.get("MemFree", 0))
            used = total - avail
            return used / total * 100, used // 1024, total // 1024
        except Exception:
            return 0, 0, 0

    def _get_uptime(self):
        try:
            with open("/proc/uptime") as f:
                secs = float(f.read().split()[0])
            h = int(secs // 3600)
            m = int((secs % 3600) // 60)
            return f"{h}시간 {m}분"
        except Exception:
            return "N/A"

    def _get_procs(self, query=""):
        try:
            out = subprocess.check_output(
                ["ps", "aux", "--sort=-%cpu"],
                stderr=subprocess.DEVNULL).decode()
            procs = []
            for line in out.strip().splitlines()[1:]:
                parts = line.split(None, 10)
                if len(parts) < 11: continue
                pid, cpu, mem, cmd = parts[1], parts[2], parts[3], parts[10][:40]
                if query and query.lower() not in cmd.lower(): continue
                procs.append((pid, cmd, cpu, mem))
            return procs[:50]
        except Exception:
            return []

    def _refresh(self):
        cpu_pct = self._get_cpu()
        mem_pct, mem_used, mem_total = self._get_mem()

        self.cpu_lbl.set_text(f"{cpu_pct:.1f}%")
        self.cpu_bar.set_fraction(min(cpu_pct / 100, 1.0))
        self.mem_lbl.set_text(f"{mem_pct:.1f}%  ({mem_used}MB / {mem_total}MB)")
        self.mem_bar.set_fraction(min(mem_pct / 100, 1.0))
        self.uptime_lbl.set_text(self._get_uptime())

        while row := self.list_box.get_first_child():
            self.list_box.remove(row)

        query = self.search.get_text() if hasattr(self, 'search') else ""
        for pid, cmd, cpu, mem in self._get_procs(query):
            row = Gtk.ListBoxRow()
            row.add_css_class("tm-row")
            box = Gtk.Box(spacing=4)
            for text, expand in [(pid, False),(cmd, True),(f"{cpu}%", False),
                                  (f"{int(float(mem) * (os.sysconf('SC_PAGE_SIZE') if False else 1)//1024+1)}KB", False)]:
                lbl = Gtk.Label(label=text, xalign=0, hexpand=expand,
                               ellipsize=3, width_chars=8 if not expand else -1)
                lbl.add_css_class("tm-row")
                box.append(lbl)
            kill = Gtk.Button(label="종료")
            kill.add_css_class("kill-btn")
            kill.connect("clicked", lambda *_, p=pid: self._kill(p))
            box.append(kill)
            row.set_child(box)
            self.list_box.append(row)

    def _auto_refresh(self):
        self._refresh()
        return True

    def _kill(self, pid):
        try:
            subprocess.Popen(["kill", pid])
            GLib.timeout_add(500, self._refresh)
        except Exception:
            pass


def main():
    TaskManager().run([])

if __name__ == "__main__":
    main()
