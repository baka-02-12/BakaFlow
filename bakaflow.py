#!/usr/bin/env python3
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib, Pango
import cairo
import math
import json
import os
import socket
import subprocess

# --- COMPACT CSS STYLING ---
CSS_BASE = """
window { background-color: #1a1b26; color: #a9b1d6; font-family: sans-serif; }
.top-bar { background-color: #16161e; border-bottom: 1px solid #292e42; padding: 3px; }
.logo { color: #ffffff; font-weight: bold; font-size: 12px; margin-right: 9px; }
.tab-btn { background: transparent; border: none; border-bottom: 2px solid transparent; color: #565f89; padding: 3px 5px; font-weight: bold; box-shadow: none; font-size: 11px; }
.tab-btn:hover { color: #c0caf5; }
.tab-btn.active { color: #7aa2f7; border-bottom: 2px solid #7aa2f7; }
.graph-bg { background-color: #16161e; border: 1px solid #292e42; border-radius: 4px; }
.preview-bg { background-color: #16161e; border: 1px solid #292e42; border-radius: 4px; }
.entry-field { background-color: #16161e; border: 1px solid #292e42; color: #c0caf5; border-radius: 3px; padding: 3px; font-size: 11px; }
.entry-field:focus { border-color: #7aa2f7; }
.css-string { background-color: #16161e; border: 1px solid #7aa2f7; color: #7aa2f7; border-radius: 3px; padding: 3px; font-family: monospace; font-size: 10px; }
.preset-list { background-color: #1a1b26; }
.preset-row { padding: 1px; border-bottom: 1px solid #292e42; color: #a9b1d6; font-size: 11px; }
.preset-row:hover { background-color: #24283b; }
.preset-row:selected { background-color: #7aa2f7; color: #16161e; }
.manage-row { padding: 3px; border-bottom: 1px solid #292e42; font-size: 11px; }
.bottom-bar { background-color: #16161e; border-top: 1px solid #292e42; padding: 5px; }
.btn-apply { background-color: #7aa2f7; color: #16161e; font-weight: bold; border-radius: 3px; padding: 5px 9px; border: none; font-size: 11px; }
.btn-secondary { background-color: #24283b; color: #c0caf5; border-radius: 3px; padding: 3px 7px; border: none; font-size: 10px; }
.btn-danger { background-color: #f7768e; color: #16161e; border-radius: 3px; padding: 3px 7px; border: none; font-weight: bold; font-size: 10px; }
.status-text { color: #565f89; font-size: 10px; font-weight: bold; }
.placeholder-text { color: #565f89; font-size: 12px; font-weight: bold; }
.import-btn { padding: 9px; font-size: 12px; }
checkbutton { color: #a9b1d6; font-size: 10px; }
"""

def _make_css(scale):
    import re
    css = CSS_BASE
    def _fs(m):
        return f"font-size: {max(7, int(int(m.group(1))*scale))}px"
    css = re.sub(r"font-size: (\d+)px", _fs, css)
    def _pad(m):
        prop = m.group(1)
        vals = m.group(2).split()
        out = []
        for v in vals:
            if v.endswith("px"):
                out.append(f"{max(1, int(int(v[:-2])*scale))}px")
            else:
                out.append(v)
        return prop + " " + " ".join(out)
    css = re.sub(r"(padding: )([\d px]+)", _pad, css)
    def _rad(m):
        return f"border-radius: {max(2, int(int(m.group(1))*scale))}px"
    css = re.sub(r"border-radius: (\d+)px", _rad, css)
    return css.encode("utf-8")

CSS = _make_css(1.0)

BUILTIN_PRESETS = {
    "Linear": (0.0, 0.0, 1.0, 1.0), "Ease": (0.25, 0.1, 0.25, 1.0),
    "Ease In": (0.42, 0.0, 1.0, 1.0), "Ease Out": (0.0, 0.0, 0.58, 1.0),
    "Ease In Out": (0.42, 0.0, 0.58, 1.0), "Sine In": (0.12, 0.0, 0.39, 0.0),
    "Sine Out": (0.61, 1.0, 0.88, 1.0), "Sine In Out": (0.37, 0.0, 0.63, 1.0),
    "Quad In": (0.11, 0.0, 0.5, 0.0), "Quad Out": (0.5, 1.0, 0.89, 1.0),
    "Quad In Out": (0.45, 0.0, 0.55, 1.0), "Cubic In": (0.32, 0.0, 0.67, 0.0),
    "Cubic Out": (0.33, 1.0, 0.68, 1.0), "Cubic In Out": (0.65, 0.0, 0.35, 1.0),
    "Quart In": (0.5, 0.0, 0.75, 0.0), "Quart Out": (0.25, 1.0, 0.5, 1.0),
    "Quart In Out": (0.76, 0.0, 0.24, 1.0), "Quint In": (0.64, 0.0, 0.78, 0.0),
    "Quint Out": (0.22, 1.0, 0.36, 1.0), "Quint In Out": (0.83, 0.0, 0.17, 1.0),
    "Expo In": (0.7, 0.0, 0.84, 0.0), "Expo Out": (0.16, 1.0, 0.3, 1.0),
    "Expo In Out": (0.87, 0.0, 0.13, 1.0), "Circ In": (0.55, 0.0, 1.0, 0.45),
    "Circ Out": (0.0, 0.55, 0.45, 1.0), "Circ In Out": (0.85, 0.0, 0.15, 1.0),
    "Back In": (0.36, 0.0, 0.66, -0.56), "Back Out": (0.34, 1.56, 0.64, 1.0),
    "Back In Out": (0.68, -0.6, 0.32, 1.6)
}

CONFIG_DIR = os.path.expanduser("~/.config/bakaflow")
CONFIG_FILE = os.path.join(CONFIG_DIR, "custom_presets.json")

# <<SPEED_MATH_BEGIN>>
MIN_INFL = 0.001

def _bz(u, p1, p2):
    return 3 * (1 - u) ** 2 * u * p1 + 3 * (1 - u) * u ** 2 * p2 + u ** 3

def _bz_d(u, p1, p2):
    return 3 * ((1 - u) ** 2 * p1 + 2 * (1 - u) * u * (p2 - p1) + u ** 2 * (1 - p2))

def solve_u(x, x1, x2):
    if x <= 0.0: return 0.0
    if x >= 1.0: return 1.0
    lo, hi = 0.0, 1.0
    for _ in range(40):
        mid = (lo + hi) / 2.0
        if _bz(mid, x1, x2) < x: lo = mid
        else: hi = mid
    return (lo + hi) / 2.0

def speed_at_u(u, x1, y1, x2, y2):
    u = min(max(u, 1e-6), 1 - 1e-6)
    dx = _bz_d(u, x1, x2)
    if abs(dx) < 1e-12: return 0.0
    return _bz_d(u, y1, y2) / dx

def speed_at_time(t, x1, y1, x2, y2):
    return speed_at_u(solve_u(t, x1, x2), x1, y1, x2, y2)

def speed_curve(x1, y1, x2, y2, n=96):
    pts = []
    for k in range(n + 1):
        u = 0.5 - 0.5 * math.cos(math.pi * k / n)
        pts.append((_bz(u, x1, x2), speed_at_u(u, x1, y1, x2, y2)))
    return pts

def curve_extent(x1, y1, x2, y2, n=100):
    ys = [_bz(k / n, y1, y2) for k in range(n + 1)]
    return min(ys), max(ys)

def bezier_to_speed(x1, y1, x2, y2):
    i0 = max(MIN_INFL, x1)
    i1 = max(MIN_INFL, 1.0 - x2)
    if x1 < MIN_INFL and abs(y1) < 1e-9:
        s0 = y2 / x2 if x2 > MIN_INFL else 0.0
    else:
        s0 = y1 / i0
    if (1.0 - x2) < MIN_INFL and abs(1.0 - y2) < 1e-9:
        s1 = (1.0 - y1) / (1.0 - x1) if (1.0 - x1) > MIN_INFL else 0.0
    else:
        s1 = (1.0 - y2) / i1
    return s0, i0, s1, i1

def speed_to_bezier(s0, i0, s1, i1):
    return (i0, s0 * i0, 1.0 - i1, 1.0 - s1 * i1)

def nice_step(span, target=4):
    raw = max(span, 1e-9) / target
    mag = 10 ** math.floor(math.log10(raw))
    for m in (1, 2, 2.5, 5, 10):
        if raw <= m * mag: return m * mag
    return 10 * mag

def fmt_num(v):
    return f"{v:.2f}".rstrip("0").rstrip(".") if abs(v) < 1000 else f"{v:.0f}"
# <<SPEED_MATH_END>>

SPEED_PRESETS = {
    "Constant Speed": speed_to_bezier(1.0, 1.0, 1.0, 1.0),
    "Acceleration": speed_to_bezier(0.0, 0.8, 2.5, 0.8),
    "Deceleration": speed_to_bezier(2.5, 0.8, 0.0, 0.8),
    "Smooth Bell": speed_to_bezier(0.0, 0.5, 0.0, 0.5),
    "Whip (Fast Start)": speed_to_bezier(8.0, 0.05, 0.0, 0.9),
    "Slam (Fast End)": speed_to_bezier(0.0, 0.9, 8.0, 0.05),
    "Hit Stop": speed_to_bezier(3.0, 0.15, 3.0, 0.15),
    "Elastic Bounce": speed_to_bezier(2.0, 0.5, -1.5, 0.5),
}

class SpeedPresetRow(Gtk.ListBoxRow):
    def __init__(self, name, bez):
        super().__init__()
        self.preset_name = name
        self.bez = tuple(bez)
        self.pts = speed_curve(*self.bez, n=28)
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=3)
        box.set_margin_start(3); box.set_margin_end(3)
        box.set_margin_top(1); box.set_margin_bottom(1)

        self.draw_area = Gtk.DrawingArea()
        self.draw_area.set_size_request(22, 17)
        self.draw_area.connect("draw", self.on_draw_mini)
        box.pack_start(self.draw_area, False, False, 0)

        self.label = Gtk.Label(label=name)
        self.label.set_xalign(0)
        box.pack_start(self.label, True, True, 0)
        self.add(box)
        self.get_style_context().add_class("preset-row")

    def on_draw_mini(self, widget, cr):
        w = widget.get_allocated_width(); h = widget.get_allocated_height()
        pad = 2
        ss = [s for _, s in self.pts]
        top = max(1.0, min(max(ss), 8.0))
        bot = max(min(min(ss), 0.0), -3.0)
        span = top - bot
        def P(t, s):
            s = min(max(s, bot), top)
            return pad + t * (w - 2 * pad), pad + (top - s) / span * (h - 2 * pad)

        rgb = (0.1, 0.1, 0.12) if self.is_selected() else (0.48, 0.64, 0.97)
        _, y0 = P(0, 0)
        x, y = P(*self.pts[0])
        cr.move_to(x, y0)
        for t, s in self.pts:
            x, y = P(t, s); cr.line_to(x, y)
        cr.line_to(P(1, 0)[0], y0); cr.close_path()
        cr.set_source_rgba(rgb[0], rgb[1], rgb[2], 0.25); cr.fill()
        cr.set_line_width(1.2); cr.set_source_rgba(rgb[0], rgb[1], rgb[2], 1.0)
        x, y = P(*self.pts[0]); cr.move_to(x, y)
        for t, s in self.pts[1:]:
            x, y = P(t, s); cr.line_to(x, y)
        cr.stroke()

class PresetRow(Gtk.ListBoxRow):
    def __init__(self, name, x1, y1, x2, y2):
        super().__init__()
        self.preset_name = name
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=3)
        box.set_margin_start(3); box.set_margin_end(3)
        box.set_margin_top(1); box.set_margin_bottom(1)
        self.draw_area = Gtk.DrawingArea()
        self.draw_area.set_size_request(17, 17)
        self.draw_area.connect("draw", self.on_draw_mini, x1, y1, x2, y2)
        box.pack_start(self.draw_area, False, False, 0)
        self.label = Gtk.Label(label=name)
        self.label.set_xalign(0)
        box.pack_start(self.label, True, True, 0)
        self.add(box)
        self.get_style_context().add_class("preset-row")

    def on_draw_mini(self, widget, cr, x1, y1, x2, y2):
        width = widget.get_allocated_width(); height = widget.get_allocated_height()
        pad = 2
        if self.is_selected(): cr.set_source_rgba(0.1, 0.1, 0.12, 1.0)
        else: cr.set_source_rgba(0.48, 0.64, 0.97, 1.0)
        cr.set_line_width(1.2)
        def to_px(x, y):
            return pad + x * (width - 2*pad), height - pad - y * (height - 2*pad)
        x0, y0 = to_px(0, 0); x1_p, y1_p = to_px(x1, y1)
        x2_p, y2_p = to_px(x2, y2); x3, y3 = to_px(1, 1)
        cr.move_to(x0, y0); cr.curve_to(x1_p, y1_p, x2_p, y2_p, x3, y3); cr.stroke()

class BakaFlow(Gtk.Window):
    def __init__(self):
        super().__init__(title="BakaFlow")
        self.set_default_size(450, 440)
        self.set_resizable(True)
        self.set_keep_above(True)

        self.default_x1, self.default_y1 = 0.42, 0.0
        self.default_x2, self.default_y2 = 0.58, 1.0
        self.curve_x1, self.curve_y1 = self.default_x1, self.default_y1
        self.curve_x2, self.curve_y2 = self.default_x2, self.default_y2

        self.dragging_handle = None
        self.is_updating_entries = False
        self.padding = 11
        self.view_scale = 1.0
        self.custom_presets = {}

        self.is_showing_success = False
        self.last_status_text = ""

        self.anim_progress = 0.0
        self.anim_eased_value = 0.0
        self.anim_source_id = None
        self.is_animating = False

        self.last_graph_tab = "easing"
        self.dragging_speed_handle = None
        self.is_scrubbing = False
        self.s_ymin, self.s_ymax = -0.1, 2.0
        self.s_ml, self.s_mr, self.s_mt, self.s_mb = 30, 10, 8, 10

        self.load_custom_presets()
        self.ui_scale = 1.0
        self._css_provider = Gtk.CssProvider()
        self._apply_style()

        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.add(main_box)

        # TOP BAR
        top_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=3)
        top_bar.get_style_context().add_class("top-bar")
        logo = Gtk.Label(label="⛩️ BakaFlow")
        logo.get_style_context().add_class("logo")
        top_bar.pack_start(logo, False, False, 0)

        self.tab_buttons = {}
        tabs = [("Value", "easing", True), ("Speed", "speed", False), ("Presets", "presets", False), ("Manage", "manage", False), ("Import/Export", "import", False)]
        for label, page_name, is_active in tabs:
            btn = Gtk.Button(label=label)
            btn.get_style_context().add_class("tab-btn")
            if is_active: btn.get_style_context().add_class("active")
            btn.connect("clicked", self.on_tab_clicked, page_name)
            top_bar.pack_start(btn, False, False, 0)
            self.tab_buttons[page_name] = btn

        self.minus_btn = Gtk.Button(label="−")
        self.minus_btn.get_style_context().add_class("btn-secondary")
        self.minus_btn.set_tooltip_text("Zoom out UI")
        self.minus_btn.connect("clicked", self.on_zoom_out)
        top_bar.pack_end(self.minus_btn, False, False, 0)

        self.plus_btn = Gtk.Button(label="+")
        self.plus_btn.get_style_context().add_class("btn-secondary")
        self.plus_btn.set_tooltip_text("Zoom in UI")
        self.plus_btn.connect("clicked", self.on_zoom_in)
        top_bar.pack_end(self.plus_btn, False, False, 0)

        self.pin_check = Gtk.CheckButton(label="📌")
        self.pin_check.set_active(True)
        self.pin_check.connect("toggled", self.on_pin_toggled)
        top_bar.pack_end(self.pin_check, False, False, 0)

        main_box.pack_start(top_bar, False, False, 0)

        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.NONE)
        main_box.pack_start(self.stack, True, True, 0)

        # EASING PAGE
        easing_page = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        left_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
        left_box.set_margin_top(4); left_box.set_margin_bottom(4)
        left_box.set_margin_start(4); left_box.set_margin_end(4)

        self.graph_area = Gtk.DrawingArea()
        self.graph_area.set_size_request(-1, 82)
        self.graph_area.get_style_context().add_class("graph-bg")
        self.graph_area.add_events(Gdk.EventMask.BUTTON_PRESS_MASK | Gdk.EventMask.BUTTON_RELEASE_MASK | Gdk.EventMask.POINTER_MOTION_MASK | Gdk.EventMask.SCROLL_MASK)
        self.graph_area.connect("draw", self.on_draw)
        self.graph_area.connect("button-press-event", self.on_button_press)
        self.graph_area.connect("button-release-event", self.on_button_release)
        self.graph_area.connect("motion-notify-event", self.on_motion_notify)
        self.graph_area.connect("scroll-event", self.on_scroll)
        left_box.pack_start(self.graph_area, True, True, 0)

        preview_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=3)
        self.preview_area = Gtk.DrawingArea()
        self.preview_area.get_style_context().add_class("preview-bg")
        self.preview_area.set_size_request(-1, 18)
        self.preview_area.connect("draw", self.on_draw_preview)
        preview_box.pack_start(self.preview_area, True, True, 0)

        duration_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
        duration_lbl = Gtk.Label(label="Sec:")
        duration_lbl.get_style_context().add_class("status-text")
        self.duration_adj = Gtk.Adjustment(value=1.0, lower=0.5, upper=10.0, step_increment=0.5, page_increment=1.0, page_size=0.0)
        self.duration_spin = Gtk.SpinButton(adjustment=self.duration_adj, climb_rate=1.0, digits=1)
        self.duration_spin.set_width_chars(2)
        duration_box.pack_start(duration_lbl, False, False, 0)
        duration_box.pack_start(self.duration_spin, False, False, 0)
        preview_box.pack_start(duration_box, False, False, 0)

        self.val_play_btn = Gtk.Button(label="▶")
        self.val_play_btn.get_style_context().add_class("btn-secondary")
        self.val_play_btn.connect("clicked", self.on_play_pause)
        preview_box.pack_start(self.val_play_btn, False, False, 0)

        left_box.pack_start(preview_box, False, False, 0)

        inputs_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=3)
        self.entries = {}
        for key, val in [("x1", self.curve_x1), ("y1", self.curve_y1), ("x2", self.curve_x2), ("y2", self.curve_y2)]:
            vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
            lbl = Gtk.Label(label=key.upper())
            lbl.set_xalign(0); lbl.get_style_context().add_class("status-text")
            entry = Gtk.Entry()
            entry.set_text(f"{val:.2f}"); entry.set_width_chars(3); entry.get_style_context().add_class("entry-field")
            entry.connect("activate", self.on_entry_changed, key)
            vbox.pack_start(lbl, False, False, 0); vbox.pack_start(entry, False, False, 0)
            inputs_box.pack_start(vbox, True, True, 0)
            self.entries[key] = entry
        left_box.pack_start(inputs_box, False, False, 0)

        self.css_entry = Gtk.Entry()
        self.css_entry.set_text(self.get_css_string())
        self.css_entry.set_editable(False); self.css_entry.get_style_context().add_class("css-string")
        self.css_entry.connect("button-press-event", self.on_css_clicked)
        left_box.pack_start(self.css_entry, False, False, 0)

        check_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=7)
        self.lock_bounds_check = Gtk.CheckButton(label="Lock Handles")
        self.snap_grid_check = Gtk.CheckButton(label="Snap 0.1")
        check_box.pack_start(self.lock_bounds_check, False, False, 0)
        check_box.pack_start(self.snap_grid_check, False, False, 0)
        left_box.pack_start(check_box, False, False, 0)

        axis_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=7)
        axis_lbl = Gtk.Label(label="Apply to Axes:")
        axis_lbl.get_style_context().add_class("status-text")
        self.axis_x = Gtk.CheckButton(label="X")
        self.axis_y = Gtk.CheckButton(label="Y")
        self.axis_z = Gtk.CheckButton(label="Z")
        self.axis_x.set_active(True)
        self.axis_y.set_active(True)
        self.axis_z.set_active(True)
        axis_box.pack_start(axis_lbl, False, False, 0)
        axis_box.pack_start(self.axis_x, False, False, 0)
        axis_box.pack_start(self.axis_y, False, False, 0)
        axis_box.pack_start(self.axis_z, False, False, 0)
        left_box.pack_start(axis_box, False, False, 0)

        launch_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=3)
        launch_lbl = Gtk.Label(label="Need a safe start?")
        launch_lbl.get_style_context().add_class("status-text")
        launch_btn = Gtk.Button(label="Launch EffectCraft")
        launch_btn.get_style_context().add_class("btn-secondary")
        launch_btn.connect("clicked", self.on_launch_effectcraft)
        launch_box.pack_start(launch_lbl, False, False, 0)
        launch_box.pack_start(launch_btn, False, False, 0)
        left_box.pack_start(launch_box, False, False, 0)

        easing_page.pack1(left_box, True, False)

        right_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_margin_top(4); self.search_entry.set_margin_bottom(4)
        self.search_entry.set_margin_start(4); self.search_entry.set_margin_end(4)
        self.search_entry.set_placeholder_text("Search presets...")
        self.search_entry.connect("search-changed", self.on_search_changed)
        right_box.pack_start(self.search_entry, False, False, 0)

        scroll = Gtk.ScrolledWindow()
        self.preset_listbox = Gtk.ListBox()
        self.preset_listbox.get_style_context().add_class("preset-list")
        self.preset_listbox.connect("row-selected", self.on_preset_selected)
        for name, (x1, y1, x2, y2) in BUILTIN_PRESETS.items():
            self.preset_listbox.add(PresetRow(name, x1, y1, x2, y2))
        scroll.add(self.preset_listbox)
        right_box.pack_start(scroll, True, True, 0)
        easing_page.pack2(right_box, True, False)
        self.stack.add_named(easing_page, "easing")
        self.stack.add_named(self.build_speed_page(), "speed")

        # OTHER PAGES
        presets_page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        presets_page.set_margin_top(4); presets_page.set_margin_bottom(4)
        presets_page.set_margin_start(4); presets_page.set_margin_end(4)
        lbl_presets = Gtk.Label(label="Your Saved Presets")
        lbl_presets.set_xalign(0); lbl_presets.set_margin_bottom(3)
        presets_page.pack_start(lbl_presets, False, False, 0)
        saved_scroll = Gtk.ScrolledWindow()
        self.saved_listbox = Gtk.ListBox()
        self.saved_listbox.get_style_context().add_class("preset-list")
        self.saved_listbox.connect("row-selected", self.on_saved_preset_selected)
        saved_scroll.add(self.saved_listbox)
        presets_page.pack_start(saved_scroll, True, True, 0)
        self.stack.add_named(presets_page, "presets")
        self.refresh_saved_list()

        manage_page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        manage_page.set_margin_top(4); manage_page.set_margin_bottom(4)
        manage_page.set_margin_start(4); manage_page.set_margin_end(4)
        lbl_manage = Gtk.Label(label="Manage Your Presets")
        lbl_manage.set_xalign(0); lbl_manage.set_margin_bottom(3)
        manage_page.pack_start(lbl_manage, False, False, 0)
        manage_scroll = Gtk.ScrolledWindow()
        self.manage_listbox = Gtk.ListBox()
        self.manage_listbox.get_style_context().add_class("preset-list")
        manage_scroll.add(self.manage_listbox)
        manage_page.pack_start(manage_scroll, True, True, 0)
        self.stack.add_named(manage_page, "manage")
        self.refresh_manage_list()

        import_page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        import_page.set_valign(Gtk.Align.CENTER); import_page.set_halign(Gtk.Align.CENTER)
        lbl_import = Gtk.Label(label="Share & Backup Your Presets")
        lbl_import.get_style_context().add_class("placeholder-text")
        import_page.pack_start(lbl_import, False, False, 0)
        btn_export = Gtk.Button(label="Export Library to File...")
        btn_export.get_style_context().add_class("btn-secondary")
        btn_export.get_style_context().add_class("import-btn")
        btn_export.connect("clicked", self.on_export_clicked)
        import_page.pack_start(btn_export, False, False, 0)
        btn_import = Gtk.Button(label="Import Library from File...")
        btn_import.get_style_context().add_class("btn-secondary")
        btn_import.get_style_context().add_class("import-btn")
        btn_import.connect("clicked", self.on_import_clicked)
        import_page.pack_start(btn_import, False, False, 0)
        self.stack.add_named(import_page, "import")

        # BOTTOM BAR
        bottom_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=3)
        bottom_bar.get_style_context().add_class("bottom-bar")
        self.status_label = Gtk.Label(label="Ready")
        self.status_label.set_xalign(0); self.status_label.get_style_context().add_class("status-text")
        bottom_bar.pack_start(self.status_label, False, False, 0)

        btn_apply = self.btn_apply = Gtk.Button(label="APPLY VALUE")
        btn_apply.get_style_context().add_class("btn-apply")
        btn_apply.connect("clicked", self.on_apply_clicked)
        bottom_bar.pack_end(btn_apply, False, False, 0)
        btn_reset = Gtk.Button(label="Reset")
        btn_reset.get_style_context().add_class("btn-secondary")
        btn_reset.connect("clicked", self.on_reset_clicked)
        bottom_bar.pack_end(btn_reset, False, False, 0)
        btn_save = Gtk.Button(label="Save Preset")
        btn_save.get_style_context().add_class("btn-secondary")
        btn_save.connect("clicked", self.on_save_preset_clicked)
        bottom_bar.pack_end(btn_save, False, False, 0)
        main_box.pack_start(bottom_bar, False, False, 0)

        self.update_entries()
        self.fit_speed_view()
        self.update_speed_info()

    def _apply_style(self):
        css = _make_css(self.ui_scale)
        self._css_provider.load_from_data(css)
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            self._css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        Gtk.StyleContext.reset_widgets(Gdk.Screen.get_default())

    def on_zoom_in(self, button):
        self.ui_scale = min(2.0, self.ui_scale + 0.15)
        w, h = self.get_size()
        self.resize(int(w * 1.1), int(h * 1.1))
        self._apply_style()

    def on_zoom_out(self, button):
        self.ui_scale = max(0.6, self.ui_scale - 0.15)
        w, h = self.get_size()
        self.resize(int(w * 0.9), int(h * 0.9))
        self._apply_style()

    def on_pin_toggled(self, checkbox):
        self.set_keep_above(checkbox.get_active())

    def solve_bezier(self, x):
        if x <= 0.0: return 0.0
        if x >= 1.0: return 1.0
        lo, hi = 0.0, 1.0
        for _ in range(20):
            mid = (lo + hi) / 2.0
            x_est = 3*(1-mid)**2 * mid * self.curve_x1 + 3*(1-mid) * mid**2 * self.curve_x2 + mid**3
            if x_est < x: lo = mid
            else: hi = mid
        t = (lo + hi) / 2.0
        return 3*(1-t)**2 * t * self.curve_y1 + 3*(1-t) * t**2 * self.curve_y2 + t**3

    def set_progress(self, t):
        if self.is_animating:
            self.is_animating = False
            if self.anim_source_id:
                GLib.source_remove(self.anim_source_id)
                self.anim_source_id = None
            if hasattr(self, "val_play_btn"): self.val_play_btn.set_label("▶")
            if hasattr(self, "speed_play_btn"): self.speed_play_btn.set_label("▶")
        self.anim_progress = max(0.0, min(1.0, t))
        self.anim_eased_value = self.solve_bezier(self.anim_progress)
        self.update_speed_info()
        self._queue_all()

    def on_play_pause(self, button):
        if self.is_animating:
            # Pause the animation
            self.is_animating = False
            if self.anim_source_id:
                GLib.source_remove(self.anim_source_id)
                self.anim_source_id = None
            if hasattr(self, "val_play_btn"): self.val_play_btn.set_label("▶")
            if hasattr(self, "speed_play_btn"): self.speed_play_btn.set_label("▶")
        else:
            # Resume or start from 0
            if self.anim_progress >= 1.0:
                self.anim_progress = 0.0
                self.anim_eased_value = 0.0
            self.is_animating = True
            if hasattr(self, "val_play_btn"): self.val_play_btn.set_label("⏸")
            if hasattr(self, "speed_play_btn"): self.speed_play_btn.set_label("⏸")
            if self.anim_source_id:
                GLib.source_remove(self.anim_source_id)
            self.anim_source_id = GLib.timeout_add(16, self.update_animation)

    def update_animation(self):
        if not self.is_animating:
            self.anim_source_id = None
            return False
        duration = self.duration_spin.get_value()
        increment = 0.016 / duration
        self.anim_progress += increment

        if self.anim_progress >= 1.0:
            self.anim_progress = 1.0
            self.anim_eased_value = 1.0
            self.is_animating = False
            self.anim_source_id = None
            if hasattr(self, "val_play_btn"): self.val_play_btn.set_label("▶")
            if hasattr(self, "speed_play_btn"): self.speed_play_btn.set_label("▶")
            self.update_speed_info()
            self._queue_all()
            return False

        self.anim_eased_value = self.solve_bezier(self.anim_progress)
        self.update_speed_info()
        self._queue_all()
        return True

    def on_draw_preview(self, widget, cr):
        width = widget.get_allocated_width(); height = widget.get_allocated_height()
        track_y = height / 2.0
        cr.set_source_rgba(0.25, 0.28, 0.4, 1.0); cr.set_line_width(2)
        cr.move_to(10, track_y); cr.line_to(width - 10, track_y); cr.stroke()

        if self.is_animating or self.anim_progress > 0:
            cx = 10 + self.anim_eased_value * (width - 20)
            cr.set_source_rgba(0.48, 0.64, 0.97, 1.0)
            cr.rectangle(cx - 5, track_y - 5, 10, 10); cr.fill()

    def on_draw(self, widget, cr):
        width = widget.get_allocated_width(); height = widget.get_allocated_height()
        x0, y0 = self.math_to_cairo(0, 0, width, height); x1, y1 = self.math_to_cairo(1, 1, width, height)

        cr.set_line_width(1); cr.set_source_rgba(0.16, 0.18, 0.25, 1.0)
        for i in range(1, 5):
            _, cy = self.math_to_cairo(0, i/4.0, width, height); cr.move_to(x0, cy); cr.line_to(x1, cy)
            cx, _ = self.math_to_cairo(i/4.0, 0, width, height); cr.move_to(cx, y1); cr.line_to(cx, y0)
        cr.stroke()

        cr.set_source_rgba(0.25, 0.28, 0.4, 1.0); cr.set_line_width(2)
        cr.rectangle(x0, y1, x1 - x0, y0 - y1); cr.stroke()
        cr.set_source_rgba(0.3, 0.35, 0.5, 1.0)
        cr.move_to(x0, y0); cr.line_to(x1, y0); cr.move_to(x0, y0); cr.line_to(x0, y1); cr.stroke()

        cx1, cy1 = self.math_to_cairo(self.curve_x1, self.curve_y1, width, height)
        cx2, cy2 = self.math_to_cairo(self.curve_x2, self.curve_y2, width, height)

        blue = (0.48, 0.64, 0.97, 1.0)
        orange = (1.0, 0.62, 0.39, 1.0)

        # Out handle dotted line (Blue)
        cr.set_source_rgba(*blue); cr.set_line_width(1.5); cr.set_dash([5, 5])
        cr.move_to(x0, y0); cr.line_to(cx1, cy1); cr.stroke()

        # In handle dotted line (Orange)
        cr.set_source_rgba(*orange); cr.set_line_width(1.5); cr.set_dash([5, 5])
        cr.move_to(x1, y1); cr.line_to(cx2, cy2); cr.stroke()
        cr.set_dash([])

        # Main curve
        cr.set_source_rgba(0.48, 0.64, 0.97, 1.0); cr.set_line_width(4)
        cr.move_to(x0, y0); cr.curve_to(cx1, cy1, cx2, cy2, x1, y1); cr.stroke()
        cr.arc(x0, y0, 5, 0, 2 * math.pi); cr.fill(); cr.arc(x1, y1, 5, 0, 2 * math.pi); cr.fill()

        # Out Handle (Blue)
        cr.set_line_width(3); cr.set_source_rgba(0.1, 0.1, 0.12, 1.0)
        cr.arc(cx1, cy1, 7, 0, 2 * math.pi); cr.fill_preserve(); cr.set_source_rgba(*blue); cr.stroke()
        
        # In Handle (Orange)
        cr.set_source_rgba(0.1, 0.1, 0.12, 1.0); cr.arc(cx2, cy2, 7, 0, 2 * math.pi); cr.fill_preserve(); cr.set_source_rgba(*orange); cr.stroke()

        if self.is_animating or self.anim_progress > 0:
            px, py = self.math_to_cairo(self.anim_progress, self.anim_eased_value, width, height)
            cr.set_source_rgba(1.0, 0.4, 0.4, 0.5); cr.set_line_width(2)
            cr.move_to(px, y1); cr.line_to(px, y0); cr.stroke()
            cr.set_source_rgba(1.0, 0.4, 0.4, 1.0); cr.arc(px, py, 6, 0, 2 * math.pi); cr.fill()

    def on_launch_effectcraft(self, button):
        test_res = self.send_ec_command("keys.info", {})
        if test_res.get("ok"):
            self.show_success_temp("🟢 EffectCraft is already connected.")
            return
        try:
            process_check = subprocess.run(["pgrep", "-f", "effectcraft"], capture_output=True, text=True)
            if process_check.stdout.strip():
                dialog = Gtk.MessageDialog(transient_for=self, flags=0, message_type=Gtk.MessageType.WARNING, buttons=Gtk.ButtonsType.OK, text="EffectCraft is running without the control channel.\n\nPlease SAVE your project and restart it from this BakaFlow launcher to enable integration.")
                dialog.run(); dialog.destroy()
                return
        except FileNotFoundError:
            pass
        try:
            subprocess.Popen(["effectcraft", "--control", "9877"])
            self.show_success_temp("🚀 Launching EffectCraft with control channel...")
        except Exception as e:
            self.show_success_temp(f"❌ Launch failed: {e}")

    def show_success_temp(self, msg):
        self.is_showing_success = True
        self.status_label.set_text(msg)
        self.last_status_text = msg
        GLib.timeout_add_seconds(3, self.end_success_msg)

    def end_success_msg(self):
        self.is_showing_success = False
        self.status_label.set_text("Ready")
        return False

    def send_ec_command(self, cmd_name, params, is_top_level=False):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(0.2)
            s.connect(("127.0.0.1", 9877))
            if is_top_level:
                payload = {"id": 1, "method": cmd_name, "params": params}
            else:
                payload = {"id": 1, "method": "engine.execute", "params": {"command": cmd_name, "params": params}}
            s.sendall((json.dumps(payload) + "\n").encode('utf-8'))
            response = b""
            while True:
                chunk = s.recv(4096)
                if not chunk: break
                response += chunk
                if b"\n" in response: break
            s.close()
            return json.loads(response.decode('utf-8'))
        except Exception:
            return {"ok": False}

    def on_apply_clicked(self, button):
        if self.last_graph_tab == "speed":
            s0, i0, s1, i1 = self.speed_handles()
            ease_out = (s0, i0 * 100.0)
            ease_in = (s1, i1 * 100.0)
            do_in = do_out = True
            send_missing = True
        else:
            in_infl = max(0.1, (1.0 - self.curve_x2) * 100.0)
            out_infl = max(0.1, self.curve_x1 * 100.0)
            ease_in = ((1.0 - self.curve_y2) / (in_infl / 100.0), in_infl)
            ease_out = (self.curve_y1 / (out_infl / 100.0), out_infl)
            do_in = do_out = True
            send_missing = True
        self._apply_ease(ease_in, ease_out, do_in, do_out, send_missing)

    def _apply_ease(self, ease_in, ease_out, do_in, do_out, send_missing):
        info_res = self.send_ec_command("keys.info", {})
        if not info_res.get("ok"):
            self.show_success_temp("❌ Error: Could not reach EffectCraft.")
            return

        selected_keys = info_res.get("result", [])
        if not selected_keys:
            self.show_success_temp("❌ Error: No keyframes selected.")
            return

        original_selection = [{"layer": k["layer"], "prop": k["path"], "time": k["time"]} for k in selected_keys]

        targets = {}
        for k in selected_keys:
            key_tuple = (k["layer"], k["path"])
            if key_tuple not in targets: targets[key_tuple] = set()
            targets[key_tuple].add(k["time"])

        applied_count = 0
        last_error = ""

        x_on = self.axis_x.get_active()
        y_on = self.axis_y.get_active()
        z_on = self.axis_z.get_active()
        checked_axes = []
        if x_on: checked_axes.append(0)
        if y_on: checked_axes.append(1)
        if z_on: checked_axes.append(2)

        in_norm, in_influence = ease_in
        out_norm, out_influence = ease_out

        for (layer_id, prop_path), selected_times in targets.items():
            tail = prop_path[-1] if prop_path else ""
            is_already_separated = tail in ("X", "Y", "Z")
            paths_to_ease = []

            if not is_already_separated:
                base_res = self.send_ec_command("prop.get", {"layer": layer_id, "path": prop_path})
                if base_res.get("ok"):
                    prop_type = base_res["result"].get("type", "scalar")

                    if prop_type == "vec3":
                        if x_on and y_on and z_on:
                            paths_to_ease = [prop_path]
                        else:
                            self.send_ec_command("prop.separateDimensions", {"layer": layer_id, "value": prop_path})
                            if x_on: paths_to_ease.append(f"{prop_path}X")
                            if y_on: paths_to_ease.append(f"{prop_path}Y")
                            if z_on: paths_to_ease.append(f"{prop_path}Z")
                    elif prop_type == "vec2":
                        if x_on and y_on:
                            paths_to_ease = [prop_path]
                        else:
                            self.send_ec_command("prop.separateDimensions", {"layer": layer_id, "value": prop_path})
                            if x_on: paths_to_ease.append(f"{prop_path}X")
                            if y_on: paths_to_ease.append(f"{prop_path}Y")
                    else:
                        paths_to_ease = [prop_path]
                else:
                    paths_to_ease = [prop_path]
            else:
                if tail == "X" and not x_on: continue
                if tail == "Y" and not y_on: continue
                if tail == "Z" and not z_on: continue
                paths_to_ease = [prop_path]

            for target_path in paths_to_ease:
                prop_res = self.send_ec_command("prop.get", {"layer": layer_id, "path": target_path})
                if not prop_res.get("ok"):
                    last_error = f"Could not read {target_path}"
                    continue

                all_keys = prop_res["result"].get("keys", [])
                if len(all_keys) < 2: continue

                for i, k in enumerate(all_keys):
                    if not any(abs(k["time"] - t) < 0.001 for t in selected_times):
                        continue

                    payload = {}

                    if do_in and i > 0:
                        k_prev = all_keys[i-1]
                        D = k["time"] - k_prev["time"]
                        if D > 0.001:
                            if isinstance(k["value"], list):
                                num_dims = len(k["value"])
                                in_speeds = [0.0] * num_dims
                                has_movement = False
                                for dim in range(min(num_dims, 3)):
                                    if dim in checked_axes:
                                        delta_v = k["value"][dim] - k_prev["value"][dim]
                                        if abs(delta_v) > 0.001:
                                            in_speeds[dim] = (in_norm * delta_v) / D
                                            has_movement = True
                                if has_movement:
                                    payload["inSpeed"] = in_speeds
                                    payload["inInfluence"] = in_influence
                            else:
                                delta_v = k["value"] - k_prev["value"]
                                if abs(delta_v) > 0.001:
                                    payload["inSpeed"] = (in_norm * delta_v) / D
                                    payload["inInfluence"] = in_influence

                    if do_out and i < len(all_keys) - 1:
                        k_next = all_keys[i+1]
                        D = k_next["time"] - k["time"]
                        if D > 0.001:
                            if isinstance(k["value"], list):
                                num_dims = len(k["value"])
                                out_speeds = [0.0] * num_dims
                                has_movement = False
                                for dim in range(min(num_dims, 3)):
                                    if dim in checked_axes:
                                        delta_v = k_next["value"][dim] - k["value"][dim]
                                        if abs(delta_v) > 0.001:
                                            out_speeds[dim] = (out_norm * delta_v) / D
                                            has_movement = True
                                if has_movement:
                                    payload["outSpeed"] = out_speeds
                                    payload["outInfluence"] = out_influence
                            else:
                                delta_v = k_next["value"] - k["value"]
                                if abs(delta_v) > 0.001:
                                    payload["outSpeed"] = (out_norm * delta_v) / D
                                    payload["outInfluence"] = out_influence

                    if payload:
                        send_in = do_in and (send_missing or "inSpeed" in payload)
                        send_out = do_out and (send_missing or "outSpeed" in payload)
                        is_sep = target_path and target_path[-1] in ("X", "Y", "Z")
                        if isinstance(k["value"], list) and not is_sep:
                            num_dims = len(k["value"])
                            for d in checked_axes:
                                if d >= num_dims: continue
                                if send_in:
                                    speed_in = payload.get("inSpeed", 0.0)
                                    if isinstance(speed_in, list): speed_in = speed_in[d]
                                    self.send_ec_command("keys.setEase", {
                                        "layer": layer_id, "path": target_path,
                                        "time": k["time"], "side": "in", "dim": d,
                                        "speed": speed_in,
                                        "influence": payload.get("inInfluence", 33.3)
                                    })
                                if send_out:
                                    speed_out = payload.get("outSpeed", 0.0)
                                    if isinstance(speed_out, list): speed_out = speed_out[d]
                                    self.send_ec_command("keys.setEase", {
                                        "layer": layer_id, "path": target_path,
                                        "time": k["time"], "side": "out", "dim": d,
                                        "speed": speed_out,
                                        "influence": payload.get("outInfluence", 33.3)
                                    })
                        else:
                            if send_in:
                                self.send_ec_command("keys.setEase", {
                                    "layer": layer_id, "path": target_path,
                                    "time": k["time"], "side": "in", "dim": 0,
                                    "speed": payload.get("inSpeed", 0.0),
                                    "influence": payload.get("inInfluence", 33.3)
                                })
                            if send_out:
                                self.send_ec_command("keys.setEase", {
                                    "layer": layer_id, "path": target_path,
                                    "time": k["time"], "side": "out", "dim": 0,
                                    "speed": payload.get("outSpeed", 0.0),
                                    "influence": payload.get("outInfluence", 33.3)
                                })
                        if send_in or send_out:
                            applied_count += 1

        if original_selection:
            self.send_ec_command("keys.select", {"keys": original_selection})

        if applied_count > 0:
            self.show_success_temp(f"✅ Success! Applied to {applied_count} keyframe(s).")
        else:
            self.show_success_temp(f"❌ Error: {last_error or 'nothing to ease (need 2+ keys with movement).'}")

    def on_export_clicked(self, button):
        dialog = Gtk.FileChooserDialog(title="Export Presets", parent=self, action=Gtk.FileChooserAction.SAVE)
        dialog.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_SAVE, Gtk.ResponseType.OK)
        dialog.set_current_name("bakaflow_presets.json")
        filter_json = Gtk.FileFilter(); filter_json.set_name("JSON Files"); filter_json.add_pattern("*.json")
        dialog.add_filter(filter_json)
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            filepath = dialog.get_filename()
            try:
                with open(filepath, "w") as f: json.dump(self.custom_presets, f, indent=4)
                self.show_success_temp(f"✅ Exported to {os.path.basename(filepath)}")
            except Exception as e: self.show_success_temp(f"❌ Failed to export: {e}")
        dialog.destroy()

    def on_import_clicked(self, button):
        dialog = Gtk.FileChooserDialog(title="Import Presets", parent=self, action=Gtk.FileChooserAction.OPEN)
        dialog.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OPEN, Gtk.ResponseType.OK)
        filter_json = Gtk.FileFilter(); filter_json.set_name("JSON Files"); filter_json.add_pattern("*.json")
        dialog.add_filter(filter_json)
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            filepath = dialog.get_filename()
            try:
                with open(filepath, "r") as f: imported_data = json.load(f)
                if not isinstance(imported_data, dict): raise ValueError("Invalid preset file format.")
                for name, curve in imported_data.items():
                    if isinstance(curve, list) and len(curve) == 4: self.custom_presets[name] = curve
                self.save_custom_presets()
                self.refresh_saved_list()
                self.refresh_manage_list()
                self.show_success_temp(f"✅ Imported presets from {os.path.basename(filepath)}")
            except Exception as e: self.show_success_temp(f"❌ Failed to import: {e}")
        dialog.destroy()

    def load_custom_presets(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f: self.custom_presets = json.load(f)
            except Exception: pass

    def save_custom_presets(self):
        os.makedirs(CONFIG_DIR, exist_ok=True)
        try:
            with open(CONFIG_FILE, "w") as f: json.dump(self.custom_presets, f, indent=4)
        except Exception: pass

    def refresh_saved_list(self):
        if hasattr(self, "speed_preset_listbox"): self.refresh_speed_presets()
        for row in self.saved_listbox.get_children(): self.saved_listbox.remove(row)
        for name in self.custom_presets.keys():
            row = Gtk.ListBoxRow()
            row_label = Gtk.Label(label=name)
            row_label.set_xalign(0); row_label.set_margin_start(4)
            row_label.set_margin_top(2); row_label.set_margin_bottom(2)
            row.get_style_context().add_class("preset-row")
            row.add(row_label); self.saved_listbox.add(row)
        self.saved_listbox.show_all()

    def refresh_manage_list(self):
        for row in self.manage_listbox.get_children(): self.manage_listbox.remove(row)
        for name in self.custom_presets.keys():
            row = Gtk.ListBoxRow()
            row_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=3)
            row_box.set_margin_start(4); row_box.set_margin_end(4)
            row_box.set_margin_top(2); row_box.set_margin_bottom(2)
            row.get_style_context().add_class("manage-row")
            lbl = Gtk.Label(label=name); lbl.set_xalign(0)
            row_box.pack_start(lbl, True, True, 0)
            btn_rename = Gtk.Button(label="Rename"); btn_rename.get_style_context().add_class("btn-secondary")
            btn_rename.connect("clicked", self.on_rename_preset, name)
            row_box.pack_start(btn_rename, False, False, 0)
            btn_delete = Gtk.Button(label="Delete"); btn_delete.get_style_context().add_class("btn-danger")
            btn_delete.connect("clicked", self.on_delete_preset, name)
            row_box.pack_start(btn_delete, False, False, 0)
            row.add(row_box); self.manage_listbox.add(row)
        self.manage_listbox.show_all()

    def on_save_preset_clicked(self, button):
        dialog = Gtk.Dialog(title="Save Custom Preset", transient_for=self, flags=0)
        dialog.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_SAVE, Gtk.ResponseType.OK)
        box = dialog.get_content_area(); box.add(Gtk.Label(label="Enter a name for this curve:"))
        entry = Gtk.Entry(); entry.set_placeholder_text("e.g., My Smooth Bounce")
        box.add(entry); box.show_all()
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            name = entry.get_text().strip()
            if name:
                self.custom_presets[name] = [self.curve_x1, self.curve_y1, self.curve_x2, self.curve_y2]
                self.save_custom_presets(); self.refresh_saved_list(); self.refresh_manage_list()
        dialog.destroy()

    def on_rename_preset(self, button, old_name):
        dialog = Gtk.Dialog(title="Rename Preset", transient_for=self, flags=0)
        dialog.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, "Rename", Gtk.ResponseType.OK)
        box = dialog.get_content_area(); box.add(Gtk.Label(label="Enter new name:"))
        entry = Gtk.Entry(); entry.set_text(old_name)
        box.add(entry); box.show_all()
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            new_name = entry.get_text().strip()
            if new_name and new_name != old_name:
                self.custom_presets[new_name] = self.custom_presets.pop(old_name)
                self.save_custom_presets(); self.refresh_saved_list(); self.refresh_manage_list()
        dialog.destroy()

    def on_delete_preset(self, button, name):
        dialog = Gtk.MessageDialog(transient_for=self, flags=0, message_type=Gtk.MessageType.QUESTION, buttons=Gtk.ButtonsType.YES_NO, text=f"Delete preset '{name}'?")
        response = dialog.run()
        if response == Gtk.ResponseType.YES:
            del self.custom_presets[name]; self.save_custom_presets(); self.refresh_saved_list(); self.refresh_manage_list()
        dialog.destroy()

    def on_saved_preset_selected(self, listbox, row):
        if row is None: return
        preset_name = row.get_child().get_text()
        if preset_name in self.custom_presets:
            x1, y1, x2, y2 = self.custom_presets[preset_name]
            self.curve_x1, self.curve_y1 = x1, y1; self.curve_x2, self.curve_y2 = x2, y2
            self.speed_preset_listbox.unselect_all()
            self.update_entries(); self.update_css_entry(); self._on_curve_changed()
            self.on_tab_clicked(None, self.last_graph_tab)

    def on_tab_clicked(self, button, page_name):
        self.stack.set_visible_child_name(page_name)
        if page_name in ("easing", "speed"):
            self.last_graph_tab = page_name
            self.btn_apply.set_label("APPLY SPEED" if page_name == "speed" else "APPLY VALUE")
            if page_name == "speed":
                self.fit_speed_view(); self.update_speed_info(); self.speed_graph.queue_draw()
        for name, btn in self.tab_buttons.items():
            if name == page_name: btn.get_style_context().add_class("active")
            else: btn.get_style_context().remove_class("active")

    def get_css_string(self):
        return f"cubic-bezier({self.curve_x1:.2f}, {self.curve_y1:.2f}, {self.curve_x2:.2f}, {self.curve_y2:.2f})"

    def update_css_entry(self):
        self.css_entry.set_text(self.get_css_string())
        if hasattr(self, "s_css_entry"): self.s_css_entry.set_text(self.get_css_string())

    def on_reset_clicked(self, button):
        self.curve_x1, self.curve_y1 = self.default_x1, self.default_y1
        self.curve_x2, self.curve_y2 = self.default_x2, self.default_y2
        self._unselect_presets()
        self.update_entries(); self.update_css_entry(); self._on_curve_changed()

    def on_css_clicked(self, widget, event):
        widget.select_region(0, -1)
        clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        clipboard.set_text(self.get_css_string(), -1)
        return False

    def math_to_cairo(self, x, y, width, height):
        cx_center = width / 2.0; cy_center = height / 2.0
        usable_w = (width - 2 * self.padding) * self.view_scale
        usable_h = (height - 2 * self.padding) * self.view_scale
        return cx_center + (x - 0.5) * usable_w, cy_center - (y - 0.5) * usable_h

    def cairo_to_math(self, cx, cy, width, height):
        cx_center = width / 2.0; cy_center = height / 2.0
        usable_w = (width - 2 * self.padding) * self.view_scale
        usable_h = (height - 2 * self.padding) * self.view_scale
        return (cx - cx_center) / usable_w + 0.5, -(cy - cy_center) / usable_h + 0.5

    def dist_to_segment(self, px, py, x1, y1, x2, y2):
        dx = x2 - x1; dy = y2 - y1
        if dx == 0 and dy == 0: return math.hypot(px - x1, py - y1)
        t = ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)
        t = max(0.0, min(1.0, t))
        return math.hypot(px - (x1 + t * dx), py - (y1 + t * dy))

    def on_scroll(self, widget, event):
        if event.direction == Gdk.ScrollDirection.UP: self.view_scale = min(3.0, self.view_scale * 1.1)
        elif event.direction == Gdk.ScrollDirection.DOWN: self.view_scale = max(0.2, self.view_scale / 1.1)
        widget.queue_draw(); return True

    def on_button_press(self, widget, event):
        width = widget.get_allocated_width(); height = widget.get_allocated_height()
        x0, y0 = self.math_to_cairo(0, 0, width, height); x1, y1 = self.math_to_cairo(1, 1, width, height)
        cx1, cy1 = self.math_to_cairo(self.curve_x1, self.curve_y1, width, height)
        cx2, cy2 = self.math_to_cairo(self.curve_x2, self.curve_y2, width, height)
        if math.hypot(event.x - cx1, event.y - cy1) < 15: self.dragging_handle = 1
        elif math.hypot(event.x - cx2, event.y - cy2) < 15: self.dragging_handle = 2
        elif self.dist_to_segment(event.x, event.y, x0, y0, cx1, cy1) < 10: self.dragging_handle = 1
        elif self.dist_to_segment(event.x, event.y, x1, y1, cx2, cy2) < 10: self.dragging_handle = 2
        else:
            # Check if inside the graph box to scrub
            if x0 <= event.x <= x1 and y1 <= event.y <= y0:
                self.is_scrubbing = True
                mx, _ = self.cairo_to_math(event.x, event.y, width, height)
                self.set_progress(mx)
        return True

    def on_motion_notify(self, widget, event):
        if self.is_scrubbing:
            width = widget.get_allocated_width(); height = widget.get_allocated_height()
            mx, _ = self.cairo_to_math(event.x, event.y, width, height)
            self.set_progress(mx)
            return True
        if not self.dragging_handle: return False
        width = widget.get_allocated_width(); height = widget.get_allocated_height()
        mx, my = self.cairo_to_math(event.x, event.y, width, height)

        if self.lock_bounds_check.get_active():
            mx = max(0.0, min(1.0, mx)); my = max(0.0, min(1.0, my))
        else:
            mx = max(0.0, min(1.0, mx)); my = max(-2.0, min(3.0, my))

        if self.snap_grid_check.get_active():
            mx = round(mx * 10) / 10.0; my = round(my * 10) / 10.0

        if self.dragging_handle == 1: self.curve_x1, self.curve_y1 = mx, my
        else: self.curve_x2, self.curve_y2 = mx, my

        self.update_entries(); self.update_css_entry()
        self._unselect_presets()
        self._on_curve_changed()
        return True

    def on_button_release(self, widget, event):
        self.dragging_handle = None
        self.is_scrubbing = False
        return True

    def update_entries(self):
        self.is_updating_entries = True
        self.entries["x1"].set_text(f"{self.curve_x1:.2f}"); self.entries["y1"].set_text(f"{self.curve_y1:.2f}")
        self.entries["x2"].set_text(f"{self.curve_x2:.2f}"); self.entries["y2"].set_text(f"{self.curve_y2:.2f}")
        if hasattr(self, "sentries"):
            s0, i0, s1, i1 = self.speed_handles()
            self.sentries["os"].set_text(fmt_num(s0)); self.sentries["oi"].set_text(f"{i0 * 100:.1f}")
            self.sentries["is"].set_text(fmt_num(s1)); self.sentries["ii"].set_text(f"{i1 * 100:.1f}")
        self.is_updating_entries = False

    def on_entry_changed(self, entry, key):
        if self.is_updating_entries: return
        try:
            val = float(entry.get_text())
            if key == "x1": self.curve_x1 = max(0.0, min(1.0, val))
            elif key == "y1": self.curve_y1 = val
            elif key == "x2": self.curve_x2 = max(0.0, min(1.0, val))
            elif key == "y2": self.curve_y2 = val
            entry.set_text(f"{getattr(self, 'curve_' + key):.2f}")
            self.update_css_entry()
            self._unselect_presets()
            self._on_curve_changed()
        except ValueError:
            self.update_entries()

    def on_preset_selected(self, listbox, row):
        if row is None: return
        preset_name = getattr(row, 'preset_name', None)
        if not preset_name: return
        if preset_name in BUILTIN_PRESETS:
            x1, y1, x2, y2 = BUILTIN_PRESETS[preset_name]
            self.speed_preset_listbox.unselect_all()
            self.curve_x1, self.curve_y1 = x1, y1; self.curve_x2, self.curve_y2 = x2, y2
            self.update_entries(); self.update_css_entry()
            self._on_curve_changed()

    def on_search_changed(self, entry):
        search_text = entry.get_text().lower()
        def filter_func(row):
            if row is None: return False
            name = getattr(row, 'preset_name', "")
            return search_text in name.lower()
        self.preset_listbox.set_filter_func(filter_func)

    def _link_checks(self, a, b):
        def on_a(w):
            if b.get_active() != w.get_active(): b.set_active(w.get_active())
        def on_b(w):
            if a.get_active() != w.get_active(): a.set_active(w.get_active())
        a.connect("toggled", on_a); b.connect("toggled", on_b)

    def build_speed_page(self):
        page = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        left = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
        left.set_margin_top(4); left.set_margin_bottom(4)
        left.set_margin_start(4); left.set_margin_end(4)

        self.speed_graph = Gtk.DrawingArea()
        self.speed_graph.set_size_request(-1, 82)
        self.speed_graph.get_style_context().add_class("graph-bg")
        self.speed_graph.add_events(Gdk.EventMask.BUTTON_PRESS_MASK | Gdk.EventMask.BUTTON_RELEASE_MASK | Gdk.EventMask.POINTER_MOTION_MASK | Gdk.EventMask.SCROLL_MASK)
        self.speed_graph.connect("draw", self.on_draw_speed)
        self.speed_graph.connect("button-press-event", self.on_s_press)
        self.speed_graph.connect("button-release-event", self.on_s_release)
        self.speed_graph.connect("motion-notify-event", self.on_s_motion)
        self.speed_graph.connect("scroll-event", self.on_s_scroll)
        self.speed_graph.set_tooltip_text("Drag a handle: up/down = speed, left/right = influence.\nShift = lock speed at 0 · Ctrl = mirror In/Out · Scroll = zoom speed axis")
        left.pack_start(self.speed_graph, True, True, 0)

        preview_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=3)
        self.speed_preview = Gtk.DrawingArea()
        self.speed_preview.get_style_context().add_class("preview-bg")
        self.speed_preview.set_size_request(-1, 18)
        self.speed_preview.connect("draw", self.on_draw_speed_preview)
        preview_box.pack_start(self.speed_preview, True, True, 0)

        duration_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
        duration_lbl = Gtk.Label(label="Sec:")
        duration_lbl.get_style_context().add_class("status-text")
        spin = Gtk.SpinButton(adjustment=self.duration_adj, climb_rate=1.0, digits=1)
        spin.set_width_chars(2)
        duration_box.pack_start(duration_lbl, False, False, 0)
        duration_box.pack_start(spin, False, False, 0)
        preview_box.pack_start(duration_box, False, False, 0)

        self.val_play_btn = Gtk.Button(label="▶")
        self.val_play_btn.get_style_context().add_class("btn-secondary")
        self.val_play_btn.connect("clicked", self.on_play_pause)
        preview_box.pack_start(self.val_play_btn, False, False, 0)
        left.pack_start(preview_box, False, False, 0)

        info_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=3)
        self.speed_info = Gtk.Label(label="")
        self.speed_info.set_xalign(0)
        self.speed_info.set_ellipsize(Pango.EllipsizeMode.END)
        self.speed_info.get_style_context().add_class("status-text")
        info_row.pack_start(self.speed_info, True, True, 0)
        left.pack_start(info_row, False, False, 0)

        inputs_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=3)
        self.sentries = {}
        for key, label in [("os", "OUT SPD"), ("oi", "OUT INF%"), ("is", "IN SPD"), ("ii", "IN INF%")]:
            vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
            lbl = Gtk.Label(label=label)
            lbl.set_xalign(0); lbl.get_style_context().add_class("status-text")
            entry = Gtk.Entry()
            entry.set_width_chars(3); entry.get_style_context().add_class("entry-field")
            entry.connect("activate", self.on_s_entry_changed, key)
            entry.connect("focus-out-event", self.on_s_entry_focus_out, key)
            vbox.pack_start(lbl, False, False, 0); vbox.pack_start(entry, False, False, 0)
            inputs_box.pack_start(vbox, True, True, 0)
            self.sentries[key] = entry
        left.pack_start(inputs_box, False, False, 0)

        self.s_css_entry = Gtk.Entry()
        self.s_css_entry.set_text(self.get_css_string())
        self.s_css_entry.set_editable(False)
        self.s_css_entry.get_style_context().add_class("css-string")
        self.s_css_entry.connect("button-press-event", self.on_css_clicked)
        left.pack_start(self.s_css_entry, False, False, 0)

        check_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=7)
        self.no_over_check = Gtk.CheckButton(label="Lock Handles")
        self.no_over_check.set_tooltip_text("Keep handles inside the graph box")
        self.s_snap_check = Gtk.CheckButton(label="Snap 0.1 · 5%")
        self.mirror_check = Gtk.CheckButton(label="Mirror")
        self.mirror_check.set_tooltip_text("In handle = Out handle (symmetric ease). Hold Ctrl while dragging for the same.")
        self._link_checks(self.no_over_check, self.lock_bounds_check)
        for c in (self.no_over_check, self.s_snap_check, self.mirror_check):
            check_box.pack_start(c, False, False, 0)
        left.pack_start(check_box, False, False, 0)

        apply_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=7)
        axes_lbl = Gtk.Label(label="Apply to Axes:")
        axes_lbl.get_style_context().add_class("status-text")
        self.s_axis_x = Gtk.CheckButton(label="X"); self.s_axis_y = Gtk.CheckButton(label="Y"); self.s_axis_z = Gtk.CheckButton(label="Z")
        for c in (self.s_axis_x, self.s_axis_y, self.s_axis_z): c.set_active(True)
        self._link_checks(self.s_axis_x, self.axis_x)
        self._link_checks(self.s_axis_y, self.axis_y)
        self._link_checks(self.s_axis_z, self.axis_z)
        for w in (axes_lbl, self.s_axis_x, self.s_axis_y, self.s_axis_z):
            apply_box.pack_start(w, False, False, 0)
        left.pack_start(apply_box, False, False, 0)

        launch_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=3)
        launch_lbl = Gtk.Label(label="Need a safe start?")
        launch_lbl.get_style_context().add_class("status-text")
        launch_btn = Gtk.Button(label="Launch EffectCraft")
        launch_btn.get_style_context().add_class("btn-secondary")
        launch_btn.connect("clicked", self.on_launch_effectcraft)
        launch_box.pack_start(launch_lbl, False, False, 0)
        launch_box.pack_start(launch_btn, False, False, 0)
        left.pack_start(launch_box, False, False, 0)

        page.pack1(left, True, False)

        right = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.speed_search = Gtk.SearchEntry()
        self.speed_search.set_margin_top(4); self.speed_search.set_margin_bottom(4)
        self.speed_search.set_margin_start(4); self.speed_search.set_margin_end(4)
        self.speed_search.set_placeholder_text("Search presets...")
        self.speed_search.connect("search-changed", self.on_s_search_changed)
        right.pack_start(self.speed_search, False, False, 0)
        scroll = Gtk.ScrolledWindow()
        self.speed_preset_listbox = Gtk.ListBox()
        self.speed_preset_listbox.get_style_context().add_class("preset-list")
        self.speed_preset_listbox.connect("row-selected", self.on_speed_preset_selected)
        scroll.add(self.speed_preset_listbox)
        right.pack_start(scroll, True, True, 0)
        page.pack2(right, True, False)
        return page

    def speed_handles(self):
        return bezier_to_speed(self.curve_x1, self.curve_y1, self.curve_x2, self.curve_y2)

    def _queue_all(self):
        self.graph_area.queue_draw(); self.preview_area.queue_draw()
        self.speed_graph.queue_draw(); self.speed_preview.queue_draw()

    def _on_curve_changed(self, fit=True):
        if fit and self.dragging_speed_handle is None:
            self.fit_speed_view()
        self.update_speed_info()
        self._queue_all()

    def _unselect_presets(self):
        self.preset_listbox.unselect_all(); self.saved_listbox.unselect_all()
        self.speed_preset_listbox.unselect_all()

    def refresh_speed_presets(self):
        lb = self.speed_preset_listbox
        for row in lb.get_children(): lb.remove(row)
        for name, c in self.custom_presets.items():
            if isinstance(c, list) and len(c) == 4:
                lb.add(SpeedPresetRow("★ " + name, c))
        for name, c in SPEED_PRESETS.items(): lb.add(SpeedPresetRow(name, c))
        for name, c in BUILTIN_PRESETS.items(): lb.add(SpeedPresetRow(name, c))
        lb.show_all()

    def on_speed_preset_selected(self, listbox, row):
        bez = getattr(row, "bez", None)
        if row is None or not bez: return
        self.curve_x1, self.curve_y1, self.curve_x2, self.curve_y2 = bez
        self.preset_listbox.unselect_all(); self.saved_listbox.unselect_all()
        self.update_entries(); self.update_css_entry(); self._on_curve_changed()

    def on_s_search_changed(self, entry):
        text = entry.get_text().lower()
        def filter_func(row):
            if row is None: return False
            return text in getattr(row, "preset_name", "").lower()
        self.speed_preset_listbox.set_filter_func(filter_func)

    def set_curve_from_speed(self, out=None, inn=None):
        if out is not None:
            s0, i0 = out
            self.curve_x1 = min(1.0, max(MIN_INFL, i0)); self.curve_y1 = s0 * self.curve_x1
        if inn is not None:
            s1, i1 = inn
            i1 = min(1.0, max(MIN_INFL, i1))
            self.curve_x2 = 1.0 - i1; self.curve_y2 = 1.0 - s1 * i1
        if self.no_over_check.get_active():
            self.curve_y1 = min(1.0, max(0.0, self.curve_y1))
            self.curve_y2 = min(1.0, max(0.0, self.curve_y2))

    def fit_speed_view(self):
        pts = speed_curve(self.curve_x1, self.curve_y1, self.curve_x2, self.curve_y2, 80)
        ss = [s for _, s in pts]
        s0, _, s1, _ = self.speed_handles()
        ss += [min(max(s0, -8.0), 15.0), min(max(s1, -8.0), 15.0)]
        top = min(15.0, max(ss + [1.0]) * 1.15)
        low = max(-8.0, min(ss + [0.0]) * 1.15)
        if top - low < 1.5: top = low + 1.5
        span = top - low
        self.s_ymin = (low if low < 0 else 0.0) - 0.08 * span
        self.s_ymax = top

    def on_fit_clicked(self, button):
        self.fit_speed_view(); self.update_speed_info(); self.speed_graph.queue_draw()

    def update_speed_info(self):
        if not hasattr(self, "speed_info"): return
        c = (self.curve_x1, self.curve_y1, self.curve_x2, self.curve_y2)
        if self.is_animating:
            t = self.anim_progress
            txt = f"t {t:.2f}  ·  speed {speed_at_time(t, *c):.2f}×  ·  value {self.anim_eased_value:.2f}"
        else:
            pk_t, pk = max(speed_curve(*c, n=60), key=lambda p: p[1])
            lo, hi = curve_extent(*c)
            over = max(hi - 1.0, -lo, 0.0)
            pk_txt = f"{pk:.2f}×" if pk < 100 else ">100×"
            ov_txt = "no overshoot" if over < 0.005 else f"overshoot {over * 100:.0f}%"
            txt = f"peak {pk_txt} @ t {pk_t:.2f}  ·  {ov_txt}"
        self.speed_info.set_text(txt)

    def s_rect(self, w, h):
        return self.s_ml, self.s_mt, w - self.s_mr, h - self.s_mb

    def s_to_px(self, t, s, w, h):
        L, T, R, B = self.s_rect(w, h)
        return L + t * (R - L), B - (s - self.s_ymin) / (self.s_ymax - self.s_ymin) * (B - T)

    def s_from_px(self, px, py, w, h):
        L, T, R, B = self.s_rect(w, h)
        return (px - L) / (R - L), self.s_ymin + (B - py) / (B - T) * (self.s_ymax - self.s_ymin)

    def _handle_px(self, w, h):
        L, T, R, B = self.s_rect(w, h)
        s0, i0, s1, i1 = self.speed_handles()
        _, oy = self.s_to_px(0, s0, w, h); _, iy = self.s_to_px(1, s1, w, h)
        oy = min(max(oy, T + 1), B - 1); iy = min(max(iy, T + 1), B - 1)
        ox = L + i0 * (R - L); ix = L + (1.0 - i1) * (R - L)
        return (L, oy, ox), (R, iy, ix)

    def on_draw_speed(self, widget, cr):
        w = widget.get_allocated_width(); h = widget.get_allocated_height()
        L, T, R, B = self.s_rect(w, h)
        if R - L < 10 or B - T < 10: return
        c = (self.curve_x1, self.curve_y1, self.curve_x2, self.curve_y2)
        X = lambda t: L + t * (R - L)
        Y = lambda s: B - (s - self.s_ymin) / (self.s_ymax - self.s_ymin) * (B - T)
        cr.select_font_face("sans-serif", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
        cr.set_font_size(9)

        step = nice_step(self.s_ymax - self.s_ymin)
        n0 = math.ceil(self.s_ymin / step); n1 = math.floor(self.s_ymax / step)
        for n in range(n0, min(n1, n0 + 14) + 1):
            v = n * step; y = Y(v)
            cr.set_line_width(1)
            cr.set_source_rgba(0.3, 0.35, 0.5, 1.0) if n == 0 else cr.set_source_rgba(0.16, 0.18, 0.25, 1.0)
            cr.move_to(L, y); cr.line_to(R, y); cr.stroke()
            txt = fmt_num(v)
            cr.set_source_rgba(0.34, 0.37, 0.54, 1.0)
            cr.move_to(L - 6 - cr.text_extents(txt).width, y + 3); cr.show_text(txt)
        cr.set_line_width(1); cr.set_source_rgba(0.16, 0.18, 0.25, 1.0)
        for i in range(1, 4):
            cr.move_to(X(i / 4.0), T); cr.line_to(X(i / 4.0), B)
        cr.stroke()
        cr.set_source_rgba(0.25, 0.28, 0.4, 1.0); cr.set_line_width(1.5)
        cr.rectangle(L, T, R - L, B - T); cr.stroke()
        if self.s_ymin <= 1.0 <= self.s_ymax:
            cr.set_source_rgba(0.62, 0.81, 0.42, 0.7); cr.set_line_width(1); cr.set_dash([4, 4])
            cr.move_to(L, Y(1.0)); cr.line_to(R, Y(1.0)); cr.stroke(); cr.set_dash([])
            cr.set_font_size(8)
            cr.move_to(R - 4 - cr.text_extents("avg").width, Y(1.0) - 3); cr.show_text("avg")
            cr.set_font_size(9)

        pts = speed_curve(*c, n=96)
        playing = self.is_animating or self.anim_progress > 0
        cr.save()
        cr.rectangle(L, T, R - L, B - T); cr.clip()
        y0 = min(max(Y(0.0), T), B)
        cr.move_to(X(pts[0][0]), y0)
        for t, s in pts: cr.line_to(X(t), Y(s))
        cr.line_to(X(pts[-1][0]), y0); cr.close_path()
        cr.set_source_rgba(0.48, 0.64, 0.97, 0.13); cr.fill()
        if playing:
            prog = self.anim_progress
            part = [p for p in pts if p[0] <= prog] + [(prog, speed_at_time(prog, *c))]
            cr.move_to(X(0.0), y0)
            for t, s in part: cr.line_to(X(t), Y(s))
            cr.line_to(X(prog), y0); cr.close_path()
            cr.set_source_rgba(1.0, 0.4, 0.4, 0.18); cr.fill()
        cr.set_source_rgba(0.48, 0.64, 0.97, 1.0); cr.set_line_width(3)
        cr.set_line_join(cairo.LINE_JOIN_ROUND)
        cr.move_to(X(pts[0][0]), Y(pts[0][1]))
        for t, s in pts[1:]: cr.line_to(X(t), Y(s))
        cr.stroke()
        cr.restore()

        blue = (0.48, 0.64, 0.97, 1.0); orange = (1.0, 0.62, 0.39, 1.0)
        (kx0, oy, ox), (kx1, iy, ix) = self._handle_px(w, h)
        cr.set_source_rgba(0.34, 0.37, 0.54, 1.0); cr.set_line_width(1.5); cr.set_dash([4, 4])
        cr.move_to(kx0, oy); cr.line_to(ox, oy); cr.move_to(kx1, iy); cr.line_to(ix, iy); cr.stroke()
        cr.set_dash([])
        for kx, ky, col in ((kx0, oy, blue), (kx1, iy, orange)):
            cr.set_source_rgba(*col); cr.rectangle(kx - 4, ky - 4, 8, 8); cr.fill()
        for hx, hy, col in ((ox, oy, blue), (ix, iy, orange)):
            cr.set_line_width(3); cr.set_source_rgba(0.1, 0.1, 0.12, 1.0)
            cr.arc(hx, hy, 7, 0, 2 * math.pi); cr.fill_preserve()
            cr.set_source_rgba(*col); cr.stroke()

        if playing:
            prog = self.anim_progress
            px = X(prog); py = min(max(Y(speed_at_time(prog, *c)), T), B)
            cr.set_source_rgba(1.0, 0.4, 0.4, 0.5); cr.set_line_width(2)
            cr.move_to(px, B); cr.line_to(px, T); cr.stroke()
            cr.set_source_rgba(1.0, 0.4, 0.4, 1.0); cr.arc(px, py, 5, 0, 2 * math.pi); cr.fill()

    def on_draw_speed_preview(self, widget, cr):
        width = widget.get_allocated_width(); height = widget.get_allocated_height()
        track_y = height / 2.0
        cr.set_source_rgba(0.25, 0.28, 0.4, 1.0); cr.set_line_width(2)
        cr.move_to(10, track_y); cr.line_to(width - 10, track_y); cr.stroke()
        if self.is_animating or self.anim_progress > 0:
            cx = 10 + self.anim_eased_value * (width - 20)
            sp = speed_at_time(self.anim_progress, self.curve_x1, self.curve_y1, self.curve_x2, self.curve_y2)
            trail = max(-30.0, min(70.0, sp * 10.0))
            tx = min(max(cx - trail, 2), width - 2)
            cr.set_source_rgba(0.48, 0.64, 0.97, 0.35); cr.set_line_width(6); cr.set_line_cap(cairo.LINE_CAP_ROUND)
            cr.move_to(tx, track_y); cr.line_to(cx, track_y); cr.stroke()
            cr.set_source_rgba(0.48, 0.64, 0.97, 1.0)
            cr.rectangle(cx - 5, track_y - 5, 10, 10); cr.fill()

    def on_s_press(self, widget, event):
        w = widget.get_allocated_width(); h = widget.get_allocated_height()
        (kx0, oy, ox), (kx1, iy, ix) = self._handle_px(w, h)
        d_out = math.hypot(event.x - ox, event.y - oy)
        d_in = math.hypot(event.x - ix, event.y - iy)
        pick = None
        if min(d_out, d_in) < 15:
            pick = "out" if d_out <= d_in else "in"
        else:
            s_out = self.dist_to_segment(event.x, event.y, kx0, oy, ox, oy)
            s_in = self.dist_to_segment(event.x, event.y, kx1, iy, ix, iy)
            if min(s_out, s_in) < 8:
                pick = "out" if s_out <= s_in else "in"
            else:
                L, T, R, B = self.s_rect(w, h)
                if L <= event.x <= R and T <= event.y <= B:
                    self.is_scrubbing = True
                    t, _ = self.s_from_px(event.x, event.y, w, h)
                    self.set_progress(t)
        self.dragging_speed_handle = pick
        return True

    def on_s_motion(self, widget, event):
        if self.is_scrubbing:
            w = widget.get_allocated_width(); h = widget.get_allocated_height()
            t, _ = self.s_from_px(event.x, event.y, w, h)
            self.set_progress(t)
            return True
        side = self.dragging_speed_handle
        if not side: return False
        w = widget.get_allocated_width(); h = widget.get_allocated_height()
        
        # Lock handles to graph boundaries
        if self.lock_bounds_check.get_active():
            L, T, R, B = self.s_rect(w, h)
            ex = min(max(event.x, L), R)
            ey = min(max(event.y, T), B)
            t, s = self.s_from_px(ex, ey, w, h)
        else:
            t, s = self.s_from_px(event.x, event.y, w, h)

        shift = bool(event.state & Gdk.ModifierType.SHIFT_MASK)
        ctrl = bool(event.state & Gdk.ModifierType.CONTROL_MASK)
        infl = t if side == "out" else 1.0 - t
        infl = min(1.0, max(MIN_INFL, infl))
        if shift: s = 0.0
        if self.s_snap_check.get_active():
            s = round(s * 10) / 10.0
            infl = min(1.0, max(MIN_INFL, round(infl * 20) / 20.0))
        
        pair = (s, infl)
        mirror = ctrl or self.mirror_check.get_active()
        if side == "out":
            self.set_curve_from_speed(out=pair, inn=pair if mirror else None)
        else:
            self.set_curve_from_speed(inn=pair, out=pair if mirror else None)
        self.update_entries(); self.update_css_entry()
        self._unselect_presets()
        self._on_curve_changed(fit=False)
        return True

    def on_s_release(self, widget, event):
        self.dragging_speed_handle = None
        self.is_scrubbing = False
        self.fit_speed_view(); self.update_speed_info(); self._queue_all()
        return True

    def on_s_scroll(self, widget, event):
        w = widget.get_allocated_width(); h = widget.get_allocated_height()
        if event.direction == Gdk.ScrollDirection.UP: f = 1.1
        elif event.direction == Gdk.ScrollDirection.DOWN: f = 1 / 1.1
        elif event.direction == Gdk.ScrollDirection.SMOOTH:
            ok, _dx, dy = event.get_scroll_deltas()
            f = 1.1 if dy < 0 else 1 / 1.1
        else:
            return False
        _, sm = self.s_from_px(event.x, event.y, w, h)
        lo = sm - (sm - self.s_ymin) / f; hi = sm + (self.s_ymax - sm) / f
        if 0.2 <= hi - lo <= 400:
            self.s_ymin, self.s_ymax = lo, hi
        widget.queue_draw()
        return True

    def on_s_entry_focus_out(self, entry, event, key):
        self.on_s_entry_changed(entry, key)
        return False

    def on_s_entry_changed(self, entry, key):
        if self.is_updating_entries: return
        try:
            val = float(entry.get_text())
        except ValueError:
            self.update_entries(); return
        s0, i0, s1, i1 = self.speed_handles()
        shown = {"os": s0, "oi": i0 * 100.0, "is": s1, "ii": i1 * 100.0}[key]
        if abs(val - shown) < (0.006 if key in ("os", "is") else 0.06):
            self.update_entries(); return
        if key == "os": s0 = val
        elif key == "oi": i0 = min(1.0, max(MIN_INFL, val / 100.0))
        elif key == "is": s1 = val
        elif key == "ii": i1 = min(1.0, max(MIN_INFL, val / 100.0))
        mirror = self.mirror_check.get_active()
        if key in ("os", "oi"):
            out = (s0, i0); inn = (s0, i0) if mirror else None
        else:
            inn = (s1, i1); out = (s1, i1) if mirror else None
        before = (self.curve_x1, self.curve_y1, self.curve_x2, self.curve_y2)
        self.set_curve_from_speed(out=out, inn=inn)
        self.update_entries(); self.update_css_entry()
        if before != (self.curve_x1, self.curve_y1, self.curve_x2, self.curve_y2):
            self._unselect_presets()
            self._on_curve_changed()

if __name__ == '__main__':
    win = BakaFlow()
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    Gtk.main()
