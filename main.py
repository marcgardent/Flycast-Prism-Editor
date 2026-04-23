import os
import customtkinter as ctk
import ctypes
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

# Global UI Settings for better aesthetics
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class FlycastViewer(ctk.CTk):
    def __init__(self):
        # Enable High DPI awareness before any widget creation
        try:
            # For Windows
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass

        # Set scaling based on system (CustomTkinter usually does this, but we can be explicit)
        # ctk.set_widget_scaling(1.0) 
        # ctk.set_window_scaling(1.0)

        super().__init__()

        self.title("Flycast G-Buffer Viewer")
        self.geometry("1500x900")

        # État de l'application
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

        # État HUD Compositor
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
        try:
            pil_logo = Image.open(self.logo_path)
            self.logo_image = ctk.CTkImage(light_image=pil_logo, dark_image=pil_logo, size=(pil_logo.width, pil_logo.height))
        except FileNotFoundError:
            print(f"Logo file not found at {self.logo_path}. Continuing without logo.")
        except Exception as e:
            print(f"Error loading logo: {e}. Continuing without logo.")


        # Gestion du chargement
        self.is_loading = False
        self.loader = EXRLoader(
            on_success=lambda *args: self.after(0, self._on_load_success, *args),
            on_error=lambda err: self.after(0, self._on_load_error, err),
            on_cancelled=lambda: self.after(0, self._on_load_cancelled),
            on_progress=self.log # Pass the log function here
        )

        # Configuration de la grille
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._setup_sidebar()
        self._setup_image_area()

        # Propre fermeture
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def _setup_sidebar(self):
        self.sidebar = ctk.CTkFrame(self, width=350, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)

        self.logo_label = ctk.CTkLabel(self.sidebar, text="FLYCAST G-BUFFER", font=ctk.CTkFont(family="Inter", size=24, weight="bold"))
        self.logo_label.pack(pady=(30, 25), padx=20)

        self.open_button = ctk.CTkButton(self.sidebar, text="OUVRIR EXR", command=self.open_file,
                                         fg_color="#3498db", hover_color="#2980b9", height=45, font=ctk.CTkFont(size=13, weight="bold"))
        self.open_button.pack(pady=10, padx=20, fill="x")

        # Section Inspecteur
        ctk.CTkLabel(self.sidebar, text="INSPECTEUR (CLIC IMAGE)", font=ctk.CTkFont(size=13, weight="bold")).pack(
            pady=(25, 5))
        self.inspect_entry = ctk.CTkEntry(self.sidebar, placeholder_text="Valeur copiée ici...", height=35)
        self.inspect_entry.pack(pady=5, padx=20, fill="x")

        # Section Outils
        ctk.CTkLabel(self.sidebar, text="OUTILS", font=ctk.CTkFont(size=13, weight="bold")).pack(pady=(25, 5))
        self.magnifier_var = ctk.BooleanVar(value=True)
        self.magnifier_switch = ctk.CTkSwitch(self.sidebar, text="Loupe Pixel-Perfect (1:1)",
                                              variable=self.magnifier_var)
        self.magnifier_switch.pack(pady=5, padx=20, anchor="w")

        # Theme switch
        self.appearance_mode_label = ctk.CTkLabel(self.sidebar, text="Mode d'apparence:", anchor="w")
        self.appearance_mode_label.pack(pady=(10, 0), padx=20, fill="x")
        self.appearance_mode_optionemenu = ctk.CTkOptionMenu(self.sidebar, values=["System", "Dark", "Light"],
                                                                       command=self._change_appearance_mode_event)
        self.appearance_mode_optionemenu.pack(pady=(0, 10), padx=20, fill="x")
        self.appearance_mode_optionemenu.set("System") # Default to system theme

        # Tabview for G-Buffer Viewer and HUD Selector
        self.tabview = ctk.CTkTabview(self.sidebar, width=300, command=self._on_tab_changed)
        self.tabview.pack(pady=(20, 0), padx=20, fill="both", expand=True)

        self.gbuffer_tab = self.tabview.add("G-Buffer Viewer")
        self.poly_routing_tab = self.tabview.add("Poly Routing")
        self.hud_compositor_tab = self.tabview.add("HUD Compositor")

        # Configure tabs
        self.tabview.tab("G-Buffer Viewer").grid_columnconfigure(0, weight=1)
        self.tabview.tab("Poly Routing").grid_columnconfigure(0, weight=1)
        self.tabview.tab("HUD Compositor").grid_columnconfigure(0, weight=1)

        # Poly Routing Tab UI
        ctk.CTkLabel(self.poly_routing_tab, text="ANNOTATION", font=ctk.CTkFont(size=11, weight="bold")).pack(pady=(10, 0), padx=20, anchor="w")
        self.poly_name_entry = ctk.CTkEntry(self.poly_routing_tab, height=30)
        self.poly_name_entry.insert(0, "my annotation")
        self.poly_name_entry.pack(pady=(0, 10), padx=15, fill="x")
        self.poly_name_entry.bind("<KeyRelease>", lambda e: self.update_poly_routing_json())

        ctk.CTkLabel(self.poly_routing_tab, text="ROUTING JSON (AUTO-UPDATE)", font=ctk.CTkFont(size=11, weight="bold")).pack(pady=(10, 0), padx=20, anchor="w")
        self.poly_json_box = ctk.CTkTextbox(self.poly_routing_tab, height=150, font=ctk.CTkFont(family="Courier", size=12))
        self.poly_json_box.pack(pady=(0, 10), padx=15, fill="x")

        self.copy_json_button = ctk.CTkButton(self.poly_routing_tab, text="COPIER JSON", command=self.copy_poly_json,
                                             fg_color="#27ae60", hover_color="#2ecc71")
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
        self.hud_name_entry = ctk.CTkEntry(self.hud_compositor_tab, textvariable=self.hud_name_var, placeholder_text="Nom du rectangle...")
        self.hud_name_entry.pack(pady=5, padx=15, fill="x")
        self.hud_name_var.trace_add("write", lambda *args: self.rename_selected_rect())

        self.hud_zen_var = ctk.BooleanVar()
        self.hud_zen_checkbox = ctk.CTkCheckBox(self.hud_compositor_tab, text="Zen Mode", 
                                               variable=self.hud_zen_var, command=self.toggle_zen_mode)
        self.hud_zen_checkbox.pack(pady=5, padx=15, anchor="w")

        self.hud_path_label = ctk.CTkLabel(self.hud_compositor_tab, text="Aucun fichier ouvert", 
                                          font=ctk.CTkFont(size=10), text_color="#777777", wraplength=180)
        self.hud_path_label.pack(pady=(10, 0), padx=15, fill="x")

        self.load_hud_btn = ctk.CTkButton(self.hud_compositor_tab, text="CHARGER JSON", command=self.load_hud_json,
                                         fg_color="#34495e", hover_color="#2c3e50")
        self.load_hud_btn.pack(pady=5, padx=15, fill="x")

        self.save_hud_btn = ctk.CTkButton(self.hud_compositor_tab, text="SAUVEGARDER", command=self.save_hud_json,
                                         fg_color="#27ae60", hover_color="#2ecc71")
        self.save_hud_btn.pack(pady=5, padx=15, fill="x")
        self.save_hud_btn.configure(state="disabled")

        self.save_as_hud_btn = ctk.CTkButton(self.hud_compositor_tab, text="SAUVEGARDER SOUS", command=self.save_hud_json_as,
                                            fg_color="#2980b9", hover_color="#3498db")
        self.save_as_hud_btn.pack(pady=(5, 10), padx=15, fill="x")

        self.delete_rect_btn = ctk.CTkButton(self.hud_compositor_tab, text="SUPPRIMER", command=self.delete_selected_rect,
                                            fg_color="#c0392b", hover_color="#e74c3c")


        # Modes Composites (moved to G-Buffer Viewer tab)
        ctk.CTkLabel(self.gbuffer_tab, text="MODES COMPOSITES", font=ctk.CTkFont(size=13, weight="bold")).pack(pady=(15, 5))
        self.composite_frame = ctk.CTkFrame(self.gbuffer_tab, fg_color="transparent")
        self.composite_frame.pack(fill="x", padx=15)
        self.composite_buttons = {
            "Composite (RGB)": self._add_view_button(self.composite_frame, "Composite (RGB)"),
            "Normal Map": self._add_view_button(self.composite_frame, "Normal Map"),
            "HUD (RGBA)": self._add_view_button(self.composite_frame, "HUD (RGBA)"),
            "Metadata": self._add_view_button(self.composite_frame, Channels.COMBINED_METADATA)
        }

        # Liste des canaux (moved to G-Buffer Viewer tab)
        ctk.CTkLabel(self.gbuffer_tab, text="CANAUX (BLEU = STANDARD)", font=ctk.CTkFont(size=13, weight="bold")).pack(
            pady=(25, 5))
        self.channels_scroll = ctk.CTkScrollableFrame(self.gbuffer_tab, height=350, fg_color="transparent")
        self.channels_scroll.pack(fill="both", expand=True, padx=15, pady=5)
        self.channel_buttons = []

        # Console
        self.info_box = ctk.CTkTextbox(self.sidebar, height=140, font=ctk.CTkFont(family="Consolas", size=11), fg_color="#0f0f0f",
                                       text_color="#00ff00", border_width=1, border_color="#333333")
        self.info_box.pack(side="bottom", fill="x", padx=20, pady=20)
        self.info_box.insert("0.0", "SYSTEM READY\n")

    def _setup_image_area(self):
        self.image_container = ctk.CTkFrame(self, fg_color="#050505", corner_radius=0)
        self.image_container.grid(row=0, column=1, sticky="nsew")

        self.display_label = ctk.CTkLabel(self.image_container, text="", cursor="crosshair")
        self.display_label.place(relx=0.5, rely=0.5, anchor="center")

        # Display logo initially if available
        if self.logo_image:
            self.display_label.configure(image=self.logo_image, text="")
            self.display_label.image = self.logo_image # Keep a reference

        # Overlay de chargement
        self.loading_overlay = ctk.CTkFrame(self.image_container, fg_color="#1a1a1a", corner_radius=15, border_width=2,
                                            border_color="#3498db")
        self.loading_label = ctk.CTkLabel(self.loading_overlay, text="TRAITEMENT EN COURS...",
                                          font=ctk.CTkFont(family="Inter", size=16, weight="bold"))
        self.loading_label.pack(pady=(20, 10), padx=30)
        self.progress_bar = ctk.CTkProgressBar(self.loading_overlay, orientation="horizontal", width=250)
        self.progress_bar.pack(pady=(0, 15), padx=30)
        self.progress_bar.configure(mode="indeterminate")

        self.cancel_button = ctk.CTkButton(self.loading_overlay, text="ANNULER", command=self.cancel_loading,
                                           fg_color="#c0392b", hover_color="#e74c3c", width=100, height=28)
        self.cancel_button.pack(pady=(0, 20))

        self.magnifier_label = ctk.CTkLabel(self.image_container, text="", fg_color="transparent")
        self.value_info_label = ctk.CTkLabel(self.image_container, text="", font=ctk.CTkFont(size=12, weight="bold"),
                                             fg_color="#3498db", text_color="white", corner_radius=4)

        self.hide_loading()
        self.image_container.bind("<Configure>", self.on_resize)
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

    def show_loading(self, message="TRAITEMENT EN COURS..."):
        self.is_loading = True
        self.loading_label.configure(text=message)
        self.open_button.configure(state="disabled", text="PATIENTEZ...")
        self.loading_overlay.place(relx=0.5, rely=0.5, anchor="center")
        self.progress_bar.start()

    def hide_loading(self):
        self.is_loading = False
        self.open_button.configure(state="normal", text="OUVRIR EXR")
        self.loading_overlay.place_forget()
        self.progress_bar.stop()

    def cancel_loading(self):
        if self.is_loading:
            self.loader.cancel()
            self.log("Demande d'annulation envoyée...")

    def on_closing(self):
        self.loader.cancel()
        self.destroy()

    def hide_magnifier(self, event=None):
        self.display_label.configure(cursor="")
        self.magnifier_label.place_forget()
        self.value_info_label.place_forget()

    def open_file(self):
        if self.is_loading: return
        path = filedialog.askopenfilename(initialdir=self.default_dir, filetypes=[("OpenEXR Files", "*.exr")])
        if path:
            self.show_loading("CHARGEMENT DE L'EXR...")
            self.loader.load(path)

    def _on_load_success(self, path, w, h, channels_data, available_channels, precomputed_images):
        self.image_size = (w, h)
        self.current_exr_data = channels_data
        self.available_channels = available_channels
        self.view_cache = precomputed_images  # Initialiser le cache avec les images pré-calculées

        self.log(f"Fichier : {os.path.basename(path)}", clear=True)
        self.log(f"Résolution : {w}x{h}")
        self.log(f"Canaux trouvés : {', '.join(sorted(available_channels))}")

        # Clear logo when EXR is loaded
        self.display_label.configure(image=None, text="")
        self.display_label.image = None

        # Mise à jour des boutons composites
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

    def _update_composite_buttons_state(self):
        # Composite (RGB) nécessite Albedo.R, G, B
        has_rgb = all(c in self.available_channels for c in [Channels.ALBEDO_R, Channels.ALBEDO_G, Channels.ALBEDO_B])
        self.composite_buttons["Composite (RGB)"].configure(state="normal" if has_rgb else "disabled")
        
        # Normal Map nécessite Normal.X, Y, Z
        has_normals = all(c in self.available_channels for c in [Channels.NORMAL_X, Channels.NORMAL_Y, Channels.NORMAL_Z])
        self.composite_buttons["Normal Map"].configure(state="normal" if has_normals else "disabled")
        
        # HUD (RGBA) nécessite HUD.R, G, B, A
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
        self.log(f"ERREUR : {error_msg}")
        messagebox.showerror("Erreur Critique", f"Le chargement a échoué :\n{error_msg}")
        self._display_logo_if_no_image() # Re-display logo on error

    def _on_load_cancelled(self):
        self.hide_loading()
        self.log("Chargement annulé.")
        self._display_logo_if_no_image() # Re-display logo on cancelled

    def _display_logo_if_no_image(self):
        if self.last_numpy_image is None and self.logo_image:
            self.display_label.configure(image=self.logo_image, text="")
            self.display_label.image = self.logo_image # Keep a reference
        elif self.last_numpy_image is None and not self.logo_image:
            self.display_label.configure(image=None, text="No image loaded and no logo available.")
            self.display_label.image = None


    def safe_update_view_mode(self, mode):
        if not self.current_exr_data or self.is_loading: return
        
        # Si l'image est déjà dans le cache, on l'affiche instantanément sans popup
        if mode in self.view_cache:
            self.update_view_mode(mode)
            return

        self.show_loading(f"CALCUL : {mode}")
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
        if self.last_numpy_image is not None and not self.is_loading:
            self.refresh_image_display()
        elif self.last_numpy_image is None and self.logo_image: # Resize logo if no image is loaded
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
            # For high-quality display and High DPI support:
            # We don't pre-resize the image to the display size anymore.
            # Instead, we pass the high-res image to CTkImage and let it handle the scaling.
            # This ensures that on High DPI screens, we use the extra resolution available.
            
            # However, to avoid memory issues with huge images, we can resize to 2x display size if needed
            # as a compromise between quality and performance.
            scaling = self._get_window_scaling()
            target_w = int(self.display_size[0] * scaling)
            target_h = int(self.display_size[1] * scaling)
            
            # Only resize if the source is significantly larger than what we need
            if display_pil.width > target_w * 1.2 or display_pil.height > target_h * 1.2:
                display_pil = display_pil.resize((target_w, target_h), Image.Resampling.LANCZOS)
            
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

        orig_w, orig_h = self.image_size
        v_scale = 480.0 / orig_h
        VW = orig_w * v_scale
        
        # Anchors in Virtual Space
        v_anchors = HudCompositor.get_anchor_table(orig_w, orig_h)
        v_anchors = {k: (v[0] * v_scale, v[1] * v_scale) for k, v in v_anchors.items()}
        
        source_anchor_vpos = v_anchors[Anchor.SCREEN_CENTER]
        
        hud_zones = []
        for r in self.hud_rects:
            vsx, vsy = r["sx"] * v_scale, r["sy"] * v_scale
            src_x = int(round(vsx - source_anchor_vpos[0]))
            src_y = int(round(vsy - source_anchor_vpos[1]))
            
            vdx, vdy = r["dx"] * v_scale, r["dy"] * v_scale
            anchor_enum = r["anchor"]
            if isinstance(anchor_enum, str): anchor_enum = Anchor[anchor_enum]
            
            dest_anchor_vpos = v_anchors[anchor_enum]
            map_x = int(round(vdx - dest_anchor_vpos[0]))
            map_y = int(round(vdy - dest_anchor_vpos[1]))
            
            zone = {
                "name": r["name"],
                "w": int(round(r["w"] * v_scale)),
                "h": int(round(r["h"] * v_scale)),
                "zen_mode": r.get("zen", False),
                "source": {
                    "x": src_x,
                    "y": src_y,
                    "anchor": "SCREEN_CENTER"
                },
                "mapping": {
                    "x": map_x,
                    "y": map_y,
                    "anchor": anchor_enum.name
                }
            }
            hud_zones.append(zone)
            
        export_data = {
            "safe_zone": {"w": 640, "h": 480},
            "hud_zones": hud_zones
        }
        
        # Smart Save: Preserve other keys
        if path and os.path.exists(path):
            try:
                with open(path, "r") as f:
                    existing_data = json.load(f)
                existing_data.update(export_data)
                export_data = existing_data
            except Exception as e:
                self.log(f"Erreur lecture fichier existant: {e}")

        json_str = json.dumps(export_data, indent=2)
        
        if to_file:
            if not path:
                path = filedialog.asksaveasfilename(defaultextension=".json",
                                                     filetypes=[("JSON files", "*.json")],
                                                     title="Sauvegarder HUD Compositor")
            if path:
                with open(path, "w") as f:
                    f.write(json_str)
                self.current_hud_path = path
                self.hud_path_label.configure(text=os.path.basename(path))
                self.save_hud_btn.configure(state="normal")
                self.log(f"HUD Sauvegardé dans: {os.path.basename(path)}")
        
    def save_hud_json(self):
        if self.current_hud_path:
            self.export_hud_json(to_file=True, path=self.current_hud_path)
        else:
            self.save_hud_json_as()

    def save_hud_json_as(self):
        self.export_hud_json(to_file=True)

    def load_hud_json(self):
        if not self.full_pil_image:
            self.log("Chargez une image EXR avant d'importer le HUD.")
            return

        file_path = filedialog.askopenfilename(filetypes=[("JSON files", "*.json")],
                                               title="Charger HUD Compositor")
        if not file_path: return

        try:
            with open(file_path, "r") as f:
                data = json.load(f)
            
            if "hud_zones" not in data:
                self.log("Format JSON invalide (hud_zones manquante).")
                return

            orig_w, orig_h = self.image_size
            v_scale = 480.0 / orig_h
            VW = orig_w * v_scale
            
            v_anchors = HudCompositor.get_anchor_table(orig_w, orig_h)
            v_anchors = {k: (v[0] * v_scale, v[1] * v_scale) for k, v in v_anchors.items()}
            source_anchor_vpos = v_anchors[Anchor.SCREEN_CENTER]

            new_hud_rects = []
            for zone in data["hud_zones"]:
                v_w = zone["w"]
                v_h = zone["h"]
                
                # Convert source back
                vsx = zone["source"]["x"] + source_anchor_vpos[0]
                vsy = zone["source"]["y"] + source_anchor_vpos[1]
                
                # Convert destination back
                anchor_name = zone["mapping"]["anchor"]
                anchor_enum = Anchor[anchor_name]
                dest_anchor_vpos = v_anchors[anchor_enum]
                vdx = zone["mapping"]["x"] + dest_anchor_vpos[0]
                vdy = zone["mapping"]["y"] + dest_anchor_vpos[1]
                
                new_rect = {
                    "name": zone["name"],
                    "sx": vsx / v_scale,
                    "sy": vsy / v_scale,
                    "dx": vdx / v_scale,
                    "dy": vdy / v_scale,
                    "w": v_w / v_scale,
                    "h": v_h / v_scale,
                    "anchor": anchor_enum,
                    "zen": zone.get("zen_mode", False)
                }
                new_hud_rects.append(new_rect)
            
            self.hud_rects = new_hud_rects
            self.current_hud_path = file_path
            self.hud_path_label.configure(text=os.path.basename(file_path))
            self.save_hud_btn.configure(state="normal")
            self.select_hud_rect(-1)
            self.refresh_image_display()
            self.log(f"HUD Chargé: {os.path.basename(file_path)} ({len(new_hud_rects)} zones)")
            
        except Exception as e:
            self.log(f"Erreur lors du chargement: {e}")
            print(f"Load Error: {e}")

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
        if self.current_pixel_value != "N/A":
            display_text = f"{self.current_view_mode}: {self.current_pixel_value}"
            self.inspect_entry.delete(0, "end")
            self.inspect_entry.insert(0, display_text)
            self.log(f"Inspecté : {display_text}")
            
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
            self.log("JSON copié dans le presse-papier !")
        else:
            self.log("Rien à copier (cliquez sur l'image d'abord)")

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
                self.display_label.configure(cursor="hand2")
            else:
                self.display_label.configure(cursor="")

        if not self.magnifier_var.get() or self.full_pil_image is None or self.is_loading:
            self.hide_magnifier()
            return

        x, y = event.x, event.y
        disp_w, disp_h = self.display_size
        orig_w, orig_h = self.full_pil_image.size
        orig_x, orig_y = int((x / disp_w) * orig_w), int((y / disp_h) * orig_h)

        if 0 <= orig_x < orig_w and 0 <= orig_y < orig_h:
            self.current_pixel_value = ImageProcessor.get_pixel_raw_values(self.current_view_mode, orig_x, orig_y, self.current_exr_data)
        else:
            self.current_pixel_value = "N/A"

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
            self.value_info_label.configure(text=f" {self.current_pixel_value} ")

            mx = x + self.display_label.winfo_x() + 40
            my = y + self.display_label.winfo_y() + 40
            if mx + self.magnifier_size > self.image_container.winfo_width(): mx -= (self.magnifier_size + 80)
            if my + self.magnifier_size > self.image_container.winfo_height(): my -= (self.magnifier_size + 80)

            self.magnifier_label.place(x=mx, y=my)
            info_y = my + self.magnifier_size + 15 if my + self.magnifier_size + 50 < self.image_container.winfo_height() else my - 35
            self.value_info_label.place(x=mx, y=info_y)
        except Exception:
            self.hide_magnifier()

    def _change_appearance_mode_event(self, new_appearance_mode: str):
        ctk.set_appearance_mode(new_appearance_mode)

if __name__ == "__main__":
    app = FlycastViewer()
    app.mainloop()
