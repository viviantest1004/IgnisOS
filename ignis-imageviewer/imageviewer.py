#!/usr/bin/env python3
"""IgnisOS 이미지 뷰어"""
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GLib, Gdk, Gio
import os, sys
sys.path.insert(0, '/usr/share/ignis/ignis-i18n')
try:
    from i18n import t
except ImportError:
    def t(k): return k

CSS = b"""
.iv-win { background: #0d0d1f; }
.iv-toolbar {
    background: rgba(10,10,20,0.95);
    border-bottom: 1px solid rgba(232,93,4,0.25);
    padding: 4px 8px;
}
.iv-toolbar button {
    background: transparent; border: none;
    color: #f1f5f9; padding: 4px 10px;
    border-radius: 6px; font-size: 13px;
}
.iv-toolbar button:hover { background: rgba(232,93,4,0.2); }
.iv-statusbar {
    background: rgba(10,10,20,0.95);
    border-top: 1px solid rgba(255,255,255,0.07);
    padding: 3px 12px; font-size: 12px; color: #64748b;
}
.iv-empty { font-size: 48px; color: #334155; }
"""

class ImageViewer(Adw.Application):
    def __init__(self):
        super().__init__(application_id="org.ignis.ImageViewer",
                         flags=Gio.ApplicationFlags.FLAGS_NONE)
        self.connect("activate", self._activate)
        self._files = []
        self._index = 0
        self._zoom = 1.0

    def _activate(self, app):
        css = Gtk.CssProvider()
        css.load_from_data(CSS)
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        self.win = Adw.ApplicationWindow(application=app)
        self.win.set_title(t('app_imageviewer'))
        self.win.set_default_size(900, 680)
        self.win.add_css_class("iv-win")

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.win.set_content(vbox)

        # 툴바
        toolbar = Gtk.Box(spacing=4)
        toolbar.add_css_class("iv-toolbar")
        for key, cb in [
            ('iv_open',   self._open),
            ('iv_prev',   self._prev),
            ('iv_next',   self._next),
        ]:
            b = Gtk.Button(label=t(key))
            b.connect("clicked", cb)
            toolbar.append(b)

        zoom_in = Gtk.Button(label="🔍+")
        zoom_in.connect("clicked", self._zoom_in)
        toolbar.append(zoom_in)

        zoom_out = Gtk.Button(label="🔍-")
        zoom_out.connect("clicked", self._zoom_out)
        toolbar.append(zoom_out)

        reset_zoom = Gtk.Button(label="↺")
        reset_zoom.connect("clicked", self._reset_zoom)
        toolbar.append(reset_zoom)

        rotate_btn = Gtk.Button(label=t('iv_rotate'))
        rotate_btn.connect("clicked", self._rotate)
        toolbar.append(rotate_btn)

        toolbar.append(Gtk.Box(hexpand=True))
        vbox.append(toolbar)

        # 스크롤 뷰
        self.scroll = Gtk.ScrolledWindow(vexpand=True, hexpand=True)
        self.scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)

        self.picture = Gtk.Picture()
        self.picture.set_can_shrink(True)
        self.picture.set_content_fit(Gtk.ContentFit.CONTAIN)

        self.empty_lbl = Gtk.Label(label=t('iv_empty'))
        self.empty_lbl.add_css_class("iv-empty")
        self.empty_lbl.set_justify(Gtk.Justification.CENTER)

        self.stack = Gtk.Stack()
        self.stack.add_named(self.empty_lbl, "empty")
        self.stack.add_named(self.picture, "image")
        self.scroll.set_child(self.stack)
        vbox.append(self.scroll)

        # 상태바
        self.statusbar = Gtk.Label(label=t('iv_no_image'), xalign=0)
        self.statusbar.add_css_class("iv-statusbar")
        vbox.append(self.statusbar)

        self._angle = 0

        # 명령줄 인자로 파일 열기
        if len(sys.argv) > 1 and os.path.exists(sys.argv[1]):
            self._load_path(sys.argv[1])

        self.win.present()

    def _open(self, *_):
        dialog = Gtk.FileDialog()
        f = Gtk.FileFilter()
        f.set_name(t('iv_filter'))
        for pat in ["*.png","*.jpg","*.jpeg","*.gif","*.bmp","*.webp","*.svg","*.tiff"]:
            f.add_pattern(pat)
        filters = Gio.ListStore.new(Gtk.FileFilter)
        filters.append(f)
        dialog.set_filters(filters)
        dialog.open(self.win, None, self._on_open, None)

    def _on_open(self, dialog, result, _):
        try:
            f = dialog.open_finish(result)
            self._load_path(f.get_path())
        except Exception:
            pass

    def _load_path(self, path):
        dirpath = os.path.dirname(path)
        exts = {'.png','.jpg','.jpeg','.gif','.bmp','.webp','.svg','.tiff'}
        self._files = sorted([
            os.path.join(dirpath, f) for f in os.listdir(dirpath)
            if os.path.splitext(f)[1].lower() in exts
        ])
        if path in self._files:
            self._index = self._files.index(path)
        else:
            self._files = [path]
            self._index = 0
        self._show_current()

    def _show_current(self):
        if not self._files:
            self.stack.set_visible_child_name("empty")
            return
        path = self._files[self._index]
        try:
            self.picture.set_filename(path)
            self._zoom = 1.0
            self._angle = 0
            self.stack.set_visible_child_name("image")
            name = os.path.basename(path)
            self.win.set_title(f"{t('app_imageviewer')} — {name}")
            self.statusbar.set_text(
                f"{name}  |  {self._index+1} / {len(self._files)}")
        except Exception as e:
            self.statusbar.set_text(f"{t('error')}: {e}")

    def _prev(self, *_):
        if self._files:
            self._index = (self._index - 1) % len(self._files)
            self._show_current()

    def _next(self, *_):
        if self._files:
            self._index = (self._index + 1) % len(self._files)
            self._show_current()

    def _zoom_in(self, *_):
        self._zoom = min(self._zoom * 1.25, 8.0)
        self._apply_zoom()

    def _zoom_out(self, *_):
        self._zoom = max(self._zoom / 1.25, 0.1)
        self._apply_zoom()

    def _reset_zoom(self, *_):
        self._zoom = 1.0
        self.picture.set_content_fit(Gtk.ContentFit.CONTAIN)
        base = self.statusbar.get_text().split(f"  |  {t('iv_zoom_lbl')}")[0]
        self.statusbar.set_text(base)

    def _apply_zoom(self):
        self.picture.set_content_fit(
            Gtk.ContentFit.SCALE_DOWN if self._zoom < 1 else Gtk.ContentFit.FILL)
        base = self.statusbar.get_text().split(f"  |  {t('iv_zoom_lbl')}")[0]
        self.statusbar.set_text(f"{base}  |  {t('iv_zoom_lbl')} {self._zoom*100:.0f}%")

    def _rotate(self, *_):
        self._angle = (self._angle + 90) % 360
        base = self.statusbar.get_text().split(f"  |  {t('iv_rotate_lbl')}")[0]
        self.statusbar.set_text(f"{base}  |  {t('iv_rotate_lbl')} {self._angle}°")


def main():
    ImageViewer().run(sys.argv[:1])

if __name__ == "__main__":
    main()
