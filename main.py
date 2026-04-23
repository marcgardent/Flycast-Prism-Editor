import sys
try:
    # ENABLE 'PER-MONITOR V2' MODE FOR WINDOWS (BEFORE ANY GRAPHICAL IMPORT)
    if sys.platform.startswith("win"):
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    pass

import os
import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageOps, ImageDraw
import numpy as np
from platformdirs import user_pictures_dir
import json
from constants import STANDARD_CHANNELS, Channels # Import Channels class
from tkinter import filedialog
from exr_loader import EXRLoader
from image_processor import ImageProcessor
from hud_compositor import HudCompositor, Anchor
from hud_config import HudConfig

# FIX KDE PLASMA / LINUX: Prevents widget deformation ("os")
try:
    ctk.DrawEngine.preferred_drawing_method = "circle_shapes"
except AttributeError:
    # Depending on CTK version, this attribute may vary or be internal
    pass

# Global UI Settings for better aesthetics
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class FlycastViewer(ctk.CTk):
    def __init__(self):
        super().__init__()

        # DYNAMIC SCALING DETECTION LOGIC (LINUX/KDE COMPATIBLE)
        try:
            # winfo_fpixels('1i') returns the number of logical pixels per inch
            # 96 is the standard value for 100% scaling (1.0)
            scaling_factor = self.winfo_fpixels('1i') / 96.0
            ctk.set_widget_scaling(scaling_factor)
            ctk.set_window_scaling(scaling_factor)
        except Exception:
            # Fallback to CTK engine automatic scaling
            pass

        # COMPILATION DIAGNOSTIC (CHECK XFT ON LINUX)
        # To check if Tkinter is linked to Xft: root.eval("tk::pkgconfig get fontsystem")
        # If it returns "xft", font rendering will be sharp. Otherwise ("x11"), they will be pixelated.

        self.title("Flycast Prism Editor")
        self.geometry("1500x900")
        self.minsize(1200, 800) # Prevent sidebars from clipping

        # MAXIMIZE WINDOW ON START (with robust delay for Linux/KDE)
        self.after(200, self._maximize_window)

        # Application State
        self.current_exr_data = {}
        self.available_channels = []
        self.image_size = (0, 0)
        self.last_numpy_image = None
        self.view_cache = {}
        self.full_pil_image = None
        self.current_view_mode = "Composite (RGB)"
        self.magnifier_size = 240
        self.display_size = (0, 0)
        self.default_dir = user_pictures_dir()
        self.current_pixel_value = "N/A"
        self.last_clicked_event = None

        # HUD Compositor State
        self.hud_rects = []
        self.selected_rect_idx = -1
        self.drag_mode = None # None, 'move', 'nw', 'ne', 'sw', 'se'
        self.drag_start_orig = None
        self.drag_rect_start = None
        self.hud_workspace = "SOURCE"
        self.current_hud_path = None

        # Logo
        self.logo_image = None
        self.logo_path = os.path.join(os.path.dirname(__file__), "assets", "logo-prism.png")
        self.icon_path = os.path.join(os.path.dirname(__file__), "assets", "logo-prism.ico")
        try:
            pil_logo = Image.open(self.logo_path)
            # Resize for sidebar header (maintain aspect ratio)
            h = 60
            w = int(pil_logo.width * (h / pil_logo.height))
            self.logo_image = ctk.CTkImage(light_image=pil_logo, dark_image=pil_logo, size=(w, h))
            
            # Set window icon
            if sys.platform.startswith("win"):
                if os.path.exists(self.icon_path):
                    try:
                        self.iconbitmap(self.icon_path)
                    except Exception as e:
                        print(f"Failed to set Windows iconbitmap: {e}")
            else:
                if os.path.exists(self.logo_path):
                    try:
                        self.icon_image = tk.PhotoImage(file=self.logo_path)
                        self.wm_iconphoto(True, self.icon_image)
                    except Exception as e:
                        print(f"Failed to set Linux/macOS window icon: {e}")
        except FileNotFoundError:
            print(f"Logo file not found at {self.logo_path}. Continuing without logo.")
        except Exception as e:
            print(f"Error loading logo: {e}. Continuing without logo.")


        # Loading Management
        self.is_loading = False
        self.loader = EXRLoader(
            on_success=lambda *args: self.after(0, self._on_load_success, *args),
            on_error=lambda err: self.after(0, self._on_load_error, err),
            on_cancelled=lambda: self.after(0, self._on_load_cancelled),
            on_progress=self.log # Pass the log function here
        )

        # Grid Configuration (3 columns)
        self.grid_columnconfigure(0, weight=0, minsize=350) # Controls / Tools (Left)
        self.grid_columnconfigure(1, weight=1)              # Image Area (Flexible - Center)
        self.grid_columnconfigure(2, weight=0, minsize=320) # Navigation / Tabs (Right)
        self.grid_rowconfigure(0, weight=1)

        self._setup_nav_sidebar()
        self._setup_sidebar()
        self._setup_image_area()

        # Initial UI state
        self._set_ui_visibility(False)

        # Clean closure
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def _setup_nav_sidebar(self):
        self.nav_sidebar = ctk.CTkFrame(self, width=320, corner_radius=0, border_width=1, border_color="#222222")
        self.nav_sidebar.grid(row=0, column=2, sticky="nsew")
        self.nav_sidebar.grid_remove() # Hide initially for splash screen

        # Composite Modes (Moved above tabs for quick access)
        ctk.CTkLabel(self.nav_sidebar, text="COMPOSITE MODES", font=ctk.CTkFont(size=13, weight="bold")).pack(pady=(20, 5))
        self.composite_frame = ctk.CTkFrame(self.nav_sidebar, fg_color="transparent")
        self.composite_frame.pack(fill="x", padx=10)
        self.composite_buttons = {
            "Composite (RGB)": self._add_view_button(self.composite_frame, "Composite (RGB)"),
            "Normal Map": self._add_view_button(self.composite_frame, "Normal Map"),
            "HUD (RGBA)": self._add_view_button(self.composite_frame, "HUD (RGBA)"),
            "Metadata": self._add_view_button(self.composite_frame, Channels.COMBINED_METADATA)
        }

        # Tabview for G-Buffer Viewer and HUD Selector
        self.tabview = ctk.CTkTabview(self.nav_sidebar, width=300, command=self._on_tab_changed)
        self.tabview.pack(pady=(10, 20), padx=10, fill="both", expand=True)

        self.gbuffer_tab = self.tabview.add("G-Buffer Viewer")
        self.poly_routing_tab = self.tabview.add("Poly Routing")
        self.hud_compositor_tab = self.tabview.add("HUD Compositor")

        # Configure tabs
        self.tabview.tab("G-Buffer Viewer").grid_columnconfigure(0, weight=1)
        self.tabview.tab("Poly Routing").grid_columnconfigure(0, weight=1)
        self.tabview.tab("HUD Compositor").grid_columnconfigure(0, weight=1)

    def _setup_sidebar(self):
        self.sidebar = ctk.CTkFrame(self, width=350, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_remove() # Hide initially for splash screen

        # Header with Logo
        if self.logo_image:
             self.logo_img_label = ctk.CTkLabel(self.sidebar, image=self.logo_image, text="")
             self.logo_img_label.pack(pady=(20, 0))

        self.logo_label = ctk.CTkLabel(self.sidebar, text="Flycast Prism Editor", font=ctk.CTkFont(family="Inter", size=18, weight="bold"))
        self.logo_label.pack(pady=(5, 20), padx=20)

        self.open_button = ctk.CTkButton(self.sidebar, text="OPEN EXR", command=self.open_file,
                                         height=45, font=ctk.CTkFont(size=13, weight="bold"))
        self.open_button.pack(pady=10, padx=20, fill="x")

        # Magnifier Panel (Fixed in sidebar)
        self.magnifier_frame = ctk.CTkFrame(self.sidebar, fg_color="#1a1a1a", corner_radius=8, border_width=1, border_color="#333333", height=360)
        self.magnifier_frame.pack(pady=10, padx=20, fill="x")
        self.magnifier_frame.pack_propagate(False) # Ensure the frame doesn't shrink when empty
        
        ctk.CTkLabel(self.magnifier_frame, text="PIXEL-PERFECT MAGNIFIER (1:1)", font=ctk.CTkFont(size=10, weight="bold"), text_color="#777777").pack(pady=(5, 0))
        
        self.magnifier_label = ctk.CTkLabel(self.magnifier_frame, text="", fg_color="black", width=240, height=240)
        self.magnifier_label.pack(pady=10, padx=10)
        
        self.info_grid_frame = ctk.CTkFrame(self.magnifier_frame, fg_color="transparent")
        self.info_grid_frame.pack(pady=(0, 10), padx=10, fill="x")
        
        self.value_info_label = ctk.CTkLabel(self.info_grid_frame, text="HOVER OVER IMAGE", font=ctk.CTkFont(family="Consolas", size=11),
                                             text_color="#777777")
        self.value_info_label.grid(row=0, column=0, columnspan=2, sticky="ew")

        # Appearance mode
        self.appearance_mode_label = ctk.CTkLabel(self.sidebar, text="Appearance Mode:", anchor="w")
        self.appearance_mode_label.pack(pady=(10, 0), padx=20, fill="x")
        self.appearance_mode_optionemenu = ctk.CTkOptionMenu(self.sidebar, values=["System", "Dark", "Light"],
                                                                       command=self._change_appearance_mode_event)
        self.appearance_mode_optionemenu.pack(pady=(0, 10), padx=20, fill="x")
        self.appearance_mode_optionemenu.set("System") # Default to system theme

        self.appearance_mode_optionemenu.set("System") # Default to system theme

        # Poly Routing Tab UI
        ctk.CTkLabel(self.poly_routing_tab, text="ANNOTATION", font=ctk.CTkFont(size=11, weight="bold")).pack(pady=(10, 0), padx=20, anchor="w")
        self.poly_name_entry = ctk.CTkEntry(self.poly_routing_tab, height=30)
        self.poly_name_entry.insert(0, "my annotation")
        self.poly_name_entry.pack(pady=(0, 10), padx=15, fill="x")
        self.poly_name_entry.bind("<KeyRelease>", lambda e: self.update_poly_routing_json())

        ctk.CTkLabel(self.poly_routing_tab, text="ROUTING JSON (AUTO-UPDATE)", font=ctk.CTkFont(size=11, weight="bold")).pack(pady=(10, 0), padx=20, anchor="w")
        self.poly_json_box = ctk.CTkTextbox(self.poly_routing_tab, height=150, font=ctk.CTkFont(family="Courier", size=12))
        self.poly_json_box.pack(pady=(0, 10), padx=15, fill="x")

        self.copy_json_button = ctk.CTkButton(self.poly_routing_tab, text="COPY JSON", command=self.copy_poly_json)
        self.copy_json_button.pack(pady=10, padx=15, fill="x")

        # HUD Compositor Tab UI
        self.hud_mode_btn = ctk.CTkSegmentedButton(self.hud_compositor_tab, values=["SOURCE", "DESTINATION"],
                                                  command=self._on_hud_workspace_changed,
                                                  height=35, font=ctk.CTkFont(weight="bold"))
        self.hud_mode_btn.set("SOURCE")
        self.hud_mode_btn.pack(pady=15, padx=15, fill="x")

        self.hud_list_frame = ctk.CTkScrollableFrame(self.hud_compositor_tab, height=220, fg_color="#1e1e1e", corner_radius=8)
        self.hud_list_frame.pack(fill="x", padx=10, pady=5)
        
        self.hud_name_var = ctk.StringVar()
        self.hud_name_entry = ctk.CTkEntry(self.hud_compositor_tab, textvariable=self.hud_name_var, placeholder_text="Rectangle name...")
        self.hud_name_entry.pack(pady=5, padx=15, fill="x")
        self.hud_name_var.trace_add("write", lambda *args: self.rename_selected_rect())

        self.hud_zen_var = ctk.BooleanVar()
        self.hud_zen_checkbox = ctk.CTkCheckBox(self.hud_compositor_tab, text="Zen Mode", 
                                               variable=self.hud_zen_var, command=self.toggle_zen_mode)
        self.hud_zen_checkbox.pack(pady=5, padx=15, anchor="w")

        self.delete_rect_btn = ctk.CTkButton(self.hud_compositor_tab, text="DELETE", command=self.delete_selected_rect, fg_color="#c0392b", hover_color="#e74c3c")
        self.delete_rect_btn.pack(pady=5, padx=15, fill="x")
        self.delete_rect_btn.configure(state="disabled")


        self.hud_path_label = ctk.CTkLabel(self.hud_compositor_tab, text="No file opened", 
                                          font=ctk.CTkFont(size=10), text_color="#777777", wraplength=180)
        self.hud_path_label.pack(pady=(10, 0), padx=15, fill="x")

        self.load_hud_btn = ctk.CTkButton(self.hud_compositor_tab, text="LOAD JSON", command=self.load_hud_json)
        self.load_hud_btn.pack(pady=5, padx=15, fill="x")

        self.save_hud_btn = ctk.CTkButton(self.hud_compositor_tab, text="SAVE", command=self.save_hud_json)
        self.save_hud_btn.pack(pady=5, padx=15, fill="x")
        self.save_hud_btn.configure(state="disabled")

        self.save_as_hud_btn = ctk.CTkButton(self.hud_compositor_tab, text="SAVE AS", command=self.save_hud_json_as)
        self.save_as_hud_btn.pack(pady=(5, 10), padx=15, fill="x")



        # Channels List (moved to G-Buffer Viewer tab)

        # Channels List (moved to G-Buffer Viewer tab)
        ctk.CTkLabel(self.gbuffer_tab, text="CHANNELS (BLUE = STANDARD)", font=ctk.CTkFont(size=13, weight="bold")).pack(
            pady=(25, 5))
        self.channels_scroll = ctk.CTkScrollableFrame(self.gbuffer_tab, height=350, fg_color="transparent")
        self.channels_scroll.pack(fill="both", expand=True, padx=15, pady=5)
        self.channel_buttons = []

        # Inspector Section (Moved to bottom)
        self.inspector_container = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.inspector_container.pack(side="bottom", fill="x", padx=20, pady=(0, 10))

        self.copy_all_btn = ctk.CTkButton(self.inspector_container, text="COPY ALL VALUES", command=self.copy_all_inspected, 
                                          height=28, fg_color="#34495e", hover_color="#2c3e50")
        self.copy_all_btn.pack(side="bottom", fill="x", pady=(5, 0))
        self.copy_all_btn.configure(state="disabled")

        self.poly_inspect_frame = ctk.CTkFrame(self.inspector_container, fg_color="#1a1a1a", corner_radius=8, border_width=1, border_color="#333333")
        self.poly_inspect_frame.pack(side="bottom", fill="x", pady=5)
        self.poly_placeholder = ctk.CTkLabel(self.poly_inspect_frame, text="CLICK ON IMAGE TO INSPECT", font=ctk.CTkFont(family="Consolas", size=11), text_color="#777777")
        self.poly_placeholder.pack(pady=10)
        
        self.pixel_inspect_frame = ctk.CTkFrame(self.inspector_container, fg_color="#1a1a1a", corner_radius=8, border_width=1, border_color="#333333")
        self.pixel_inspect_frame.pack(side="bottom", fill="x", pady=5)
        self.pixel_placeholder = ctk.CTkLabel(self.pixel_inspect_frame, text="CLICK ON IMAGE TO INSPECT", font=ctk.CTkFont(family="Consolas", size=11), text_color="#777777")
        self.pixel_placeholder.pack(pady=10)

        ctk.CTkLabel(self.inspector_container, text="INSPECTOR (IMAGE CLICK)", font=ctk.CTkFont(size=13, weight="bold")).pack(side="bottom", pady=(10, 5))

        # Console has been moved to the bottom panel

    def _setup_image_area(self):
        self.center_container = ctk.CTkFrame(self, fg_color="transparent", corner_radius=0)
        self.center_container.grid(row=0, column=1, sticky="nsew")

        self.image_container = ctk.CTkFrame(self.center_container, fg_color="#050505", corner_radius=0)
        self.image_container.pack(fill="both", expand=True)

        # Bottom Panel with Tabs
        self.bottom_panel = ctk.CTkFrame(self.center_container, height=280, corner_radius=0, border_width=1, border_color="#222222")
        self.bottom_panel.pack(side="bottom", fill="x")
        self.bottom_panel.pack_propagate(False) # Keep fixed height
        
        self.bottom_tabs = ctk.CTkTabview(self.bottom_panel)
        self.bottom_tabs.pack(fill="both", expand=True, padx=10, pady=0)
        
        tab_console = self.bottom_tabs.add("Console")
        tab_pixel = self.bottom_tabs.add("Pixel Request")
        tab_poly = self.bottom_tabs.add("Poly Request")
        
        # Setup Console Tab
        self.info_box = ctk.CTkTextbox(tab_console, font=ctk.CTkFont(family="Consolas", size=11), fg_color="#0f0f0f",
                                       text_color="#00ff00", border_width=1, border_color="#333333")
        self.info_box.pack(fill="both", expand=True, padx=5, pady=5)
        self.info_box.insert("0.0", "SYSTEM READY\n")
        
        # Setup Pixel Request Tab
        self.pixel_req_entry = ctk.CTkTextbox(tab_pixel, font=ctk.CTkFont(family="Consolas", size=12), border_width=1, border_color="#333333")
        self.pixel_req_entry.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        self.pixel_req_entry.insert("0.0", "# Enter Pixel Request here...\n")
        
        self.pixel_req_btn = ctk.CTkButton(tab_pixel, text="EVALUATE", command=self.evaluate_pixel_request, width=120)
        self.pixel_req_btn.pack(side="right", padx=10, pady=10)
        
        # Setup Poly Request Tab
        self.poly_req_entry = ctk.CTkTextbox(tab_poly, font=ctk.CTkFont(family="Consolas", size=12), border_width=1, border_color="#333333")
        self.poly_req_entry.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        self.poly_req_entry.insert("0.0", "# Enter Poly Request here...\n")
        
        self.poly_req_btn = ctk.CTkButton(tab_poly, text="EVALUATE", command=self.evaluate_poly_request, width=120)
        self.poly_req_btn.pack(side="right", padx=10, pady=10)


        self.display_label = ctk.CTkLabel(self.image_container, text="", cursor="crosshair")
        self.display_label.place(relx=0.5, rely=0.5, anchor="center")

        # Display initially empty (Splash Screen will handle the logo)

        # Loading Overlay
        self.loading_overlay = ctk.CTkFrame(self.image_container, fg_color="#1a1a1a", corner_radius=15, border_width=2)
        self.loading_label = ctk.CTkLabel(self.loading_overlay, text="PROCESSING...",
                                          font=ctk.CTkFont(family="Inter", size=16, weight="bold"))
        self.loading_label.pack(pady=(20, 10), padx=30)
        self.progress_bar = ctk.CTkProgressBar(self.loading_overlay, orientation="horizontal", width=250)
        self.progress_bar.pack(pady=(0, 15), padx=30)
        self.progress_bar.configure(mode="indeterminate")

        self.cancel_button = ctk.CTkButton(self.loading_overlay, text="CANCEL", command=self.cancel_loading, width=100, height=28)
        self.cancel_button.pack(pady=(0, 20))

        self.hide_loading()

        # Splash Screen (visible when no EXR)
        self.splash_frame = ctk.CTkFrame(self.image_container, fg_color="transparent")
        self.splash_frame.place(relx=0.5, rely=0.5, anchor="center")

        if self.logo_image:
             self.splash_logo = ctk.CTkLabel(self.splash_frame, image=self.logo_image, text="")
             self.splash_logo.pack(pady=20)
        
        self.splash_btn = ctk.CTkButton(self.splash_frame, text="OPEN EXR FILE", command=self.open_file,
                                        width=300, height=60, font=ctk.CTkFont(size=16, weight="bold"))
        self.splash_btn.pack(pady=20)

        self.splash_hint = ctk.CTkLabel(self.splash_frame, text="Drag & drop or click to start", 
                                        font=ctk.CTkFont(size=12), text_color="#555555")
        self.splash_hint.pack()

        self.hide_loading()
        # Bind resize to the main window to handle layout shifts better
        self.bind("<Configure>", self.on_resize)
        self.display_label.bind("<Motion>", self.update_magnifier)
        self.display_label.bind("<Button-1>", self.on_mouse_down)
        self.display_label.bind("<B1-Motion>", self.on_mouse_move)
        self.display_label.bind("<ButtonRelease-1>", self.on_mouse_up)
        self.display_label.bind("<Leave>", self.hide_magnifier)
        self.bind("<space>", self.toggle_hud_workspace)

    def _add_view_button(self, parent, text):
        btn = ctk.CTkButton(parent, text=text, command=lambda t=text: self.safe_update_view_mode(t),
                            anchor="w", height=38, fg_color="transparent", border_width=1, 
                            border_color="#3d3d3d", hover_color="#2c3e50", font=ctk.CTkFont(size=12))
        btn.pack(fill="x", pady=4)
        return btn

    def log(self, text, clear=False):
        if clear: self.info_box.delete("0.0", "end")
        self.info_box.insert("end", f"> {text}\n")
        self.info_box.see("end")
        print(text)

    def show_loading(self, message="PROCESSING..."):
        self.is_loading = True
        self.loading_label.configure(text=message)
        self.open_button.configure(state="disabled", text="PLEASE WAIT...")
        self.loading_overlay.place(relx=0.5, rely=0.5, anchor="center")
        self.progress_bar.start()

    def hide_loading(self):
        self.is_loading = False
        self.open_button.configure(state="normal", text="OPEN EXR")
        self.loading_overlay.place_forget()
        self.progress_bar.stop()

    def cancel_loading(self):
        if self.is_loading:
            self.loader.cancel()
            self.log("Cancellation request sent...")

    def on_closing(self):
        self.loader.cancel()
        self.destroy()

    def _set_ui_visibility(self, visible):
        """Show or hide the interface side panels"""
        if visible:
            self.nav_sidebar.grid()
            self.sidebar.grid()
            self.splash_frame.place_forget()
        else:
            self.nav_sidebar.grid_remove()
            self.sidebar.grid_remove()
            self.splash_frame.place(relx=0.5, rely=0.5, anchor="center")

    def hide_magnifier(self, event=None):
        if self.display_label.cget("cursor") != "":
            self.display_label.configure(cursor="")
        # Clear the fixed magnifier labels instead of hiding them
        self.magnifier_label.configure(image=None)
        self.current_pixel_value = {} # Clear data
        self._update_info_table({})

    def open_file(self):
        if self.is_loading: return
        path = filedialog.askopenfilename(initialdir=self.default_dir, filetypes=[("OpenEXR Files", "*.exr")])
        if path:
            self.show_loading("LOADING EXR...")
            self.loader.load(path)

    def _on_load_success(self, path, w, h, channels_data, available_channels, precomputed_images):
        self.image_size = (w, h)
        self.current_exr_data = channels_data
        self.available_channels = available_channels
        self.view_cache = precomputed_images  # Initialiser le cache avec les images pré-calculées

        self.log(f"File: {os.path.basename(path)}", clear=True)
        self.log(f"Resolution: {w}x{h}")
        self.log(f"Channels found: {', '.join(sorted(available_channels))}")

        # Clear logo when EXR is loaded
        self.display_label.configure(image=None, text="")
        self.display_label.image = None

        # Update composite buttons
        self._update_composite_buttons_state()

        for btn in self.channel_buttons: btn.destroy()
        self.channel_buttons = []

        for name in sorted(self.available_channels):
            is_std = name in STANDARD_CHANNELS
            bg_color = "#2980b9" if is_std else "#34495e"
            btn = ctk.CTkButton(self.channels_scroll, text=f" {'★' if is_std else ' '} {name}",
                                command=lambda n=name: self.safe_update_view_mode(n),
                                anchor="w", height=30, fg_color=bg_color)
            btn.pack(fill="x", pady=2)
            self.channel_buttons.append(btn)

        self.hide_loading()
        
        # Choisir un mode par défaut valide
        default_mode = "Composite (RGB)"
        if self.composite_buttons[default_mode].cget("state") == "disabled":
            if self.available_channels:
                default_mode = sorted(self.available_channels)[0]
            else:
                default_mode = None
        
        if default_mode:
            self.update_view_mode(default_mode)
        
        # Reveal UI once loaded
        self._set_ui_visibility(True)

    def _update_composite_buttons_state(self):
        # Composite (RGB) requires Albedo.R, G, B
        has_rgb = all(c in self.available_channels for c in [Channels.ALBEDO_R, Channels.ALBEDO_G, Channels.ALBEDO_B])
        self.composite_buttons["Composite (RGB)"].configure(state="normal" if has_rgb else "disabled")
        
        # Normal Map requires Normal.X, Y, Z
        has_normals = all(c in self.available_channels for c in [Channels.NORMAL_X, Channels.NORMAL_Y, Channels.NORMAL_Z])
        self.composite_buttons["Normal Map"].configure(state="normal" if has_normals else "disabled")
        
        # HUD (RGBA) requires HUD.R, G, B, A
        has_hud_rgba = all(c in self.available_channels for c in [Channels.HUD_R, Channels.HUD_G, Channels.HUD_B, Channels.HUD_A])
        self.composite_buttons["HUD (RGBA)"].configure(state="normal" if has_hud_rgba else "disabled")

        # Metadata (Combined)
        metadata_channels = [
            Channels.METADATA_WORLDPOS_X, Channels.METADATA_WORLDPOS_Y, Channels.METADATA_WORLDPOS_Z,
            Channels.METADATA_TEXTURE_HASH, Channels.METADATA_POLY_COUNT
        ]
        has_metadata = any(c in self.available_channels for c in metadata_channels)
        self.composite_buttons["Metadata"].configure(state="normal" if has_metadata else "disabled")


    def _on_load_error(self, error_msg):
        self.hide_loading()
        self.log(f"ERROR: {error_msg}")
        messagebox.showerror("Critical Error", f"Loading failed:\n{error_msg}")
        self._display_logo_if_no_image() # Re-display logo on error

    def _on_load_cancelled(self):
        self.hide_loading()
        self.log("Loading cancelled.")
        self._display_logo_if_no_image() # Re-display logo on cancelled

    def _display_logo_if_no_image(self):
        # Only show logo in display_label if the splash screen is hidden
        if self.last_numpy_image is None and self.logo_image:
            if self.splash_frame.winfo_manager() == "": # Check if not placed
                self.display_label.configure(image=self.logo_image, text="")
                self.display_label.image = self.logo_image
        elif self.last_numpy_image is None and not self.logo_image:
            self.display_label.configure(image=None, text="No image loaded")
            self.display_label.image = None


    def safe_update_view_mode(self, mode):
        if not self.current_exr_data or self.is_loading: return
        
        # Si l'image est déjà dans le cache, on l'affiche instantanément sans popup
        if mode in self.view_cache:
            self.update_view_mode(mode)
            return

        self.show_loading(f"CALCULATING: {mode}")
        self.after(10, lambda: self._process_view_mode(mode))

    def _process_view_mode(self, mode):
        try:
            self.update_view_mode(mode)
        finally:
            self.hide_loading()

    def update_view_mode(self, mode):
        self.current_view_mode = mode
        
        # Utiliser le cache si disponible, sinon calculer et mettre en cache
        if mode not in self.view_cache:
            self.view_cache[mode] = ImageProcessor.process_view_mode(mode, self.image_size, self.current_exr_data)
        
        self.last_numpy_image = self.view_cache[mode]
        self.refresh_image_display()

    def _on_tab_changed(self):
        # Refresh display to show/hide safe zone or other tab-specific overlays
        self.refresh_image_display()


    def on_resize(self, event=None):
        # Only process resize events for the root window to avoid RecursionError
        # (Binding to root window catches events for all children, leading to recursion)
        if event and event.widget != self:
            return

        # Prevent jitter by checking if the actual dimensions changed
        cont_w, cont_h = self.image_container.winfo_width(), self.image_container.winfo_height()
        if hasattr(self, "_last_size") and self._last_size == (cont_w, cont_h):
            return
        self._last_size = (cont_w, cont_h)
        
        # Debounce the refresh to allow layout to settle
        if hasattr(self, "_resize_after_id") and self._resize_after_id:
            self.after_cancel(self._resize_after_id)
        
        self._resize_after_id = self.after(100, self._perform_resize_refresh)

    def _perform_resize_refresh(self):
        self._resize_after_id = None
        
        # Force layout update safely outside the event loop
        self.update_idletasks()
        
        # Refresh sidebars only if they are currently visible
        if self.sidebar.winfo_viewable():
            # Forceful grid toggle to "wake up" the layout engine (critical for KDE maximization)
            self.sidebar.grid_remove()
            self.nav_sidebar.grid_remove()
            
            # Let the grid settle for a micro-second
            self.update_idletasks()
            
            # Restore with original grid parameters
            self.sidebar.grid(row=0, column=0, sticky="nsew")
            self.nav_sidebar.grid(row=0, column=2, sticky="nsew")
            
            # Final UI synchronization
            self.nav_sidebar.update()
            self.sidebar.update()
        
        if self.last_numpy_image is not None and not self.is_loading:
            self.refresh_image_display()
        elif self.last_numpy_image is None and self.logo_image:
            self._display_logo_if_no_image()


    def refresh_image_display(self):
        if self.last_numpy_image is None:
            self._display_logo_if_no_image()
            return

        cont_w, cont_h = self.image_container.winfo_width(), self.image_container.winfo_height()
        if cont_w < 50 or cont_h < 50: return

        self.full_pil_image = Image.fromarray(self.last_numpy_image)
        
        # Apply overlays based on active tab
        display_pil = self.full_pil_image
        if self.tabview.get() == "HUD Compositor":
            display_pil = HudCompositor.draw_overlay(self.full_pil_image, self.hud_rects, self.selected_rect_idx, self.hud_workspace)

        img_w, img_h = display_pil.size
        
        # Le padding est maintenant géré à l'intérieur de HudCompositor.draw_overlay
        ratio = min(cont_w / img_w, cont_h / img_h)
        self.display_size = (int(img_w * ratio), int(img_h * ratio))

        if self.display_size[0] > 0 and self.display_size[1] > 0:
            # OPTIMISATION DES ASSETS : Utilisation de CTkImage pour le HiDPI
            # On conserve une résolution source élevée pour un rendu cible net via filtre Lanczos
            
            scaling = self._get_window_scaling()
            target_w = int(self.display_size[0] * scaling)
            target_h = int(self.display_size[1] * scaling)
            
            # Oversampling via Lanczos pour garantir une netteté cristalline
            if display_pil.width > target_w or display_pil.height > target_h:
                display_pil = display_pil.resize((target_w, target_h), Image.Resampling.LANCZOS)
            
            # La classe CTkImage gère le scaling interne pour les écrans Retina/HiDPI
            ctk_img = ctk.CTkImage(light_image=display_pil, dark_image=display_pil, size=self.display_size)
            self.display_label.configure(image=ctk_img)
            self.display_label.image = ctk_img # Keep a reference
        else:
            self.display_label.configure(image=None, text="Image too small to display")
            self.display_label.image = None

    def on_mouse_down(self, event):
        if self.tabview.get() == "HUD Compositor":
            self._on_hud_mouse_down(event)
        else:
            self.on_image_click(event)

    def on_mouse_move(self, event):
        if self.tabview.get() == "HUD Compositor":
            self._on_hud_mouse_move(event)
        
    def on_mouse_up(self, event):
        if self.tabview.get() == "HUD Compositor":
            self._on_hud_mouse_up(event)

    def _get_orig_coords(self, event):
        if self.display_size[0] == 0 or self.display_size[1] == 0: return 0, 0
        mx, my = event.x, event.y
        dw, dh = self.display_size
        
        if self.tabview.get() == "HUD Compositor":
             orig_w, orig_h = self.image_size
             p = HudCompositor.PADDING
             padded_w, padded_h = orig_w + 2*p, orig_h + 2*p
             px = int(mx * padded_w / dw)
             py = int(my * padded_h / dh)
             return px - p, py - p
        else:
             orig_w, orig_h = self.image_size
             return int(mx * orig_w / dw), int(my * orig_h / dh)

    def _get_safe_zone_bounds(self):
        if self.image_size[0] == 0: return 0, 0, 0, 0
        w, h = self.image_size
        scale = h / HudCompositor.VIRT_H
        safeW = HudCompositor.VIRT_W * scale
        safeX = (w - safeW) / 2.0
        return safeX, 0, safeW, h

    def toggle_hud_workspace(self, event=None):
        if self.tabview.get() == "HUD Compositor":
            new_mode = "DESTINATION" if self.hud_workspace == "SOURCE" else "SOURCE"
            self.hud_mode_btn.set(new_mode)
            self._on_hud_workspace_changed(new_mode)

    def _on_hud_workspace_changed(self, mode):
        self.hud_workspace = mode
        # Editing is now allowed in both modes
        self.hud_name_entry.configure(state="normal")
        if self.selected_rect_idx != -1:
            self.delete_rect_btn.configure(state="normal")
        else:
            self.delete_rect_btn.configure(state="disabled")
            
        self.refresh_image_display()

    def _on_hud_mouse_down(self, event):
        # We allow interaction in both SOURCE and DESTINATION now
        ox, oy = self._get_orig_coords(event)
        self.drag_start_orig = (ox, oy)
        
        mode = self.hud_workspace
        orig_w, orig_h = self.image_size
        
        # In DESTINATION mode, check for anchor selection first if a rectangle is active
        if mode == "DESTINATION" and self.selected_rect_idx != -1:
            anchors = HudCompositor.get_anchor_table(orig_w, orig_h)
            for anchor, apos in anchors.items():
                if abs(ox - apos[0]) < 20 and abs(oy - apos[1]) < 20: # 20px threshold
                    self.hud_rects[self.selected_rect_idx]["anchor"] = anchor
                    self.refresh_image_display()
                    return
        
        # Check for handles of selected rect (SOURCE only)
        if self.selected_rect_idx != -1 and mode == "SOURCE":
            r = self.hud_rects[self.selected_rect_idx]
            h_size = 15 # handle click area
            
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
                    self.drag_mode = m
                    self.drag_rect_start = r.copy()
                    return

        # Check for rect body
        for i, r in enumerate(reversed(self.hud_rects)):
            idx = len(self.hud_rects) - 1 - i
            rx = r["sx"] if mode == "SOURCE" else r["dx"]
            ry = r["sy"] if mode == "SOURCE" else r["dy"]
            if rx <= ox <= rx + r["w"] and ry <= oy <= ry + r["h"]:
                self.select_hud_rect(idx)
                self.drag_mode = 'move'
                self.drag_rect_start = r.copy()
                return
        
        # Creation mode (only in SOURCE suggested? user didn't specify, but usually creation is in source)
        # Let's allow in both, but it sets both sx/dx to start point
        sx, sy, sw, sh = self._get_safe_zone_bounds()
        if sx <= ox <= sx + sw and sy <= oy <= sy + sh:
            self.drag_mode = 'create'
            new_rect = {
                "name": f"Rectangle {len(self.hud_rects)+1}", 
                "sx": ox, "sy": oy, 
                "dx": ox, "dy": oy, 
                "w": 0, "h": 0,
                "anchor": Anchor.SCREEN_TOP_LEFT,
                "zen": False
            }
            self.hud_rects.append(new_rect)
            self.select_hud_rect(len(self.hud_rects)-1)
            self.drag_rect_start = new_rect.copy()
        else:
            self.select_hud_rect(-1)

    def _on_hud_mouse_move(self, event):
        if not self.drag_mode or self.selected_rect_idx == -1: return
        
        ox, oy = self._get_orig_coords(event)
        sx, sy, sw, sh = self._get_safe_zone_bounds()
        iw, ih = self.image_size
        
        # Constrain ox, oy to safe zone (for creation and handles)
        # Note: if we are moving a destination rect, we might want ox/oy outside safe zone
        if self.hud_workspace == "SOURCE" or self.drag_mode != 'move':
            ox = max(sx, min(sx + sw, ox))
            oy = max(sy, min(sy + sh, oy))
        else:
            # Full screen for destination move
            ox = max(0, min(iw, ox))
            oy = max(0, min(ih, oy))
        
        dx, dy = ox - self.drag_start_orig[0], oy - self.drag_start_orig[1]
        r = self.hud_rects[self.selected_rect_idx]
        s = self.drag_rect_start
        mode = self.hud_workspace
        
        if self.drag_mode == 'move':
            if mode == "SOURCE":
                r["sx"] = max(sx, min(sx + sw - r["w"], s["sx"] + dx))
                r["sy"] = max(sy, min(sy + sh - r["h"], s["sy"] + dy))
            else:
                # DESTINATION: Full screen bounds
                r["dx"] = max(0, min(iw - r["w"], s["dx"] + dx))
                r["dy"] = max(0, min(ih - r["h"], s["dy"] + dy))
            
        elif self.drag_mode == 'nw':
            start_x = s["sx"] if mode == "SOURCE" else s["dx"]
            start_y = s["sy"] if mode == "SOURCE" else s["dy"]
            
            new_x = max(sx, min(start_x + s["w"] - 10, start_x + dx))
            new_y = max(sy, min(start_y + s["h"] - 10, start_y + dy))
            
            if mode == "SOURCE": r["sx"], r["sy"] = new_x, new_y
            else: r["dx"], r["dy"] = new_x, new_y
            
            r["w"] = start_x + s["w"] - new_x
            r["h"] = start_y + s["h"] - new_y
            
        elif self.drag_mode == 'ne':
            start_x = s["sx"] if mode == "SOURCE" else s["dx"]
            start_y = s["sy"] if mode == "SOURCE" else s["dy"]
            
            new_y = max(sy, min(start_y + s["h"] - 10, start_y + dy))
            new_w = max(10, min(sx + sw - start_x, s["w"] + dx))
            
            if mode == "SOURCE": r["sy"] = new_y
            else: r["dy"] = new_y
            
            r["w"], r["h"] = new_w, start_y + s["h"] - new_y
            
        elif self.drag_mode == 'sw':
            start_x = s["sx"] if mode == "SOURCE" else s["dx"]
            start_y = s["sy"] if mode == "SOURCE" else s["dy"]
            
            new_x = max(sx, min(start_x + s["w"] - 10, start_x + dx))
            new_h = max(10, min(sy + sh - start_y, s["h"] + dy))
            
            if mode == "SOURCE": r["sx"] = new_x
            else: r["dx"] = new_x
            
            r["w"], r["h"] = start_x + s["w"] - new_x, new_h
            
        elif self.drag_mode == 'se':
            start_x = s["sx"] if mode == "SOURCE" else s["dx"]
            start_y = s["sy"] if mode == "SOURCE" else s["dy"]
            
            r["w"], r["h"] = max(10, min(sx + sw - start_x, s["w"] + dx)), max(10, min(sy + sh - start_y, s["h"] + dy))
            
        elif self.drag_mode == 'create':
            x1, y1 = self.drag_start_orig
            x2, y2 = ox, oy
            r["sx"], r["sy"] = min(x1, x2), min(y1, y2)
            r["dx"], r["dy"] = r["sx"], r["sy"]
            r["w"], r["h"] = abs(x2 - x1), abs(y2 - y1)
            
        # Screen-safe correction for destination position when size changes
        if self.drag_mode in ['nw', 'ne', 'sw', 'se', 'create']:
            r["dx"] = max(0, min(iw - r["w"], r["dx"]))
            r["dy"] = max(0, min(ih - r["h"], r["dy"]))
            
        self.refresh_image_display()

    def _on_hud_mouse_up(self, event):
        if self.drag_mode == 'create' and self.selected_rect_idx != -1:
            r = self.hud_rects[self.selected_rect_idx]
            # If too small, delete it (accidental click)
            if r["w"] < 5 or r["h"] < 5:
                self.delete_selected_rect()
        
        self.drag_mode = None
        self.update_hud_list()

    def add_hud_rect(self):
        w, h = self.image_size
        new_rect = {"name": f"Rectangle {len(self.hud_rects)+1}", "x": w//4, "y": h//4, "w": 200, "h": 150}
        self.hud_rects.append(new_rect)
        self.select_hud_rect(len(self.hud_rects)-1)
        self.refresh_image_display()

    def export_hud_json(self, to_file=False, path=None):
        if not self.hud_rects:
            self.log("Aucune zone HUD à exporter.")
            return

        export_data = HudConfig.export(self.hud_rects, self.image_size, path)
        
        if to_file:
            if not path:
                path = filedialog.asksaveasfilename(defaultextension=".json",
                                                     filetypes=[("JSON files", "*.json")],
                                                     title="Save HUD Compositor")
            if path:
                HudConfig.save(export_data, path)
                self.current_hud_path = path
                self.hud_path_label.configure(text=os.path.basename(path))
                self.save_hud_btn.configure(state="normal")
                self.log(f"HUD Saved to: {os.path.basename(path)}")
        
    def save_hud_json(self):
        if self.current_hud_path:
            self.export_hud_json(to_file=True, path=self.current_hud_path)
        else:
            self.save_hud_json_as()

    def save_hud_json_as(self):
        self.export_hud_json(to_file=True)

    def load_hud_json(self):
        if not self.full_pil_image:
            self.log("Please load an EXR image before importing HUD.")
            return

        file_path = filedialog.askopenfilename(filetypes=[("JSON files", "*.json")],
                                               title="Load HUD Compositor")
        if not file_path: return

        try:
            new_hud_rects = HudConfig.load(file_path, self.image_size)
            
            self.hud_rects = new_hud_rects
            self.current_hud_path = file_path
            self.hud_path_label.configure(text=os.path.basename(file_path))
            self.save_hud_btn.configure(state="normal")
            self.select_hud_rect(-1)
            self.refresh_image_display()
            self.log(f"HUD Loaded: {os.path.basename(file_path)} ({len(new_hud_rects)} zones)")
            
        except json.JSONDecodeError as e:
            msg = f"JSON Syntax Error: {e.msg} at line {e.lineno}, col {e.colno}"
            self.log(msg)
            messagebox.showerror("Load Error", msg)
        except KeyError as e:
            msg = f"Missing mandatory key: {e}"
            self.log(msg)
            messagebox.showerror("Load Error", msg)
        except Exception as e:
            msg = f"Failed to parse HUD JSON: {e}"
            self.log(msg)
            messagebox.showerror("Load Error", msg)

    def select_hud_rect(self, idx):
        self.selected_rect_idx = idx
        if idx != -1:
            r = self.hud_rects[idx]
            self.hud_name_var.set(r["name"])
            self.hud_zen_var.set(r.get("zen", False))
            self.delete_rect_btn.configure(state="normal")
            self.hud_zen_checkbox.configure(state="normal")
        else:
            self.hud_name_var.set("")
            self.hud_zen_var.set(False)
            self.delete_rect_btn.configure(state="disabled")
            self.hud_zen_checkbox.configure(state="disabled")
        self.update_hud_list()
        self.refresh_image_display()

    def toggle_zen_mode(self):
        if self.selected_rect_idx != -1:
            self.hud_rects[self.selected_rect_idx]["zen"] = self.hud_zen_var.get()
            self.refresh_image_display()

    def rename_selected_rect(self):
        if self.selected_rect_idx != -1:
            self.hud_rects[self.selected_rect_idx]["name"] = self.hud_name_var.get()
            self.update_hud_list()
            self.refresh_image_display()

    def delete_selected_rect(self):
        if self.selected_rect_idx != -1:
            del self.hud_rects[self.selected_rect_idx]
            if self.hud_rects:
                self.select_hud_rect(0)
            else:
                self.select_hud_rect(-1)
            self.refresh_image_display()

    def update_hud_list(self):
        for child in self.hud_list_frame.winfo_children():
            child.destroy()
        
        for i, r in enumerate(self.hud_rects):
            is_sel = (i == self.selected_rect_idx)
            btn = ctk.CTkButton(self.hud_list_frame, text=r["name"], 
                                fg_color="#f1c40f" if is_sel else "transparent",
                                text_color="white" if is_sel else "#aaaaaa",
                                hover_color="#f39c12" if is_sel else "#333333",
                                anchor="w", height=28,
                                command=lambda idx=i: self.select_hud_rect(idx))
            btn.pack(fill="x", pady=1)

    def on_image_click(self, event):
        if self.current_pixel_value:
            self._update_inspect_table(self.current_pixel_value)
            self.copy_all_btn.configure(state="normal")
            
            # Summary for log
            summary = " | ".join([f"{k}:{v}" for k, v in self.current_pixel_value.items()])
            self.log(f"Inspected: {summary}")
            
            # Update Poly Routing JSON if data is available
            self.last_clicked_event = event
            self.update_poly_routing_json()

    def update_poly_routing_json(self, event=None):
        # Use provided event or the last stored one
        evt = event or self.last_clicked_event
        if evt is None or self.full_pil_image is None or not self.current_exr_data:
            return

        x, y = evt.x, evt.y
        disp_w, disp_h = self.display_size
        orig_w, orig_h = self.full_pil_image.size
        orig_x, orig_y = int((x / disp_w) * orig_w), int((y / disp_h) * orig_h)

        if not (0 <= orig_x < orig_w and 0 <= orig_y < orig_h):
            return

        metadata = ImageProcessor.get_pixel_metadata(orig_x, orig_y, self.current_exr_data)
        if metadata:
            import json
            # Build the JSON object with nested 'match' and empty 'actions'
            poly_data = {
                "name": self.poly_name_entry.get(),
                "match": metadata,
                "actions": []
            }
            json_str = json.dumps(poly_data, indent=2)
            
            self.poly_json_box.delete("0.0", "end")
            self.poly_json_box.insert("0.0", json_str)

    def copy_poly_json(self):
        json_content = self.poly_json_box.get("0.0", "end-1c")
        if json_content.strip():
            self.clipboard_clear()
            self.clipboard_append(json_content)
            self.log("JSON copied to clipboard!")
        else:
            self.log("Nothing to copy (click on the image first)")

    def update_magnifier(self, event):
        # Update cursor for HUD if applicable
        if self.tabview.get() == "HUD Compositor":
            ox, oy = self._get_orig_coords(event)
            mode = self.hud_workspace
            hover_rect = False
            for r in self.hud_rects:
                rx = r["sx"] if mode == "SOURCE" else r["dx"]
                ry = r["sy"] if mode == "SOURCE" else r["dy"]
                if rx <= ox <= rx + r["w"] and ry <= oy <= ry + r["h"]:
                    hover_rect = True
                    break
            
            if hover_rect:
                if self.display_label.cget("cursor") != "hand2":
                    self.display_label.configure(cursor="hand2")
            else:
                if self.display_label.cget("cursor") != "":
                    self.display_label.configure(cursor="")

        if self.full_pil_image is None or self.is_loading:
            self.hide_magnifier()
            return

        x, y = event.x, event.y
        disp_w, disp_h = self.display_size
        orig_w, orig_h = self.full_pil_image.size
        orig_x, orig_y = int((x / disp_w) * orig_w), int((y / disp_h) * orig_h)

        if 0 <= orig_x < orig_w and 0 <= orig_y < orig_h:
            self.current_pixel_value = ImageProcessor.get_pixel_raw_values(orig_x, orig_y, self.current_exr_data)
        else:
            self.current_pixel_value = {}

        self._update_info_table(self.current_pixel_value)

        m_half = self.magnifier_size // 2
        left, top = max(0, orig_x - m_half), max(0, orig_y - m_half)
        right, bottom = min(orig_w, orig_x + m_half), min(orig_h, orig_y + m_half)

        try:
            crop = self.full_pil_image.crop((left, top, right, bottom))
            zoomed = Image.new("RGB", (self.magnifier_size, self.magnifier_size), (0, 0, 0))
            zoomed.paste(crop, (max(0, m_half - orig_x), max(0, m_half - orig_y)))

            draw = ImageDraw.Draw(zoomed)
            mid, length = self.magnifier_size // 2, 12
            for color, width in [("black", 3), ("white", 1)]:
                draw.line([(mid - length, mid), (mid + length, mid)], fill=color, width=width)
                draw.line([(mid, mid - length), (mid, mid + length)], fill=color, width=width)

            zoomed = ImageOps.expand(zoomed, border=2, fill='#3498db')
            zoom_ctk = ctk.CTkImage(light_image=zoomed, dark_image=zoomed, size=(self.magnifier_size + 4, self.magnifier_size + 4))

            self.magnifier_label.configure(image=zoom_ctk)
            self.magnifier_label.image = zoom_ctk # Keep reference
        except Exception:
            self.hide_magnifier()

    def _update_inspect_table(self, data):
        """Updates the inspector grids with clicked pixel data."""
        for child in self.pixel_inspect_frame.winfo_children():
            child.destroy()
        for child in self.poly_inspect_frame.winfo_children():
            child.destroy()
        
        if not data:
            self.pixel_placeholder = ctk.CTkLabel(self.pixel_inspect_frame, text="CLICK ON IMAGE TO INSPECT", font=ctk.CTkFont(family="Consolas", size=11), text_color="#777777")
            self.pixel_placeholder.pack(pady=10)
            self.poly_placeholder = ctk.CTkLabel(self.poly_inspect_frame, text="CLICK ON IMAGE TO INSPECT", font=ctk.CTkFont(family="Consolas", size=11), text_color="#777777")
            self.poly_placeholder.pack(pady=10)
            return

        # Render Pixel Level
        ctk.CTkLabel(self.pixel_inspect_frame, text="PIXEL LEVEL", font=ctk.CTkFont(size=10, weight="bold"), text_color="#777777").pack(pady=(5, 0))
        pixel_grid = ctk.CTkFrame(self.pixel_inspect_frame, fg_color="transparent")
        pixel_grid.pack(pady=5, padx=10, fill="x")
        
        # Render Poly Level
        ctk.CTkLabel(self.poly_inspect_frame, text="POLY LEVEL", font=ctk.CTkFont(size=10, weight="bold"), text_color="#777777").pack(pady=(5, 0))
        poly_grid = ctk.CTkFrame(self.poly_inspect_frame, fg_color="transparent")
        poly_grid.pack(pady=5, padx=10, fill="x")

        pixel_keys = ["RGB", "Normals", "Depth", "HUD"]
        poly_keys = ["MatID", "MatList", "MatFlags", "WorldPos", "TexHash", "PolyCnt"]

        p_row, py_row = 0, 0
        for key, val in data.items():
            if key in pixel_keys:
                k_lbl = ctk.CTkLabel(pixel_grid, text=f"{key}:", font=ctk.CTkFont(family="Consolas", size=10, weight="bold"), text_color="#aaaaaa", anchor="w")
                k_lbl.grid(row=p_row, column=0, sticky="w", padx=(0, 10))
                v_lbl = ctk.CTkLabel(pixel_grid, text=val, font=ctk.CTkFont(family="Consolas", size=10), text_color="#2ecc71", anchor="w")
                v_lbl.grid(row=p_row, column=1, sticky="w")
                p_row += 1
            elif key in poly_keys:
                k_lbl = ctk.CTkLabel(poly_grid, text=f"{key}:", font=ctk.CTkFont(family="Consolas", size=10, weight="bold"), text_color="#aaaaaa", anchor="w")
                k_lbl.grid(row=py_row, column=0, sticky="w", padx=(0, 10))
                v_lbl = ctk.CTkLabel(poly_grid, text=val, font=ctk.CTkFont(family="Consolas", size=10), text_color="#2ecc71", anchor="w")
                v_lbl.grid(row=py_row, column=1, sticky="w")
                py_row += 1
            else:
                # Fallback for unexpected keys
                k_lbl = ctk.CTkLabel(poly_grid, text=f"{key}:", font=ctk.CTkFont(family="Consolas", size=10, weight="bold"), text_color="#aaaaaa", anchor="w")
                k_lbl.grid(row=py_row, column=0, sticky="w", padx=(0, 10))
                v_lbl = ctk.CTkLabel(poly_grid, text=val, font=ctk.CTkFont(family="Consolas", size=10), text_color="#2ecc71", anchor="w")
                v_lbl.grid(row=py_row, column=1, sticky="w")
                py_row += 1

    def copy_all_inspected(self):
        """Copies current inspected data to clipboard."""
        if self.current_pixel_value:
            summary = " | ".join([f"{k}:{v}" for k, v in self.current_pixel_value.items()])
            self.clipboard_clear()
            self.clipboard_append(summary)
            self.log("All values copied to clipboard!")

    def _update_info_table(self, data):
        """Updates the grid of labels with pixel data."""
        # Clear current grid
        for child in self.info_grid_frame.winfo_children():
            child.destroy()
        
        if not data:
            lbl = ctk.CTkLabel(self.info_grid_frame, text="HOVER OVER IMAGE", font=ctk.CTkFont(family="Consolas", size=11), text_color="#777777")
            lbl.grid(row=0, column=0, columnspan=2, sticky="ew")
            return

        for i, (key, val) in enumerate(data.items()):
            k_lbl = ctk.CTkLabel(self.info_grid_frame, text=f"{key}:", font=ctk.CTkFont(family="Consolas", size=10, weight="bold"), 
                                 text_color="#aaaaaa", anchor="w")
            k_lbl.grid(row=i, column=0, sticky="w", padx=(0, 10))
            
            v_lbl = ctk.CTkLabel(self.info_grid_frame, text=val, font=ctk.CTkFont(family="Consolas", size=10), 
                                 text_color="#3498db", anchor="w")
            v_lbl.grid(row=i, column=1, sticky="w")

    def _change_appearance_mode_event(self, new_appearance_mode: str):
        ctk.set_appearance_mode(new_appearance_mode)

    def evaluate_pixel_request(self):
        req = self.pixel_req_entry.get("0.0", "end-1c").strip()
        self.log(f"Pixel Request evaluated:\n{req}")

    def evaluate_poly_request(self):
        req = self.poly_req_entry.get("0.0", "end-1c").strip()
        self.log(f"Poly Request evaluated:\n{req}")

    def _maximize_window(self):
        """Robust maximization for different platforms and window managers (KDE/X11)"""
        try:
            if sys.platform.startswith("win"):
                self.state("zoomed")
            else:
                # Try X11 attribute first
                self.attributes("-zoomed", True)
                # Fallback to state if attribute didn't work or isn't enough for some WMs
                try:
                    self.state("zoomed")
                except:
                    pass
        except Exception as e:
            print(f"Maximization failed: {e}")

if __name__ == "__main__":
    app = FlycastViewer()
    app.mainloop()
