import os
from tkinter import filedialog, messagebox
from PIL import Image
from core.app_state import AppState
from exr_loader import EXRLoader
from image_processor import ImageProcessor
from constants import STANDARD_CHANNELS, Channels

class MainController:
    def __init__(self, ui_root):
        self.state = AppState()
        self.ui = ui_root
        
        # Loader initialization
        self.loader = EXRLoader(
            on_success=lambda *args: self.ui.after(0, self._on_load_success, *args),
            on_error=lambda err: self.ui.after(0, self._on_load_error, err),
            on_cancelled=lambda: self.ui.after(0, self._on_load_cancelled),
            on_progress=self.log
        )

    def log(self, text, clear=False):
        # Delegate to UI's bottom panel log
        if hasattr(self.ui, 'bottom_panel'):
            self.ui.bottom_panel.log(text, clear)
        else:
            print(f"LOG: {text}")

    def on_open_click(self):
        if self.state.is_loading: return
        path = filedialog.askopenfilename(initialdir=self.state.default_dir, filetypes=[("OpenEXR Files", "*.exr")])
        if path:
            self.state.is_loading = True
            self.ui.image_area.show_loading("LOADING EXR...")
            self.ui.sidebar.open_button.configure(state="disabled", text="PLEASE WAIT...")
            self.loader.load(path)

    def on_cancel(self):
        if self.state.is_loading:
            self.loader.cancel()
            self.log("Cancellation request sent...")

    def _on_load_success(self, path, w, h, channels_data, available_channels, precomputed_images):
        self.state.image_size = (w, h)
        self.state.current_exr_data = channels_data
        self.state.available_channels = available_channels
        self.state.view_cache = precomputed_images

        self.log(f"File: {os.path.basename(path)}", clear=True)
        self.log(f"Resolution: {w}x{h}")
        self.log(f"Channels found: {', '.join(sorted(available_channels))}")

        self._update_composite_buttons_state()
        self.ui.nav_sidebar.update_channel_buttons(available_channels, STANDARD_CHANNELS)

        self._hide_loading()
        
        # Update UI visibility
        self.ui.set_ui_visibility(True)
        
        # We need to trigger an initial mode update
        default_mode = "Composite (RGB)"
        if self.ui.nav_sidebar.composite_buttons[default_mode].cget("state") == "disabled":
            if self.state.available_channels:
                default_mode = sorted(self.state.available_channels)[0]
            else:
                default_mode = None
        
        if default_mode:
            self.safe_update_view_mode(default_mode)

    def _update_composite_buttons_state(self):
        btns = self.ui.nav_sidebar.composite_buttons
        av = self.state.available_channels
        
        has_rgb = all(c in av for c in [Channels.ALBEDO_R, Channels.ALBEDO_G, Channels.ALBEDO_B])
        btns["Composite (RGB)"].configure(state="normal" if has_rgb else "disabled")
        
        has_normals = all(c in av for c in [Channels.NORMAL_X, Channels.NORMAL_Y, Channels.NORMAL_Z])
        btns["Normal Map"].configure(state="normal" if has_normals else "disabled")
        
        has_hud_rgba = all(c in av for c in [Channels.HUD_R, Channels.HUD_G, Channels.HUD_B, Channels.HUD_A])
        btns["HUD (RGBA)"].configure(state="normal" if has_hud_rgba else "disabled")

        metadata_channels = [
            Channels.METADATA_WORLDPOS_X, Channels.METADATA_WORLDPOS_Y, Channels.METADATA_WORLDPOS_Z,
            Channels.METADATA_TEXTURE_HASH, Channels.METADATA_POLY_COUNT
        ]
        has_metadata = any(c in av for c in metadata_channels)
        btns["Metadata"].configure(state="normal" if has_metadata else "disabled")

    def _on_load_error(self, error_msg):
        self._hide_loading()
        self.log(f"ERROR: {error_msg}")
        messagebox.showerror("Critical Error", f"Loading failed:\n{error_msg}")
        self.ui.set_ui_visibility(False)

    def _on_load_cancelled(self):
        self._hide_loading()
        self.log("Loading cancelled.")
        self.ui.set_ui_visibility(False)

    def _hide_loading(self):
        self.state.is_loading = False
        self.ui.image_area.hide_loading()
        self.ui.sidebar.open_button.configure(state="normal", text="OPEN EXR")

    def safe_update_view_mode(self, mode):
        if not self.state.current_exr_data or self.state.is_loading: return
        
        if mode in self.state.view_cache:
            self._update_view_mode(mode)
            return

        self.state.is_loading = True
        self.ui.image_area.show_loading(f"CALCULATING: {mode}")
        self.ui.after(10, lambda: self._process_view_mode(mode))

    def _process_view_mode(self, mode):
        try:
            self._update_view_mode(mode)
        finally:
            self._hide_loading()

    def _update_view_mode(self, mode):
        self.state.current_view_mode = mode
        
        if mode not in self.state.view_cache:
            self.state.view_cache[mode] = ImageProcessor.process_view_mode(mode, self.state.image_size, self.state.current_exr_data)
        
        self.state.last_numpy_image = self.state.view_cache[mode]
        self.refresh_image_display()

    def refresh_image_display(self):
        if self.state.last_numpy_image is None:
            return

        cont_w, cont_h = self.ui.image_area.winfo_width(), self.ui.image_area.winfo_height()
        if cont_w < 50 or cont_h < 50: return

        from PIL import ImageOps
        from hud_compositor import HudCompositor
        
        raw_pil = Image.fromarray(self.state.last_numpy_image)
        self.state.full_pil_image = ImageOps.expand(raw_pil, border=HudCompositor.PADDING, fill=(10, 10, 10))
        display_pil = self.state.full_pil_image.copy()
        
        # Apply overlays based on active tab
        active_tab = self.ui.nav_sidebar.tabview.get()
        if active_tab == "HUD Compositor":
            from hud_compositor import HudCompositor
            display_pil = HudCompositor.draw_overlay(
                self.state.full_pil_image, 
                self.state.hud_rects, 
                self.state.selected_rect_idx, 
                self.state.hud_workspace
            )
        
        # HUD overlays will be delegated to HUD controller in the future, 
        # but for now we'll do the PIL scaling here
        
        img_w, img_h = display_pil.size
        ratio = min(cont_w / img_w, cont_h / img_h)
        self.state.display_size = (int(img_w * ratio), int(img_h * ratio))

        if self.state.display_size[0] > 0 and self.state.display_size[1] > 0:
            scaling = self.ui._get_window_scaling()
            target_w = int(self.state.display_size[0] * scaling)
            target_h = int(self.state.display_size[1] * scaling)
            
            if display_pil.width > target_w or display_pil.height > target_h:
                display_pil = display_pil.resize((target_w, target_h), Image.Resampling.LANCZOS)
            
            import customtkinter as ctk
            ctk_img = ctk.CTkImage(light_image=display_pil, dark_image=display_pil, size=self.state.display_size)
            self.ui.image_area.display_label.configure(image=ctk_img, text="")
            self.ui.image_area.display_label.image = ctk_img
        else:
            self.ui.image_area.display_label.configure(image=None, text="Image too small to display")
            self.ui.image_area.display_label.image = None
