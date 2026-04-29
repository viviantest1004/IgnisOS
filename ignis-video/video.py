#!/usr/bin/env python3
"""IgnisOS 동영상 플레이어"""
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GLib, Gdk, Gio
import os, sys, subprocess
sys.path.insert(0, '/usr/share/ignis/ignis-i18n')
try:
    from i18n import t
except ImportError:
    def t(k): return k

CSS = b"""
.video-win { background: #000; }
.video-ctrl {
    background: rgba(0,0,0,0.85);
    border-top: 1px solid rgba(255,255,255,0.1);
    padding: 8px 12px;
}
.video-ctrl button {
    background: rgba(232,93,4,0.2); border: 1px solid rgba(232,93,4,0.4);
    border-radius: 8px; color: #fb923c;
    padding: 6px 16px; font-size: 13px;
}
.video-ctrl button:hover { background: rgba(232,93,4,0.4); }
.video-title { font-size: 13px; color: #94a3b8; padding: 4px 12px; }
"""

class VideoPlayer(Adw.Application):
    def __init__(self):
        super().__init__(application_id="org.ignis.Video",
                         flags=Gio.ApplicationFlags.FLAGS_NONE)
        self.connect("activate", self._activate)
        self._proc = None

    def _activate(self, app):
        css = Gtk.CssProvider()
        css.load_from_data(CSS)
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        self.win = Adw.ApplicationWindow(application=app)
        self.win.set_title(t('app_video'))
        self.win.set_default_size(800, 520)
        self.win.add_css_class("video-win")

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.win.set_content(vbox)

        # 영상 영역 (플레이스홀더)
        self.video_area = Gtk.Label()
        self.video_area.set_markup(
            '<span font="48" foreground="#1e293b">🎬</span>\n'
            f'<span foreground="#334155" font="14">{t("video_hint")}</span>')
        self.video_area.set_justify(Gtk.Justification.CENTER)
        self.video_area.set_vexpand(True)
        vbox.append(self.video_area)

        # 현재 파일명
        self.title_lbl = Gtk.Label(label="", xalign=0)
        self.title_lbl.add_css_class("video-title")
        vbox.append(self.title_lbl)

        # 컨트롤
        ctrl = Gtk.Box(spacing=8)
        ctrl.add_css_class("video-ctrl")
        for key, cb in [
            ('video_open', self._open),
            ('video_play', self._play),
            ('video_stop', self._stop),
        ]:
            b = Gtk.Button(label=t(key))
            b.connect("clicked", cb)
            ctrl.append(b)
        vbox.append(ctrl)

        if len(sys.argv) > 1 and os.path.exists(sys.argv[1]):
            self._launch(sys.argv[1])

        self.win.present()

    def _open(self, *_):
        dialog = Gtk.FileDialog()
        f = Gtk.FileFilter()
        f.set_name(t('video_filter'))
        for pat in ["*.mp4","*.mkv","*.avi","*.mov","*.webm","*.flv","*.wmv","*.m4v"]:
            f.add_pattern(pat)
        filters = Gio.ListStore.new(Gtk.FileFilter)
        filters.append(f)
        dialog.set_filters(filters)
        dialog.open(self.win, None, self._on_open, None)

    def _on_open(self, dialog, result, _):
        try:
            f = dialog.open_finish(result)
            self._launch(f.get_path())
        except Exception:
            pass

    def _launch(self, path):
        self._stop()
        name = os.path.basename(path)
        self.title_lbl.set_text(name)
        self.win.set_title(f"{t('app_video')} — {name}")
        try:
            self._proc = subprocess.Popen(
                ["ffplay", "-window_title", name, path],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except FileNotFoundError:
            try:
                self._proc = subprocess.Popen(
                    ["mpv", path],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except FileNotFoundError:
                self.title_lbl.set_text("ffplay / mpv required")

    def _play(self, *_):
        pass

    def _stop(self, *_):
        if self._proc:
            self._proc.terminate()
            self._proc = None


def main():
    VideoPlayer().run(sys.argv[:1])

if __name__ == "__main__":
    main()
