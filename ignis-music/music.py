#!/usr/bin/env python3
"""IgnisOS 음악 플레이어"""
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GLib, Gdk, Gio
import os, sys, subprocess, threading

CSS = b"""
.music-win { background: #0d0d1f; }
.music-header {
    background: rgba(10,10,20,0.95);
    border-bottom: 1px solid rgba(232,93,4,0.25);
    padding: 12px 16px;
}
.track-title { font-size: 18px; font-weight: 700; color: #f1f5f9; }
.track-artist { font-size: 13px; color: #94a3b8; }
.ctrl-btn {
    background: rgba(232,93,4,0.15);
    border: 1px solid rgba(232,93,4,0.4);
    border-radius: 50px; color: #fb923c;
    padding: 10px 24px; font-size: 14px; font-weight: 600;
}
.ctrl-btn:hover { background: rgba(232,93,4,0.3); }
.play-btn {
    background: linear-gradient(135deg, #e85d04, #fb923c);
    border: none; border-radius: 50px; color: white;
    padding: 14px 36px; font-size: 16px; font-weight: 700;
}
.play-btn:hover { opacity: 0.9; }
.playlist-row label { font-size: 13px; color: #e2e8f0; padding: 8px 12px; }
.playlist-row.active label { color: #fb923c; }
"""

class MusicPlayer(Adw.Application):
    def __init__(self):
        super().__init__(application_id="org.ignis.Music",
                         flags=Gio.ApplicationFlags.FLAGS_NONE)
        self.connect("activate", self._activate)
        self._playlist = []
        self._index = 0
        self._proc = None
        self._playing = False

    def _activate(self, app):
        css = Gtk.CssProvider()
        css.load_from_data(CSS)
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        self.win = Adw.ApplicationWindow(application=app)
        self.win.set_title("음악 플레이어")
        self.win.set_default_size(480, 640)
        self.win.add_css_class("music-win")

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.win.set_content(vbox)

        # 헤더 (현재 트랙)
        header = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        header.add_css_class("music-header")
        header.set_margin_bottom(8)

        self.album_art = Gtk.Label(label="🎵")
        self.album_art.set_markup('<span font="64">🎵</span>')
        header.append(self.album_art)

        self.title_lbl = Gtk.Label(label="트랙 없음")
        self.title_lbl.add_css_class("track-title")
        header.append(self.title_lbl)

        self.artist_lbl = Gtk.Label(label="파일을 추가하세요")
        self.artist_lbl.add_css_class("track-artist")
        header.append(self.artist_lbl)

        # 진행바
        self.progress = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 1)
        self.progress.set_draw_value(False)
        self.progress.set_hexpand(True)
        self.progress.set_margin_top(8)
        header.append(self.progress)

        vbox.append(header)

        # 컨트롤
        ctrl = Gtk.Box(spacing=12, halign=Gtk.Align.CENTER,
                       margin_top=16, margin_bottom=16)
        self.prev_btn = Gtk.Button(label="⏮")
        self.prev_btn.add_css_class("ctrl-btn")
        self.prev_btn.connect("clicked", self._prev)

        self.play_btn = Gtk.Button(label="▶ 재생")
        self.play_btn.add_css_class("play-btn")
        self.play_btn.connect("clicked", self._toggle)

        self.next_btn = Gtk.Button(label="⏭")
        self.next_btn.add_css_class("ctrl-btn")
        self.next_btn.connect("clicked", self._next)

        ctrl.append(self.prev_btn)
        ctrl.append(self.play_btn)
        ctrl.append(self.next_btn)
        vbox.append(ctrl)

        # 볼륨
        vol_box = Gtk.Box(spacing=8, halign=Gtk.Align.CENTER, margin_bottom=12)
        vol_box.append(Gtk.Label(label="🔈"))
        self.vol = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 1)
        self.vol.set_value(80)
        self.vol.set_size_request(180, -1)
        self.vol.set_draw_value(False)
        vol_box.append(self.vol)
        vol_box.append(Gtk.Label(label="🔊"))
        vbox.append(vol_box)

        # 플레이리스트 툴바
        pl_bar = Gtk.Box(spacing=8, margin_start=12, margin_end=12, margin_bottom=6)
        add_btn = Gtk.Button(label="➕ 파일 추가")
        add_btn.add_css_class("ctrl-btn")
        add_btn.connect("clicked", self._add_files)
        clear_btn = Gtk.Button(label="🗑 전체 삭제")
        clear_btn.add_css_class("ctrl-btn")
        clear_btn.connect("clicked", self._clear)
        pl_bar.append(add_btn)
        pl_bar.append(clear_btn)
        vbox.append(pl_bar)

        # 플레이리스트
        scroll = Gtk.ScrolledWindow(vexpand=True)
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_margin_start(12)
        scroll.set_margin_end(12)
        scroll.set_margin_bottom(12)
        self.listbox = Gtk.ListBox()
        self.listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.listbox.connect("row-activated", self._on_row_activated)
        scroll.set_child(self.listbox)
        vbox.append(scroll)

        self.win.present()

    def _add_files(self, *_):
        dialog = Gtk.FileDialog()
        f = Gtk.FileFilter()
        f.set_name("오디오")
        for pat in ["*.mp3","*.flac","*.wav","*.ogg","*.m4a","*.aac","*.opus"]:
            f.add_pattern(pat)
        filters = Gio.ListStore.new(Gtk.FileFilter)
        filters.append(f)
        dialog.set_filters(filters)
        dialog.open_multiple(self.win, None, self._on_add, None)

    def _on_add(self, dialog, result, _):
        try:
            files = dialog.open_multiple_finish(result)
            for f in files:
                path = f.get_path()
                self._playlist.append(path)
                row = Gtk.ListBoxRow()
                row.add_css_class("playlist-row")
                lbl = Gtk.Label(label=os.path.basename(path), xalign=0)
                row.set_child(lbl)
                self.listbox.append(row)
            if len(self._playlist) == len(files):
                self._index = 0
                self._update_info()
        except Exception:
            pass

    def _on_row_activated(self, listbox, row):
        self._index = row.get_index()
        self._play()

    def _update_info(self):
        if not self._playlist:
            return
        name = os.path.basename(self._playlist[self._index])
        base = os.path.splitext(name)[0]
        parts = base.split(" - ", 1)
        if len(parts) == 2:
            self.artist_lbl.set_text(parts[0])
            self.title_lbl.set_text(parts[1])
        else:
            self.title_lbl.set_text(base)
            self.artist_lbl.set_text("")
        self.win.set_title(f"음악 — {name}")

    def _play(self):
        self._stop_proc()
        if not self._playlist:
            return
        path = self._playlist[self._index]
        self._update_info()
        try:
            self._proc = subprocess.Popen(
                ["ffplay", "-nodisp", "-autoexit", "-volume",
                 str(int(self.vol.get_value())), path],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self._playing = True
            self.play_btn.set_label("⏸ 일시정지")
            threading.Thread(target=self._watch_proc, daemon=True).start()
        except FileNotFoundError:
            # ffplay 없으면 aplay 시도
            try:
                self._proc = subprocess.Popen(
                    ["aplay", path],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                self._playing = True
                self.play_btn.set_label("⏸ 일시정지")
            except Exception:
                self.artist_lbl.set_text("ffplay 또는 aplay가 필요합니다")

    def _watch_proc(self):
        if self._proc:
            self._proc.wait()
            GLib.idle_add(self._on_track_end)

    def _on_track_end(self):
        if self._playing:
            self._next()

    def _toggle(self, *_):
        if self._playing:
            self._stop_proc()
        else:
            self._play()

    def _stop_proc(self):
        if self._proc:
            self._proc.terminate()
            self._proc = None
        self._playing = False
        self.play_btn.set_label("▶ 재생")

    def _prev(self, *_):
        if self._playlist:
            self._index = (self._index - 1) % len(self._playlist)
            self._play()

    def _next(self, *_):
        if self._playlist:
            self._index = (self._index + 1) % len(self._playlist)
            self._play()

    def _clear(self, *_):
        self._stop_proc()
        self._playlist = []
        self._index = 0
        while row := self.listbox.get_first_child():
            self.listbox.remove(row)
        self.title_lbl.set_text("트랙 없음")
        self.artist_lbl.set_text("파일을 추가하세요")


def main():
    MusicPlayer().run(sys.argv[:1])

if __name__ == "__main__":
    main()
