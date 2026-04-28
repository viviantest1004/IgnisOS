#!/usr/bin/env python3
"""IgnisOS 메모장 — 탭 지원 텍스트 편집기"""
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GLib, Gdk, Gio, Pango
import os, subprocess

CSS = b"""
.notepad-win { background: #0d0d1f; }
.notepad-toolbar {
    background: rgba(10,10,20,0.95);
    border-bottom: 1px solid rgba(232,93,4,0.25);
    padding: 4px 8px;
}
.notepad-toolbar button {
    background: transparent; border: none;
    color: #f1f5f9; padding: 4px 10px;
    border-radius: 6px; font-size: 13px;
    transition: background 0.15s ease;
}
.notepad-toolbar button:hover { background: rgba(232,93,4,0.2); }
.tab-bar {
    background: rgba(5,5,15,0.95);
    border-bottom: 1px solid rgba(255,255,255,0.07);
}
.tab-btn {
    background: transparent; border: none; border-radius: 0;
    color: #94a3b8; padding: 6px 16px; font-size: 13px;
    border-bottom: 2px solid transparent;
    transition: color 0.15s ease, border-color 0.15s ease;
}
.tab-btn.active { color: #f1f5f9; border-bottom-color: #e85d04; }
.tab-btn:hover { color: #f1f5f9; }
.tab-close {
    background: transparent; border: none; color: #64748b;
    padding: 0 4px; font-size: 11px; border-radius: 4px;
}
.tab-close:hover { color: #f87171; background: rgba(239,68,68,0.15); }
.notepad-view {
    background: #0d0d1f; color: #e2e8f0;
    font-family: 'Ubuntu Mono', 'Courier New', monospace;
    font-size: 14px; padding: 16px;
}
.notepad-statusbar {
    background: rgba(10,10,20,0.95);
    border-top: 1px solid rgba(255,255,255,0.07);
    padding: 2px 12px;
    font-size: 12px; color: #64748b;
}
"""

class Tab:
    def __init__(self, path=None):
        self.path = path
        self.modified = False
        self.title = os.path.basename(path) if path else "새 문서"

        self.scroll = Gtk.ScrolledWindow(vexpand=True, hexpand=True)
        self.view = Gtk.TextView()
        self.view.add_css_class("notepad-view")
        self.view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.buffer = self.view.get_buffer()
        self.scroll.set_child(self.view)

        if path and os.path.exists(path):
            try:
                with open(path) as f:
                    self.buffer.set_text(f.read())
            except Exception:
                pass

        self.buffer.connect("changed", self._on_changed)

    def _on_changed(self, *_):
        self.modified = True


class Notepad(Adw.Application):
    def __init__(self):
        super().__init__(application_id="org.ignis.Notepad",
                         flags=Gio.ApplicationFlags.FLAGS_NONE)
        self.connect("activate", self._activate)
        self._tabs = []
        self._current = -1

    def _activate(self, app):
        css = Gtk.CssProvider()
        css.load_from_data(CSS)
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), css,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        self.win = Adw.ApplicationWindow(application=app)
        self.win.set_title("메모장")
        self.win.set_default_size(800, 600)
        self.win.add_css_class("notepad-win")

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.win.set_content(vbox)

        # 툴바
        toolbar = Gtk.Box(spacing=4)
        toolbar.add_css_class("notepad-toolbar")
        for label, cb in [
            ("📄 새로 만들기", self._new_tab),
            ("📂 열기",        self._open_file),
            ("💾 저장",        self._save),
            ("💾 다른 이름 저장", self._save_as),
        ]:
            b = Gtk.Button(label=label)
            b.connect("clicked", cb)
            toolbar.append(b)

        toolbar.append(Gtk.Box(hexpand=True))

        # 글꼴 크기
        for icon, delta in [("A-", -1), ("A+", 1)]:
            b = Gtk.Button(label=icon)
            b.connect("clicked", lambda _, d=delta: self._font_size(d))
            toolbar.append(b)

        vbox.append(toolbar)

        # 탭 바
        self.tab_bar = Gtk.Box(spacing=0)
        self.tab_bar.add_css_class("tab-bar")
        tab_scroll = Gtk.ScrolledWindow()
        tab_scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.NEVER)
        tab_scroll.set_child(self.tab_bar)
        tab_scroll.set_size_request(-1, 36)
        vbox.append(tab_scroll)

        # 콘텐츠 영역
        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.stack.set_transition_duration(120)
        vbox.append(self.stack)

        # 상태바
        self.statusbar = Gtk.Label(label="줄 1, 열 1", xalign=0)
        self.statusbar.add_css_class("notepad-statusbar")
        vbox.append(self.statusbar)

        self._font_size_val = 14
        self._new_tab()
        self.win.present()

    def _new_tab(self, *_, path=None):
        tab = Tab(path)
        self._tabs.append(tab)

        # 탭 버튼
        tab_box = Gtk.Box(spacing=4)
        btn = Gtk.Button()
        btn.add_css_class("tab-btn")
        lbl = Gtk.Label(label=tab.title)
        close = Gtk.Button(label="✕")
        close.add_css_class("tab-close")
        tab_box.append(lbl)
        tab_box.append(close)
        btn.set_child(tab_box)

        idx = len(self._tabs) - 1
        btn.connect("clicked", lambda *_, i=idx: self._switch_tab(i))
        close.connect("clicked", lambda *_, i=idx: self._close_tab(i))

        tab._tab_btn = btn
        tab._tab_lbl = lbl
        self.tab_bar.append(btn)

        name = f"tab{idx}"
        self.stack.add_named(tab.scroll, name)

        tab.buffer.connect("changed", lambda *_: self._update_status(tab))
        tab.view.get_buffer().connect("mark-set", lambda *_: self._update_status(tab))

        self._switch_tab(idx)

    def _switch_tab(self, idx):
        if idx < 0 or idx >= len(self._tabs):
            return
        self._current = idx
        self.stack.set_visible_child_name(f"tab{idx}")
        for i, t in enumerate(self._tabs):
            if hasattr(t, '_tab_btn'):
                if i == idx:
                    t._tab_btn.add_css_class("active")
                else:
                    t._tab_btn.remove_css_class("active")
        self._update_status(self._tabs[idx])

    def _close_tab(self, idx):
        if len(self._tabs) == 1:
            self._new_tab()
        tab = self._tabs.pop(idx)
        self.stack.remove(tab.scroll)
        self.tab_bar.remove(tab._tab_btn)
        self._switch_tab(min(idx, len(self._tabs) - 1))

    def _update_status(self, tab):
        buf = tab.buffer
        it = buf.get_iter_at_mark(buf.get_insert())
        line = it.get_line() + 1
        col = it.get_line_offset() + 1
        chars = buf.get_char_count()
        modified = " ●" if tab.modified else ""
        self.statusbar.set_text(f"줄 {line}, 열 {col}  |  {chars}자{modified}")

    def _save(self, *_):
        if self._current < 0:
            return
        tab = self._tabs[self._current]
        if tab.path:
            self._write(tab)
        else:
            self._save_as()

    def _save_as(self, *_):
        if self._current < 0:
            return
        dialog = Gtk.FileDialog()
        dialog.save(self.win, None, self._on_save_response, None)

    def _on_save_response(self, dialog, result, _):
        try:
            f = dialog.save_finish(result)
            tab = self._tabs[self._current]
            tab.path = f.get_path()
            tab.title = os.path.basename(tab.path)
            if hasattr(tab, '_tab_lbl'):
                tab._tab_lbl.set_text(tab.title)
            self._write(tab)
        except Exception:
            pass

    def _write(self, tab):
        try:
            buf = tab.buffer
            text = buf.get_text(buf.get_start_iter(), buf.get_end_iter(), True)
            with open(tab.path, "w") as f:
                f.write(text)
            tab.modified = False
            self._update_status(tab)
        except Exception as e:
            print(f"저장 실패: {e}")

    def _open_file(self, *_):
        dialog = Gtk.FileDialog()
        dialog.open(self.win, None, self._on_open_response, None)

    def _on_open_response(self, dialog, result, _):
        try:
            f = dialog.open_finish(result)
            self._new_tab(path=f.get_path())
        except Exception:
            pass

    def _font_size(self, delta):
        self._font_size_val = max(8, min(32, self._font_size_val + delta))
        for tab in self._tabs:
            tab.view.override_font(
                Pango.FontDescription(f"Ubuntu Mono {self._font_size_val}"))


def main():
    Notepad().run([])

if __name__ == "__main__":
    main()
