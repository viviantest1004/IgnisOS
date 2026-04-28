#!/usr/bin/env python3
"""IgnisOS Calculator — 계산기"""
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, Gdk, Gio
import math

CSS = b"""
.calc-window { background: #0d0d1f; }
.calc-display {
    background: rgba(0,0,0,0.5);
    border-radius: 16px;
    border: 1px solid rgba(232,93,4,0.3);
    padding: 16px;
    margin: 12px;
}
.calc-result {
    font-size: 40px; font-weight: 300;
    color: #f1f5f9; font-family: monospace;
}
.calc-expr {
    font-size: 14px; color: #94a3b8; font-family: monospace;
}
.calc-btn {
    font-size: 18px; font-weight: 500;
    border-radius: 12px;
    border: none;
    padding: 0;
    min-height: 58px; min-width: 58px;
}
.btn-num    { background: rgba(255,255,255,0.08); color: #f1f5f9; }
.btn-num:hover { background: rgba(255,255,255,0.15); }
.btn-op     { background: rgba(232,93,4,0.2);   color: #fb923c; }
.btn-op:hover { background: rgba(232,93,4,0.35); }
.btn-eq     { background: #e85d04; color: #fff; }
.btn-eq:hover { background: #c74c00; }
.btn-fn     { background: rgba(255,255,255,0.05); color: #94a3b8; font-size: 14px; }
.btn-fn:hover { background: rgba(255,255,255,0.1); }
.btn-clear  { background: rgba(239,68,68,0.2); color: #f87171; }
.btn-clear:hover { background: rgba(239,68,68,0.35); }
.mode-btn { border-radius: 8px; padding: 4px 12px; font-size: 12px;
            background: transparent; border: 1px solid rgba(255,255,255,0.2);
            color: #94a3b8; }
.mode-btn.active { background: rgba(232,93,4,0.25); border-color: #e85d04; color: #fb923c; }
"""

BUTTONS_STD = [
    [("C", "clear"), ("±", "neg"),  ("%", "%"),    ("÷", "/")],
    [("7", "7"),     ("8", "8"),    ("9", "9"),    ("×", "*")],
    [("4", "4"),     ("5", "5"),    ("6", "6"),    ("−", "-")],
    [("1", "1"),     ("2", "2"),    ("3", "3"),    ("+", "+")],
    [("0", "0"),     (".", "."),    ("⌫", "back"), ("=", "=")],
]

BUTTONS_SCI = [
    [("sin",  "sin"),  ("cos",  "cos"),  ("tan",  "tan"),  ("π",    "pi")],
    [("ln",   "ln"),   ("log",  "log"),  ("√",    "sqrt"), ("x²",   "sq")],
    [("xʸ",  "pow"),   ("1/x", "inv"),  ("e",    "e"),    ("!",    "fact")],
    [("(",    "("),    (")",    ")"),    ("mod",  "mod"),  ("abs",  "abs")],
]


class Calculator(Adw.Application):
    def __init__(self):
        super().__init__(application_id="org.ignis.Calculator",
                         flags=Gio.ApplicationFlags.FLAGS_NONE)
        self.connect("activate", self._on_activate)
        self._expr = ""
        self._display = "0"
        self._sci_mode = False
        self._new_num = True

    def _on_activate(self, app):
        css = Gtk.CssProvider()
        css.load_from_data(CSS)
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), css,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        self.win = Adw.ApplicationWindow(application=app)
        self.win.set_title("계산기")
        self.win.set_default_size(340, 520)
        self.win.set_resizable(False)
        self.win.add_css_class("calc-window")

        main = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.win.set_content(main)

        # 모드 선택
        mode_box = Gtk.Box(spacing=6, margin_top=8, margin_start=12, margin_end=12)
        self.std_btn = Gtk.Button(label="일반")
        self.std_btn.add_css_class("mode-btn")
        self.std_btn.add_css_class("active")
        self.std_btn.connect("clicked", lambda *_: self._set_mode(False))
        self.sci_btn = Gtk.Button(label="공학용")
        self.sci_btn.add_css_class("mode-btn")
        self.sci_btn.connect("clicked", lambda *_: self._set_mode(True))
        mode_box.append(self.std_btn)
        mode_box.append(self.sci_btn)
        main.append(mode_box)

        # 디스플레이
        disp_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        disp_box.add_css_class("calc-display")

        self.expr_lbl = Gtk.Label(label="", xalign=1)
        self.expr_lbl.add_css_class("calc-expr")
        disp_box.append(self.expr_lbl)

        self.result_lbl = Gtk.Label(label="0", xalign=1)
        self.result_lbl.add_css_class("calc-result")
        self.result_lbl.set_ellipsize(3)
        disp_box.append(self.result_lbl)

        main.append(disp_box)

        # 버튼 그리드 (과학용)
        self.sci_grid = Gtk.Grid(row_spacing=6, column_spacing=6,
                                 margin_start=12, margin_end=12, margin_bottom=6)
        for r, row in enumerate(BUTTONS_SCI):
            for c, (lbl, val) in enumerate(row):
                btn = Gtk.Button(label=lbl)
                btn.add_css_class("calc-btn")
                btn.add_css_class("btn-fn")
                btn.set_hexpand(True)
                btn.set_vexpand(True)
                v = val
                btn.connect("clicked", lambda _b, v=v: self._on_sci(v))
                self.sci_grid.attach(btn, c, r, 1, 1)
        self.sci_grid.set_visible(False)
        main.append(self.sci_grid)

        # 일반 버튼 그리드
        self.std_grid = Gtk.Grid(row_spacing=6, column_spacing=6,
                                 margin_start=12, margin_end=12, margin_bottom=12)
        for r, row in enumerate(BUTTONS_STD):
            for c, (lbl, val) in enumerate(row):
                btn = Gtk.Button(label=lbl)
                btn.add_css_class("calc-btn")
                if val in ("+", "-", "*", "/"):
                    btn.add_css_class("btn-op")
                elif val == "=":
                    btn.add_css_class("btn-eq")
                elif val in ("clear", "back"):
                    btn.add_css_class("btn-clear")
                elif val == "%":
                    btn.add_css_class("btn-op")
                else:
                    btn.add_css_class("btn-num")
                btn.set_hexpand(True)
                btn.set_vexpand(True)
                v = val
                btn.connect("clicked", lambda _b, v=v: self._on_btn(v))
                if lbl == "0":
                    self.std_grid.attach(btn, c, r, 1, 1)
                else:
                    self.std_grid.attach(btn, c, r, 1, 1)
        main.append(self.std_grid)

        # 키보드 입력
        key_ctrl = Gtk.EventControllerKey()
        key_ctrl.connect("key-pressed", self._on_key)
        self.win.add_controller(key_ctrl)

        self.win.present()

    def _set_mode(self, sci):
        self._sci_mode = sci
        self.sci_grid.set_visible(sci)
        if sci:
            self.sci_btn.add_css_class("active")
            self.std_btn.remove_css_class("active")
            self.win.set_default_size(340, 720)
        else:
            self.std_btn.add_css_class("active")
            self.sci_btn.remove_css_class("active")
            self.win.set_default_size(340, 520)

    def _on_btn(self, val):
        if val == "clear":
            self._expr = ""
            self._display = "0"
            self._new_num = True
        elif val == "back":
            if self._display and self._display != "0":
                self._display = self._display[:-1] or "0"
        elif val == "neg":
            if self._display != "0":
                self._display = str(-float(self._display))
        elif val == "%":
            try:
                self._display = str(float(self._display) / 100)
            except Exception:
                self._display = "오류"
        elif val == "=":
            self._calculate()
        elif val in ("+", "-", "*", "/"):
            self._expr += self._display + val
            self._new_num = True
        elif val == ".":
            if "." not in self._display:
                self._display += "."
                self._new_num = False
        else:
            if self._new_num:
                self._display = val
                self._new_num = False
            else:
                if self._display == "0":
                    self._display = val
                else:
                    self._display += val

        self._update_display()

    def _on_sci(self, val):
        try:
            x = float(self._display)
            result = None
            if val == "sin":   result = math.sin(math.radians(x))
            elif val == "cos": result = math.cos(math.radians(x))
            elif val == "tan": result = math.tan(math.radians(x))
            elif val == "ln":  result = math.log(x)
            elif val == "log": result = math.log10(x)
            elif val == "sqrt":result = math.sqrt(x)
            elif val == "sq":  result = x ** 2
            elif val == "pi":  self._display = str(math.pi); self._update_display(); return
            elif val == "e":   self._display = str(math.e);  self._update_display(); return
            elif val == "inv": result = 1 / x
            elif val == "fact":result = math.factorial(int(x))
            elif val == "abs": result = abs(x)
            elif val in ("(", ")", "mod"):
                self._expr += val; self._update_display(); return
            elif val == "pow": self._expr += self._display + "**"; self._new_num = True; self._update_display(); return
            if result is not None:
                self._expr = f"{val}({self._display})"
                self._display = self._fmt(result)
                self._new_num = True
        except Exception:
            self._display = "오류"
        self._update_display()

    def _calculate(self):
        try:
            full = self._expr + self._display
            self.expr_lbl.set_text(full + " =")
            result = eval(full, {"__builtins__": {}}, {
                "sin": math.sin, "cos": math.cos, "tan": math.tan,
                "sqrt": math.sqrt, "log": math.log10, "pi": math.pi, "e": math.e,
            })
            self._display = self._fmt(result)
            self._expr = ""
            self._new_num = True
        except Exception:
            self._display = "오류"
        self._update_display()

    def _fmt(self, v):
        if isinstance(v, float) and v == int(v):
            return str(int(v))
        return f"{v:.10g}"

    def _update_display(self):
        self.result_lbl.set_text(self._display)
        if not self._expr:
            self.expr_lbl.set_text("")

    def _on_key(self, ctrl, keyval, keycode, state):
        key = chr(keyval) if 32 <= keyval < 127 else None
        if key in "0123456789.":
            self._on_btn(key)
        elif key in "+-*/":
            self._on_btn(key)
        elif keyval == 65293:  # Enter
            self._on_btn("=")
        elif keyval == 65288:  # Backspace
            self._on_btn("back")
        elif key in ("c", "C"):
            self._on_btn("clear")
        return False


def main():
    app = Calculator()
    app.run([])


if __name__ == "__main__":
    main()
