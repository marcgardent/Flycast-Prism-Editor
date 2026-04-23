import json
import customtkinter as ctk
from PIL import Image, ImageOps, ImageDraw
import numpy as np
import threading
import cexprtk
from image_processor import ImageProcessor
from constants import Channels

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

    def evaluate_expression(self, expr_string):
        st = self.mc.state
        if st.full_pil_image is None or not st.current_exr_data:
            self.mc.log("No EXR data available for evaluation.")
            return

        self.mc.log(f"Evaluating: {expr_string}...")
        self.mc.ui.image_area.show_loading("EVALUATING...")
        
        # Start background thread to avoid freezing UI
        thread = threading.Thread(target=self._eval_thread, args=(expr_string,))
        thread.daemon = True
        thread.start()

    def _eval_thread(self, expr_string):
        st = self.mc.state
        exr_data = st.current_exr_data
        w, h = st.image_size
        
        # Extract channels into 1D flattened arrays to speed up access
        channels_map = {
            'R': Channels.ALBEDO_R, 'G': Channels.ALBEDO_G, 'B': Channels.ALBEDO_B,
            'WP_X': Channels.METADATA_WORLDPOS_X, 'WP_Y': Channels.METADATA_WORLDPOS_Y, 'WP_Z': Channels.METADATA_WORLDPOS_Z,
            'N_X': Channels.NORMAL_X, 'N_Y': Channels.NORMAL_Y, 'N_Z': Channels.NORMAL_Z,
            'Z': Channels.DEPTH_Z,
            'TH': Channels.METADATA_TEXTURE_HASH, 'PC': Channels.METADATA_POLY_COUNT,
            'MID_RAW': Channels.MATERIAL_ID
        }
        
        arrays = {}
        for var_name, ch_name in channels_map.items():
            if ch_name in exr_data:
                arrays[var_name] = exr_data[ch_name].flatten()
            else:
                arrays[var_name] = np.zeros(h * w, dtype=np.float32)

        # Decompose MID into its separate arrays
        mid_raw = arrays.get('MID_RAW', np.zeros(h * w, dtype=np.float32))
        mid_int = mid_raw.astype(np.int32)
        
        list_type_val = (mid_int >> 4) & 0b111
        arrays['MID_OPAQUE'] = (list_type_val == 0).astype(np.float32)
        arrays['MID_OPAQUE_MOD'] = (list_type_val == 1).astype(np.float32)
        arrays['MID_TRANSLUCENT'] = (list_type_val == 2).astype(np.float32)
        arrays['MID_TRANSLUCENT_MOD'] = (list_type_val == 3).astype(np.float32)
        arrays['MID_PUNCH_THROUGH'] = (list_type_val == 4).astype(np.float32)
        
        arrays['MID_HAS_TEX'] = ((mid_int >> 3) & 1).astype(np.float32)
        arrays['MID_GOURAUD'] = ((mid_int >> 2) & 1).astype(np.float32)
        arrays['MID_HAS_BUMP'] = ((mid_int >> 1) & 1).astype(np.float32)
        arrays['MID_FOG'] = (mid_int & 1).astype(np.float32)
        
        # To avoid passing MID_RAW directly if user expects MID, alias it:
        arrays['MID'] = mid_raw

        # Set up cexprtk
        sym_dict = {k: 0.0 for k in arrays.keys()}
        try:
            symbol_table = cexprtk.Symbol_Table(sym_dict, add_constants=True)
            expression = cexprtk.Expression(expr_string, symbol_table)
        except Exception as e:
            self.mc.ui.after(0, self._eval_done, None, f"Parse Error: {e}")
            return

        mask_flat = np.zeros(h * w, dtype=bool)
        
        total_pixels = h * w
        
        try:
            # We must iterate over all pixels. Since we use Python loop, this might be slow.
            # Using st.variables directly to update Symbol_Table is the way.
            # Convert arrays to python lists for slightly faster inner loop access if memory permits,
            # but direct numpy indexing is okay too.
            var_refs = symbol_table.variables
            
            # For optimal speed, pre-fetch variable reference dict keys and arrays
            keys = list(arrays.keys())
            arr_refs = [arrays[k] for k in keys]
            
            for i in range(total_pixels):
                # Update symbol table
                for k, arr in zip(keys, arr_refs):
                    var_refs[k] = float(arr[i])
                    
                val = expression.value()
                if val > 0:
                    mask_flat[i] = True
                    
        except Exception as e:
            self.mc.ui.after(0, self._eval_done, None, f"Eval Error: {e}")
            return

        mask_2d = mask_flat.reshape((h, w))
        self.mc.ui.after(0, self._eval_done, mask_2d, "Evaluation complete.")

    def _eval_done(self, mask, msg):
        st = self.mc.state
        st.is_loading = False
        self.mc.ui.image_area.hide_loading()
        self.mc.log(msg)
        
        if mask is not None:
            st.expression_mask = mask
            self.mc.refresh_image_display()
