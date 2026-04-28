#!/usr/bin/env python3
"""
IgnisOS Files — 파일 관리자
복사, 붙여넣기, 이름변경, 이동, 삭제, 새 폴더 등
"""
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, Gdk, Gio, GLib
import os, shutil, subprocess, mimetypes, stat, datetime

CSS = b"""
.files-win { background: #0d0d1f; }
.sidebar-btn {
    background: transparent; border: none;
    color: #cbd5e1; border-radius: 8px;
    padding: 8px 12px; text-align: left;
}
.sidebar-btn:hover { background: rgba(232,93,4,0.15); color: #fff; }
.sidebar-btn.active { background: rgba(232,93,4,0.25); color: #fb923c; }
.file-row { border-radius: 8px; margin: 1px 4px; }
.file-row:hover { background: rgba(255,255,255,0.06); }
.file-row:selected { background: rgba(232,93,4,0.2); }
.toolbar-btn {
    background: rgba(255,255,255,0.07); border: 1px solid rgba(255,255,255,0.1);
    border-radius: 8px; color: #e2e8f0; padding: 4px 10px; font-size: 13px;
}
.toolbar-btn:hover { background: rgba(255,255,255,0.13); }
.path-bar {
    background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1);
    border-radius: 8px; color: #e2e8f0; padding: 5px 12px; font-size: 13px; font-family: monospace;
}
.status-bar { color: #64748b; font-size: 12px; padding: 4px 8px; }
.file-name { color: #f1f5f9; font-size: 13px; }
.file-meta { color: #64748b; font-size: 11px; }
.col-header { color: #94a3b8; font-size: 12px; font-weight: 600; }
"""

PLACES = [
    ("🏠", "홈",      os.path.expanduser("~")),
    ("🖥️", "바탕화면", os.path.expanduser("~/Desktop")),
    ("📄", "문서",     os.path.expanduser("~/Documents")),
    ("⬇️", "다운로드", os.path.expanduser("~/Downloads")),
    ("🎵", "음악",     os.path.expanduser("~/Music")),
    ("🖼️", "사진",     os.path.expanduser("~/Pictures")),
    ("🎬", "동영상",   os.path.expanduser("~/Videos")),
    ("🗑️", "휴지통",  os.path.expanduser("~/.local/share/Trash/files")),
    ("💾", "루트 (/)", "/"),
]

FILE_ICONS = {
    "dir":   "📁",
    "image": "🖼️",
    "video": "🎬",
    "audio": "🎵",
    "text":  "📄",
    "pdf":   "📕",
    "zip":   "🗜️",
    "code":  "💻",
    "exec":  "⚙️",
    "other": "📄",
}


def get_icon(path, is_dir):
    if is_dir:
        return FILE_ICONS["dir"]
    mime, _ = mimetypes.guess_type(path)
    if not mime:
        if os.access(path, os.X_OK):
            return FILE_ICONS["exec"]
        return FILE_ICONS["other"]
    if mime.startswith("image"):  return FILE_ICONS["image"]
    if mime.startswith("video"):  return FILE_ICONS["video"]
    if mime.startswith("audio"):  return FILE_ICONS["audio"]
    if "pdf" in mime:             return FILE_ICONS["pdf"]
    if mime.startswith("text"):   return FILE_ICONS["text"]
    if any(x in mime for x in ("zip", "tar", "gzip", "bzip", "xz", "rar")):
        return FILE_ICONS["zip"]
    if any(x in mime for x in ("python", "javascript", "java", "c", "cpp", "sh")):
        return FILE_ICONS["code"]
    return FILE_ICONS["other"]


def fmt_size(size):
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def fmt_time(ts):
    return datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")


class IgnisFiles(Adw.Application):
    def __init__(self):
        super().__init__(application_id="org.ignis.Files",
                         flags=Gio.ApplicationFlags.FLAGS_NONE)
        self.connect("activate", self._on_activate)
        self._cwd = os.path.expanduser("~")
        self._history = [self._cwd]
        self._hist_idx = 0
        self._clipboard = None   # ("copy"|"cut", [paths])
        self._selected = []
        self._show_hidden = False

    def _on_activate(self, app):
        css = Gtk.CssProvider()
        css.load_from_data(CSS)
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), css,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        self.win = Adw.ApplicationWindow(application=app)
        self.win.set_title("파일")
        self.win.set_default_size(1000, 650)
        self.win.add_css_class("files-win")

        # ── 메인 박스 ────────────────────────────
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.win.set_content(vbox)

        # ── 툴바 ─────────────────────────────────
        toolbar = Gtk.Box(spacing=6, margin_start=10, margin_end=10,
                         margin_top=8, margin_bottom=8)
        vbox.append(toolbar)

        # 뒤로/앞으로/위로
        for label, cb in [("◀", self._go_back), ("▶", self._go_forward), ("↑", self._go_up)]:
            b = Gtk.Button(label=label)
            b.add_css_class("toolbar-btn")
            b.connect("clicked", cb)
            toolbar.append(b)

        # 경로 표시줄
        self.path_entry = Gtk.Entry()
        self.path_entry.add_css_class("path-bar")
        self.path_entry.set_hexpand(True)
        self.path_entry.set_text(self._cwd)
        self.path_entry.connect("activate", self._on_path_enter)
        toolbar.append(self.path_entry)

        # 검색
        self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_placeholder_text("검색...")
        self.search_entry.set_size_request(160, -1)
        self.search_entry.connect("search-changed", self._on_search)
        toolbar.append(self.search_entry)

        # 숨김 파일 토글
        hidden_btn = Gtk.ToggleButton(label="숨김")
        hidden_btn.add_css_class("toolbar-btn")
        hidden_btn.connect("toggled", self._toggle_hidden)
        toolbar.append(hidden_btn)

        # ── 컨텍스트 메뉴 버튼들 ──────────────────
        action_bar = Gtk.Box(spacing=4, margin_start=10, margin_end=10, margin_bottom=6)
        vbox.append(action_bar)

        actions = [
            ("📁 새 폴더",   self._new_folder),
            ("📄 새 파일",   self._new_file),
            ("📋 붙여넣기",  self._paste),
        ]
        for lbl, cb in actions:
            b = Gtk.Button(label=lbl)
            b.add_css_class("toolbar-btn")
            b.connect("clicked", cb)
            action_bar.append(b)

        action_bar.append(Gtk.Box(hexpand=True))

        for lbl, cb in [("📤 열기", self._open_selected),
                        ("✂️ 잘라내기", self._cut),
                        ("📋 복사", self._copy),
                        ("✏️ 이름변경", self._rename),
                        ("🗑️ 삭제", self._delete)]:
            b = Gtk.Button(label=lbl)
            b.add_css_class("toolbar-btn")
            b.connect("clicked", cb)
            action_bar.append(b)

        # ── 분할 뷰 (사이드바 + 파일 목록) ─────────
        paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL, hexpand=True, vexpand=True)
        vbox.append(paned)

        # 사이드바
        sidebar = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2,
                         margin_top=8, margin_bottom=8, margin_start=6, margin_end=6)
        sidebar_scroll = Gtk.ScrolledWindow()
        sidebar_scroll.set_size_request(180, -1)
        sidebar_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        sidebar_scroll.set_child(sidebar)

        lbl_places = Gtk.Label(label="즐겨찾기", xalign=0)
        lbl_places.set_margin_start(8)
        lbl_places.set_markup('<span size="10000" color="#64748b" weight="bold">즐겨찾기</span>')
        sidebar.append(lbl_places)

        for icon, name, path in PLACES:
            btn = Gtk.Button(label=f"{icon}  {name}")
            btn.add_css_class("sidebar-btn")
            p = path
            btn.connect("clicked", lambda _b, p=p: self._navigate(p))
            sidebar.append(btn)

        paned.set_start_child(sidebar_scroll)
        paned.set_position(185)

        # 파일 목록 (컬럼 뷰)
        right = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        # 컬럼 헤더
        hdr = Gtk.Box(spacing=0, margin_start=8, margin_end=8, margin_top=4)
        for lbl, expand in [("이름", True), ("크기", False), ("종류", False), ("수정일", False)]:
            h = Gtk.Label(label=lbl, xalign=0)
            h.add_css_class("col-header")
            h.set_hexpand(expand)
            h.set_size_request(0 if expand else (80 if lbl == "크기" else (100 if lbl == "종류" else 130)), -1)
            hdr.append(h)
        right.append(hdr)

        sep = Gtk.Separator()
        sep.set_margin_top(4)
        right.append(sep)

        # 파일 리스트박스
        scroll = Gtk.ScrolledWindow(hexpand=True, vexpand=True)
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.file_list = Gtk.ListBox()
        self.file_list.set_selection_mode(Gtk.SelectionMode.MULTIPLE)
        self.file_list.connect("row-activated", self._on_row_activated)
        scroll.set_child(self.file_list)
        right.append(scroll)

        # 상태바
        self.status = Gtk.Label(label="", xalign=0)
        self.status.add_css_class("status-bar")
        right.append(self.status)

        paned.set_end_child(right)

        # 우클릭 메뉴
        gesture = Gtk.GestureClick()
        gesture.set_button(3)
        gesture.connect("pressed", self._on_right_click)
        self.file_list.add_controller(gesture)

        self._load_dir(self._cwd)
        self.win.present()

    def _load_dir(self, path):
        if not os.path.isdir(path):
            return
        self._cwd = path
        self.path_entry.set_text(path)
        self.win.set_title(f"파일 — {os.path.basename(path) or path}")

        while row := self.file_list.get_first_child():
            self.file_list.remove(row)

        try:
            entries = os.scandir(path)
            items = sorted(entries, key=lambda e: (not e.is_dir(), e.name.lower()))
        except PermissionError:
            self.status.set_text("⛔ 권한 없음")
            return

        count = 0
        for entry in items:
            if not self._show_hidden and entry.name.startswith("."):
                continue
            row = self._make_row(entry)
            self.file_list.append(row)
            count += 1

        self.status.set_text(f"  항목 {count}개")

    def _make_row(self, entry):
        row = Gtk.ListBoxRow()
        row.add_css_class("file-row")

        box = Gtk.Box(spacing=8, margin_top=5, margin_bottom=5,
                     margin_start=8, margin_end=8)

        is_dir = entry.is_dir(follow_symlinks=False)
        icon = get_icon(entry.path, is_dir)

        ico = Gtk.Label(label=icon)
        ico.set_size_request(24, -1)
        box.append(ico)

        name = Gtk.Label(label=entry.name, xalign=0, hexpand=True, ellipsize=3)
        name.add_css_class("file-name")
        box.append(name)

        try:
            st = entry.stat(follow_symlinks=False)
            size_lbl = Gtk.Label(label="" if is_dir else fmt_size(st.st_size), xalign=1)
            size_lbl.add_css_class("file-meta")
            size_lbl.set_size_request(80, -1)
            box.append(size_lbl)

            kind = "폴더" if is_dir else (entry.name.rsplit(".", 1)[-1].upper() + " 파일"
                                         if "." in entry.name else "파일")
            kind_lbl = Gtk.Label(label=kind, xalign=0)
            kind_lbl.add_css_class("file-meta")
            kind_lbl.set_size_request(100, -1)
            box.append(kind_lbl)

            date_lbl = Gtk.Label(label=fmt_time(st.st_mtime), xalign=0)
            date_lbl.add_css_class("file-meta")
            date_lbl.set_size_request(130, -1)
            box.append(date_lbl)
        except Exception:
            pass

        row.set_child(box)
        row._path = entry.path
        row._is_dir = is_dir
        row._name = entry.name
        return row

    def _on_row_activated(self, lb, row):
        if row._is_dir:
            self._navigate(row._path)
        else:
            self._open_file(row._path)

    def _navigate(self, path):
        if not os.path.isdir(path):
            return
        if self._hist_idx < len(self._history) - 1:
            self._history = self._history[:self._hist_idx + 1]
        self._history.append(path)
        self._hist_idx = len(self._history) - 1
        self._load_dir(path)

    def _go_back(self, *_):
        if self._hist_idx > 0:
            self._hist_idx -= 1
            self._load_dir(self._history[self._hist_idx])

    def _go_forward(self, *_):
        if self._hist_idx < len(self._history) - 1:
            self._hist_idx += 1
            self._load_dir(self._history[self._hist_idx])

    def _go_up(self, *_):
        parent = os.path.dirname(self._cwd)
        if parent != self._cwd:
            self._navigate(parent)

    def _on_path_enter(self, entry):
        path = entry.get_text().strip()
        if os.path.isdir(path):
            self._navigate(path)

    def _on_search(self, entry):
        q = entry.get_text().lower()
        row = self.file_list.get_first_child()
        while row:
            if hasattr(row, "_name"):
                row.set_visible(q in row._name.lower())
            row = row.get_next_sibling()

    def _toggle_hidden(self, btn):
        self._show_hidden = btn.get_active()
        self._load_dir(self._cwd)

    def _get_selected_paths(self):
        paths = []
        row = self.file_list.get_first_child()
        while row:
            if self.file_list.row_is_selected(row) and hasattr(row, "_path"):
                paths.append(row._path)
            row = row.get_next_sibling()
        return paths

    def _open_selected(self, *_):
        for p in self._get_selected_paths():
            self._open_file(p)

    def _open_file(self, path):
        try:
            subprocess.Popen(["xdg-open", path],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass

    def _copy(self, *_):
        paths = self._get_selected_paths()
        if paths:
            self._clipboard = ("copy", paths)
            self.status.set_text(f"  📋 {len(paths)}개 복사됨")

    def _cut(self, *_):
        paths = self._get_selected_paths()
        if paths:
            self._clipboard = ("cut", paths)
            self.status.set_text(f"  ✂️ {len(paths)}개 잘라냄")

    def _paste(self, *_):
        if not self._clipboard:
            return
        action, paths = self._clipboard
        for src in paths:
            dst = os.path.join(self._cwd, os.path.basename(src))
            try:
                if action == "copy":
                    if os.path.isdir(src):
                        shutil.copytree(src, dst)
                    else:
                        shutil.copy2(src, dst)
                else:  # cut
                    shutil.move(src, dst)
            except Exception as e:
                self._show_error(str(e))
        if action == "cut":
            self._clipboard = None
        self._load_dir(self._cwd)

    def _rename(self, *_):
        paths = self._get_selected_paths()
        if not paths:
            return
        src = paths[0]
        old_name = os.path.basename(src)

        dialog = Adw.MessageDialog(transient_for=self.win)
        dialog.set_heading("이름 변경")
        entry = Gtk.Entry()
        entry.set_text(old_name)
        entry.select_region(0, -1)
        dialog.set_extra_child(entry)
        dialog.add_response("cancel", "취소")
        dialog.add_response("ok", "변경")
        dialog.set_default_response("ok")

        def on_response(d, r):
            if r == "ok":
                new_name = entry.get_text().strip()
                if new_name and new_name != old_name:
                    dst = os.path.join(os.path.dirname(src), new_name)
                    try:
                        os.rename(src, dst)
                        self._load_dir(self._cwd)
                    except Exception as e:
                        self._show_error(str(e))
        dialog.connect("response", on_response)
        dialog.present()

    def _delete(self, *_):
        paths = self._get_selected_paths()
        if not paths:
            return
        dialog = Adw.MessageDialog(transient_for=self.win)
        dialog.set_heading("삭제 확인")
        dialog.set_body(f"{len(paths)}개 항목을 삭제하시겠습니까?")
        dialog.add_response("cancel", "취소")
        dialog.add_response("delete", "삭제")
        dialog.set_response_appearance("delete", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.set_default_response("cancel")

        def on_response(d, r):
            if r == "delete":
                for p in paths:
                    try:
                        trash = os.path.expanduser("~/.local/share/Trash/files")
                        os.makedirs(trash, exist_ok=True)
                        shutil.move(p, os.path.join(trash, os.path.basename(p)))
                    except Exception:
                        try:
                            if os.path.isdir(p):
                                shutil.rmtree(p)
                            else:
                                os.remove(p)
                        except Exception as e:
                            self._show_error(str(e))
                self._load_dir(self._cwd)
        dialog.connect("response", on_response)
        dialog.present()

    def _new_folder(self, *_):
        dialog = Adw.MessageDialog(transient_for=self.win)
        dialog.set_heading("새 폴더")
        entry = Gtk.Entry()
        entry.set_text("새 폴더")
        entry.select_region(0, -1)
        dialog.set_extra_child(entry)
        dialog.add_response("cancel", "취소")
        dialog.add_response("ok", "만들기")
        dialog.set_default_response("ok")

        def on_response(d, r):
            if r == "ok":
                name = entry.get_text().strip()
                if name:
                    try:
                        os.makedirs(os.path.join(self._cwd, name), exist_ok=True)
                        self._load_dir(self._cwd)
                    except Exception as e:
                        self._show_error(str(e))
        dialog.connect("response", on_response)
        dialog.present()

    def _new_file(self, *_):
        dialog = Adw.MessageDialog(transient_for=self.win)
        dialog.set_heading("새 파일")
        entry = Gtk.Entry()
        entry.set_text("새 파일.txt")
        entry.select_region(0, -1)
        dialog.set_extra_child(entry)
        dialog.add_response("cancel", "취소")
        dialog.add_response("ok", "만들기")
        dialog.set_default_response("ok")

        def on_response(d, r):
            if r == "ok":
                name = entry.get_text().strip()
                if name:
                    try:
                        open(os.path.join(self._cwd, name), "a").close()
                        self._load_dir(self._cwd)
                    except Exception as e:
                        self._show_error(str(e))
        dialog.connect("response", on_response)
        dialog.present()

    def _on_right_click(self, gesture, n, x, y):
        row = self.file_list.get_row_at_y(int(y))
        if row:
            self.file_list.select_row(row)
        menu = Gtk.PopoverMenu()
        model = Gio.Menu()
        model.append("열기",        "app.open")
        model.append("복사",        "app.copy")
        model.append("잘라내기",    "app.cut")
        model.append("붙여넣기",    "app.paste")
        model.append("이름 변경",   "app.rename")
        model.append("삭제",        "app.delete")
        model.append("새 폴더",     "app.new_folder")
        menu.set_menu_model(model)
        menu.set_parent(self.file_list)
        menu.popup()

    def _show_error(self, msg):
        d = Adw.MessageDialog(transient_for=self.win, heading="오류", body=msg)
        d.add_response("ok", "확인")
        d.present()


def main():
    app = IgnisFiles()
    app.run([])


if __name__ == "__main__":
    main()
