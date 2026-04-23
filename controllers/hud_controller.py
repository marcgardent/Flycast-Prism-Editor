import os
import json
import customtkinter as ctk
from tkinter import filedialog, messagebox
from hud_compositor import Anchor
from hud_config import HudConfig

class HUDController:
    def __init__(self, main_controller):
        self.mc = main_controller

    def _get_orig_coords(self, event):
        return self.mc.interaction_ctrl._get_orig_coords(event.x, event.y)

    def _get_safe_zone_bounds(self):
        # We need the safe zone bounds to constrain drag operations.
        # This was part of ImageProcessor or HudCompositor logic in main.py.
        # But we can approximate it or implement it:
        orig_w, orig_h = self.mc.state.image_size
        return 0, 0, orig_w, orig_h # Usually the safe zone is the whole image minus padding.

    def on_mouse_down(self, event):
        st = self.mc.state
        ox, oy = self._get_orig_coords(event)
        st.drag_start_orig = (ox, oy)
        
        mode = st.hud_workspace
        orig_w, orig_h = st.image_size
        
        if mode == "DESTINATION" and st.selected_rect_idx != -1:
            from hud_compositor import HudCompositor
            anchors = HudCompositor.get_anchor_table(orig_w, orig_h)
            for anchor, apos in anchors.items():
                if abs(ox - apos[0]) < 20 and abs(oy - apos[1]) < 20:
                    st.hud_rects[st.selected_rect_idx]["anchor"] = anchor
                    self.mc.refresh_image_display()
                    return
        
        if st.selected_rect_idx != -1 and mode == "SOURCE":
            r = st.hud_rects[st.selected_rect_idx]
            h_size = 15
            
            rx = r["sx"] if mode == "SOURCE" else r["dx"]
            ry = r["sy"] if mode == "SOURCE" else r["dy"]
            rw, rh = r["w"], r["h"]
            
            handles = {
                'nw': (rx, ry),
                'ne': (rx + rw, ry),
                'sw': (rx, ry + rh),
                'se': (rx + rw, ry + rh)
            }
            
            for m, (hx, hy) in handles.items():
                if abs(ox - hx) < h_size and abs(oy - hy) < h_size:
                    st.drag_mode = m
                    st.drag_rect_start = r.copy()
                    return

        for i, r in enumerate(reversed(st.hud_rects)):
            idx = len(st.hud_rects) - 1 - i
            rx = r["sx"] if mode == "SOURCE" else r["dx"]
            ry = r["sy"] if mode == "SOURCE" else r["dy"]
            if rx <= ox <= rx + r["w"] and ry <= oy <= ry + r["h"]:
                self.select_hud_rect(idx)
                st.drag_mode = 'move'
                st.drag_rect_start = r.copy()
                return
        
        sx, sy, sw, sh = self._get_safe_zone_bounds()
        if sx <= ox <= sx + sw and sy <= oy <= sy + sh:
            st.drag_mode = 'create'
            new_rect = {
                "name": f"Rectangle {len(st.hud_rects)+1}", 
                "sx": ox, "sy": oy, 
                "dx": ox, "dy": oy, 
                "w": 0, "h": 0,
                "anchor": Anchor.SCREEN_TOP_LEFT,
                "zen": False
            }
            st.hud_rects.append(new_rect)
            self.select_hud_rect(len(st.hud_rects)-1)
            st.drag_rect_start = new_rect.copy()
        else:
            self.select_hud_rect(-1)

    def on_mouse_move(self, event):
        st = self.mc.state
        if not st.drag_mode or st.selected_rect_idx == -1: return
        
        ox, oy = self._get_orig_coords(event)
        sx, sy, sw, sh = self._get_safe_zone_bounds()
        iw, ih = st.image_size
        
        if st.hud_workspace == "SOURCE" or st.drag_mode != 'move':
            ox = max(sx, min(sx + sw, ox))
            oy = max(sy, min(sy + sh, oy))
        else:
            ox = max(0, min(iw, ox))
            oy = max(0, min(ih, oy))
        
        dx, dy = ox - st.drag_start_orig[0], oy - st.drag_start_orig[1]
        r = st.hud_rects[st.selected_rect_idx]
        s = st.drag_rect_start
        mode = st.hud_workspace
        
        if st.drag_mode == 'move':
            if mode == "SOURCE":
                r["sx"] = max(sx, min(sx + sw - r["w"], s["sx"] + dx))
                r["sy"] = max(sy, min(sy + sh - r["h"], s["sy"] + dy))
            else:
                r["dx"] = max(0, min(iw - r["w"], s["dx"] + dx))
                r["dy"] = max(0, min(ih - r["h"], s["dy"] + dy))
            
        elif st.drag_mode == 'nw':
            start_x = s["sx"] if mode == "SOURCE" else s["dx"]
            start_y = s["sy"] if mode == "SOURCE" else s["dy"]
            new_x = max(sx, min(start_x + s["w"] - 10, start_x + dx))
            new_y = max(sy, min(start_y + s["h"] - 10, start_y + dy))
            if mode == "SOURCE": r["sx"], r["sy"] = new_x, new_y
            else: r["dx"], r["dy"] = new_x, new_y
            r["w"] = start_x + s["w"] - new_x
            r["h"] = start_y + s["h"] - new_y
            
        elif st.drag_mode == 'ne':
            start_x = s["sx"] if mode == "SOURCE" else s["dx"]
            start_y = s["sy"] if mode == "SOURCE" else s["dy"]
            new_y = max(sy, min(start_y + s["h"] - 10, start_y + dy))
            new_w = max(10, min(sx + sw - start_x, s["w"] + dx))
            if mode == "SOURCE": r["sy"] = new_y
            else: r["dy"] = new_y
            r["w"], r["h"] = new_w, start_y + s["h"] - new_y
            
        elif st.drag_mode == 'sw':
            start_x = s["sx"] if mode == "SOURCE" else s["dx"]
            start_y = s["sy"] if mode == "SOURCE" else s["dy"]
            new_x = max(sx, min(start_x + s["w"] - 10, start_x + dx))
            new_h = max(10, min(sy + sh - start_y, s["h"] + dy))
            if mode == "SOURCE": r["sx"] = new_x
            else: r["dx"] = new_x
            r["w"], r["h"] = start_x + s["w"] - new_x, new_h
            
        elif st.drag_mode == 'se':
            start_x = s["sx"] if mode == "SOURCE" else s["dx"]
            start_y = s["sy"] if mode == "SOURCE" else s["dy"]
            r["w"], r["h"] = max(10, min(sx + sw - start_x, s["w"] + dx)), max(10, min(sy + sh - start_y, s["h"] + dy))
            
        elif st.drag_mode == 'create':
            x1, y1 = st.drag_start_orig
            x2, y2 = ox, oy
            r["sx"], r["sy"] = min(x1, x2), min(y1, y2)
            r["dx"], r["dy"] = r["sx"], r["sy"]
            r["w"], r["h"] = abs(x2 - x1), abs(y2 - y1)
            
        if st.drag_mode in ['nw', 'ne', 'sw', 'se', 'create']:
            r["dx"] = max(0, min(iw - r["w"], r["dx"]))
            r["dy"] = max(0, min(ih - r["h"], r["dy"]))
            
        self.mc.refresh_image_display()

    def on_mouse_up(self, event):
        st = self.mc.state
        if st.drag_mode == 'create' and st.selected_rect_idx != -1:
            r = st.hud_rects[st.selected_rect_idx]
            if r["w"] < 5 or r["h"] < 5:
                self.delete_selected_rect()
        
        st.drag_mode = None
        self.mc.ui.nav_sidebar.update_hud_list(st.hud_rects, st.selected_rect_idx)

    def on_workspace_changed(self, mode):
        self.mc.state.hud_workspace = mode
        self.mc.ui.nav_sidebar.hud_name_entry.configure(state="normal")
        if self.mc.state.selected_rect_idx != -1:
            self.mc.ui.nav_sidebar.delete_rect_btn.configure(state="normal")
        else:
            self.mc.ui.nav_sidebar.delete_rect_btn.configure(state="disabled")
        self.mc.refresh_image_display()

    def select_hud_rect(self, idx):
        st = self.mc.state
        ns = self.mc.ui.nav_sidebar
        st.selected_rect_idx = idx
        
        if idx != -1:
            r = st.hud_rects[idx]
            ns.hud_name_var.set(r["name"])
            ns.hud_zen_var.set(r.get("zen", False))
            ns.delete_rect_btn.configure(state="normal")
            ns.hud_zen_checkbox.configure(state="normal")
        else:
            ns.hud_name_var.set("")
            ns.hud_zen_var.set(False)
            ns.delete_rect_btn.configure(state="disabled")
            ns.hud_zen_checkbox.configure(state="disabled")
            
        ns.update_hud_list(st.hud_rects, st.selected_rect_idx)
        self.mc.refresh_image_display()

    def toggle_zen_mode(self):
        st = self.mc.state
        if st.selected_rect_idx != -1:
            st.hud_rects[st.selected_rect_idx]["zen"] = self.mc.ui.nav_sidebar.hud_zen_var.get()
            self.mc.refresh_image_display()

    def rename_selected_rect(self):
        st = self.mc.state
        if st.selected_rect_idx != -1:
            st.hud_rects[st.selected_rect_idx]["name"] = self.mc.ui.nav_sidebar.hud_name_var.get()
            self.mc.ui.nav_sidebar.update_hud_list(st.hud_rects, st.selected_rect_idx)
            self.mc.refresh_image_display()

    def delete_selected_rect(self):
        st = self.mc.state
        if st.selected_rect_idx != -1:
            del st.hud_rects[st.selected_rect_idx]
            if st.hud_rects:
                self.select_hud_rect(0)
            else:
                self.select_hud_rect(-1)
            self.mc.refresh_image_display()

    def export_hud_json(self, to_file=False, path=None):
        st = self.mc.state
        if not st.hud_rects:
            self.mc.log("Aucune zone HUD à exporter.")
            return

        export_data = HudConfig.export(st.hud_rects, st.image_size, path)
        
        if to_file:
            if not path:
                path = filedialog.asksaveasfilename(defaultextension=".json",
                                                     filetypes=[("JSON files", "*.json")],
                                                     title="Save HUD Compositor")
            if path:
                HudConfig.save(export_data, path)
                st.current_hud_path = path
                self.mc.ui.nav_sidebar.hud_path_label.configure(text=os.path.basename(path))
                self.mc.ui.nav_sidebar.save_hud_btn.configure(state="normal")
                self.mc.log(f"HUD Saved to: {os.path.basename(path)}")
        
    def save_hud_json(self):
        if self.mc.state.current_hud_path:
            self.export_hud_json(to_file=True, path=self.mc.state.current_hud_path)
        else:
            self.save_hud_json_as()

    def save_hud_json_as(self):
        self.export_hud_json(to_file=True)

    def load_hud_json(self):
        st = self.mc.state
        if not st.full_pil_image:
            self.mc.log("Please load an EXR image before importing HUD.")
            return

        file_path = filedialog.askopenfilename(filetypes=[("JSON files", "*.json")],
                                               title="Load HUD Compositor")
        if not file_path: return

        try:
            new_hud_rects = HudConfig.load(file_path, st.image_size)
            
            st.hud_rects = new_hud_rects
            st.current_hud_path = file_path
            self.mc.ui.nav_sidebar.hud_path_label.configure(text=os.path.basename(file_path))
            self.mc.ui.nav_sidebar.save_hud_btn.configure(state="normal")
            self.select_hud_rect(-1)
            self.mc.refresh_image_display()
            self.mc.log(f"HUD Loaded: {os.path.basename(file_path)} ({len(new_hud_rects)} zones)")
            
        except Exception as e:
            msg = f"Load Error: {e}"
            self.mc.log(msg)
            messagebox.showerror("Load Error", msg)
