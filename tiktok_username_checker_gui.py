#!/usr/bin/env python3
"""
TikTok Username Checker - modern interface (CustomTkinter).

Keep this file in the SAME folder as tiktok_username_checker.py.
Install the two packages it needs:   pip install requests customtkinter
Start it with:                       python tiktok_username_checker_gui.py
(rename it to .pyw to hide the black console window)

Tip: right-click any name (Results table or Review lists) to find similar names.

Files it keeps next to the program:
  available_usernames.txt   names waiting to be tested in the TikTok app
  confirmed_usernames.txt   names that showed the checkmark in the app
  rejected_usernames.txt    names the app refused
  taken_usernames.txt       names found taken (skipped for 30 days)
  pending_usernames.txt     names a stopped run didn't get to (for Resume)
  tiktok_checker_settings.json   your settings
"""
import csv
import json
import os
import queue
import re
import sys
import threading
import time
import tkinter as tk
from datetime import datetime
from tkinter import filedialog, messagebox, ttk
from types import SimpleNamespace

try:
    import winsound
except ImportError:
    winsound = None

# Next to the .exe when packaged, otherwise next to this script
if getattr(sys, "frozen", False):
    BASE = os.path.dirname(sys.executable)
else:
    BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)


def resource_path(name):
    """Find a bundled file (works from source and inside the packaged .exe)."""
    for folder in (getattr(sys, "_MEIPASS", None), BASE, os.path.join(BASE, "Assets")):
        if folder and os.path.exists(os.path.join(folder, name)):
            return os.path.join(folder, name)
    return None


if os.name == "nt":  # lets Windows show our own icon on the taskbar
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("tiktok.username.checker")
    except Exception:
        pass

try:
    import customtkinter as ctk
    from Backend import tiktok_username_checker as core
except ImportError as exc:
    _root = tk.Tk()
    _root.withdraw()
    messagebox.showerror(
        "Missing package or file",
        "Could not start the interface.\n\n"
        "1) Install the packages:\n    pip install requests customtkinter\n\n"
        "2) Make sure tiktok_username_checker.py is in the same folder as this file.\n\n"
        f"Details: {exc}",
    )
    sys.exit(1)

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# ------------------------------------------------------------------- look
BG = "#0b1020"
CARD = "#131a2e"
CARD_DARK = "#0d1324"
SURFACE = "#1c2540"
SURFACE_HOVER = "#27325a"
BORDER = "#26314d"
TEXT = "#e6edf7"
MUTED = "#8a97b2"
ACCENT = "#6366f1"
ACCENT_HOVER = "#4f46e5"
GREEN = "#34d399"
RED = "#f87171"
YELLOW = "#fbbf24"
GRAY = "#94a3b8"
STATUS_COLORS = {"available": GREEN, "taken": RED, "blocked": YELLOW, "unknown": GRAY, "error": GRAY}

APP_TITLE = "TikTok Username Checker"
MODES = {"Random": "random", "Word-like": "wordlike", "Pattern": "pattern",
         "Word list": "words", "Combine": "combine", "Variations": "variations"}
TABS = ("Check", "Results", "Review")
MAX_ROWS = 20000


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("1240x800")
        self.minsize(1120, 720)
        self.configure(fg_color=BG)
        self._set_icon()

        # --- SET WINDOW & TASKBAR ICON ---
        icon_path = resource_path("app_icon.ico")
        if icon_path and os.path.exists(icon_path):
            try:
                self.iconbitmap(icon_path)
            except Exception:
                pass
        # ---------------------------------

        self.f_h1 = ctk.CTkFont(size=24, weight="bold")
        self.f_h2 = ctk.CTkFont(size=14, weight="bold")
        self.f_body = ctk.CTkFont(size=13)
        self.f_small = ctk.CTkFont(size=11)
        self.f_metric = ctk.CTkFont(size=26, weight="bold")
        self.f_btn = ctk.CTkFont(size=13, weight="bold")
        self.f_nav = ctk.CTkFont(size=14, weight="bold")

        # Create a dedicated 'data' folder next to the .exe so it never litters your desktop
        DATA_DIR = os.path.join(BASE, "data")
        os.makedirs(DATA_DIR, exist_ok=True)

        self.available_path = os.path.join(DATA_DIR, "available_usernames.txt")
        self.confirmed_path = os.path.join(DATA_DIR, "confirmed_usernames.txt")
        self.rejected_path = os.path.join(DATA_DIR, "rejected_usernames.txt")
        self.taken_path = os.path.join(DATA_DIR, "taken_usernames.txt")
        self.pending_path = os.path.join(DATA_DIR, "pending_usernames.txt")
        self.settings_path = os.path.join(DATA_DIR, "tiktok_checker_settings.json")

        self.q: queue.Queue = queue.Queue()
        self.running = False
        self.recheck_mode = False
        self.start_time = 0.0
        self.rows: list = []          # (name, status) for the Results table
        self.run_names: list = []     # names of the current/last run
        self.run_results: dict = {}   # name -> result for the current/last run
        self._empty_shown = False
        self._chip_state = None

        self._init_vars()
        self._style_tree()
        self._build()
        self._load_settings()
        self._on_mode(self.v_mode.get())
        self._load_saved()
        self._refresh_resume()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(100, self._poll)

    def _set_icon(self):
        ico, png = resource_path("app_icon.ico"), resource_path("app_icon.png")

        def apply_ico():
            try:
                self.iconbitmap(ico)
            except Exception:
                pass

        try:
            if os.name == "nt" and ico:
                self.after(250, apply_ico)  # CustomTkinter sets its own icon first; ours goes on top
            elif png:
                self._icon_img = tk.PhotoImage(file=png)
                self.iconphoto(True, self._icon_img)
        except Exception:
            pass

    # ---------------------------------------------------------------- vars
    def _init_vars(self):
        S, B = tk.StringVar, tk.BooleanVar
        self.v_mode = S(value="Random")
        self.v_min = S(value="5")
        self.v_max = S(value="6")
        self.v_digits = B(value=True)
        self.v_underscores = B(value=True)
        self.v_pattern = S(value="")
        self.v_words = S(value="")
        self.v_sep = S(value="none")
        self.v_variations = S(value="")
        self.v_contains = S(value="")
        self.v_starts = S(value="")
        self.v_ends = S(value="")
        self.v_limit = S(value="100")
        self.v_workers = S(value="3")
        self.v_delay = S(value="2.0")
        self.v_auto = B(value=True)
        self.v_sound = B(value=True)
        self.v_remember = B(value=True)
        self.v_best = B(value=True)
        self.v_filter = S(value="All")

        self.stat_checked = S(value="0 / 0")
        self.stat_available = S(value="0")
        self.stat_speed = S(value="0.0 / s")
        self.stat_eta = S(value="--")
        self.status = S(value="Ready.")
        self.pace_text = S(value="")

        self.persist = {
            "mode": self.v_mode, "min_len": self.v_min, "max_len": self.v_max,
            "digits": self.v_digits, "underscores": self.v_underscores,
            "pattern": self.v_pattern, "words": self.v_words, "sep": self.v_sep,
            "variations": self.v_variations,
            "contains": self.v_contains, "starts": self.v_starts, "ends": self.v_ends,
            "limit": self.v_limit, "workers": self.v_workers, "delay": self.v_delay,
            "auto": self.v_auto, "sound": self.v_sound, "remember": self.v_remember,
            "best": self.v_best,
        }

    def _style_tree(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.layout("Dark.Treeview", [("Treeview.treearea", {"sticky": "nswe"})])
        style.configure("Dark.Treeview", background=CARD_DARK, fieldbackground=CARD_DARK,
                        foreground=TEXT, rowheight=28, borderwidth=0, relief="flat",
                        bordercolor=CARD_DARK, lightcolor=CARD_DARK, darkcolor=CARD_DARK,
                        font=("Segoe UI", 10))
        style.configure("Dark.Treeview.Heading", background=SURFACE, foreground=MUTED,
                        relief="flat", borderwidth=0, padding=(8, 6), font=("Segoe UI", 10, "bold"))
        style.map("Dark.Treeview", background=[("selected", "#2b3a6b")],
                  foreground=[("selected", "#ffffff")])
        style.map("Dark.Treeview.Heading", background=[("active", SURFACE_HOVER)])

        def fixed(option):
            return [e for e in style.map("Dark.Treeview", query_opt=option)
                    if e[:2] != ("!disabled", "!selected")]
        style.map("Dark.Treeview", foreground=fixed("foreground"), background=fixed("background"))

    # ------------------------------------------------------------- helpers
    def _card(self, parent, **kw):
        return ctk.CTkFrame(parent, fg_color=CARD, corner_radius=14,
                            border_width=1, border_color=BORDER, **kw)

    def _lbl(self, parent, text="", muted=False, font=None, **kw):
        return ctk.CTkLabel(parent, text=text, text_color=MUTED if muted else TEXT,
                            font=font or self.f_body, anchor="w", **kw)

    def _entry(self, parent, var, width=110):
        return ctk.CTkEntry(parent, textvariable=var, width=width, height=34, corner_radius=8,
                            fg_color=CARD_DARK, border_color=BORDER, text_color=TEXT)

    def _btn(self, parent, text, cmd, kind="primary", **kw):
        colors = {"primary": (ACCENT, ACCENT_HOVER), "danger": ("#dc2626", "#b91c1c"),
                  "ghost": (SURFACE, SURFACE_HOVER), "success": ("#059669", "#047857")}
        fg, hover = colors[kind]
        opts = dict(fg_color=fg, hover_color=hover, corner_radius=10, height=36,
                    font=self.f_btn, text_color_disabled="#64748b")
        opts.update(kw)
        return ctk.CTkButton(parent, text=text, command=cmd, **opts)

    def _switch(self, parent, text, var):
        return ctk.CTkSwitch(parent, text=text, variable=var, font=self.f_body, text_color=TEXT,
                             progress_color=ACCENT, button_color="#e2e8f0")

    def _rule(self, parent, row):
        ctk.CTkFrame(parent, height=1, fg_color=BORDER).grid(
            row=row, column=0, sticky="ew", padx=16, pady=8)

    def _heading(self, parent, text, row):
        self._lbl(parent, text, muted=True, font=self.f_small).grid(
            row=row, column=0, sticky="w", padx=18, pady=(12, 4))

    # --------------------------------------------------------------- build
    def _build(self):
        head = ctk.CTkFrame(self, fg_color="transparent")
        head.pack(fill="x", padx=24, pady=(16, 0))
        titles = ctk.CTkFrame(head, fg_color="transparent")
        titles.pack(side="left")
        self._lbl(titles, APP_TITLE, font=self.f_h1).pack(anchor="w")
        self._lbl(titles, "Find names that look free, then confirm them in the TikTok app.",
                  muted=True).pack(anchor="w")
        self.chip = ctk.CTkLabel(head, text="●  Ready", width=130, height=32, corner_radius=16,
                                 fg_color=SURFACE, text_color=GRAY, font=self.f_btn)
        self.chip.pack(side="right", pady=8)

        self.nav = ctk.CTkSegmentedButton(
            self, values=list(TABS), command=self._show_tab, selected_color=ACCENT,
            selected_hover_color=ACCENT_HOVER, unselected_color=SURFACE,
            unselected_hover_color=SURFACE_HOVER, fg_color=SURFACE, text_color=TEXT,
            font=self.f_nav, height=40)
        self.nav.pack(anchor="w", padx=24, pady=(14, 10))
        self.nav.set(TABS[0])

        foot = ctk.CTkFrame(self, fg_color=CARD, corner_radius=0, height=34)
        foot.pack(fill="x", side="bottom")
        ctk.CTkLabel(foot, textvariable=self.status, text_color=TEXT, font=self.f_small,
                     anchor="w").pack(side="left", padx=18, pady=6)
        ctk.CTkLabel(foot, textvariable=self.pace_text, text_color=MUTED, font=self.f_small,
                     anchor="e").pack(side="right", padx=18)

        pages = ctk.CTkFrame(self, fg_color="transparent")
        pages.pack(fill="both", expand=True, padx=18, pady=(0, 6))
        pages.columnconfigure(0, weight=1)
        pages.rowconfigure(0, weight=1)
        self.page = {}
        for name in TABS:
            frame = ctk.CTkFrame(pages, fg_color="transparent")
            frame.grid(row=0, column=0, sticky="nsew")
            self.page[name] = frame

        self._build_check(self.page["Check"])
        self._build_results(self.page["Results"])
        self._build_review(self.page["Review"])
        self._build_menu()
        self._show_tab(TABS[0])

    def _build_menu(self):
        self.ctx_name = None
        self.menu = tk.Menu(self, tearoff=0, bg=CARD, fg=TEXT, activebackground=ACCENT,
                            activeforeground="#ffffff", bd=0, relief="flat", font=("Segoe UI", 10))
        self.menu.add_command(label="✨  Find similar names",
                              command=lambda: self._find_similar(self.ctx_name))
        self.menu.add_command(label="Copy name", command=self._ctx_copy)
        buttons = ("<Button-2>", "<Control-Button-1>") if sys.platform == "darwin" else ("<Button-3>",)
        for widget, source in ((self.tree, "tree"), (self.avail_list, "list"), (self.conf_list, "list")):
            for button in buttons:
                widget.bind(button, lambda e, src=source: self._popup(e, src))

    def _popup(self, event, source):
        widget = event.widget
        if source == "tree":
            iid = widget.identify_row(event.y)
            if not iid:
                return
            widget.selection_set(iid)
            name = str(widget.item(iid, "values")[0]).lstrip("@")
        else:
            if widget.size() == 0:
                return
            idx = widget.nearest(event.y)
            widget.selection_clear(0, "end")
            widget.selection_set(idx)
            name = widget.get(idx)
        self.ctx_name = name
        try:
            self.menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.menu.grab_release()

    def _ctx_copy(self):
        if self.ctx_name:
            self.clipboard_clear()
            self.clipboard_append(self.ctx_name)
            self.status.set(f"Copied {self.ctx_name}")

    def _show_tab(self, name):
        for tab, frame in self.page.items():
            if tab == name:
                frame.grid()
            else:
                frame.grid_remove()
        self.nav.set(name)

    def _metric(self, parent, col, title, var, color):
        card = self._card(parent)
        card.grid(row=0, column=col, sticky="nsew", padx=5)
        self._lbl(card, title, muted=True, font=self.f_small).pack(anchor="w", padx=16, pady=(12, 0))
        ctk.CTkLabel(card, textvariable=var, text_color=color, font=self.f_metric,
                     anchor="w").pack(anchor="w", padx=16, pady=(0, 12))

    def _build_check(self, t):
        t.columnconfigure(0, weight=1)
        t.rowconfigure(2, weight=1)

        metrics = ctk.CTkFrame(t, fg_color="transparent")
        metrics.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        for i in range(4):
            metrics.columnconfigure(i, weight=1)
        self._metric(metrics, 0, "PROGRESS", self.stat_checked, ACCENT)
        self._metric(metrics, 1, "AVAILABLE", self.stat_available, GREEN)
        self._metric(metrics, 2, "SPEED", self.stat_speed, YELLOW)
        self._metric(metrics, 3, "TIME LEFT", self.stat_eta, TEXT)

        ctrl = ctk.CTkFrame(t, fg_color="transparent")
        ctrl.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        ctrl.columnconfigure(3, weight=1)
        self.start_btn = self._btn(ctrl, "▶  Start checking", self.start, width=170, height=40)
        self.start_btn.grid(row=0, column=0, padx=(5, 8))
        self.stop_btn = self._btn(ctrl, "■  Stop", self.stop, kind="ghost", width=100, height=40,
                                  state="disabled")
        self.stop_btn.grid(row=0, column=1, padx=(0, 8))
        self.resume_btn = self._btn(ctrl, "↻  Resume", self.resume, kind="ghost", width=170, height=40)
        self.resume_btn.grid(row=0, column=2, padx=(0, 14))
        self.resume_btn.grid_remove()
        self.progress = ctk.CTkProgressBar(ctrl, height=10, corner_radius=5, progress_color=ACCENT,
                                           fg_color=SURFACE)
        self.progress.set(0)
        self.progress.grid(row=0, column=3, sticky="ew", padx=(0, 5))

        body = ctk.CTkFrame(t, fg_color="transparent")
        body.grid(row=2, column=0, sticky="nsew")
        body.columnconfigure(0, weight=3, uniform="cards")
        body.columnconfigure(1, weight=2, uniform="cards")
        body.rowconfigure(0, weight=1)

        lc = self._card(body)
        lc.grid(row=0, column=0, sticky="nsew", padx=(5, 6))
        lc.columnconfigure(0, weight=1)

        self._heading(lc, "NAME SOURCE", 0)
        self.mode_btn = ctk.CTkSegmentedButton(
            lc, values=list(MODES), variable=self.v_mode, command=self._on_mode,
            selected_color=ACCENT, selected_hover_color=ACCENT_HOVER,
            unselected_color=SURFACE, unselected_hover_color=SURFACE_HOVER,
            fg_color=SURFACE, text_color=TEXT, font=self.f_btn, height=34)
        self.mode_btn.grid(row=1, column=0, sticky="w", padx=16, pady=(0, 10))

        mc = ctk.CTkFrame(lc, fg_color="transparent")
        mc.grid(row=2, column=0, sticky="ew", padx=16)

        self.f_len = ctk.CTkFrame(mc, fg_color="transparent")
        self._lbl(self.f_len, "Length").grid(row=0, column=0, padx=(0, 8))
        self._entry(self.f_len, self.v_min, 56).grid(row=0, column=1)
        self._lbl(self.f_len, " to ").grid(row=0, column=2)
        self._entry(self.f_len, self.v_max, 56).grid(row=0, column=3)
        self._lbl(self.f_len, "characters  (5 or more works best)", muted=True,
                  font=self.f_small).grid(row=0, column=4, padx=(10, 0))

        self.f_charset = ctk.CTkFrame(mc, fg_color="transparent")
        self._switch(self.f_charset, "Include numbers", self.v_digits).grid(row=0, column=0, padx=(0, 22))
        self._switch(self.f_charset, "Include underscores (_)", self.v_underscores).grid(row=0, column=1)

        self.f_pattern = ctk.CTkFrame(mc, fg_color="transparent")
        self._lbl(self.f_pattern, "Pattern").grid(row=0, column=0, padx=(0, 8))
        self._entry(self.f_pattern, self.v_pattern, 220).grid(row=0, column=1)
        self._lbl(self.f_pattern, "?  letter     #  number     *  letter or number     e.g.  ak??   nova#",
                  muted=True, font=self.f_small).grid(row=1, column=0, columnspan=2, sticky="w", pady=(4, 0))

        self.f_wordfile = ctk.CTkFrame(mc, fg_color="transparent")
        self._lbl(self.f_wordfile, "Word list").grid(row=0, column=0, padx=(0, 8))
        self._entry(self.f_wordfile, self.v_words, 300).grid(row=0, column=1, padx=(0, 8))
        self._btn(self.f_wordfile, "Browse...", self._browse, kind="ghost", width=90).grid(row=0, column=2)

        self.f_sep = ctk.CTkFrame(mc, fg_color="transparent")
        self._lbl(self.f_sep, "Join words with").grid(row=0, column=0, padx=(0, 8))
        ctk.CTkOptionMenu(self.f_sep, values=["none", "_", "both"], variable=self.v_sep, width=90,
                          fg_color=SURFACE, button_color=SURFACE_HOVER,
                          button_hover_color=ACCENT).grid(row=0, column=1)
        self._lbl(self.f_sep, "nova + fox  ->  novafox / nova_fox", muted=True,
                  font=self.f_small).grid(row=0, column=2, padx=(12, 0))

        self.f_var = ctk.CTkFrame(mc, fg_color="transparent")
        self._lbl(self.f_var, "Base words").grid(row=0, column=0, padx=(0, 8))
        self._entry(self.f_var, self.v_variations, 300).grid(row=0, column=1)
        self._lbl(self.f_var, "Separate with spaces, e.g.  nova atlas  ->  novaa, itsnova, nva, novaofc ...",
                  muted=True, font=self.f_small).grid(row=1, column=0, columnspan=2, sticky="w", pady=(4, 0))

        for i, f in enumerate((self.f_len, self.f_charset, self.f_pattern,
                               self.f_wordfile, self.f_sep, self.f_var)):
            f.grid(row=i, column=0, sticky="w", pady=4)

        self._rule(lc, 3)
        self._heading(lc, "FILTERS  (optional)", 4)
        flt = ctk.CTkFrame(lc, fg_color="transparent")
        flt.grid(row=5, column=0, sticky="w", padx=16, pady=(0, 14))
        for r, (text, var, width) in enumerate((
                ("Must contain", self.v_contains, 200),
                ("Starts with", self.v_starts, 130),
                ("Ends with", self.v_ends, 130))):
            self._lbl(flt, text).grid(row=r, column=0, sticky="w", padx=(0, 12), pady=4)
            self._entry(flt, var, width).grid(row=r, column=1, sticky="w", pady=4)
        self._lbl(flt, "separate several with spaces, e.g.  x 7", muted=True,
                  font=self.f_small).grid(row=0, column=2, sticky="w", padx=(12, 0))

        rc = self._card(body)
        rc.grid(row=0, column=1, sticky="nsew", padx=(6, 5))
        rc.columnconfigure(0, weight=1)

        self._heading(rc, "SPEED", 0)
        sp = ctk.CTkFrame(rc, fg_color="transparent")
        sp.grid(row=1, column=0, sticky="w", padx=16)
        self._lbl(sp, "Max names").grid(row=0, column=0, sticky="w", padx=(0, 14), pady=5)
        self._entry(sp, self.v_limit, 80).grid(row=0, column=1, columnspan=2, sticky="w", pady=5)
        self._lbl(sp, "Workers").grid(row=1, column=0, sticky="w", padx=(0, 14), pady=5)
        self.workers_slider = ctk.CTkSlider(sp, from_=1, to=8, number_of_steps=7, width=150,
                                            command=self._on_workers, progress_color=ACCENT,
                                            button_color=ACCENT, button_hover_color=ACCENT_HOVER)
        self.workers_slider.set(3)
        self.workers_slider.grid(row=1, column=1, pady=5)
        ctk.CTkLabel(sp, textvariable=self.v_workers, width=26, text_color=TEXT,
                     font=self.f_btn).grid(row=1, column=2, padx=(8, 0))
        self._lbl(sp, "Delay (s)").grid(row=2, column=0, sticky="w", padx=(0, 14), pady=5)
        self._entry(sp, self.v_delay, 80).grid(row=2, column=1, columnspan=2, sticky="w", pady=5)

        self._rule(rc, 2)
        self._heading(rc, "BEHAVIOUR", 3)
        sw = ctk.CTkFrame(rc, fg_color="transparent")
        sw.grid(row=4, column=0, sticky="w", padx=16, pady=(0, 14))
        self._switch(sw, "Auto-pace (adapts to TikTok)", self.v_auto).grid(row=0, column=0, sticky="w", pady=6)
        self._switch(sw, "Best names first", self.v_best).grid(row=1, column=0, sticky="w", pady=6)
        self._switch(sw, "Remember taken names", self.v_remember).grid(row=2, column=0, sticky="w", pady=6)
        self._switch(sw, "Alert when a name is found", self.v_sound).grid(row=3, column=0, sticky="w", pady=6)

    def _build_results(self, t):
        t.columnconfigure(0, weight=1)
        t.rowconfigure(1, weight=1)
        bar = ctk.CTkFrame(t, fg_color="transparent")
        bar.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        self._lbl(bar, "Show").pack(side="left", padx=(5, 10))
        ctk.CTkSegmentedButton(
            bar, values=["All", "Available", "Taken", "Blocked", "Other"], variable=self.v_filter,
            command=lambda v: self._refresh_table(), selected_color=ACCENT,
            selected_hover_color=ACCENT_HOVER, unselected_color=SURFACE,
            unselected_hover_color=SURFACE_HOVER, fg_color=SURFACE, text_color=TEXT).pack(side="left")
        self._btn(bar, "Clear", self._clear_rows, kind="ghost", width=80).pack(side="right", padx=5)
        self._btn(bar, "Export CSV", self._export_csv, kind="ghost", width=110).pack(side="right")
        self._btn(bar, "✨  Find similar", self._similar_from_results, kind="ghost",
                  width=130).pack(side="right", padx=(0, 6))

        card = self._card(t)
        card.grid(row=1, column=0, sticky="nsew", padx=5, pady=(0, 6))
        card.columnconfigure(0, weight=1)
        card.rowconfigure(0, weight=1)
        self.tree = ttk.Treeview(card, columns=("name", "status", "length"), show="headings",
                                 style="Dark.Treeview", selectmode="browse")
        self.tree.heading("name", text="USERNAME", anchor="w")
        self.tree.heading("status", text="STATUS", anchor="w")
        self.tree.heading("length", text="LENGTH", anchor="w")
        self.tree.column("name", width=420, anchor="w")
        self.tree.column("status", width=160, anchor="w")
        self.tree.column("length", width=100, anchor="w")
        for status, color in STATUS_COLORS.items():
            self.tree.tag_configure(status, foreground=color)
        sb = ctk.CTkScrollbar(card, command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.grid(row=0, column=0, sticky="nsew", padx=(12, 0), pady=12)
        sb.grid(row=0, column=1, sticky="ns", padx=(0, 6), pady=12)
        self.empty_results = ctk.CTkLabel(
            card, text="No results yet.\nStart a check on the Check tab.\n\n"
                 "Tip: right-click any name to find similar ones.", text_color=MUTED,
            font=self.f_body, fg_color=CARD_DARK, justify="center")
        self._set_empty(True)

    def _set_empty(self, show):
        if show != self._empty_shown:
            self._empty_shown = show
            if show:
                self.empty_results.place(relx=0.5, rely=0.5, anchor="center")
            else:
                self.empty_results.place_forget()

    def _make_list(self, parent, placeholder):
        wrap = ctk.CTkFrame(parent, fg_color="transparent")
        wrap.pack(fill="both", expand=True, padx=14, pady=(0, 8))
        lb = tk.Listbox(wrap, font=("Consolas", 13), bg=CARD_DARK, fg=TEXT, selectbackground=ACCENT,
                        selectforeground="#ffffff", activestyle="none", exportselection=False,
                        highlightthickness=0, relief="flat", borderwidth=0, height=5)
        sb = ctk.CTkScrollbar(wrap, command=lb.yview)
        lb.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        lb.pack(side="left", fill="both", expand=True)
        empty = ctk.CTkLabel(wrap, text=placeholder, text_color=MUTED, font=self.f_body,
                             fg_color=CARD_DARK, justify="center")
        return lb, empty

    def _build_review(self, t):
        t.columnconfigure((0, 1), weight=1, uniform="col")
        t.rowconfigure(0, weight=1)

        left = self._card(t)
        left.grid(row=0, column=0, sticky="nsew", padx=(5, 6), pady=(0, 6))
        self._lbl(left, "Available - test these in the TikTok app", font=self.f_h2).pack(
            anchor="w", padx=16, pady=(14, 2))
        self._lbl(left, "In TikTok: Edit profile > Username. Type the name but don't save, "
                        "then mark what you saw.  Right-click a name to find similar ones.",
                  muted=True, font=self.f_small,
                  wraplength=520, justify="left").pack(anchor="w", padx=16, pady=(0, 8))
        self.recheck_btn = self._btn(left, "↻  Re-check these names first", self.recheck, kind="ghost")
        self.recheck_btn.pack(side="bottom", anchor="w", padx=14, pady=(0, 14))
        row = ctk.CTkFrame(left, fg_color="transparent")
        row.pack(side="bottom", fill="x", padx=14, pady=(0, 8))
        self._btn(row, "✓  Checkmark  (Y)", lambda: self._decide(True), kind="success",
                  width=140).pack(side="left", padx=(0, 6))
        self._btn(row, "✗  Red error  (N)", lambda: self._decide(False), kind="danger",
                  width=140).pack(side="left", padx=(0, 6))
        self._btn(row, "Copy", self._copy_selected, kind="ghost", width=64).pack(side="right")
        self._btn(row, "✨  Similar", self._similar_from_review, kind="ghost",
                  width=100).pack(side="right", padx=(0, 6))
        self.avail_list, self.avail_empty = self._make_list(
            left, "No names to test yet.\nRun a check first.")
        self.avail_list.bind("<Key-y>", lambda e: self._decide(True))
        self.avail_list.bind("<Key-n>", lambda e: self._decide(False))
        self.avail_list.bind("<Double-Button-1>", lambda e: self._copy_selected())

        right = self._card(t)
        right.grid(row=0, column=1, sticky="nsew", padx=(6, 5), pady=(0, 6))
        self._lbl(right, "Confirmed - these work", font=self.f_h2).pack(anchor="w", padx=16, pady=(14, 8))
        row = ctk.CTkFrame(right, fg_color="transparent")
        row.pack(side="bottom", fill="x", padx=14, pady=(0, 14))
        self._btn(row, "Copy all", self._copy_confirmed, kind="ghost", width=90).pack(side="right")
        self.conf_list, self.conf_empty = self._make_list(
            right, "Names you confirm\nwill appear here.")

    def _load_settings(self):
        try:
            with open(self.settings_path, encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, ValueError):
            return
        for key, var in self.persist.items():
            if key in data:
                try:
                    var.set(data[key])
                except Exception:
                    pass
        self.workers_slider.set(self._int(self.v_workers.get(), 3))
        if self.v_mode.get() not in MODES:
            self.v_mode.set("Random")

    def _save_settings(self):
        try:
            with open(self.settings_path, "w", encoding="utf-8") as f:
                json.dump({k: v.get() for k, v in self.persist.items()}, f, indent=2)
        except OSError:
            pass

    @staticmethod
    def _int(text, default):
        try:
            return int(float(text))
        except (TypeError, ValueError):
            return default

    def _on_workers(self, value):
        self.v_workers.set(str(int(round(float(value)))))

    def _on_mode(self, mode):
        m = MODES.get(mode, "random")
        show = {
            self.f_len: m in ("random", "wordlike", "combine"),
            self.f_charset: m in ("random", "variations"),
            self.f_pattern: m == "pattern",
            self.f_wordfile: m in ("words", "combine"),
            self.f_sep: m == "combine",
            self.f_var: m == "variations",
        }
        for frame, visible in show.items():
            if visible:
                frame.grid()
            else:
                frame.grid_remove()

    def _browse(self):
        path = filedialog.askopenfilename(
            title="Choose a word list", filetypes=[("Text files", "*.txt"), ("All files", "*.*")])
        if path:
            self.v_words.set(path)

    def _sorted(self, names):
        return sorted(names, key=lambda n: (core.name_score(n), n))

    def _load_saved(self):
        decided = core.read_set(self.confirmed_path) | core.read_set(self.rejected_path)
        for n in self._sorted(core.read_set(self.available_path) - decided):
            self.avail_list.insert("end", n)
        for n in self._sorted(core.read_set(self.confirmed_path)):
            self.conf_list.insert("end", n)
        if self.avail_list.size():
            self.avail_list.selection_set(0)
            self.status.set(f"Loaded {self.avail_list.size()} saved names to test (Review tab).")
        self._sync_lists()

    def _sync_lists(self):
        self.stat_available.set(str(self.avail_list.size()))
        for lb, empty in ((self.avail_list, self.avail_empty), (self.conf_list, self.conf_empty)):
            if lb.size():
                empty.place_forget()
            else:
                empty.place(relx=0.5, rely=0.5, anchor="center")

    def _save_available(self):
        names = list(self.avail_list.get(0, "end"))
        try:
            with open(self.available_path, "w", encoding="utf-8") as f:
                f.write("\n".join(names) + ("\n" if names else ""))
        except OSError:
            pass

    @staticmethod
    def _group(status):
        return status if status in ("available", "taken", "blocked") else "other"

    def _filter_ok(self, status):
        f = self.v_filter.get()
        return f == "All" or self._group(status) == f.lower()

    def _insert_row(self, name, status):
        iid = self.tree.insert("", "end", values=(f"@{name}", status.upper(), len(name)), tags=(status,))
        self.tree.see(iid)
        self._set_empty(False)

    def _add_row(self, name, status):
        self.rows.append((name, status))
        if len(self.rows) > MAX_ROWS:
            self.rows = self.rows[-MAX_ROWS:]
            self._refresh_table()
        elif self._filter_ok(status):
            self._insert_row(name, status)

    def _refresh_table(self):
        self.tree.delete(*self.tree.get_children())
        for name, status in self.rows:
            if self._filter_ok(status):
                self._insert_row(name, status)
        self._set_empty(not self.tree.get_children())

    def _clear_rows(self):
        self.rows.clear()
        self._refresh_table()

    def _export_csv(self):
        shown = [(n, s) for n, s in self.rows if self._filter_ok(s)]
        if not shown:
            messagebox.showinfo("Nothing to export", "There are no results to export yet.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".csv", filetypes=[("CSV file", "*.csv")],
            initialfile=f"usernames_{datetime.now():%Y%m%d_%H%M%S}.csv")
        if not path:
            return
        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                w = csv.writer(f)
                w.writerow(["username", "status", "length"])
                for n, s in shown:
                    w.writerow([n, s, len(n)])
        except OSError as exc:
            messagebox.showerror("Could not save", str(exc))
            return
        self.status.set(f"Exported {len(shown)} rows to {path}")

    def _copy_selected(self):
        for lb in (self.avail_list, self.conf_list):
            sel = lb.curselection()
            if sel:
                self.clipboard_clear()
                self.clipboard_append(lb.get(sel[0]))
                self.status.set(f"Copied {lb.get(sel[0])}")
                return

    def _copy_confirmed(self):
        names = list(self.conf_list.get(0, "end"))
        if names:
            self.clipboard_clear()
            self.clipboard_append("\n".join(names))
            self.status.set(f"Copied {len(names)} confirmed names.")

    def _decide(self, ok: bool):
        sel = self.avail_list.curselection()
        if not sel:
            return
        idx = sel[0]
        name = self.avail_list.get(idx)
        if ok:
            core.append_line(self.confirmed_path, name)
            names = self._sorted(list(self.conf_list.get(0, "end")) + [name])
            self.conf_list.delete(0, "end")
            for n in names:
                self.conf_list.insert("end", n)
        else:
            core.append_line(self.rejected_path, name)
        self.avail_list.delete(idx)
        if self.avail_list.size():
            self.avail_list.selection_set(min(idx, self.avail_list.size() - 1))
            self.avail_list.focus_set()
        self._save_available()
        self._sync_lists()

    def _read_speed(self):
        try:
            workers = max(1, min(8, int(self.v_workers.get())))
            delay = max(0.5, float(self.v_delay.get()))
        except ValueError:
            messagebox.showerror("Invalid input", "Workers and delay must be numbers.")
            return None
        self.v_workers.set(str(workers))
        self.workers_slider.set(workers)
        self.v_delay.set(str(delay))
        return workers, delay

    def start(self):
        if self.running:
            return
        speed = self._read_speed()
        if speed is None:
            return
        workers, delay = speed
        try:
            limit = max(1, min(5000, int(self.v_limit.get())))
        except ValueError:
            messagebox.showerror("Invalid input", "Max names must be a number.")
            return
        self.v_limit.set(str(limit))

        mode = MODES.get(self.v_mode.get(), "random")
        contains = [c for c in re.split(r"[\s,]+", self.v_contains.get().lower().strip()) if c]
        starts = self.v_starts.get().lower().strip().lstrip("@")
        ends = self.v_ends.get().lower().strip()
        words = self.v_words.get().strip()
        pattern = self.v_pattern.get().lower().strip()
        bases = []
        min_len = max_len = None

        if mode in ("random", "wordlike", "combine"):
            try:
                min_len = int(self.v_min.get())
                max_len = int(self.v_max.get())
            except ValueError:
                messagebox.showerror("Invalid input", "Length must be whole numbers.")
                return
            if not (1 <= min_len <= max_len <= 24):
                messagebox.showerror(
                    "Invalid length", "Lengths must be between 1 and 24, and the first can't be bigger than the second.")
                return
        if mode in ("random", "wordlike"):
            needed = len(starts) + len(ends) + (sum(len(c) for c in contains) if mode == "random" else 1)
            if needed > max_len:
                messagebox.showerror(
                    "Filters too long",
                    f"Your filters need {needed} characters but the maximum length is {max_len}.")
                return
        if mode == "pattern" and not re.fullmatch(r"[a-z0-9_.?#*]{2,24}", pattern):
            messagebox.showerror(
                "Invalid pattern",
                "Use 2-24 characters: letters, numbers, _ and . plus\n"
                "? (any letter), # (any number) and * (letter or number).\nExample: ak??  or  nova#")
            return
        if mode in ("words", "combine") and not os.path.isfile(words):
            messagebox.showerror("File not found", "Choose a word list file first.")
            return
        if mode == "variations":
            bases = [w for w in re.split(r"[\s,]+", self.v_variations.get().lower().strip())
                     if re.fullmatch(r"[a-z0-9]+", w)]
            if not bases:
                messagebox.showerror("No base words",
                                     "Type one or more words (letters and numbers), e.g.  nova atlas")
                return

        remember = self.v_remember.get()
        args = SimpleNamespace(
            mode=mode, words=words or None, pattern=pattern or None, variations=bases or None,
            combine=(mode == "combine"), combine_sep=self.v_sep.get(),
            style="wordlike" if mode == "wordlike" else "random",
            length=max_len, min_length=min_len,
            digits=self.v_digits.get(), underscores=self.v_underscores.get(), limit=limit,
            order="best" if self.v_best.get() else "random",
            contains=contains, starts_with=starts, ends_with=ends,
            confirmed_out=self.confirmed_path, rejected_out=self.rejected_path,
            taken_out=self.taken_path if remember else None, taken_days=30)

        candidates = core.load_candidates(args)
        if not candidates:
            messagebox.showinfo(
                "No names to check",
                "No new names to check. Your filters may be too strict, or you've already "
                "checked or reviewed all of these names recently.")
            return
        self._launch(candidates, workers, delay, recheck=False)

    def recheck(self):
        if self.running:
            return
        names = list(self.avail_list.get(0, "end"))
        if not names:
            messagebox.showinfo("Nothing to re-check", "The Available list is empty.")
            return
        speed = self._read_speed()
        if speed is None:
            return
        self._launch(names, speed[0], speed[1], recheck=True)

    def _similar_from_results(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Select a name",
                                "Click a name in the table first (or right-click it).")
            return
        self._find_similar(str(self.tree.item(sel[0], "values")[0]).lstrip("@"))

    def _similar_from_review(self):
        for lb in (self.avail_list, self.conf_list):
            sel = lb.curselection()
            if sel:
                self._find_similar(lb.get(sel[0]))
                return
        messagebox.showinfo("Select a name",
                            "Select a name in one of the lists first (or right-click it).")

    def _find_similar(self, name):
        if not name:
            return
        if self.running:
            messagebox.showinfo("Busy", "A check is running. Wait for it to finish (or press Stop) first.")
            return
        speed = self._read_speed()
        if speed is None:
            return
        try:
            limit = max(1, min(500, int(self.v_limit.get())))
        except ValueError:
            limit = 100
        args = SimpleNamespace(
            mode="similar", similar_to=[name], words=None, pattern=None, variations=None,
            combine=False, combine_sep="none", style="random", length=None, min_length=None,
            digits=self.v_digits.get(), underscores=self.v_underscores.get(), limit=limit,
            order="best", contains=[], starts_with="", ends_with="",
            confirmed_out=self.confirmed_path, rejected_out=self.rejected_path,
            taken_out=self.taken_path if self.v_remember.get() else None, taken_days=30)
        names = core.load_candidates(args)
        if not names:
            messagebox.showinfo(
                "No new suggestions",
                f"No new names to try for @{name}. You've already checked or reviewed the "
                "similar names recently.")
            return
        self._launch(names, speed[0], speed[1], recheck=False, tab="Results")
        self.status.set(f"Checking {len(names)} names similar to @{name}...")

    def resume(self):
        if self.running:
            return
        decided = (core.read_set(self.confirmed_path) | core.read_set(self.rejected_path)
                   | core.read_taken(self.taken_path, 30))
        names = [n for n in core.load_pending(self.pending_path) if n not in decided]
        if not names:
            core.clear_pending(self.pending_path)
            self._refresh_resume()
            messagebox.showinfo("Nothing to resume", "All of those names have been dealt with already.")
            return
        speed = self._read_speed()
        if speed is None:
            return
        self._launch(names, speed[0], speed[1], recheck=False)

    def _launch(self, names, workers, delay, recheck, tab=None):
        core.start_run(delay, self.v_auto.get())
        self.recheck_mode = recheck
        self.run_names = list(names)
        self.run_results = {}
        self.title(APP_TITLE)
        self.progress.set(0)
        self.stat_checked.set(f"0 / {len(names)}")
        self.stat_speed.set("0.0 / s")
        self.stat_eta.set("--")
        self._set_running(True)
        self.start_time = time.time()
        self.status.set(f"{'Re-checking' if recheck else 'Checking'} {len(names)} names...")
        self._show_tab(tab or ("Results" if recheck else "Check"))
        taken = self.taken_path if self.v_remember.get() else None
        threading.Thread(target=self._worker, args=(names, workers, delay, taken), daemon=True).start()

    def _worker(self, names, workers, delay, taken_path):
        try:
            core.run_checks(
                names, workers, delay, taken_path=taken_path,
                on_result=lambda n, r, d, t: self.q.put(("result", n, r, d, t)))
        finally:
            self.q.put(("done",))

    def stop(self):
        if self.running:
            core.stop.set()
            self.stop_btn.configure(state="disabled", fg_color=SURFACE)
            self.status.set("Stopping...")
            self._set_chip("Stopping", YELLOW)

    def _set_running(self, running):
        self.running = running
        if running:
            self.start_btn.configure(state="disabled", fg_color=SURFACE)
            self.recheck_btn.configure(state="disabled")
            self.stop_btn.configure(state="normal", fg_color="#dc2626", hover_color="#b91c1c")
            self.resume_btn.grid_remove()
            self._set_chip("Checking", GREEN)
        else:
            self.start_btn.configure(state="normal", fg_color=ACCENT)
            self.recheck_btn.configure(state="normal")
            self.stop_btn.configure(state="disabled", fg_color=SURFACE, hover_color=SURFACE_HOVER)
            self._refresh_resume()

    def _set_chip(self, text, color):
        if (text, color) != self._chip_state:
            self._chip_state = (text, color)
            self.chip.configure(text=f"●  {text}", text_color=color)

    def _refresh_resume(self):
        left = len(core.load_pending(self.pending_path))
        if left and not self.running:
            self.resume_btn.configure(text=f"↻  Resume ({left} left)")
            self.resume_btn.grid()
        else:
            self.resume_btn.grid_remove()

    def _update_pending(self):
        if self.recheck_mode or not self.run_names:
            return
        remaining = [n for n in self.run_names if self.run_results.get(n) in (None, "blocked")]
        if remaining:
            core.save_pending(self.pending_path, remaining)
        else:
            core.clear_pending(self.pending_path)

    def _poll(self):
        try:
            for _ in range(300):
                self._handle(self.q.get_nowait())
        except queue.Empty:
            pass

        if self.running:
            if core.pace["auto"]:
                self.pace_text.set(f"Auto-pace delay: {core.pace['delay']:.1f}s")
            if not core.stop.is_set():
                wait = core.state["pause_until"] - time.time()
                if wait > 1:
                    self.status.set(f"Rate limited by TikTok - waiting {int(wait)}s...")
                    self._set_chip("Rate limited", YELLOW)
                else:
                    self._set_chip("Checking", GREEN)
        else:
            self.pace_text.set("")
        self.after(100, self._poll)

    def _alert(self, name):
        try:
            self.title(f"🔥 Found @{name}")
        except Exception:
            pass
        if not self.v_sound.get():
            return
        try:
            if winsound:
                threading.Thread(target=lambda: [winsound.Beep(800, 120), winsound.Beep(1200, 180)],
                                 daemon=True).start()
            else:
                self.bell()
        except Exception:
            pass
        try:
            self.lift()
            self.attributes("-topmost", True)
            self.after(500, lambda: self.attributes("-topmost", False))
        except Exception:
            pass

    @staticmethod
    def _fmt_eta(seconds):
        seconds = int(seconds)
        if seconds >= 3600:
            return f"{seconds // 3600}h {seconds % 3600 // 60}m"
        if seconds >= 60:
            return f"{seconds // 60}m {seconds % 60}s"
        return f"{seconds}s"

    def _handle(self, msg):
        if msg[0] == "result":
            _, name, result, done, total = msg
            self.run_results[name] = result
            self._add_row(name, result)
            self.progress.set(done / total if total else 0)
            self.stat_checked.set(f"{done} / {total}")

            elapsed = max(time.time() - self.start_time, 0.001)
            speed = done / elapsed
            self.stat_speed.set(f"{speed:.1f} / s")
            self.stat_eta.set(self._fmt_eta((total - done) / speed) if speed > 0 else "--")

            if result == "available" and not self.recheck_mode:
                if name not in self.avail_list.get(0, "end"):
                    self.avail_list.insert("end", name)
                    if not self.avail_list.curselection():
                        self.avail_list.selection_set(0)
                    self._save_available()
                    self._sync_lists()
                    self._alert(name)
                    self.status.set(f"Found @{name}  |  {done}/{total} checked")
                    return
            elif result == "taken" and self.recheck_mode:
                names = list(self.avail_list.get(0, "end"))
                if name in names:
                    self.avail_list.delete(names.index(name))
                    self._save_available()
                    self._sync_lists()
            self.status.set(f"{'Re-checked' if self.recheck_mode else 'Checked'} {done}/{total}")

        elif msg[0] == "done":
            self.title(APP_TITLE)
            self._update_pending()
            self._set_running(False)
            n = self.avail_list.size()
            blocked = core.stop.is_set() and core.state["blocked_in_row"] >= 5
            if blocked:
                self.status.set("Stopped: TikTok keeps blocking requests. Use Resume later.")
                self._set_chip("Blocked", RED)
                messagebox.showwarning(
                    "Blocked by TikTok",
                    "TikTok keeps blocking requests, so the check stopped early.\n\n"
                    "Wait a while, then press Resume (or try again with fewer workers "
                    "or a longer delay).")
            elif core.stop.is_set():
                self.status.set(f"Stopped. {n} names waiting to be tested in the Review tab.")
                self._set_chip("Stopped", YELLOW)
            elif self.recheck_mode:
                self.status.set(f"Re-check finished. {n} names still look available.")
                self._set_chip("Done", GREEN)
            else:
                self.status.set(f"Finished. {n} names waiting to be tested in the Review tab.")
                self._set_chip("Done", GREEN)
            self._save_available()
            self._refresh_resume()
            if n and not self.avail_list.curselection():
                self.avail_list.selection_set(0)

    def _on_close(self):
        core.stop.set()
        if self.running:
            try:
                while True:
                    msg = self.q.get_nowait()
                    if msg[0] == "result":
                        self.run_results[msg[1]] = msg[2]
            except queue.Empty:
                pass
            self._update_pending()
        self._save_settings()
        self._save_available()
        self.destroy()


if __name__ == "__main__":
    App().mainloop()