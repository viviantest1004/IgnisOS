#!/usr/bin/env python3
"""IgnisOS 아카이브 관리자 — zip/tar/gz 압축/해제"""
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GLib, Gdk, Gio
import os, subprocess, threading

CSS = b"""
.arc-win { background: #0d0d1f; }
.arc-toolbar {
    background: rgba(10,10,20,0.95);
    border-bottom: 1px solid rgba(232,93,4,0.25);
    padding: 6px 10px;
}
.arc-toolbar button {
    background: rgba(232,93,4,0.15); border: 1px solid rgba(232,93,4,0.35);
    border-radius: 8px; color: #fb923c;
    padding: 6px 14px; font-size: 13px;
}
.arc-toolbar button:hover { background: rgba(232,93,4,0.3); }
.arc-row label { font-size: 13px; color: #e2e8f0; padding: 6px 10px; }
.arc-status {
    background: rgba(10,10,20,0.95);
    border-top: 1px solid rgba(255,255,255,0.07);
    padding: 4px 12px; font-size: 12px; color: #64748b;
}
"""

class ArchiveManager(Adw.Application):
    def __init__(self):
        super().__init__(application_id="org.ignis.Archive",
                         flags=Gio.ApplicationFlags.FLAGS_NONE)
        self.connect("activate", self._activate)

    def _activate(self, app):
        css = Gtk.CssProvider()
        css.load_from_data(CSS)
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        self.win = Adw.ApplicationWindow(application=app)
        self.win.set_title("아카이브 관리자")
        self.win.set_default_size(640, 500)
        self.win.add_css_class("arc-win")

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.win.set_content(vbox)

        # 툴바
        toolbar = Gtk.Box(spacing=6)
        toolbar.add_css_class("arc-toolbar")
        for label, cb in [
            ("📂 아카이브 열기", self._open_archive),
            ("📦 압축하기", self._compress),
            ("📤 압축 해제", self._extract),
        ]:
            b = Gtk.Button(label=label)
            b.connect("clicked", cb)
            toolbar.append(b)
        vbox.append(toolbar)

        # 파일 목록
        scroll = Gtk.ScrolledWindow(vexpand=True)
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.listbox = Gtk.ListBox()
        self.listbox.set_selection_mode(Gtk.SelectionMode.MULTIPLE)
        scroll.set_child(self.listbox)
        vbox.append(scroll)

        # 상태바
        self.status = Gtk.Label(label="아카이브를 열어보세요", xalign=0)
        self.status.add_css_class("arc-status")
        vbox.append(self.status)

        self._archive_path = None
        self.win.present()

    def _open_archive(self, *_):
        dialog = Gtk.FileDialog()
        f = Gtk.FileFilter()
        f.set_name("아카이브")
        for pat in ["*.zip","*.tar","*.tar.gz","*.tgz","*.tar.bz2","*.tar.xz","*.7z","*.rar"]:
            f.add_pattern(pat)
        filters = Gio.ListStore.new(Gtk.FileFilter)
        filters.append(f)
        dialog.set_filters(filters)
        dialog.open(self.win, None, self._on_open, None)

    def _on_open(self, dialog, result, _):
        try:
            f = dialog.open_finish(result)
            self._archive_path = f.get_path()
            self._list_archive()
        except Exception:
            pass

    def _list_archive(self):
        if not self._archive_path:
            return
        while row := self.listbox.get_first_child():
            self.listbox.remove(row)
        path = self._archive_path
        try:
            if path.endswith('.zip'):
                out = subprocess.check_output(["unzip", "-l", path]).decode()
                lines = out.strip().splitlines()[3:-2]
                entries = [l.split(None, 3)[-1] for l in lines if l.strip()]
            else:
                out = subprocess.check_output(["tar", "-tf", path]).decode()
                entries = out.strip().splitlines()

            for entry in entries:
                row = Gtk.ListBoxRow()
                row.add_css_class("arc-row")
                ext = os.path.splitext(entry)[1]
                icon = {"":  "📁", ".py": "🐍", ".txt": "📄",
                        ".jpg": "🖼️", ".png": "🖼️", ".mp3": "🎵",
                        ".mp4": "🎬", ".pdf": "📕"}.get(ext.lower(), "📄")
                lbl = Gtk.Label(label=f"{icon}  {entry}", xalign=0)
                lbl.add_css_class("arc-row")
                row.set_child(lbl)
                self.listbox.append(row)

            name = os.path.basename(path)
            self.status.set_text(f"{name}  |  {len(entries)}개 파일")
            self.win.set_title(f"아카이브 — {name}")
        except Exception as e:
            self.status.set_text(f"오류: {e}")

    def _extract(self, *_):
        if not self._archive_path:
            return
        dialog = Gtk.FileDialog()
        dialog.select_folder(self.win, None, self._on_extract_dest, None)

    def _on_extract_dest(self, dialog, result, _):
        try:
            dest = dialog.select_folder_finish(result).get_path()
            path = self._archive_path
            self.status.set_text("압축 해제 중...")
            def do_extract():
                try:
                    if path.endswith('.zip'):
                        subprocess.run(["unzip", "-o", path, "-d", dest], check=True)
                    else:
                        subprocess.run(["tar", "-xf", path, "-C", dest], check=True)
                    GLib.idle_add(self.status.set_text, f"압축 해제 완료: {dest}")
                except Exception as e:
                    GLib.idle_add(self.status.set_text, f"오류: {e}")
            threading.Thread(target=do_extract, daemon=True).start()
        except Exception:
            pass

    def _compress(self, *_):
        dialog = Gtk.FileDialog()
        dialog.open_multiple(self.win, None, self._on_compress_files, None)

    def _on_compress_files(self, dialog, result, _):
        try:
            files = [f.get_path() for f in dialog.open_multiple_finish(result)]
            if not files:
                return
            save_dialog = Gtk.FileDialog()
            save_dialog.save(self.win, None, lambda d, r, _: self._do_compress(d, r, files), None)
        except Exception:
            pass

    def _do_compress(self, dialog, result, files):
        try:
            out_path = dialog.save_finish(result).get_path()
            if not out_path.endswith('.zip'):
                out_path += '.zip'
            self.status.set_text("압축 중...")
            def do_compress():
                try:
                    subprocess.run(["zip", "-r", out_path] + files, check=True)
                    GLib.idle_add(self.status.set_text, f"압축 완료: {out_path}")
                except Exception as e:
                    GLib.idle_add(self.status.set_text, f"오류: {e}")
            threading.Thread(target=do_compress, daemon=True).start()
        except Exception:
            pass


def main():
    ArchiveManager().run([])

if __name__ == "__main__":
    main()
