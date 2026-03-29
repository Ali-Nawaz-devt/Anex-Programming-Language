"""
ANEX Visual Debugger — gui.py
Install : pip install customtkinter
Run     : cd anex && python gui.py
"""

import sys, os, re, time, threading
sys.path.insert(0, os.path.dirname(__file__))

import customtkinter as ctk
import tkinter as tk
from tkinter import font as tkfont

from src.lexer       import Lexer
from src.parser      import Parser
from src.interpreter import Interpreter, ReturnException
from src.anex_ast    import (
    Program, Unit, VarDecl, EmitStmt, IfStmt, WhileStmt,
    FuncDecl, ReturnStmt, FuncCall, BinOp, Number, Identifier,
    LogicalOp, NotOp, BoolLiteral, TextLiteral,
)
from src.tokens import KEYWORDS

# ══════════════════════════════════════════════════════════════════════════════
#  COLOUR PALETTE  — deep obsidian + premium neon accents
# ══════════════════════════════════════════════════════════════════════════════
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

C = {
    # backgrounds — near-black obsidian
    "bg":        "#07080f",   # deepest bg
    "sidebar":   "#09091a",   # editor bg
    "panel":     "#0a0b1c",   # right panel bg
    "tab_bar":   "#070818",   # tab strip
    "tab_act":   "#10122a",   # active tab bg
    "tab_idle":  "#070818",   # inactive tab bg
    "card":      "#0d0f22",   # inner card bg
    "header":    "#0b0d1e",   # section headers
    "border":    "#181b38",   # subtle border
    "glow_dim":  "#141628",   # glow bg

    # text
    "text":      "#e4e8ff",
    "muted":     "#555880",
    "dim":       "#22243c",
    "sub":       "#8890bb",
    "bright":    "#ffffff",

    # accents — premium vivid
    "green":     "#00ffaa",
    "pink":      "#ff3d96",
    "yellow":    "#ffcc44",
    "cyan":      "#00d4ff",
    "purple":    "#aa44ff",
    "orange":    "#ff7a28",
    "red":       "#ff2448",
    "blue":      "#3a88ff",
    "teal":      "#00e8c0",
    "indigo":    "#5564ff",
    "lime":      "#aaff44",
    "rose":      "#ff6080",

    # token colours
    "KEYWORD":   "#ff3d96",
    "NUMBER":    "#ffcc44",
    "STRING":    "#00ffaa",
    "OP":        "#ff7a28",
    "SYM":       "#00d4ff",
    "IDENT":     "#e4e8ff",
    "EOF":       "#393d60",
}

STEP_COL = {
    "visit":  C["teal"],
    "eval":   C["cyan"],
    "assign": C["orange"],
    "emit":   C["green"],
    "call":   C["purple"],
    "return": C["pink"],
    "branch": C["yellow"],
    "error":  C["red"],
}

STEP_ICON = {
    "visit":  "→",
    "eval":   "=",
    "assign": "←",
    "emit":   "▶",
    "call":   "⤷",
    "return": "⤶",
    "branch": "⑂",
    "error":  "✕",
}

SAMPLES = {
    "Hello World": """\
unit Main {
    emit("Hello, ANEX!");
    int x = 10;
    int y = 4;
    int result = x + y;
    emit(result);

    if result > 12 {
        emit("Big result!");
    } else {
        emit("Small result.");
    }
}""",
    "Factorial": """\
unit Main {
    func factorial(n) {
        if n <= 1 {
            return 1;
        }
        return n * factorial(n - 1);
    }

    int ans = factorial(7);
    emit("7! =");
    emit(ans);
}""",
    "While Loop": """\
unit Main {
    int i = 1;
    int total = 0;

    while i <= 5 {
        emit(i);
        total = total + i;
        i = i + 1;
    }

    emit("Sum =");
    emit(total);
}""",
    "Functions": """\
unit Main {
    func add(a, b) {
        return a + b;
    }

    func square(x) {
        return x * x;
    }

    emit(add(3, 4));
    emit(square(6));
}""",
    "Logic": """\
unit Main {
    bool a = true;
    bool b = false;

    emit(a and b);
    emit(a or b);
    emit(not a);

    int x = 15;
    emit(x > 10 and x < 20);
    emit(x == 15);
}""",
    "Fibonacci": """\
unit Main {
    func fib(n) {
        if n <= 1 {
            return n;
        }
        return fib(n - 1) + fib(n - 2);
    }

    int i = 0;
    while i <= 9 {
        emit(fib(i));
        i = i + 1;
    }
}""",
}

# ══════════════════════════════════════════════════════════════════════════════
#  TRACING INTERPRETER
# ══════════════════════════════════════════════════════════════════════════════
class TracingInterpreter(Interpreter):
    def __init__(self):
        super().__init__()
        self.steps:             list[tuple[str,str]] = []
        self.outputs:           list[str]            = []
        self.var_info:          dict                 = {}   # name→{type,value,scope,updates}
        self.func_call_counts:  dict                 = {}   # name→count
        self.func_return_vals:  dict                 = {}   # name→last return
        self.call_stack:        list                 = []   # [{name,params,locals}]
        self._scope_stack:      list                 = ["global"]

    def _s(self, kind: str, msg: str) -> None:
        self.steps.append((kind, msg))

    def visit(self, node):
        if isinstance(node, EmitStmt):
            val  = self.eval_expr(node.expr)
            disp = "true" if val is True else ("false" if val is False else str(val))
            self._s("emit", f"emit  →  {disp}")
            self.outputs.append(disp)

        elif isinstance(node, VarDecl):
            self._s("visit", f"Declare  {node.var_type}  {node.name}")
            val = self.eval_expr(node.value)
            self.env[node.name] = val
            self._s("assign", f"{node.name}  ←  {val}")
            scope = self._scope_stack[-1] if self._scope_stack else "global"
            self.var_info[node.name] = {
                "type": node.var_type, "value": val,
                "scope": scope, "updates": 0
            }

        elif isinstance(node, tuple) and node[0] == "assign":
            _, name, expr = node
            if name not in self.env:
                raise Exception(f"Undefined variable '{name}'")
            val = self.eval_expr(expr)
            self._s("assign", f"Update  {name}  ←  {val}")
            self.env[name] = val
            if name in self.var_info:
                self.var_info[name]["value"]   = val
                self.var_info[name]["updates"] += 1

        elif isinstance(node, FuncDecl):
            self.functions[node.name] = node
            self._s("visit", f"Register  func {node.name}({', '.join(node.params)})")
            self.func_call_counts.setdefault(node.name, 0)

        elif isinstance(node, ReturnStmt):
            val = self.eval_expr(node.expr)
            self._s("return", f"return  {val}")
            raise ReturnException(val)

        elif isinstance(node, IfStmt):
            cond = self.eval_expr(node.condition)
            self._s("branch", f"if → {cond}  ·  {'then' if cond else 'else'} branch")
            if cond:
                for s in node.then_body:   self.visit(s)
            elif node.else_body:
                for s in node.else_body:   self.visit(s)

        elif isinstance(node, WhileStmt):
            itr = 0
            while self.eval_expr(node.condition):
                itr += 1
                self._s("branch", f"while  iter {itr}")
                for s in node.body: self.visit(s)
                if itr > 300:
                    self._s("error", "Loop limit 300 reached"); break
            self._s("branch", f"while done  ·  {itr} iterations")
        else:
            super().visit(node)

    def eval_expr(self, expr):
        if isinstance(expr, BinOp):
            L, R = self.eval_expr(expr.left), self.eval_expr(expr.right)
            if expr.op == "/" and R == 0: raise Exception("Division by zero")
            ops = {"+":lambda a,b:a+b,"-":lambda a,b:a-b,
                   "*":lambda a,b:a*b,"/":lambda a,b:a//b,
                   ">":lambda a,b:a>b,"<":lambda a,b:a<b,
                   ">=":lambda a,b:a>=b,"<=":lambda a,b:a<=b,
                   "==":lambda a,b:a==b,"!=":lambda a,b:a!=b}
            res = ops[expr.op](L, R)
            self._s("eval", f"{L}  {expr.op}  {R}  =  {res}")
            return res

        if isinstance(expr, Identifier):
            if expr.name not in self.env:
                raise Exception(f"Undefined variable '{expr.name}'")
            val = self.env[expr.name]
            self._s("eval", f"Read  {expr.name}  =  {val}")
            return val

        if isinstance(expr, FuncCall):
            if expr.name not in self.functions:
                raise Exception(f"Undefined function '{expr.name}'")
            fn   = self.functions[expr.name]
            avs  = [self.eval_expr(a) for a in expr.args]
            self._s("call", f"Call  {expr.name}({', '.join(map(str,avs))})")
            self.func_call_counts[expr.name] = self.func_call_counts.get(expr.name, 0) + 1
            old  = self.env.copy()
            for p, v in zip(fn.params, avs): self.env[p] = v
            # push call stack frame
            self._scope_stack.append(f"func:{expr.name}")
            self.call_stack.append({"name": expr.name,
                                    "params": dict(zip(fn.params, avs)),
                                    "locals": {}})
            ret  = None
            try:
                for s in fn.body: self.visit(s)
            except ReturnException as r:
                ret = r.value
            # pop call stack frame
            if self.call_stack: self.call_stack.pop()
            if self._scope_stack: self._scope_stack.pop()
            self.env = old
            self.func_return_vals[expr.name] = ret
            self._s("return", f"{expr.name}  →  {ret}")
            return ret

        if isinstance(expr, LogicalOp):
            L = self.eval_expr(expr.left)
            if expr.op == "and" and not L:
                self._s("eval", "short-circuit  and  →  False"); return False
            if expr.op == "or"  and     L:
                self._s("eval", "short-circuit  or   →  True");  return True
            R   = self.eval_expr(expr.right)
            res = (L and R) if expr.op == "and" else (L or R)
            self._s("eval", f"{L}  {expr.op}  {R}  =  {res}")
            return res

        if isinstance(expr, NotOp):
            v = self.eval_expr(expr.expr)
            self._s("eval", f"not {v}  =  {not v}")
            return not v

        return super().eval_expr(expr)


# ══════════════════════════════════════════════════════════════════════════════
#  AST  →  coloured lines
# ══════════════════════════════════════════════════════════════════════════════
#  AST  →  tree node dicts  { label, colour, children }
# ══════════════════════════════════════════════════════════════════════════════
def ast_tree(node) -> dict:
    """Return a nested dict: {label, colour, children:[...]}"""
    def N(label: str, colour: str, children: list) -> dict:
        return {"label": label, "colour": colour, "children": children}

    if isinstance(node, Program):
        return N("PROGRAM", C["cyan"], [ast_tree(node.unit)])

    if isinstance(node, Unit):
        return N(f"UNIT  '{node.name}'", C["purple"],
                 [ast_tree(s) for s in node.statements])

    if isinstance(node, VarDecl):
        return N(f"VAR  {node.var_type}  {node.name}", C["cyan"],
                 [ast_tree(node.value)])

    if isinstance(node, tuple) and node[0] == "assign":
        return N(f"ASSIGN  {node[1]}", C["orange"], [ast_tree(node[2])])

    if isinstance(node, EmitStmt):
        return N("EMIT", C["green"], [ast_tree(node.expr)])

    if isinstance(node, IfStmt):
        kids = [N("cond", C["muted"], [ast_tree(node.condition)]),
                N("then", C["muted"], [ast_tree(s) for s in node.then_body])]
        if node.else_body:
            kids.append(N("else", C["muted"],
                          [ast_tree(s) for s in node.else_body]))
        return N("IF", C["pink"], kids)

    if isinstance(node, WhileStmt):
        return N("WHILE", C["pink"], [
            N("cond", C["muted"], [ast_tree(node.condition)]),
            N("body", C["muted"], [ast_tree(s) for s in node.body]),
        ])

    if isinstance(node, FuncDecl):
        params = ", ".join(node.params) if node.params else ""
        return N(f"FUNC  {node.name}({params})", C["yellow"],
                 [ast_tree(s) for s in node.body])

    if isinstance(node, ReturnStmt):
        return N("RETURN", C["red"], [ast_tree(node.expr)])

    if isinstance(node, FuncCall):
        return N(f"CALL  {node.name}()", C["purple"],
                 [ast_tree(a) for a in node.args])

    if isinstance(node, BinOp):
        return N(f"BINOP  {node.op}", C["orange"],
                 [ast_tree(node.left), ast_tree(node.right)])

    if isinstance(node, LogicalOp):
        return N(f"LOGIC  {node.op}", C["pink"],
                 [ast_tree(node.left), ast_tree(node.right)])

    if isinstance(node, NotOp):
        return N("NOT", C["pink"], [ast_tree(node.expr)])

    if isinstance(node, Number):
        return N(str(node.value), C["yellow"], [])

    if isinstance(node, BoolLiteral):
        return N(str(node.value), C["pink"], [])

    if isinstance(node, TextLiteral):
        return N(f'"{node.value}"', C["green"], [])

    if isinstance(node, Identifier):
        return N(node.name, C["text"], [])

    return N(repr(node)[:30], C["muted"], [])


# ══════════════════════════════════════════════════════════════════════════════
#  CANVAS  AST  TREE  WIDGET  — top-down layout, click to collapse
# ══════════════════════════════════════════════════════════════════════════════
class ASTTreeCanvas(tk.Canvas):
    """
    Proper top-down visual tree.
    Each node is a coloured box; children hang below connected by lines.
    Click a node to collapse/expand its subtree.
    """

    # ── layout constants ──────────────────────────────────────────────────────
    BOX_H    = 28          # box height px
    BOX_PAD  = 14          # horizontal text padding inside box
    LEVEL_H  = 70          # vertical distance between depth levels
    SIBLING_GAP = 18       # minimum horizontal gap between sibling boxes
    FONT     = ("Courier New", 10, "bold")
    FONT_IND = ("Courier New", 9)

    def __init__(self, master, **kw):
        kw.setdefault("bg",                C["card"])
        kw.setdefault("highlightthickness", 0)
        kw.setdefault("relief",            "flat")
        kw.setdefault("bd",                0)
        super().__init__(master, **kw)

        self._tree:      dict = {}
        self._collapsed: set  = set()
        self._click_map: dict = {}

        self.bind("<Button-1>", self._on_click)
        self.bind("<Button-4>", lambda e: self.yview_scroll(-1, "units"))
        self.bind("<Button-5>", lambda e: self.yview_scroll( 1, "units"))

    # ── public API ────────────────────────────────────────────────────────────
    def load(self, tree: dict):
        self._tree      = tree
        self._collapsed = set()
        self._click_map = {}
        self._redraw()

    def clear(self):
        self.delete("all")
        self._tree      = {}
        self._click_map = {}

    # ── redraw ────────────────────────────────────────────────────────────────
    def _redraw(self):
        self.delete("all")
        self._click_map = {}
        if not self._tree:
            return

        import tkinter.font as tkf
        self._fnt = tkf.Font(family="Courier New", size=10, weight="bold")

        # Phase 1 — compute subtree widths (bottom-up)
        self._compute_widths(self._tree, "root")

        # Phase 2 — assign (cx, cy) to every visible node (top-down)
        self._pos: dict[str, tuple] = {}   # path → (cx, cy, w)
        margin = 30
        root_cx = margin + self._tree["_w"] // 2
        self._assign_positions(self._tree, "root", root_cx, 30)

        # Phase 3 — draw lines first (so nodes appear on top)
        self._draw_lines(self._tree, "root")

        # Phase 4 — draw nodes
        self._draw_nodes(self._tree, "root")

        # update scroll region
        self.update_idletasks()
        bbox = self.bbox("all")
        if bbox:
            self.configure(scrollregion=(
                bbox[0] - 20, bbox[1] - 20,
                bbox[2] + 30, bbox[3] + 30))

    # ── Phase 1: subtree width ────────────────────────────────────────────────
    def _compute_widths(self, node: dict, path: str):
        label    = node["label"]
        children = node["children"]
        collapsed = path in self._collapsed

        box_w = self._fnt.measure(label) + self.BOX_PAD * 2

        if collapsed or not children:
            node["_w"] = box_w
            return

        total_children_w = 0
        for i, child in enumerate(children):
            child_path = f"{path}/{i}"
            self._compute_widths(child, child_path)
            total_children_w += child["_w"]

        total_children_w += self.SIBLING_GAP * (len(children) - 1)
        node["_w"] = max(box_w, total_children_w)

    # ── Phase 2: assign positions ─────────────────────────────────────────────
    def _assign_positions(self, node: dict, path: str, cx: float, cy: float):
        self._pos[path] = (cx, cy)
        collapsed = path in self._collapsed
        children  = node["children"]

        if collapsed or not children:
            return

        # spread children evenly under parent
        total_w = sum(c["_w"] for c in children) + self.SIBLING_GAP * (len(children) - 1)
        child_y = cy + self.LEVEL_H
        child_x = cx - total_w / 2

        for i, child in enumerate(children):
            child_cx   = child_x + child["_w"] / 2
            child_path = f"{path}/{i}"
            self._assign_positions(child, child_path, child_cx, child_y)
            child_x   += child["_w"] + self.SIBLING_GAP

    # ── Phase 3: draw lines ───────────────────────────────────────────────────
    def _draw_lines(self, node: dict, path: str):
        if path not in self._pos:
            return
        px, py = self._pos[path]
        collapsed = path in self._collapsed

        if not collapsed:
            for i, child in enumerate(node["children"]):
                child_path = f"{path}/{i}"
                if child_path not in self._pos:
                    continue
                cx, cy = self._pos[child_path]
                mid_y  = (py + cy) / 2
                col    = node["colour"]
                coords = [px, py + self.BOX_H // 2,
                              px, mid_y,
                              cx, mid_y,
                              cx, cy - self.BOX_H // 2]
                self.create_line(*coords,
                                 fill=col, width=1.5, tags="line")
                self._draw_lines(child, child_path)

    # ── Phase 4: draw node boxes ──────────────────────────────────────────────
    def _draw_nodes(self, node: dict, path: str):
        if path not in self._pos:
            return

        cx, cy    = self._pos[path]
        label     = node["label"]
        colour    = node["colour"]
        collapsed = path in self._collapsed
        has_kids  = bool(node["children"])

        box_w  = self._fnt.measure(label) + self.BOX_PAD * 2
        x0, y0 = cx - box_w / 2, cy - self.BOX_H / 2
        x1, y1 = cx + box_w / 2, cy + self.BOX_H / 2

        # dim background fill (pure hex, no alpha — tkinter doesn't do alpha)
        bg = self._dim_hex(colour)
        rect = self.create_rectangle(
            x0, y0, x1, y1,
            fill=bg, outline=colour, width=2,
            tags="node")
        self._click_map[rect] = path

        # label
        txt = self.create_text(
            cx, cy,
            text=label, fill=colour,
            font=self.FONT, tags="node")
        self._click_map[txt] = path

        # collapse triangle indicator
        if has_kids:
            tri = "▸" if collapsed else "▾"
            self.create_text(
                x1 + 9, cy,
                text=tri, fill=colour,
                font=self.FONT_IND, tags="node")

        # recurse
        if not collapsed:
            for i, child in enumerate(node["children"]):
                self._draw_nodes(child, f"{path}/{i}")

    # ── helpers ───────────────────────────────────────────────────────────────
    @staticmethod
    def _dim_hex(hex_colour: str) -> str:
        """Return a darkened version of a #RRGGBB colour for box backgrounds."""
        h = hex_colour.lstrip("#")
        if len(h) != 6:
            return "#1a1c33"
        r, g, b = int(h[0:2],16), int(h[2:4],16), int(h[4:6],16)
        r, g, b = int(r*0.18), int(g*0.18), int(b*0.18)
        return f"#{r:02x}{g:02x}{b:02x}"

    def _on_click(self, event):
        x = self.canvasx(event.x)
        y = self.canvasy(event.y)
        items = self.find_overlapping(x - 3, y - 3, x + 3, y + 3)
        for item in items:
            if item in self._click_map:
                path = self._click_map[item]
                if path in self._collapsed:
                    self._collapsed.discard(path)
                else:
                    self._collapsed.add(path)
                self._redraw()
                return


# ══════════════════════════════════════════════════════════════════════════════
#  COLOURED TEXT BOX
# ══════════════════════════════════════════════════════════════════════════════
MONO = ("Courier New", 11)
MONO_B = ("Courier New", 11, "bold")
MONO_L = ("Courier New", 12)

class RichText(tk.Text):
    def __init__(self, master, fontsize=11, **kw):
        _mono   = ("Courier New", fontsize)
        _mono_b = ("Courier New", fontsize, "bold")
        kw.setdefault("bg",                C["card"])
        kw.setdefault("fg",                C["text"])
        kw.setdefault("font",              _mono)
        kw.setdefault("relief",            "flat")
        kw.setdefault("bd",                0)
        kw.setdefault("wrap",              "none")
        kw.setdefault("state",             "disabled")
        kw.setdefault("insertbackground",  C["green"])
        kw.setdefault("selectbackground",  C["glow_dim"])
        kw.setdefault("spacing1",          4)
        kw.setdefault("spacing3",          4)
        kw.setdefault("highlightthickness",0)
        kw.setdefault("padx",              10)
        kw.setdefault("pady",              6)
        self._mono   = _mono
        self._mono_b = _mono_b
        super().__init__(master, **kw)

    def clear(self):
        self.config(state="normal")
        self.delete("1.0", "end")
        self.config(state="disabled")

    def w(self, text: str, colour: str = "", bold: bool = False) -> None:
        self.config(state="normal")
        tag = f"_c{colour}{bold}"
        self.tag_configure(tag,
                           foreground=colour or C["text"],
                           font=self._mono_b if bold else self._mono)
        self.insert("end", text, tag)
        self.config(state="disabled")

    def tip(self):
        self.see("end")


# ══════════════════════════════════════════════════════════════════════════════
#  CUSTOM TAB BAR  — underline indicator style, no emojis
# ══════════════════════════════════════════════════════════════════════════════
class TabBar(tk.Frame):
    TAB_H = 40
    UL_H  = 3

    def __init__(self, master, tabs: list[tuple[str,str,str]], on_switch, **kw):
        super().__init__(master, bg=C["tab_bar"], height=self.TAB_H, **kw)
        self.pack_propagate(False)
        self._on_switch = on_switch
        self._btns:   dict[str, tuple[tk.Label, str]] = {}
        self._unders: dict[str, tk.Frame]             = {}
        self._active  = tabs[0][0]
        self._font_act  = tkfont.Font(family="Helvetica", size=11, weight="bold")
        self._font_idle = tkfont.Font(family="Helvetica", size=11)

        for key, label, col in tabs:
            wrapper = tk.Frame(self, bg=C["tab_bar"])
            wrapper.pack(side="left")

            lbl = tk.Label(wrapper, text=label,
                           font=self._font_act if key == self._active else self._font_idle,
                           bg=C["tab_act"] if key == self._active else C["tab_bar"],
                           fg=col if key == self._active else C["sub"],
                           padx=12, pady=8, cursor="hand2")
            lbl.pack(fill="both", expand=True)

            ul = tk.Frame(wrapper,
                          bg=col if key == self._active else C["tab_bar"],
                          height=self.UL_H)
            ul.pack(fill="x")

            lbl.bind("<Button-1>", lambda e, k=key, c=col: self._switch(k, c))
            lbl.bind("<Enter>",    lambda e, w=lbl, k=key: self._hover(w, k, True))
            lbl.bind("<Leave>",    lambda e, w=lbl, k=key: self._hover(w, k, False))

            self._btns[key]   = (lbl, col)
            self._unders[key] = ul

    def _hover(self, widget, key, enter):
        if key != self._active:
            widget.configure(fg=C["text"] if enter else C["sub"])

    def _switch(self, key: str, col: str):
        for k, (lbl, c) in self._btns.items():
            active = (k == key)
            lbl.configure(
                bg=C["tab_act"] if active else C["tab_bar"],
                fg=c           if active else C["sub"],
                font=self._font_act if active else self._font_idle)
            self._unders[k].configure(bg=c if active else C["tab_bar"])
        self._active = key
        self._on_switch(key)

    def flash(self, key: str):
        if key in self._btns:
            lbl, col = self._btns[key]
            lbl.configure(fg=col)


# ══════════════════════════════════════════════════════════════════════════════
#  PIPELINE  INDICATOR  — canvas glow dot with pulse animation
# ══════════════════════════════════════════════════════════════════════════════
class PipeDot(tk.Frame):
    SZ = 14

    def __init__(self, master, label: str, colour: str):
        super().__init__(master, bg=C["header"])
        self._col   = colour
        self._on_   = False
        self._pulse = 0

        self._canvas = tk.Canvas(self, width=self.SZ+8, height=self.SZ+8,
                                 bg=C["header"], highlightthickness=0)
        self._canvas.pack(side="left", padx=(0, 4))
        self._lbl = tk.Label(self, text=label,
                             font=("Helvetica", 10, "bold"),
                             bg=C["header"], fg=C["muted"])
        self._lbl.pack(side="left")
        self._draw(False)

    def _draw(self, active: bool):
        self._canvas.delete("all")
        cx, cy = (self.SZ+8)//2, (self.SZ+8)//2
        r = self.SZ // 2
        if active:
            # outer glow rings
            for i, alpha in [(r+5, "#0d1020"), (r+3, "#151830")]:
                self._canvas.create_oval(cx-i, cy-i, cx+i, cy+i,
                                         fill=self._blend(self._col, 0.25),
                                         outline="")
            # bright core
            self._canvas.create_oval(cx-r, cy-r, cx+r, cy+r,
                                     fill=self._col, outline=self._col, width=1)
            # white hot centre
            self._canvas.create_oval(cx-3, cy-3, cx+3, cy+3,
                                     fill="#ffffff", outline="")
        else:
            self._canvas.create_oval(cx-r, cy-r, cx+r, cy+r,
                                     fill=C["dim"], outline=C["border"], width=1)

    def _blend(self, hex_col, factor):
        h = hex_col.lstrip("#")
        r, g, b = int(h[0:2],16), int(h[2:4],16), int(h[4:6],16)
        r = int(r * factor); g = int(g * factor); b = int(b * factor)
        return f"#{r:02x}{g:02x}{b:02x}"

    def on(self):
        self._on_ = True
        self._draw(True)
        self._lbl.configure(fg=self._col)
        self._pulse = 0
        self._animate()

    def off(self):
        self._on_ = False
        self._draw(False)
        self._lbl.configure(fg=C["muted"])

    def _animate(self):
        if not self._on_: return
        # subtle brightness pulse
        self._pulse = (self._pulse + 1) % 20
        self._canvas.after(80, self._animate)


# ══════════════════════════════════════════════════════════════════════════════
#  STAT PILL  — clean metric display
# ══════════════════════════════════════════════════════════════════════════════
class StatPill(tk.Frame):
    def __init__(self, master, label: str, colour: str):
        super().__init__(master, bg=C["glow_dim"],
                         highlightbackground=colour,
                         highlightthickness=1)
        self._colour = colour
        self._v = tk.StringVar(value="—")
        inner = tk.Frame(self, bg=C["glow_dim"])
        inner.pack(padx=10, pady=3)
        tk.Label(inner, text=label.upper(),
                 font=("Helvetica", 8, "bold"),
                 bg=C["glow_dim"], fg=C["sub"]).pack()
        tk.Label(inner, textvariable=self._v,
                 font=("Courier New", 15, "bold"),
                 bg=C["glow_dim"], fg=colour).pack()

    def set(self, v):   self._v.set(str(v))
    def reset(self):    self._v.set("—")


# ══════════════════════════════════════════════════════════════════════════════
#  SEMANTIC  ANALYSER
# ══════════════════════════════════════════════════════════════════════════════
class SemanticAnalyzer:
    """Walk the AST and collect type / scope / declaration errors."""

    ERR_ICON  = "✕"
    WARN_ICON = "⚠"
    OK_ICON   = "✔"

    def __init__(self):
        self.errors:   list[dict] = []
        self.warnings: list[dict] = []
        self.checks:   list[dict] = []   # passed checks
        self._vars:    dict = {}         # name→type
        self._funcs:   dict = {}         # name→param_count
        self._scope    = "global"

    def analyze(self, prog):
        try:
            if isinstance(prog, Program):
                self._walk(prog.unit)
            # final summary checks
            if not self.errors:
                self.checks.append({"msg": "All variables declared before use"})
                self.checks.append({"msg": "All function calls match declarations"})
                self.checks.append({"msg": "No duplicate declarations found"})
                self.checks.append({"msg": "Type assignments are consistent"})
        except Exception:
            pass
        return self.errors, self.warnings, self.checks

    def _err(self, kind, msg, suggestion=""):
        self.errors.append({"kind": kind, "msg": msg, "sug": suggestion})

    def _warn(self, kind, msg, suggestion=""):
        self.warnings.append({"kind": kind, "msg": msg, "sug": suggestion})

    def _walk(self, node):
        if node is None: return
        if isinstance(node, Unit):
            for s in node.statements: self._walk(s)
        elif isinstance(node, VarDecl):
            if node.name in self._vars:
                self._err("Duplicate Decl",
                          f"Variable '{node.name}' declared more than once",
                          f"Remove the second declaration of '{node.name}'")
            else:
                self._vars[node.name] = node.var_type
            inferred = self._infer(node.value)
            expected_map = {"int": "number", "bool": "boolean", "string": "string"}
            expected = expected_map.get(node.var_type)
            if expected and inferred not in ("unknown", expected):
                self._err("Type Mismatch",
                          f"'{node.name}' declared as {node.var_type} but value is {inferred}",
                          f"Change declaration type or fix assigned value")
            self._walk_expr(node.value)
        elif isinstance(node, tuple) and node[0] == "assign":
            _, name, expr = node
            if name not in self._vars:
                self._err("Undeclared Var",
                          f"Assignment to undeclared variable '{name}'",
                          f"Declare '{name}' with  int/bool/string {name} = ...")
            self._walk_expr(expr)
        elif isinstance(node, FuncDecl):
            if node.name in self._funcs:
                self._err("Duplicate Func",
                          f"Function '{node.name}' declared more than once",
                          f"Rename or remove the duplicate function")
            else:
                self._funcs[node.name] = len(node.params)
            old_vars, old_scope = self._vars.copy(), self._scope
            self._scope = f"func:{node.name}"
            for p in node.params: self._vars[p] = "param"
            for s in node.body:   self._walk(s)
            self._vars, self._scope = old_vars, old_scope
        elif isinstance(node, IfStmt):
            cond_t = self._infer(node.condition)
            if cond_t not in ("unknown", "boolean"):
                self._warn("Type Warning",
                           f"if-condition has type '{cond_t}', expected boolean",
                           "Wrap in a comparison: e.g.  x > 0")
            self._walk_expr(node.condition)
            for s in node.then_body: self._walk(s)
            if node.else_body:
                for s in node.else_body: self._walk(s)
        elif isinstance(node, WhileStmt):
            self._walk_expr(node.condition)
            for s in node.body: self._walk(s)
        elif isinstance(node, EmitStmt):
            self._walk_expr(node.expr)
        elif isinstance(node, ReturnStmt):
            self._walk_expr(node.expr)

    def _walk_expr(self, expr):
        if expr is None: return
        if isinstance(expr, Identifier):
            if expr.name not in self._vars and expr.name not in self._funcs:
                self._err("Undeclared Var",
                          f"Use of undeclared variable '{expr.name}'",
                          f"Declare '{expr.name}' before using it")
        elif isinstance(expr, BinOp):
            self._walk_expr(expr.left); self._walk_expr(expr.right)
        elif isinstance(expr, LogicalOp):
            self._walk_expr(expr.left); self._walk_expr(expr.right)
        elif isinstance(expr, NotOp):
            self._walk_expr(expr.expr)
        elif isinstance(expr, FuncCall):
            if expr.name not in self._funcs:
                self._err("Undeclared Func",
                          f"Call to undeclared function '{expr.name}'",
                          f"Define 'func {expr.name}(...)' before calling it")
            else:
                exp = self._funcs[expr.name]
                got = len(expr.args)
                if got != exp:
                    self._err("Arg Count",
                              f"'{expr.name}' expects {exp} arg(s) but got {got}",
                              f"Pass exactly {exp} argument(s)")
            for a in expr.args: self._walk_expr(a)

    def _infer(self, expr):
        if isinstance(expr, Number):      return "number"
        if isinstance(expr, BoolLiteral): return "boolean"
        if isinstance(expr, TextLiteral): return "string"
        if isinstance(expr, BinOp):
            if expr.op in (">","<",">=","<=","==","!="): return "boolean"
            return "number"
        if isinstance(expr, (LogicalOp, NotOp)): return "boolean"
        return "unknown"


# ══════════════════════════════════════════════════════════════════════════════
#  OPTIMIZER
# ══════════════════════════════════════════════════════════════════════════════
class Optimizer:
    """Constant folding, dead-code elimination, identity reduction."""

    def __init__(self):
        self.opts: list[dict] = []
        self._env: dict = {}   # known constant values

    def optimize(self, prog):
        try:
            if isinstance(prog, Program):
                self._walk_unit(prog.unit)
        except Exception:
            pass
        return self.opts

    def _add(self, kind, original, optimized, desc):
        self.opts.append({"kind": kind, "orig": original,
                          "opt": optimized, "desc": desc})

    def _walk_unit(self, unit):
        if isinstance(unit, Unit):
            for s in unit.statements: self._walk(s)

    def _walk(self, node):
        if node is None: return
        if isinstance(node, VarDecl):
            folded = self._fold(node.value)
            orig   = self._es(node.value)
            if folded is not None:
                if orig != str(folded):
                    self._add("Constant Folding",
                              f"{node.name} = {orig}",
                              f"{node.name} = {folded}",
                              f"Computed '{orig}' at compile time → {folded}")
                self._env[node.name] = folded
            self._check_identity(node.name, node.value)
        elif isinstance(node, tuple) and node[0] == "assign":
            _, name, expr = node
            folded = self._fold(expr)
            orig   = self._es(expr)
            if folded is not None and orig != str(folded):
                self._add("Constant Folding",
                          f"{name} = {orig}",
                          f"{name} = {folded}",
                          f"Computed '{orig}' at compile time → {folded}")
        elif isinstance(node, IfStmt):
            v = self._fold(node.condition)
            if v is True:
                self._add("Dead Code Elimination",
                          f"if ({self._es(node.condition)}) {{ ... }} else {{ ... }}",
                          "always runs then-branch",
                          "Condition is always true — else branch is unreachable dead code")
            elif v is False:
                self._add("Dead Code Elimination",
                          f"if ({self._es(node.condition)}) {{ ... }}",
                          "entire if-block skipped",
                          "Condition is always false — then branch is unreachable dead code")
            for s in node.then_body: self._walk(s)
            if node.else_body:
                for s in node.else_body: self._walk(s)
        elif isinstance(node, WhileStmt):
            v = self._fold(node.condition)
            if v is False:
                self._add("Dead Code Elimination",
                          f"while ({self._es(node.condition)}) {{ ... }}",
                          "loop removed",
                          "Loop condition is always false — body never executes")
            for s in node.body: self._walk(s)
        elif isinstance(node, FuncDecl):
            for s in node.body: self._walk(s)

    def _check_identity(self, name, expr):
        if not isinstance(expr, BinOp): return
        r = expr.right
        if isinstance(r, Number):
            if expr.op in ("+", "-") and r.value == 0:
                self._add("Identity Elimination",
                          f"{name} = {self._es(expr)}",
                          f"{name} = {self._es(expr.left)}",
                          f"Adding/subtracting 0 has no effect")
            elif expr.op == "*" and r.value == 1:
                self._add("Identity Elimination",
                          f"{name} = {self._es(expr)}",
                          f"{name} = {self._es(expr.left)}",
                          "Multiplying by 1 has no effect")
            elif expr.op == "*" and r.value == 0:
                self._add("Strength Reduction",
                          f"{name} = {self._es(expr)}",
                          f"{name} = 0",
                          "Anything multiplied by 0 is always 0")

    def _fold(self, expr):
        if isinstance(expr, Number):      return expr.value
        if isinstance(expr, BoolLiteral): return expr.value
        if isinstance(expr, TextLiteral): return expr.value
        if isinstance(expr, Identifier):  return self._env.get(expr.name)
        if isinstance(expr, BinOp):
            L, R = self._fold(expr.left), self._fold(expr.right)
            if L is None or R is None: return None
            try:
                ops = {"+":lambda a,b:a+b,"-":lambda a,b:a-b,
                       "*":lambda a,b:a*b,"/":lambda a,b:a//b if b else None,
                       ">":lambda a,b:a>b,"<":lambda a,b:a<b,
                       ">=":lambda a,b:a>=b,"<=":lambda a,b:a<=b,
                       "==":lambda a,b:a==b,"!=":lambda a,b:a!=b}
                return ops[expr.op](L, R)
            except: return None
        if isinstance(expr, LogicalOp):
            L, R = self._fold(expr.left), self._fold(expr.right)
            if L is None or R is None: return None
            return (L and R) if expr.op == "and" else (L or R)
        if isinstance(expr, NotOp):
            v = self._fold(expr.expr)
            return not v if v is not None else None
        return None

    def _es(self, expr):
        """Expression → string."""
        if isinstance(expr, Number):      return str(expr.value)
        if isinstance(expr, BoolLiteral): return str(expr.value)
        if isinstance(expr, TextLiteral): return f'"{expr.value}"'
        if isinstance(expr, Identifier):  return expr.name
        if isinstance(expr, BinOp):
            return f"{self._es(expr.left)} {expr.op} {self._es(expr.right)}"
        if isinstance(expr, LogicalOp):
            return f"{self._es(expr.left)} {expr.op} {self._es(expr.right)}"
        if isinstance(expr, NotOp):
            return f"not {self._es(expr.expr)}"
        if isinstance(expr, FuncCall):
            return f"{expr.name}({', '.join(self._es(a) for a in expr.args)})"
        return "?"


# ══════════════════════════════════════════════════════════════════════════════
#  CODE  GENERATOR  (Three-Address Code + Pseudo-Assembly)
# ══════════════════════════════════════════════════════════════════════════════
class CodeGenerator:
    """Produce TAC and pseudo-assembly from an AST."""

    def __init__(self):
        self.tac:      list[str] = []
        self.asm:      list[str] = []
        self.frames:   dict      = {}   # func→{params,tac_lines}
        self._tc  = 0    # temp counter
        self._lc  = 0    # label counter
        self._reg = 0    # register counter

    def _t(self):
        self._tc += 1; return f"t{self._tc}"

    def _l(self, pfx="L"):
        self._lc += 1; return f"{pfx}{self._lc}"

    def _r(self):
        self._reg = (self._reg % 8) + 1; return f"R{self._reg}"

    def generate(self, prog):
        try:
            if isinstance(prog, Program):
                self._gen_unit(prog.unit)
        except Exception:
            pass
        return {"tac": self.tac, "asm": self.asm, "frames": self.frames}

    def _tac(self, s): self.tac.append(s)
    def _asm(self, s): self.asm.append(s)

    def _gen_unit(self, unit):
        if not isinstance(unit, Unit): return
        self._tac(f"BEGIN  {unit.name}")
        self._asm(f"; ══ Unit  {unit.name} ══")
        for s in unit.statements: self._gen_stmt(s)
        self._tac("END")
        self._asm("HALT")

    def _gen_stmt(self, node):
        if isinstance(node, VarDecl):
            res = self._gen_expr(node.value)
            self._tac(f"  {node.name}  =  {res}")
            self._asm(f"  STORE  {res},  [{node.name}]")

        elif isinstance(node, tuple) and node[0] == "assign":
            _, name, expr = node
            res = self._gen_expr(expr)
            self._tac(f"  {name}  =  {res}")
            self._asm(f"  STORE  {res},  [{name}]")

        elif isinstance(node, EmitStmt):
            res = self._gen_expr(node.expr)
            self._tac(f"  PRINT  {res}")
            self._asm(f"  OUT    {res}")

        elif isinstance(node, IfStmt):
            cond   = self._gen_expr(node.condition)
            l_then = self._l("THEN")
            l_else = self._l("ELSE")
            l_end  = self._l("ENDIF")
            self._tac(f"  if {cond} goto {l_then} else goto {l_else}")
            self._asm(f"  CMP    {cond},  #true")
            self._asm(f"  JEQ    {l_then}")
            self._asm(f"  JMP    {l_else}")
            self._tac(f"{l_then}:")
            self._asm(f"{l_then}:")
            for s in node.then_body:  self._gen_stmt(s)
            self._tac(f"  goto {l_end}")
            self._asm(f"  JMP    {l_end}")
            self._tac(f"{l_else}:")
            self._asm(f"{l_else}:")
            if node.else_body:
                for s in node.else_body: self._gen_stmt(s)
            self._tac(f"{l_end}:")
            self._asm(f"{l_end}:")

        elif isinstance(node, WhileStmt):
            l_loop = self._l("LOOP")
            l_body = self._l("BODY")
            l_end  = self._l("WEND")
            self._tac(f"{l_loop}:")
            self._asm(f"{l_loop}:")
            cond = self._gen_expr(node.condition)
            self._tac(f"  if {cond} goto {l_body} else goto {l_end}")
            self._asm(f"  CMP    {cond},  #true")
            self._asm(f"  JEQ    {l_body}")
            self._asm(f"  JMP    {l_end}")
            self._tac(f"{l_body}:")
            self._asm(f"{l_body}:")
            for s in node.body: self._gen_stmt(s)
            self._tac(f"  goto {l_loop}")
            self._asm(f"  JMP    {l_loop}")
            self._tac(f"{l_end}:")
            self._asm(f"{l_end}:")

        elif isinstance(node, FuncDecl):
            self._tac(f"")
            self._tac(f"FUNC  {node.name}({', '.join(node.params)})")
            self._asm(f"")
            self._asm(f"; --- func  {node.name} ---")
            self._asm(f"{node.name}:")
            start = len(self.tac)
            for p in node.params:
                self._tac(f"  PARAM  {p}")
                self._asm(f"  POP    {p}")
            for s in node.body: self._gen_stmt(s)
            self._tac(f"ENDFUNC  {node.name}")
            self._asm(f"  RET")
            self.frames[node.name] = {
                "params": node.params,
                "tac_lines": self.tac[start:]
            }

        elif isinstance(node, ReturnStmt):
            res = self._gen_expr(node.expr)
            self._tac(f"  RETURN  {res}")
            self._asm(f"  PUSH   {res}")
            self._asm(f"  RET")

    def _gen_expr(self, expr) -> str:
        if isinstance(expr, Number):      return str(expr.value)
        if isinstance(expr, BoolLiteral): return str(expr.value).lower()
        if isinstance(expr, TextLiteral): return f'"{expr.value}"'
        if isinstance(expr, Identifier):
            t = self._t(); r = self._r()
            self._tac(f"  {t}  =  {expr.name}")
            self._asm(f"  LOAD   [{expr.name}],  {r}   ; {t}")
            return t
        if isinstance(expr, BinOp):
            L = self._gen_expr(expr.left)
            R = self._gen_expr(expr.right)
            t = self._t(); r = self._r()
            self._tac(f"  {t}  =  {L}  {expr.op}  {R}")
            asm_op = {"+" :"ADD   ","−":"SUB   ","-":"SUB   ",
                      "*" :"MUL   ","/":"DIV   ",
                      ">" :"CMP_GT","<":"CMP_LT",
                      ">=":"CMP_GE","<=":"CMP_LE",
                      "==":"CMP_EQ","!=":"CMP_NE"}.get(expr.op, expr.op)
            self._asm(f"  {asm_op} {L},  {R},  {r}   ; {t}")
            return t
        if isinstance(expr, LogicalOp):
            L = self._gen_expr(expr.left)
            R = self._gen_expr(expr.right)
            t = self._t()
            op = "AND   " if expr.op == "and" else "OR    "
            self._tac(f"  {t}  =  {L}  {expr.op}  {R}")
            self._asm(f"  {op} {L},  {R},  {t}")
            return t
        if isinstance(expr, NotOp):
            v = self._gen_expr(expr.expr)
            t = self._t()
            self._tac(f"  {t}  =  not  {v}")
            self._asm(f"  NOT    {v},  {t}")
            return t
        if isinstance(expr, FuncCall):
            arg_ts = [self._gen_expr(a) for a in expr.args]
            for at in arg_ts:
                self._tac(f"  PUSH_ARG  {at}")
                self._asm(f"  PUSH   {at}")
            t = self._t()
            self._tac(f"  {t}  =  CALL  {expr.name}({', '.join(arg_ts)})")
            self._asm(f"  CALL   {expr.name}")
            self._asm(f"  POP    {t}")
            return t
        return "?"


# ══════════════════════════════════════════════════════════════════════════════
#  MAIN APP
# ══════════════════════════════════════════════════════════════════════════════
class AnexDebugger(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("ANEX  ·  Visual Compiler Debugger")
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        w, h   = min(1480, int(sw*0.94)), min(900, int(sh*0.92))
        self.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")
        self.minsize(1024, 640)
        self.configure(fg_color=C["bg"])
        self._status_msg = tk.StringVar(value="  Ready  —  write code and press  ▶  Run  or  Ctrl+Enter")
        self._build()
        self._load_sample("Hello World")
        # keyboard shortcut
        self.bind("<Control-Return>", lambda e: self._run())
        self.bind("<Control-b>",      lambda e: self._toggle_editor())

    # ─────────────────────────────────────────────────────────────────────────
    def _build(self):
        self._build_topbar()
        self._build_body()
        self._build_statusbar()

    # ── TOP BAR ──────────────────────────────────────────────────────────────
    def _build_topbar(self):
        # ── outer container
        top = tk.Frame(self, bg=C["sidebar"], height=104)
        top.pack(fill="x")
        top.pack_propagate(False)

        # decorative bottom border line
        tk.Frame(self, bg=C["indigo"], height=2).pack(fill="x")

        # ── ROW 1 — branding + run + clock ───────────────────────────────────
        row1 = tk.Frame(top, bg=C["sidebar"], height=56)
        row1.pack(fill="x")
        row1.pack_propagate(False)

        # Logo badge
        logo_outer = tk.Frame(row1, bg=C["indigo"], padx=2, pady=2)
        logo_outer.pack(side="left", padx=(14, 0), pady=10)
        logo_inner = tk.Frame(logo_outer, bg=C["card"])
        logo_inner.pack()
        tk.Label(logo_inner, text="  ANEX  ",
                 font=("Helvetica", 16, "bold"),
                 bg=C["card"], fg=C["green"],
                 padx=10, pady=4).pack(side="left")
        tk.Label(logo_inner, text="Compiler Debugger",
                 font=("Helvetica", 9),
                 bg=C["card"], fg=C["sub"],
                 padx=4, pady=4).pack(side="left")

        # divider
        tk.Frame(row1, bg=C["border"], width=1, height=32).pack(
            side="left", padx=14, pady=9)

        # Examples label + dropdown
        tk.Label(row1, text="Examples",
                 font=("Helvetica", 9),
                 bg=C["sidebar"], fg=C["sub"]).pack(side="left", padx=(0, 6))

        self._sample_var = ctk.StringVar(value="Hello World")
        sample_menu = ctk.CTkOptionMenu(
            row1,
            values=list(SAMPLES.keys()),
            variable=self._sample_var,
            font=ctk.CTkFont(size=11),
            fg_color=C["card"], button_color=C["border"],
            button_hover_color=C["indigo"],
            dropdown_fg_color=C["card"],
            dropdown_hover_color=C["glow_dim"],
            text_color=C["cyan"],
            width=150, height=30, corner_radius=6,
            command=self._load_sample)
        sample_menu.pack(side="left")

        # divider
        tk.Frame(row1, bg=C["border"], width=1, height=32).pack(
            side="left", padx=14, pady=9)

        # Run button — glowing
        self._run_btn = tk.Button(
            row1, text="  ▶   Run Program  ",
            font=("Helvetica", 13, "bold"),
            bg=C["green"], fg=C["bg"],
            activebackground=C["teal"], activeforeground=C["bg"],
            relief="flat", bd=0, padx=16, pady=6,
            cursor="hand2",
            command=self._run)
        self._run_btn.pack(side="left", padx=4)

        # Ctrl+Enter hint
        tk.Label(row1, text="Ctrl+Enter",
                 font=("Helvetica", 8),
                 bg=C["sidebar"], fg=C["muted"]).pack(side="left", padx=(4, 0))

        # clock on far right
        self._clock_lbl = tk.Label(row1, text="",
                                   font=("Courier New", 12, "bold"),
                                   bg=C["sidebar"], fg=C["sub"])
        self._clock_lbl.pack(side="right", padx=16)
        self._update_clock()

        # ── ROW 2 — pipeline + stats ─────────────────────────────────────────
        row2 = tk.Frame(top, bg=C["header"], height=48)
        row2.pack(fill="x")
        row2.pack_propagate(False)

        # pipeline stages
        self._pipe: dict[str, PipeDot] = {}
        stages = [
            ("source", "Source",      C["yellow"]),
            ("lexer",  "Lexer",       C["pink"]),
            ("parser", "Parser",      C["cyan"]),
            ("interp", "Interpreter", C["purple"]),
            ("output", "Output",      C["green"]),
        ]
        for i, (key, lbl, col) in enumerate(stages):
            pd = PipeDot(row2, lbl, col)
            pd.pack(side="left", padx=(14 if i == 0 else 4), pady=0)
            self._pipe[key] = pd
            if key != "output":
                tk.Label(row2, text=" -->",
                         font=("Courier New", 9),
                         bg=C["header"], fg=C["dim"]).pack(side="left")

        # stat pills
        tk.Frame(row2, bg=C["border"], width=1).pack(
            side="left", padx=16, fill="y", pady=6)

        self._stats: dict[str, StatPill] = {}
        pills = [
            ("tok", "tokens",  C["pink"]),
            ("nod", "nodes",   C["cyan"]),
            ("stp", "steps",   C["purple"]),
            ("var", "vars",    C["orange"]),
            ("out", "output",  C["green"]),
            ("ms",  "ms",      C["yellow"]),
        ]
        for key, lbl, col in pills:
            sp = StatPill(row2, lbl, col)
            sp.pack(side="left", padx=3, pady=3)
            self._stats[key] = sp

    def _update_clock(self):
        import datetime
        now = datetime.datetime.now().strftime("%H:%M:%S")
        self._clock_lbl.configure(text=now)
        self.after(1000, self._update_clock)

    # ── BODY  =  editor (left)  +  tab panel (right) ─────────────────────────
    def _build_body(self):
        body = tk.Frame(self, bg=C["bg"])
        body.pack(fill="both", expand=True)
        body.columnconfigure(0, weight=38)
        body.columnconfigure(1, weight=62)
        body.rowconfigure(0, weight=1)
        self._body = body
        self._editor_minimized = False
        self._build_editor(body)
        self._build_viewer(body)

    # ── EDITOR ───────────────────────────────────────────────────────────────
    def _build_editor(self, parent):
        col = tk.Frame(parent, bg=C["sidebar"])
        col.grid(row=0, column=0, sticky="nsew")
        self._editor_col = col

        # ── file tab header (VS Code style) ──────────────────────────────────
        tab_strip = tk.Frame(col, bg=C["bg"], height=38)
        tab_strip.pack(fill="x"); tab_strip.pack_propagate(False)

        # Active file tab
        file_tab = tk.Frame(tab_strip, bg=C["sidebar"])
        file_tab.pack(side="left")
        tk.Frame(file_tab, bg=C["green"], height=2).pack(fill="x")  # top accent
        file_hdr = tk.Frame(file_tab, bg=C["sidebar"])
        file_hdr.pack(fill="both", expand=True)
        tk.Label(file_hdr, text=" >> ",
                 font=("Helvetica", 11),
                 bg=C["sidebar"], fg=C["yellow"],
                 pady=6).pack(side="left")
        tk.Label(file_hdr, text="main.anex",
                 font=("Helvetica", 10, "bold"),
                 bg=C["sidebar"], fg=C["text"],
                 pady=6).pack(side="left")
        tk.Label(file_hdr, text="  [x]  ",
                 font=("Helvetica", 10),
                 bg=C["sidebar"], fg=C["muted"],
                 pady=6).pack(side="left")

        # minimize button
        self._minimize_btn = tk.Button(
            tab_strip, text="«",
            font=("Helvetica", 11, "bold"),
            bg=C["bg"], fg=C["muted"],
            activebackground=C["border"], activeforeground=C["sub"],
            relief="flat", bd=0, padx=8, pady=8,
            cursor="hand2",
            command=self._toggle_editor)
        self._minimize_btn.pack(side="right")

        self._line_lbl = tk.Label(tab_strip, text="",
                                  font=("Courier New", 9),
                                  bg=C["bg"], fg=C["muted"])
        self._line_lbl.pack(side="right", padx=10)

        # ── gutter + editor ───────────────────────────────────────────────────
        edit_frame = tk.Frame(col, bg=C["sidebar"])
        edit_frame.pack(fill="both", expand=True)

        self._gutter = tk.Text(
            edit_frame, width=4,
            bg=C["header"], fg=C["muted"],
            font=("Courier New", 12),
            state="disabled", relief="flat", bd=0,
            highlightthickness=0,
            selectbackground=C["header"])
        self._gutter.pack(side="left", fill="y")

        # thin separator
        tk.Frame(edit_frame, bg=C["indigo"], width=2).pack(side="left", fill="y")

        self._editor = tk.Text(
            edit_frame,
            bg=C["sidebar"], fg=C["text"],
            font=("Courier New", 13),
            insertbackground=C["green"],
            relief="flat", bd=0,
            selectbackground=C["glow_dim"],
            wrap="none", undo=True,
            highlightthickness=0,
            padx=12, pady=8,
            tabs=("1.6c",),
            spacing1=2, spacing3=2)

        esb = ctk.CTkScrollbar(edit_frame, command=self._editor.yview,
                               button_color=C["border"],
                               button_hover_color=C["sub"], width=8)
        self._editor.configure(yscrollcommand=esb.set)
        esb.pack(side="right", fill="y")
        self._editor.pack(side="left", fill="both", expand=True)
        self._editor.bind("<KeyRelease>", self._on_edit)
        self._editor.bind("<MouseWheel>",
            lambda e: self._gutter.yview_moveto(self._editor.yview()[0]))

        # ── run button bar ────────────────────────────────────────────────────
        run_bar = tk.Frame(col, bg=C["header"], height=52)
        run_bar.pack(fill="x"); run_bar.pack_propagate(False)
        # accent top line
        tk.Frame(run_bar, bg=C["border"], height=1).pack(fill="x")

        btn_frame = tk.Frame(run_bar, bg=C["header"])
        btn_frame.pack(fill="both", expand=True, padx=10, pady=6)

        self._run_btn = tk.Button(
            btn_frame,
            text="  ▶   Run Program  ",
            font=("Helvetica", 14, "bold"),
            bg=C["green"], fg=C["bg"],
            activebackground=C["teal"], activeforeground=C["bg"],
            relief="flat", bd=0,
            cursor="hand2",
            command=self._run)
        self._run_btn.pack(fill="x", ipady=7)

    # ── VIEWER  (tab bar + stacked panels) ───────────────────────────────────
    def _build_viewer(self, parent):
        col = tk.Frame(parent, bg=C["panel"])
        col.grid(row=0, column=1, sticky="nsew")

        TABS = [
            ("tokens",   "  [ TOKENS ]  ",      C["pink"]),
            ("ast",      "  [ AST ]  ",          C["cyan"]),
            ("exec",     "  [ EXECUTION ]  ",    C["purple"]),
            ("env",      "  [ SYMBOL TABLE ]  ", C["orange"]),
            ("semantic", "  [ SEMANTIC ]  ",     C["teal"]),
            ("optimize", "  [ OPTIMIZER ]  ",    C["yellow"]),
            ("codegen",  "  [ CODE GEN ]  ",     C["blue"]),
            ("output",   "  [ OUTPUT ]  ",       C["green"]),
            ("howto",    "  [ GUIDE ]  ",        C["sub"]),
        ]

        # tab bar row
        tabbar_row = tk.Frame(col, bg=C["tab_bar"], height=TabBar.TAB_H)
        tabbar_row.pack(fill="x"); tabbar_row.pack_propagate(False)

        # restore button — visible only when editor is minimized
        self._restore_btn = tk.Button(
            tabbar_row, text="»",
            font=("Helvetica", 13, "bold"),
            bg=C["tab_bar"], fg=C["yellow"],
            activebackground=C["glow_dim"], activeforeground=C["yellow"],
            relief="flat", bd=0, padx=10,
            cursor="hand2",
            command=self._toggle_editor)
        # don't pack yet

        self._tabbar = TabBar(tabbar_row, TABS, self._switch_tab)
        self._tabbar.pack(side="left", fill="both", expand=True)

        # thin accent line under tab bar
        self._tab_accent = tk.Frame(col, bg=C["pink"], height=2)
        self._tab_accent.pack(fill="x")

        # content stack
        stack = tk.Frame(col, bg=C["panel"])
        stack.pack(fill="both", expand=True)

        self._frames: dict[str, tk.Frame] = {}
        for key, _, _ in TABS:
            f = tk.Frame(stack, bg=C["panel"])
            f.place(relx=0, rely=0, relwidth=1, relheight=1)
            self._frames[key] = f

        # build content inside each frame
        self._rtok   = self._scrollbox(self._frames["tokens"],
                                       title=">> LEXER TOKENS", col=C["pink"])
        self._rast   = self._build_ast_panel(self._frames["ast"])
        self._rexec  = self._scrollbox(self._frames["exec"],
                                       title=">> EXECUTION TRACE", col=C["purple"])
        self._renv   = self._scrollbox(self._frames["env"],
                                       title=">> SYMBOL TABLE", col=C["orange"])
        self._rsem   = self._scrollbox(self._frames["semantic"],
                                       title=">> SEMANTIC ANALYSIS", col=C["teal"])
        self._ropt   = self._scrollbox(self._frames["optimize"],
                                       title=">> OPTIMIZER", col=C["yellow"])
        self._rcgen  = self._build_codegen_panel(self._frames["codegen"])
        self._rout   = self._scrollbox(self._frames["output"], fontsize=13,
                                       title=">> PROGRAM OUTPUT", col=C["green"])
        self._build_guide(self._frames["howto"])

        self._tab_colours = {k: c for k, _, c in TABS}
        self._switch_tab("tokens")

    # ── STATUS BAR ───────────────────────────────────────────────────────────
    def _build_statusbar(self):
        bar = tk.Frame(self, bg=C["header"], height=26)
        bar.pack(fill="x", side="bottom")
        bar.pack_propagate(False)
        tk.Frame(bar, bg=C["indigo"], height=1).pack(fill="x")
        inner = tk.Frame(bar, bg=C["header"])
        inner.pack(fill="both", expand=True)

        # status message
        tk.Label(inner, textvariable=self._status_msg,
                 font=("Helvetica", 9),
                 bg=C["header"], fg=C["sub"],
                 anchor="w").pack(side="left", padx=12)

        # right side info
        info_items = [
            ("ANEX  v2.0", C["green"]),
            ("|", C["border"]),
            ("Compiler Construction", C["indigo"]),
            ("|", C["border"]),
            ("Ctrl+Enter = Run", C["muted"]),
            ("|", C["border"]),
            ("Ctrl+B = Toggle Editor", C["muted"]),
        ]
        for text, col in reversed(info_items):
            tk.Label(inner, text=text,
                     font=("Helvetica", 9),
                     bg=C["header"], fg=col).pack(side="right", padx=5)

    def _set_status(self, msg: str, col: str = ""):
        self._status_msg.set(f"  {msg}")

    # ── MINIMIZE / RESTORE EDITOR  (VS Code style) ───────────────────────────
    def _toggle_editor(self):
        if self._editor_minimized:
            self._editor_col.grid(row=0, column=0, sticky="nsew")
            self._body.columnconfigure(0, weight=38)
            self._body.columnconfigure(1, weight=62)
            self._restore_btn.pack_forget()
            self._editor_minimized = False
            self._set_status("Editor restored")
        else:
            self._editor_col.grid_remove()
            self._body.columnconfigure(0, weight=0)
            self._body.columnconfigure(1, weight=1)
            self._restore_btn.pack(side="left", padx=(4, 0))
            self._editor_minimized = True
            self._set_status("Editor minimized  —  press » to restore")

    def _scrollbox(self, parent, fontsize=11, title="", col="") -> RichText:
        """Create a RichText with optional panel header and scrollbar."""
        if title:
            hdr = tk.Frame(parent, bg=C["header"], height=32)
            hdr.pack(fill="x"); hdr.pack_propagate(False)
            # coloured left accent bar
            tk.Frame(hdr, bg=col or C["indigo"], width=3).pack(side="left", fill="y")
            tk.Label(hdr, text=f"  {title}",
                     font=("Helvetica", 10, "bold"),
                     bg=C["header"], fg=col or C["text"],
                     pady=7).pack(side="left")
        container = tk.Frame(parent, bg=C["card"])
        container.pack(fill="both", expand=True)
        rt = RichText(container, fontsize=fontsize, bg=C["card"])
        sb = ctk.CTkScrollbar(container, command=rt.yview,
                              button_color=C["border"],
                              button_hover_color=C["sub"], width=8)
        rt.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y", padx=1, pady=4)
        rt.pack(side="left", fill="both", expand=True, padx=(8, 0), pady=4)
        return rt

    def _build_ast_panel(self, parent) -> "ASTTreeCanvas":
        # panel header
        hdr = tk.Frame(parent, bg=C["header"], height=32)
        hdr.pack(fill="x"); hdr.pack_propagate(False)
        tk.Frame(hdr, bg=C["cyan"], width=3).pack(side="left", fill="y")
        tk.Label(hdr, text="  ABSTRACT SYNTAX TREE",
                 font=("Helvetica", 10, "bold"),
                 bg=C["header"], fg=C["cyan"], pady=7).pack(side="left")
        tk.Label(hdr, text="  Click node to collapse / expand  |  Scroll to pan horizontally",
                 font=("Helvetica", 8),
                 bg=C["header"], fg=C["muted"]).pack(side="left", padx=8)

        area = tk.Frame(parent, bg=C["card"])
        area.pack(fill="both", expand=True, padx=4, pady=(0, 4))

        vsb = ctk.CTkScrollbar(area, width=8,
                               button_color=C["border"],
                               button_hover_color=C["sub"])
        hsb = ctk.CTkScrollbar(area, orientation="horizontal", height=8,
                               button_color=C["border"],
                               button_hover_color=C["sub"])
        canvas = ASTTreeCanvas(area, xscrollcommand=hsb.set, yscrollcommand=vsb.set)
        vsb.configure(command=canvas.yview)
        hsb.configure(command=canvas.xview)
        vsb.pack(side="right",  fill="y")
        hsb.pack(side="bottom", fill="x")
        canvas.pack(side="left", fill="both", expand=True)
        return canvas

    def _build_codegen_panel(self, parent) -> dict:
        hdr = tk.Frame(parent, bg=C["header"], height=32)
        hdr.pack(fill="x"); hdr.pack_propagate(False)
        tk.Frame(hdr, bg=C["blue"], width=3).pack(side="left", fill="y")
        tk.Label(hdr, text="  CODE GENERATION  —  TAC  +  Pseudo-Assembly",
                 font=("Helvetica", 10, "bold"),
                 bg=C["header"], fg=C["blue"], pady=7).pack(side="left")

        pane = tk.Frame(parent, bg=C["panel"])
        pane.pack(fill="both", expand=True)
        pane.columnconfigure(0, weight=1)
        pane.columnconfigure(1, weight=1)
        pane.rowconfigure(0, weight=1)

        # TAC pane
        left = tk.Frame(pane, bg=C["panel"])
        left.grid(row=0, column=0, sticky="nsew", padx=(4,2), pady=4)
        lhdr = tk.Frame(left, bg=C["glow_dim"], height=26)
        lhdr.pack(fill="x"); lhdr.pack_propagate(False)
        tk.Frame(lhdr, bg=C["cyan"], width=2).pack(side="left", fill="y")
        tk.Label(lhdr, text="  THREE-ADDRESS CODE (TAC)",
                 font=("Helvetica", 9, "bold"),
                 bg=C["glow_dim"], fg=C["cyan"], pady=5).pack(side="left")
        tac_box = self._scrollbox(left)

        # Assembly pane
        right = tk.Frame(pane, bg=C["panel"])
        right.grid(row=0, column=1, sticky="nsew", padx=(2,4), pady=4)
        rhdr = tk.Frame(right, bg=C["glow_dim"], height=26)
        rhdr.pack(fill="x"); rhdr.pack_propagate(False)
        tk.Frame(rhdr, bg=C["purple"], width=2).pack(side="left", fill="y")
        tk.Label(rhdr, text="  PSEUDO-ASSEMBLY",
                 font=("Helvetica", 9, "bold"),
                 bg=C["glow_dim"], fg=C["purple"], pady=5).pack(side="left")
        asm_box = self._scrollbox(right)

        return {"tac": tac_box, "asm": asm_box}

    def _switch_tab(self, key: str):
        for k, f in self._frames.items():
            f.lift() if k == key else f.lower()
        col = self._tab_colours.get(key, C["pink"])
        self._tab_accent.configure(bg=col)
        self._set_status(f"Viewing: {key.upper()}")

    # ── GUIDE PANEL ──────────────────────────────────────────────────────────
    def _build_guide(self, parent):
        # header
        hdr = tk.Frame(parent, bg=C["header"], height=32)
        hdr.pack(fill="x"); hdr.pack_propagate(False)
        tk.Frame(hdr, bg=C["sub"], width=3).pack(side="left", fill="y")
        tk.Label(hdr, text="  COMPILER PIPELINE — HOW IT WORKS",
                 font=("Helvetica", 10, "bold"),
                 bg=C["header"], fg=C["sub"], pady=7).pack(side="left")

        # scrollable canvas
        canvas = tk.Canvas(parent, bg=C["card"], highlightthickness=0)
        vsb = ctk.CTkScrollbar(parent, command=canvas.yview,
                               button_color=C["border"],
                               button_hover_color=C["sub"], width=8)
        canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        inner = tk.Frame(canvas, bg=C["card"])
        canvas.create_window((0, 0), window=inner, anchor="nw")
        inner.bind("<Configure>",
                   lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

        PIPELINE_STEPS = [
            ("1", C["yellow"],  "SOURCE CODE",
             "Write ANEX code in the editor on the left.\n"
             "Press  Run Program  or Ctrl+Enter to execute.\n"
             "The source is the starting point for the entire compiler pipeline."),
            ("2", C["pink"],    "LEXER  ->  TOKENS",
             "The Lexer (Lexical Analyser) reads source character by character\n"
             "and groups them into typed tokens:\n"
             "  KEYWORD  NUMBER  STRING  OP  SYM  IDENT  EOF\n"
             "This is the first phase of every compiler — also called scanning."),
            ("3", C["cyan"],    "PARSER  ->  AST",
             "The Parser reads the token stream and builds an Abstract Syntax Tree.\n"
             "The AST captures the structure and hierarchy of the program.\n"
             "Click any node to collapse its subtree. This is the second phase."),
            ("4", C["purple"],  "INTERPRETER  ->  EXECUTION",
             "The Interpreter walks the AST node by node.\n"
             "Every variable declaration, expression evaluation,\n"
             "branch decision, and function call is traced step by step."),
            ("5", C["orange"],  "SYMBOL TABLE",
             "Tracks every identifier in the program:\n"
             "  Variables — name, type, scope, current value, update count\n"
             "  Functions — params, call count, last return value\n"
             "Also shows the call stack at end of execution."),
            ("6", C["teal"],    "SEMANTIC ANALYSIS",
             "Checks meaning and correctness beyond grammar rules:\n"
             "  - Type checking  — are values used with the right types?\n"
             "  - Scope rules    — are variables declared before use?\n"
             "  - Duplicate decl — same name declared twice?\n"
             "  - Arg counts     — function calls match declarations?"),
            ("7", C["yellow"],  "OPTIMIZER",
             "Applies compile-time optimizations:\n"
             "  - Constant Folding       — 2 + 3  ->  5\n"
             "  - Dead Code Elimination  — remove unreachable branches\n"
             "  - Identity Elimination   — x + 0  ->  x\n"
             "  - Strength Reduction     — x * 0  ->  0"),
            ("8", C["blue"],    "CODE GENERATION",
             "Translates the AST into lower-level representations:\n"
             "  - Three-Address Code — intermediate form with temp variables\n"
             "  - Pseudo-Assembly    — LOAD/STORE/ADD/CMP/JMP instructions\n"
             "  - Labels for control flow  +  PUSH/CALL/RET for functions"),
            ("9", C["green"],   "OUTPUT",
             "Every  emit(value)  statement prints a line here.\n"
             "This is the program's final visible result.\n"
             "The output stage completes the full compiler pipeline."),
        ]

        for step, col, heading, body_text in PIPELINE_STEPS:
            card = tk.Frame(inner, bg=C["header"],
                            highlightbackground=C["border"],
                            highlightthickness=1)
            card.pack(fill="x", padx=12, pady=5)

            # step number badge
            badge = tk.Frame(card, bg=col, width=32)
            badge.pack(side="left", fill="y")
            badge.pack_propagate(False)
            tk.Label(badge, text=step,
                     font=("Courier New", 13, "bold"),
                     bg=col, fg=C["bg"]).pack(expand=True)

            # content
            content = tk.Frame(card, bg=C["header"])
            content.pack(side="left", fill="both", expand=True, padx=14, pady=10)

            tk.Label(content, text=heading,
                     font=("Helvetica", 12, "bold"),
                     bg=C["header"], fg=col,
                     anchor="w").pack(fill="x")

            tk.Label(content, text=body_text,
                     font=("Helvetica", 10),
                     bg=C["header"], fg=C["sub"],
                     anchor="w", justify="left").pack(fill="x", pady=(4, 0))

        # pipeline diagram at bottom
        diag = tk.Frame(inner, bg=C["card"])
        diag.pack(fill="x", padx=12, pady=(8, 16))
        tk.Label(diag, text="Full Pipeline:",
                 font=("Helvetica", 9, "bold"),
                 bg=C["card"], fg=C["muted"]).pack(side="left", padx=(8, 4))
        stages_diag = [
            ("Source", C["yellow"]), ("->", C["dim"]),
            ("Lexer",  C["pink"]),   ("->", C["dim"]),
            ("Parser", C["cyan"]),   ("->", C["dim"]),
            ("Interp", C["purple"]), ("->", C["dim"]),
            ("Symbols",C["orange"]), ("->", C["dim"]),
            ("Sem",    C["teal"]),   ("->", C["dim"]),
            ("Opt",    C["yellow"]), ("->", C["dim"]),
            ("CodeGen",C["blue"]),   ("->", C["dim"]),
            ("Output", C["green"]),
        ]
        for text, col in stages_diag:
            tk.Label(diag, text=text,
                     font=("Courier New", 9, "bold") if text != "->" else ("Courier New", 9),
                     bg=C["card"], fg=col).pack(side="left", padx=1)

    # ── EDITOR HELPERS ────────────────────────────────────────────────────────
    def _load_sample(self, name: str):
        self._editor.delete("1.0", "end")
        self._editor.insert("1.0", SAMPLES[name])
        self._hl()
        self._update_gutter()

    def _on_edit(self, _=None):
        self._update_gutter()
        self._hl()

    def _update_gutter(self):
        n = int(self._editor.index("end-1c").split(".")[0])
        self._line_lbl.configure(text=f"{n} lines")
        self._gutter.configure(state="normal")
        self._gutter.delete("1.0", "end")
        self._gutter.insert("1.0", "\n".join(f" {i} " for i in range(1, n+1)))
        self._gutter.configure(state="disabled")
        self._gutter.yview_moveto(self._editor.yview()[0])

    def _hl(self):
        src = self._editor.get("1.0", "end")
        for t in self._editor.tag_names():
            if t.startswith("hl_"):
                self._editor.tag_remove(t, "1.0", "end")

        def cfg(name: str, colour: str, bold: bool = False) -> None:
            f = ("Courier New", 13, "bold") if bold else ("Courier New", 13)
            self._editor.tag_configure(name, foreground=colour, font=f)

        def mark(name: str, a: int, b: int) -> None:
            self._editor.tag_add(name, f"1.0+{a}c", f"1.0+{b}c")

        cfg("hl_str", C["STRING"])
        cfg("hl_kw",  C["KEYWORD"], bold=True)
        cfg("hl_num", C["NUMBER"])
        cfg("hl_op",  C["OP"])
        cfg("hl_cmt", C["muted"])

        for m in re.finditer(r'"[^"]*"', src):
            mark("hl_str", m.start(), m.end())
        for m in re.finditer(r'\b(' + '|'.join(KEYWORDS) + r')\b', src):
            mark("hl_kw", m.start(), m.end())
        for m in re.finditer(r'\b\d+\b', src):
            mark("hl_num", m.start(), m.end())
        for m in re.finditer(r'[+\-*/=<>!]+', src):
            mark("hl_op", m.start(), m.end())
        for m in re.finditer(r'#[^\n]*', src):
            mark("hl_cmt", m.start(), m.end())

    # ── PIPELINE ──────────────────────────────────────────────────────────────
    def _pipe_reset(self):
        for pd in self._pipe.values(): pd.off()

    def _pipe_on(self, key: str):
        self._pipe[key].on()

    # ── RUN ───────────────────────────────────────────────────────────────────
    def _run(self):
        self._run_btn.configure(state="disabled", text="  >>  Running...",
                                bg=C["border"], fg=C["muted"])
        self._set_status("Running pipeline…")
        self._pipe_reset()
        for rt in [self._rtok, self._rast, self._rexec, self._renv,
                   self._rsem, self._ropt,
                   self._rcgen["tac"], self._rcgen["asm"], self._rout]:
            rt.clear()
        for s in self._stats.values(): s.reset()
        threading.Thread(target=self._pipeline, daemon=True).start()

    def _pipeline(self):
        src = self._editor.get("1.0", "end")
        t0  = time.perf_counter()

        self.after(0,  lambda: self._pipe_on("source"))

        # LEX
        try:
            lex = Lexer(src); tokens = []
            while True:
                tok = lex.get_next_token(); tokens.append(tok)
                if tok.kind == "EOF": break
        except Exception as e:
            self.after(0, lambda err=e: self._err(str(err), "Lexer Error")); return

        self.after(60, lambda: self._pipe_on("lexer"))
        self.after(60, lambda: self._render_tokens(tokens))

        # PARSE
        try:
            prog = Parser(Lexer(src)).parse()
        except Exception as e:
            self.after(160, lambda err=e: self._err(str(err), "Parser Error")); return

        ms = round((time.perf_counter() - t0) * 1000, 1)
        self.after(160, lambda: self._pipe_on("parser"))
        self.after(160, lambda: self._render_ast(prog))
        self.after(160, lambda: self._stats["ms"].set(ms))

        # SEMANTIC ANALYSIS
        sem = SemanticAnalyzer()
        sem_errs, sem_warns, sem_checks = sem.analyze(prog)
        self.after(220, lambda: self._render_semantic(sem_errs, sem_warns, sem_checks))

        # OPTIMIZATION
        opt = Optimizer()
        opt_list = opt.optimize(prog)
        self.after(240, lambda: self._render_optimizer(opt_list))

        # CODE GENERATION
        cg = CodeGenerator()
        cg_result = cg.generate(prog)
        self.after(260, lambda: self._render_codegen(cg_result))

        # INTERPRET
        interp = TracingInterpreter()
        err_msg = None
        try:
            interp.run(prog)
        except Exception as e:
            err_msg = str(e)

        self.after(300, lambda: self._pipe_on("interp"))
        self.after(300, lambda: self._render_exec(interp.steps))
        self.after(300, lambda: self._render_env(
            interp.env, interp.functions,
            interp.var_info, interp.func_call_counts,
            interp.func_return_vals, interp.call_stack))
        self.after(300, lambda: self._stats["stp"].set(len(interp.steps)))
        self.after(300, lambda: self._stats["var"].set(len(interp.env)))

        if err_msg:
            self.after(300, lambda m=err_msg: self._err(m, "Runtime Error"))

        self.after(420, lambda: self._pipe_on("output"))
        self.after(420, lambda: self._render_output(interp.outputs))
        self.after(420, lambda: self._stats["out"].set(len(interp.outputs)))
        self.after(420, lambda: self._count_nodes(prog))
        self.after(520, lambda: self._run_btn.configure(
            state="normal", text="  ▶   Run Program  ",
            bg=C["green"], fg=C["bg"]))
        self.after(520, lambda: self._set_status(
            f"Done  —  {len(interp.steps)} steps  ·  {len(interp.outputs)} output(s)  ·  {round((time.perf_counter()-t0)*1000,1)} ms"))

        # auto-switch to output tab if there's output
        if interp.outputs:
            self.after(500, lambda: self._switch_tab("output"))

    # ── RENDER: TOKENS ────────────────────────────────────────────────────────
    def _render_tokens(self, tokens):
        b = self._rtok; b.clear()
        real = [t for t in tokens if t.kind != "EOF"]

        # header
        b.w(f"\n  {len(real)} tokens found\n\n", C["muted"])

        # legend row
        counts: dict[str,int] = {}
        for t in real: counts[t.kind] = counts.get(t.kind, 0) + 1
        b.w("  ", C["muted"])
        for kind, n in counts.items():
            b.w(f" {kind}", C.get(kind, C["muted"]), bold=True)
            b.w(f"×{n} ", C["muted"])
        b.w("\n\n", C["muted"])

        # separator
        b.w("  " + "─" * 58 + "\n\n", C["border"])

        # each token
        for i, tok in enumerate(tokens):
            col = C.get(tok.kind, C["muted"])
            val = f'"{tok.value}"' if isinstance(tok.value, str) else str(tok.value)
            # row number
            b.w(f"  {i+1:>3}  ", C["dim"])
            # kind badge
            b.w(f" {tok.kind:<8} ", col, bold=True)
            # value
            b.w(f"  {val:<24}", C["text"])
            # line number
            b.w(f"  line {tok.line}\n", C["muted"])

        self._stats["tok"].set(len(real))
        self._tabbar.flash("tokens")

    # ── RENDER: AST ───────────────────────────────────────────────────────────
    def _render_ast(self, prog):
        tree = ast_tree(prog)
        self._rast.load(tree)

    def _count_nodes(self, node):
        n = [0]
        def walk(x):
            if x is None: return
            n[0] += 1
            for a in ("unit","statements","then_body","else_body","body",
                      "args","left","right","expr","condition","value"):
                ch = getattr(x, a, None)
                if ch is None: continue
                if isinstance(ch, list):
                    for c in ch: walk(c)
                elif hasattr(ch, "__class__") and \
                     ch.__class__.__module__ not in ("builtins",):
                    walk(ch)
        walk(node)
        self._stats["nod"].set(n[0])

    # ── RENDER: EXEC ──────────────────────────────────────────────────────────
    def _render_exec(self, steps):
        b = self._rexec; b.clear()
        b.w(f"\n  {len(steps)} execution steps\n\n", C["muted"])
        b.w("  " + "─" * 58 + "\n\n", C["border"])

        for i, (kind, msg) in enumerate(steps, 1):
            col  = STEP_COL.get(kind, C["muted"])
            icon = STEP_ICON.get(kind, "·")
            b.w(f"  {i:>4}  ", C["dim"])
            b.w(f" {icon} ", col, bold=True)
            b.w(f" {kind:<8} ", col)
            b.w("  " + msg + "\n", C["text"])

        b.tip()

    # ── RENDER: SYMBOL TABLE (enhanced Environment) ──────────────────────────
    def _render_env(self, env, functions, var_info=None,
                    func_call_counts=None, func_return_vals=None,
                    call_stack=None):
        b = self._renv; b.clear()
        var_info        = var_info        or {}
        func_call_counts = func_call_counts or {}
        func_return_vals = func_return_vals or {}
        call_stack      = call_stack      or []

        # ── Symbol Table ──────────────────────────────────────────────────────
        b.w("\n  SYMBOL TABLE\n", C["orange"], bold=True)
        b.w("  " + "─" * 68 + "\n", C["border"])
        # header row
        b.w(f"  {'NAME':<16}", C["muted"], bold=True)
        b.w(f"  {'TYPE':<8}",  C["muted"], bold=True)
        b.w(f"  {'SCOPE':<14}",C["muted"], bold=True)
        b.w(f"  {'VALUE':<18}",C["muted"], bold=True)
        b.w(f"  {'UPDATES'}\n",C["muted"], bold=True)
        b.w("  " + "─" * 68 + "\n", C["border"])

        if env:
            for name, val in env.items():
                info  = var_info.get(name, {})
                typ   = info.get("type", "?")
                scope = info.get("scope", "global")
                upds  = info.get("updates", 0)
                if isinstance(val, bool):  vcol = C["pink"]
                elif isinstance(val, str): vcol = C["green"]
                elif isinstance(val, int): vcol = C["yellow"]
                else:                      vcol = C["cyan"]
                disp = f'"{val}"' if isinstance(val, str) else str(val)

                b.w(f"  {name:<16}", C["text"])
                b.w(f"  {typ:<8}",   C["cyan"])
                b.w(f"  {scope:<14}",C["muted"])
                b.w(f"  {disp:<18}", vcol, bold=True)
                b.w(f"  {upds}×\n",  C["dim"])
        else:
            b.w("\n  No variables declared.\n", C["muted"])

        # ── Function Registry ─────────────────────────────────────────────────
        if functions:
            b.w("\n\n  FUNCTION REGISTRY\n", C["purple"], bold=True)
            b.w("  " + "─" * 68 + "\n", C["border"])
            b.w(f"  {'NAME':<16}", C["muted"], bold=True)
            b.w(f"  {'PARAMS':<24}",C["muted"], bold=True)
            b.w(f"  {'CALLS':<8}", C["muted"], bold=True)
            b.w(f"  {'LAST RETURN'}\n", C["muted"], bold=True)
            b.w("  " + "─" * 68 + "\n", C["border"])
            for fname, fn in functions.items():
                calls  = func_call_counts.get(fname, 0)
                retval = func_return_vals.get(fname, "—")
                params = f"({', '.join(fn.params)})" if fn.params else "()"
                b.w(f"  {fname:<16}", C["yellow"], bold=True)
                b.w(f"  {params:<24}", C["muted"])
                b.w(f"  {calls:<8}", C["cyan"])
                b.w(f"  {retval}\n",  C["green"])

        # ── Call Stack (snapshot) ─────────────────────────────────────────────
        b.w("\n\n  CALL STACK  (at end of execution)\n", C["teal"], bold=True)
        b.w("  " + "─" * 68 + "\n", C["border"])
        if call_stack:
            for i, frame in enumerate(reversed(call_stack)):
                depth = len(call_stack) - i
                b.w(f"  [{depth}] ", C["dim"])
                b.w(f"{frame['name']}", C["purple"], bold=True)
                params_str = ", ".join(f"{k}={v}" for k,v in frame.get("params",{}).items())
                b.w(f"({params_str})\n", C["muted"])
        else:
            b.w("  Stack is empty — all calls returned normally.\n", C["muted"])

        total = len(env) + len(functions)
        self._stats["var"].set(total)

    # ── RENDER: SEMANTIC ANALYSIS ─────────────────────────────────────────────
    def _render_semantic(self, errors, warnings, checks):
        b = self._rsem; b.clear()

        # summary banner
        if not errors and not warnings:
            b.w("\n  ✔  Semantic Analysis Passed — No Issues Found\n",
                C["green"], bold=True)
        else:
            total = len(errors) + len(warnings)
            b.w(f"\n  Found {len(errors)} error(s),  {len(warnings)} warning(s)\n",
                C["red"] if errors else C["yellow"], bold=True)
        b.w("  " + "─" * 60 + "\n\n", C["border"])

        # errors
        if errors:
            b.w("  ERRORS\n", C["red"], bold=True)
            b.w("  " + "─" * 60 + "\n", C["border"])
            for e in errors:
                b.w(f"\n  ✕  ", C["red"], bold=True)
                b.w(f"[{e['kind']}]  ", C["pink"], bold=True)
                b.w(f"{e['msg']}\n", C["text"])
                if e.get("sug"):
                    b.w(f"     TIP: {e['sug']}\n", C["muted"])
            b.w("\n", C["muted"])

        # warnings
        if warnings:
            b.w("  WARNINGS\n", C["yellow"], bold=True)
            b.w("  " + "─" * 60 + "\n", C["border"])
            for w in warnings:
                b.w(f"\n  ⚠  ", C["yellow"], bold=True)
                b.w(f"[{w['kind']}]  ", C["orange"], bold=True)
                b.w(f"{w['msg']}\n", C["text"])
                if w.get("sug"):
                    b.w(f"     TIP: {w['sug']}\n", C["muted"])
            b.w("\n", C["muted"])

        # passed checks
        if checks:
            b.w("  PASSED CHECKS\n", C["teal"], bold=True)
            b.w("  " + "─" * 60 + "\n", C["border"])
            for c in checks:
                b.w(f"\n  ✔  ", C["teal"], bold=True)
                b.w(f"{c['msg']}\n", C["muted"])

        # explanation
        b.w("\n\n  WHAT IS SEMANTIC ANALYSIS?\n", C["cyan"], bold=True)
        b.w("  " + "─" * 60 + "\n", C["border"])
        for line in [
            "  Semantic Analysis is the 4th stage of a compiler.",
            "  It checks meaning and correctness beyond grammar rules:",
            "",
            "  • Type Checking   — Are values used with the right types?",
            "  • Scope Rules     — Are variables declared before use?",
            "  • Duplicate Decl  — Is the same name declared twice?",
            "  • Arg Counts      — Do function calls match declarations?",
            "",
            "  The parser only checks syntax (shape of code).",
            "  The semantic analyser checks logic (meaning of code).",
        ]:
            b.w(line + "\n", C["muted"])

    # ── RENDER: OPTIMIZER ────────────────────────────────────────────────────
    def _render_optimizer(self, opts):
        b = self._ropt; b.clear()

        b.w(f"\n  Optimizer found {len(opts)} optimization(s)\n",
            C["yellow"] if opts else C["muted"], bold=True)
        b.w("  " + "─" * 60 + "\n\n", C["border"])

        KIND_COL = {
            "Constant Folding":     C["cyan"],
            "Dead Code Elimination":C["red"],
            "Identity Elimination": C["orange"],
            "Strength Reduction":   C["purple"],
        }

        if opts:
            for i, o in enumerate(opts, 1):
                col = KIND_COL.get(o["kind"], C["muted"])
                b.w(f"  {i:>3}  ", C["dim"])
                b.w(f" {o['kind']} \n", col, bold=True)
                b.w(f"       Before  : ", C["muted"])
                b.w(f"{o['orig']}\n",     C["pink"])
                b.w(f"       After   : ", C["muted"])
                b.w(f"{o['opt']}\n",      C["green"])
                b.w(f"       Why     : ", C["muted"])
                b.w(f"{o['desc']}\n\n",   C["text"])
        else:
            b.w("  No optimizations found — code is already optimal.\n\n",
                C["muted"])

        # explanation
        b.w("  OPTIMIZATION TECHNIQUES EXPLAINED\n", C["cyan"], bold=True)
        b.w("  " + "─" * 60 + "\n", C["border"])
        techniques = [
            (C["cyan"],   "Constant Folding",
             "Evaluate constant expressions at compile time.\n"
             "  Example:  x = 2 + 3   →   x = 5\n"
             "  No need for the CPU to add 2+3 every time the program runs."),
            (C["red"],    "Dead Code Elimination",
             "Remove code that can never be executed.\n"
             "  Example:  if (false) { ... }  →  entire block removed.\n"
             "  Reduces binary size and improves speed."),
            (C["orange"], "Identity Elimination",
             "Remove operations that have no effect.\n"
             "  Example:  x = x + 0  →  x = x     (adding zero does nothing)\n"
             "            y = y * 1  →  y = y     (multiply by 1 does nothing)"),
            (C["purple"], "Strength Reduction",
             "Replace expensive operations with cheaper ones.\n"
             "  Example:  x = n * 0  →  x = 0\n"
             "  Avoids a multiply instruction entirely."),
        ]
        for col, name, desc in techniques:
            b.w(f"\n  ▶  {name}\n", col, bold=True)
            for ln in desc.split("\n"):
                b.w(f"  {ln}\n", C["muted"])

    # ── RENDER: CODE GENERATION ──────────────────────────────────────────────
    def _render_codegen(self, result):
        tac_lines = result.get("tac", [])
        asm_lines = result.get("asm", [])
        frames    = result.get("frames", {})

        # ── TAC panel ────────────────────────────────────────────────────────
        b = self._rcgen["tac"]; b.clear()
        b.w(f"\n  {len(tac_lines)} TAC instructions\n\n", C["muted"])
        b.w("  " + "─" * 44 + "\n\n", C["border"])

        LABEL_RE = re.compile(r'^[A-Z_]+\d*:$|^[A-Z]+\s')
        for i, line in enumerate(tac_lines, 1):
            stripped = line.strip()
            if not stripped:
                b.w("\n", C["muted"]); continue
            # section headers (BEGIN, END, FUNC, ENDFUNC)
            if any(stripped.startswith(k) for k in
                   ("BEGIN","END","FUNC ","ENDFUNC")):
                b.w(f"\n  {stripped}\n", C["purple"], bold=True)
            # labels (THEN1:, LOOP1: etc.)
            elif stripped.endswith(":"):
                b.w(f"\n{stripped}\n", C["yellow"], bold=True)
            # instructions with = (assignments / TAC ops)
            elif "=" in stripped:
                parts = stripped.split("=", 1)
                b.w(f"  {i:>4}  ", C["dim"])
                b.w(parts[0].rstrip(), C["cyan"])
                b.w("  =  ", C["dim"])
                b.w(parts[1].strip() + "\n", C["text"])
            # PRINT, PUSH_ARG, RETURN etc.
            elif stripped.startswith(("PRINT","PUSH","RETURN","PARAM","goto","if ")):
                b.w(f"  {i:>4}  ", C["dim"])
                kw = stripped.split()[0]
                rest = stripped[len(kw):]
                b.w(f"{kw}", C["pink"], bold=True)
                b.w(rest + "\n", C["text"])
            else:
                b.w(f"  {i:>4}  {stripped}\n", C["muted"])

        # ── Assembly panel ────────────────────────────────────────────────────
        b = self._rcgen["asm"]; b.clear()
        b.w(f"\n  {len(asm_lines)} assembly instructions\n\n", C["muted"])
        b.w("  " + "─" * 44 + "\n\n", C["border"])

        ASM_OPS = {"LOAD","STORE","ADD","SUB","MUL","DIV",
                   "CMP_GT","CMP_LT","CMP_GE","CMP_LE","CMP_EQ","CMP_NE",
                   "AND","OR","NOT","CMP","JEQ","JMP","CALL",
                   "PUSH","POP","OUT","RET","HALT"}
        for i, line in enumerate(asm_lines, 1):
            stripped = line.strip()
            if not stripped:
                b.w("\n", C["muted"]); continue
            if stripped.startswith(";"):
                b.w(f"  {stripped}\n", C["muted"]); continue
            if stripped.endswith(":") and not stripped.startswith(" "):
                b.w(f"\n{stripped}\n", C["yellow"], bold=True); continue
            parts = stripped.split(None, 1)
            op    = parts[0]
            rest  = parts[1] if len(parts) > 1 else ""
            b.w(f"  {i:>4}  ", C["dim"])
            if op in ASM_OPS:
                b.w(f"{op:<8}", C["blue"], bold=True)
            else:
                b.w(f"{op:<8}", C["pink"], bold=True)
            # comment in rest
            if ";" in rest:
                code_part, cmt = rest.split(";", 1)
                b.w(code_part, C["text"])
                b.w(f"; {cmt.strip()}\n", C["muted"])
            else:
                b.w(rest + "\n", C["text"])

    # ── RENDER: OUTPUT ────────────────────────────────────────────────────────
    def _render_output(self, outputs):
        b = self._rout; b.clear()
        if outputs:
            b.w(f"\n  {len(outputs)} line(s) of output\n", C["muted"])
            b.w("  " + "─" * 50 + "\n\n", C["border"])
            for i, line in enumerate(outputs, 1):
                b.w(f"  {i:>3}  ", C["dim"])
                b.w("▶  ", C["green"], bold=True)
                b.w(line + "\n", C["text"])
        else:
            b.w("\n\n  No output produced.\n", C["muted"])

    # ── ERROR ─────────────────────────────────────────────────────────────────
    def _err(self, msg: str, title: str = "Error"):
        b = self._rexec
        b.configure(state="normal")
        b.w(f"\n\n  ✕  {title}\n", C["red"], bold=True)
        b.w("  " + "─" * 50 + "\n\n", C["border"])
        b.w(f"  {msg}\n", C["orange"])
        b.configure(state="disabled")
        self._run_btn.configure(state="normal", text="  ▶   Run Program  ",
                                bg=C["pink"], fg=C["bg"])
        self._set_status(f"✕  {title}: {msg[:60]}")
        self._switch_tab("exec")


# ══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    app = AnexDebugger()
    app.mainloop()