#!/usr/bin/env python3
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib
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
        self.set_default_size(425, 385)
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
        tabs = [("Easing", "easing", True), ("Presets", "presets", False), ("Manage", "manage", False), ("Import/Export", "import", False)]
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

        # ANIMATION PREVIEW & DURATION
        preview_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=3)

        self.preview_area = Gtk.DrawingArea()
        self.preview_area.get_style_context().add_class("preview-bg")
        self.preview_area.set_size_request(-1, 18)
        self.preview_area.connect("draw", self.on_draw_preview)
        preview_box.pack_start(self.preview_area, True, True, 0)

        duration_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
        duration_lbl = Gtk.Label(label="Sec:")
        duration_lbl.get_style_context().add_class("status-text")
        self.duration_spin = Gtk.SpinButton.new_with_range(0.5, 10.0, 0.5)
        self.duration_spin.set_value(1.0)
        self.duration_spin.set_width_chars(2)
        duration_box.pack_start(duration_lbl, False, False, 0)
        duration_box.pack_start(self.duration_spin, False, False, 0)
        preview_box.pack_start(duration_box, False, False, 0)

        play_btn = Gtk.Button(label="▶")
        play_btn.get_style_context().add_class("btn-secondary")
        play_btn.connect("clicked", self.on_play_preview)
        preview_box.pack_start(play_btn, False, False, 0)

        left_box.pack_start(preview_box, False, False, 0)

        # INPUTS
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

        # AXIS CHECKBOXES
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

        # RIGHT SIDE
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

        btn_apply = Gtk.Button(label="APPLY EASING")
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

    def on_play_preview(self, button):
        if self.anim_source_id:
            GLib.source_remove(self.anim_source_id)
        self.anim_progress = 0.0
        self.anim_eased_value = 0.0
        self.is_animating = True
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
            self.preview_area.queue_draw()
            self.graph_area.queue_draw()
            return False

        self.anim_eased_value = self.solve_bezier(self.anim_progress)
        self.preview_area.queue_draw()
        self.graph_area.queue_draw()
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

        cr.set_source_rgba(0.34, 0.37, 0.54, 1.0); cr.set_line_width(2); cr.set_dash([5, 5])
        cr.move_to(x0, y0); cr.line_to(cx1, cy1); cr.move_to(x1, y1); cr.line_to(cx2, cy2); cr.stroke()
        cr.set_dash([])

        cr.set_source_rgba(0.48, 0.64, 0.97, 1.0); cr.set_line_width(4)
        cr.move_to(x0, y0); cr.curve_to(cx1, cy1, cx2, cy2, x1, y1); cr.stroke()
        cr.arc(x0, y0, 5, 0, 2 * math.pi); cr.fill(); cr.arc(x1, y1, 5, 0, 2 * math.pi); cr.fill()

        cr.set_line_width(3); cr.set_source_rgba(0.1, 0.1, 0.12, 1.0)
        cr.arc(cx1, cy1, 7, 0, 2 * math.pi); cr.fill_preserve(); cr.set_source_rgba(0.48, 0.64, 0.97, 1.0); cr.stroke()
        cr.set_source_rgba(0.1, 0.1, 0.12, 1.0); cr.arc(cx2, cy2, 7, 0, 2 * math.pi); cr.fill_preserve(); cr.set_source_rgba(0.48, 0.64, 0.97, 1.0); cr.stroke()

        if self.is_animating or self.anim_progress > 0:
            px, py = self.math_to_cairo(self.anim_progress, self.anim_eased_value, width, height)
            cr.set_source_rgba(1.0, 0.4, 0.4, 0.5); cr.set_line_width(2)
            cr.move_to(px, py); cr.line_to(px, y0); cr.stroke()
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

        for (layer_id, prop_path), selected_times in targets.items():
            tail = prop_path[-1] if prop_path else ""
            is_already_separated = tail in ("X", "Y", "Z")
            paths_to_ease = []

            if not is_already_separated:
                base_res = self.send_ec_command("prop.get", {"layer": layer_id, "path": prop_path})
                if base_res.get("ok"):
                    prop_type = base_res["result"].get("type", "scalar")
                    all_keys = base_res["result"].get("keys", [])

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

                    if i > 0:
                        k_prev = all_keys[i-1]
                        D = k["time"] - k_prev["time"]
                        if D > 0.001:
                            in_influence = max(0.1, (1.0 - self.curve_x2) * 100.0)

                            if isinstance(k["value"], list):
                                num_dims = len(k["value"])
                                in_speeds = [0.0] * num_dims
                                has_movement = False
                                for dim in range(min(num_dims, 3)):
                                    if dim in checked_axes:
                                        delta_v = k["value"][dim] - k_prev["value"][dim]
                                        if abs(delta_v) > 0.001:
                                            in_speeds[dim] = ((1.0 - self.curve_y2) * delta_v) / (D * (in_influence / 100.0))
                                            has_movement = True
                                if has_movement:
                                    payload["inSpeed"] = in_speeds
                                    payload["inInfluence"] = in_influence
                            else:
                                delta_v = k["value"] - k_prev["value"]
                                if abs(delta_v) > 0.001:
                                    in_speed = ((1.0 - self.curve_y2) * delta_v) / (D * (in_influence / 100.0))
                                    payload["inSpeed"] = in_speed
                                    payload["inInfluence"] = in_influence

                    if i < len(all_keys) - 1:
                        k_next = all_keys[i+1]
                        D = k_next["time"] - k["time"]
                        if D > 0.001:
                            out_influence = max(0.1, self.curve_x1 * 100.0)

                            if isinstance(k["value"], list):
                                num_dims = len(k["value"])
                                out_speeds = [0.0] * num_dims
                                has_movement = False
                                for dim in range(min(num_dims, 3)):
                                    if dim in checked_axes:
                                        delta_v = k_next["value"][dim] - k["value"][dim]
                                        if abs(delta_v) > 0.001:
                                            out_speeds[dim] = (self.curve_y1 * delta_v) / (D * (out_influence / 100.0))
                                            has_movement = True
                                if has_movement:
                                    payload["outSpeed"] = out_speeds
                                    payload["outInfluence"] = out_influence
                            else:
                                delta_v = k_next["value"] - k["value"]
                                if abs(delta_v) > 0.001:
                                    out_speed = (self.curve_y1 * delta_v) / (D * (out_influence / 100.0))
                                    payload["outSpeed"] = out_speed
                                    payload["outInfluence"] = out_influence

                    if payload:
                        is_sep = target_path and target_path[-1] in ("X", "Y", "Z")
                        if isinstance(k["value"], list) and not is_sep:
                            num_dims = len(k["value"])
                            for d in checked_axes:
                                if d >= num_dims:
                                    continue
                                speed_in = payload.get("inSpeed", 0.0)
                                if isinstance(speed_in, list): speed_in = speed_in[d]
                                speed_out = payload.get("outSpeed", 0.0)
                                if isinstance(speed_out, list): speed_out = speed_out[d]
                                self.send_ec_command("keys.setEase", {
                                    "layer": layer_id, "path": target_path,
                                    "time": k["time"], "side": "in", "dim": d,
                                    "speed": speed_in,
                                    "influence": payload.get("inInfluence", 33.3)
                                })
                                self.send_ec_command("keys.setEase", {
                                    "layer": layer_id, "path": target_path,
                                    "time": k["time"], "side": "out", "dim": d,
                                    "speed": speed_out,
                                    "influence": payload.get("outInfluence", 33.3)
                                })
                        else:
                            self.send_ec_command("keys.setEase", {
                                "layer": layer_id, "path": target_path,
                                "time": k["time"], "side": "in", "dim": 0,
                                "speed": payload.get("inSpeed", 0.0),
                                "influence": payload.get("inInfluence", 33.3)
                            })
                            self.send_ec_command("keys.setEase", {
                                "layer": layer_id, "path": target_path,
                                "time": k["time"], "side": "out", "dim": 0,
                                "speed": payload.get("outSpeed", 0.0),
                                "influence": payload.get("outInfluence", 33.3)
                            })
                        applied_count += 1

        if original_selection:
            self.send_ec_command("keys.select", {"keys": original_selection})

        if applied_count > 0:
            self.show_success_temp(f"✅ Success! Applied to {applied_count} keyframe(s).")
        else:
            self.show_success_temp(f"❌ Error: {last_error}")

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
            self.update_entries(); self.update_css_entry(); self.graph_area.queue_draw()
            self.stack.set_visible_child_name("easing"); self.on_tab_clicked(None, "easing")

    def on_tab_clicked(self, button, page_name):
        self.stack.set_visible_child_name(page_name)
        for name, btn in self.tab_buttons.items():
            if name == page_name: btn.get_style_context().add_class("active")
            else: btn.get_style_context().remove_class("active")

    def get_css_string(self):
        return f"cubic-bezier({self.curve_x1:.2f}, {self.curve_y1:.2f}, {self.curve_x2:.2f}, {self.curve_y2:.2f})"

    def update_css_entry(self):
        self.css_entry.set_text(self.get_css_string())

    def on_reset_clicked(self, button):
        self.curve_x1, self.curve_y1 = self.default_x1, self.default_y1
        self.curve_x2, self.curve_y2 = self.default_x2, self.default_y2
        self.preset_listbox.unselect_all(); self.saved_listbox.unselect_all()
        self.update_entries(); self.update_css_entry(); self.graph_area.queue_draw()

    def on_css_clicked(self, widget, event):
        self.css_entry.select_region(0, -1)
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
        return True

    def on_motion_notify(self, widget, event):
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
        self.preset_listbox.unselect_all(); self.saved_listbox.unselect_all()
        widget.queue_draw(); self.preview_area.queue_draw()
        return True

    def on_button_release(self, widget, event):
        self.dragging_handle = None; return True

    def update_entries(self):
        self.is_updating_entries = True
        self.entries["x1"].set_text(f"{self.curve_x1:.2f}"); self.entries["y1"].set_text(f"{self.curve_y1:.2f}")
        self.entries["x2"].set_text(f"{self.curve_x2:.2f}"); self.entries["y2"].set_text(f"{self.curve_y2:.2f}")
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
            self.preset_listbox.unselect_all(); self.saved_listbox.unselect_all()
            self.graph_area.queue_draw(); self.preview_area.queue_draw()
        except ValueError:
            self.update_entries()

    def on_preset_selected(self, listbox, row):
        if row is None: return
        preset_name = getattr(row, 'preset_name', None)
        if not preset_name: return
        if preset_name in BUILTIN_PRESETS:
            x1, y1, x2, y2 = BUILTIN_PRESETS[preset_name]
            self.curve_x1, self.curve_y1 = x1, y1; self.curve_x2, self.curve_y2 = x2, y2
            self.update_entries(); self.update_css_entry()
            self.graph_area.queue_draw(); self.preview_area.queue_draw()

    def on_search_changed(self, entry):
        search_text = entry.get_text().lower()
        def filter_func(row):
            if row is None: return False
            name = getattr(row, 'preset_name', "")
            return search_text in name.lower()
        self.preset_listbox.set_filter_func(filter_func)

if __name__ == '__main__':
    win = BakaFlow()
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    Gtk.main()
