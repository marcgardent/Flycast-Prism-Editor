import json
import customtkinter as ctk
from PIL import Image, ImageOps, ImageDraw
from image_processor import ImageProcessor

class InteractionController:
    def __init__(self, main_controller):
        self.mc = main_controller

    def on_mouse_down(self, event):
        # Delegate based on active tab
        active_tab = self.mc.ui.nav_sidebar.tabview.get()
        if active_tab == "HUD Compositor":
            self.mc.hud_ctrl.on_mouse_down(event)
        else:
            self.on_image_click(event)

    def on_mouse_move(self, event):
        active_tab = self.mc.ui.nav_sidebar.tabview.get()
        if active_tab == "HUD Compositor":
            self.mc.hud_ctrl.on_mouse_move(event)
        self.update_magnifier(event)

    def on_mouse_up(self, event):
        active_tab = self.mc.ui.nav_sidebar.tabview.get()
        if active_tab == "HUD Compositor":
            self.mc.hud_ctrl.on_mouse_up(event)

    def on_mouse_leave(self, event):
        self.hide_magnifier()

    def _get_orig_coords(self, mx, my):
        st = self.mc.state
        if st.display_size[0] == 0 or st.display_size[1] == 0: return 0, 0
        dw, dh = st.display_size
        
        orig_w, orig_h = st.image_size
        
        from hud_compositor import HudCompositor
        p = HudCompositor.PADDING
        padded_w, padded_h = orig_w + 2*p, orig_h + 2*p
        
        px = int(mx * padded_w / dw)
        py = int(my * padded_h / dh)
        return px - p, py - p

    def on_image_click(self, event):
        if self.mc.state.current_pixel_value:
            # Update inspector
            self.mc.ui.sidebar.update_inspect_table(self.mc.state.current_pixel_value)
            
            # Summary for log
            summary = " | ".join([f"{k}:{v}" for k, v in self.mc.state.current_pixel_value.items()])
            self.mc.log(f"Inspected: {summary}")
            
            # Update Poly Routing JSON
            self.mc.state.last_clicked_event = event
            self.update_poly_routing_json()

    def update_poly_routing_json(self):
        st = self.mc.state
        evt = st.last_clicked_event
        if evt is None or st.full_pil_image is None or not st.current_exr_data:
            return

        orig_x, orig_y = self._get_orig_coords(evt.x, evt.y)
        orig_w, orig_h = st.image_size

        if not (0 <= orig_x < orig_w and 0 <= orig_y < orig_h):
            return

        metadata = ImageProcessor.get_pixel_metadata(orig_x, orig_y, st.current_exr_data)
        if metadata:
            poly_data = {
                "name": self.mc.ui.nav_sidebar.poly_name_entry.get(),
                "match": metadata,
                "actions": []
            }
            json_str = json.dumps(poly_data, indent=2)
            
            self.mc.ui.nav_sidebar.poly_json_box.delete("0.0", "end")
            self.mc.ui.nav_sidebar.poly_json_box.insert("0.0", json_str)

    def update_magnifier(self, event):
        st = self.mc.state

        # Update cursor for HUD if applicable
        if self.mc.ui.nav_sidebar.tabview.get() == "HUD Compositor":
            ox, oy = self._get_orig_coords(event.x, event.y)
            mode = st.hud_workspace
            hover_rect = False
            for r in st.hud_rects:
                rx = r["sx"] if mode == "SOURCE" else r["dx"]
                ry = r["sy"] if mode == "SOURCE" else r["dy"]
                if rx <= ox <= rx + r["w"] and ry <= oy <= ry + r["h"]:
                    hover_rect = True
                    break
            
            if hover_rect:
                if self.mc.ui.image_area.display_label.cget("cursor") != "hand2":
                    self.mc.ui.image_area.display_label.configure(cursor="hand2")
            else:
                if self.mc.ui.image_area.display_label.cget("cursor") != "":
                    self.mc.ui.image_area.display_label.configure(cursor="")

        if st.full_pil_image is None or st.is_loading:
            self.hide_magnifier()
            return

        orig_w, orig_h = st.image_size
        orig_x, orig_y = self._get_orig_coords(event.x, event.y)

        if 0 <= orig_x < orig_w and 0 <= orig_y < orig_h:
            st.current_pixel_value = ImageProcessor.get_pixel_raw_values(orig_x, orig_y, st.current_exr_data)
        else:
            st.current_pixel_value = {}

        self.mc.ui.sidebar.update_info_table(st.current_pixel_value)

        m_half = st.magnifier_size // 2
        left, top = max(0, orig_x - m_half), max(0, orig_y - m_half)
        right, bottom = min(orig_w, orig_x + m_half), min(orig_h, orig_y + m_half)

        try:
            crop = st.full_pil_image.crop((left, top, right, bottom))
            zoomed = Image.new("RGB", (st.magnifier_size, st.magnifier_size), (0, 0, 0))
            zoomed.paste(crop, (max(0, m_half - orig_x), max(0, m_half - orig_y)))

            draw = ImageDraw.Draw(zoomed)
            mid, length = st.magnifier_size // 2, 12
            for color, width in [("black", 3), ("white", 1)]:
                draw.line([(mid - length, mid), (mid + length, mid)], fill=color, width=width)
                draw.line([(mid, mid - length), (mid, mid + length)], fill=color, width=width)

            zoomed = ImageOps.expand(zoomed, border=2, fill='#3498db')
            zoom_ctk = ctk.CTkImage(light_image=zoomed, dark_image=zoomed, size=(st.magnifier_size + 4, st.magnifier_size + 4))

            self.mc.ui.sidebar.magnifier_label.configure(image=zoom_ctk)
            self.mc.ui.sidebar.magnifier_label.image = zoom_ctk # Keep reference
        except Exception:
            self.hide_magnifier()

    def hide_magnifier(self):
        if self.mc.ui.image_area.display_label.cget("cursor") != "":
            self.mc.ui.image_area.display_label.configure(cursor="")
        self.mc.ui.sidebar.magnifier_label.configure(image=None)
        self.mc.state.current_pixel_value = {}
        self.mc.ui.sidebar.update_info_table({})
