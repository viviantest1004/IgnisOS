#!/usr/bin/env python3
"""IgnisOS Terminal — 터미널 에뮬레이터"""
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
try:
    gi.require_version('Vte', '3.91')
    from gi.repository import Vte
    HAS_VTE = True
except Exception:
    HAS_VTE = False
from gi.repository import Gtk, Adw, Gdk, Gio, GLib
import subprocess, os

CSS = b"""
.term-win { background: #070714; }
.term-toolbar {
    background: #0d0d1f;
    border-bottom: 1px solid rgba(232,93,4,0.25);
    padding: 4px 8px;
}
.term-tab {
    background: rgba(255,255,255,0.06); border: none;
    border-radius: 6px; color: #94a3b8;
    padding: 4px 12px; font-size: 12px;
}
.term-tab.active { background: rgba(232,93,4,0.2); color: #fb923c; }
.term-tab-add {
    background: transparent; border: none; color: #64748b;
    border-radius: 6px; padding: 4px 8px;
}
.term-tab-add:hover { color: #94a3b8; background: rgba(255,255,255,0.06); }
"""


class TerminalTab(Gtk.Box):
    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        if HAS_VTE:
            self.term = Vte.Terminal()
            self.term.set_size_request(300, 200)
            # 색상 설정
            from gi.repository import Gdk
            bg = Gdk.RGBA()
            bg.parse("#070714")
            fg = Gdk.RGBA()
            fg.parse("#e2e8f0")
            palette = [
                "#0d0d1f", "#ef4444", "#22c55e", "#f59e0b",
                "#3b82f6", "#a855f7", "#06b6d4", "#e2e8f0",
                "#334155", "#f87171", "#4ade80", "#fbbf24",
                "#60a5fa", "#c084fc", "#22d3ee", "#f8fafc",
            ]
            colors = []
            for hex_c in palette:
                c = Gdk.RGBA()
                c.parse(hex_c)
                colors.append(c)
            self.term.set_colors(fg, bg, colors)
            self.term.set_font_desc(
                __import__("gi.repository.Pango", fromlist=["FontDescription"]).FontDescription("Monospace 12"))
            self.term.set_scrollback_lines(5000)

            shell = os.environ.get("SHELL", "/bin/bash")
            self.term.spawn_async(
                Vte.PtyFlags.DEFAULT, os.environ.get("HOME", "/"),
                [shell], None, GLib.SpawnFlags.DO_NOT_REAP_CHILD,
                None, None, -1, None, None)

            scroll = Gtk.ScrolledWindow(vexpand=True)
            scroll.set_child(self.term)
            self.append(scroll)
        else:
            self._build_fallback()

    def _build_fallback(self):
        """VTE 없을 때 폴백 — subprocess 기반 간이 터미널"""
        self._input_history = []
        self._hist_idx = 0
        self._cwd = os.path.expanduser("~")

        scroll = Gtk.ScrolledWindow(vexpand=True)
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        self.output = Gtk.TextView()
        self.output.set_editable(False)
        self.output.set_cursor_visible(False)
        self.output.set_monospace(True)
        self.output.set_wrap_mode(Gtk.WrapMode.CHAR)

        buf = self.output.get_buffer()
        buf.insert(buf.get_end_iter(),
                   "IgnisOS Terminal\n"
                   "─────────────────────────────────────────\n"
                   "참고: python3-vte 패키지 설치 시 완전한 터미널 사용 가능\n\n")
        self._buf = buf
        scroll.set_child(self.output)
        self.append(scroll)

        input_box = Gtk.Box(spacing=4, margin_start=6, margin_end=6, margin_bottom=6)
        self._prompt = Gtk.Label(xalign=0)
        self._update_prompt()
        input_box.append(self._prompt)

        self._entry = Gtk.Entry(hexpand=True)
        self._entry.set_monospace(True)
        self._entry.connect("activate", self._on_cmd)
        self._entry.connect("key-pressed" if hasattr(Gtk.Entry, "connect") else "key-press-event",
                           self._on_key)
        input_box.append(self._entry)
        self.append(input_box)
        self._entry.grab_focus()

    def _update_prompt(self):
        home = os.path.expanduser("~")
        cwd = self._cwd.replace(home, "~")
        self._prompt.set_markup(f'<span color="#22c55e" weight="bold">ignis</span>'
                                f'<span color="#64748b">:</span>'
                                f'<span color="#3b82f6">{cwd}</span>'
                                f'<span color="#a855f7"> ❯ </span>')

    def _on_key(self, entry, keyval, *_):
        if keyval == 65362:  # Up
            if self._hist_idx > 0:
                self._hist_idx -= 1
                entry.set_text(self._input_history[self._hist_idx])
                entry.set_position(-1)
        elif keyval == 65364:  # Down
            if self._hist_idx < len(self._input_history) - 1:
                self._hist_idx += 1
                entry.set_text(self._input_history[self._hist_idx])
            else:
                self._hist_idx = len(self._input_history)
                entry.set_text("")

    def _on_cmd(self, entry):
        cmd = entry.get_text().strip()
        entry.set_text("")
        if not cmd:
            return
        self._input_history.append(cmd)
        self._hist_idx = len(self._input_history)

        # cd 처리
        if cmd.startswith("cd "):
            path = cmd[3:].strip().replace("~", os.path.expanduser("~"))
            try:
                if not os.path.isabs(path):
                    path = os.path.join(self._cwd, path)
                os.chdir(path)
                self._cwd = os.path.realpath(path)
            except Exception as e:
                self._append(f"cd: {e}\n")
            self._update_prompt()
            return
        if cmd == "clear":
            self._buf.set_text("")
            return
        if cmd in ("exit", "quit"):
            self._append("logout\n")
            return

        try:
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True,
                cwd=self._cwd, timeout=30)
            out = result.stdout
            err = result.stderr
            prompt_line = f"$ {cmd}\n"
            self._append(prompt_line)
            if out:
                self._append(out)
            if err:
                self._append(err)
        except subprocess.TimeoutExpired:
            self._append("[타임아웃]\n")
        except Exception as e:
            self._append(f"[오류] {e}\n")

    def _append(self, text):
        end = self._buf.get_end_iter()
        self._buf.insert(end, text)
        self.output.scroll_to_iter(self._buf.get_end_iter(), 0, False, 0, 0)


class IgnisTerminal(Adw.Application):
    def __init__(self):
        super().__init__(application_id="org.ignis.Terminal",
                         flags=Gio.ApplicationFlags.FLAGS_NONE)
        self.connect("activate", self._on_activate)

    def _on_activate(self, app):
        css = Gtk.CssProvider()
        css.load_from_data(CSS)
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), css,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        self.win = Adw.ApplicationWindow(application=app)
        self.win.set_title("터미널")
        self.win.set_default_size(800, 520)
        self.win.add_css_class("term-win")

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.win.set_content(vbox)

        # 탭 바
        toolbar = Gtk.Box(spacing=4)
        toolbar.add_css_class("term-toolbar")
        self.tab_bar = Gtk.Box(spacing=4)
        toolbar.append(self.tab_bar)
        toolbar.append(Gtk.Box(hexpand=True))

        new_tab = Gtk.Button(label="+")
        new_tab.add_css_class("term-tab-add")
        new_tab.connect("clicked", self._add_tab)
        toolbar.append(new_tab)
        vbox.append(toolbar)

        # 탭 컨텐츠
        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        vbox.append(self.stack)

        self._tabs = []
        self._add_tab()
        self.win.present()

    def _add_tab(self, *_):
        idx = len(self._tabs)
        tab = TerminalTab()
        name = f"term{idx}"
        self.stack.add_named(tab, name)
        self._tabs.append((name, tab))

        btn = Gtk.ToggleButton(label=f"터미널 {idx + 1}")
        btn.add_css_class("term-tab")
        btn.connect("clicked", lambda _b, n=name: self.stack.set_visible_child_name(n))
        self.tab_bar.append(btn)

        self.stack.set_visible_child_name(name)
        btn.set_active(True)

        if HAS_VTE and hasattr(tab, "term"):
            tab.term.grab_focus()


def main():
    app = IgnisTerminal()
    app.run([])


if __name__ == "__main__":
    main()
