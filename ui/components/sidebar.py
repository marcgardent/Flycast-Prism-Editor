import customtkinter as ctk
import tkinter as tk
import os

class SidebarComponent(ctk.CTkFrame):
    def __init__(self, master, callbacks, **kwargs):
        super().__init__(master, width=350, corner_radius=0, **kwargs)
        self.callbacks = callbacks
        self.logo_image = None
        self._load_logo()
        self._setup_ui()

    def _load_logo(self):
        from PIL import Image
        logo_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "assets", "logo-prism.png")
        try:
            pil_logo = Image.open(logo_path)
            h = 60
            w = int(pil_logo.width * (h / pil_logo.height))
            self.logo_image = ctk.CTkImage(light_image=pil_logo, dark_image=pil_logo, size=(w, h))
        except Exception:
            pass

    def _setup_ui(self):
        if self.logo_image:
            self.logo_img_label = ctk.CTkLabel(self, image=self.logo_image, text="")
            self.logo_img_label.pack(pady=(20, 0))

        self.logo_label = ctk.CTkLabel(self, text="Flycast Prism Editor", font=ctk.CTkFont(family="Inter", size=18, weight="bold"))
        self.logo_label.pack(pady=(5, 20), padx=20)

        self.open_button = ctk.CTkButton(self, text="OPEN EXR", command=lambda: self.callbacks.get('on_open_click', lambda: None)(),
                                         height=45, font=ctk.CTkFont(size=13, weight="bold"))
        self.open_button.pack(pady=10, padx=20, fill="x")

        # Magnifier Panel
        self.magnifier_frame = ctk.CTkFrame(self, fg_color="#1a1a1a", corner_radius=8, border_width=1, border_color="#333333", height=360)
        self.magnifier_frame.pack(pady=10, padx=20, fill="x")
        self.magnifier_frame.pack_propagate(False)
        
        ctk.CTkLabel(self.magnifier_frame, text="PIXEL-PERFECT MAGNIFIER (1:1)", font=ctk.CTkFont(size=10, weight="bold"), text_color="#777777").pack(pady=(5, 0))
        
        self.magnifier_label = ctk.CTkLabel(self.magnifier_frame, text="", fg_color="black", width=240, height=240)
        self.magnifier_label.pack(pady=10, padx=10)
        
        self.info_grid_frame = ctk.CTkFrame(self.magnifier_frame, fg_color="transparent")
        self.info_grid_frame.pack(pady=(0, 10), padx=10, fill="x")
        
        self.value_info_label = ctk.CTkLabel(self.info_grid_frame, text="HOVER OVER IMAGE", font=ctk.CTkFont(family="Consolas", size=11), text_color="#777777")
        self.value_info_label.grid(row=0, column=0, columnspan=2, sticky="ew")

        # Appearance mode
        self.appearance_mode_label = ctk.CTkLabel(self, text="Appearance Mode:", anchor="w")
        self.appearance_mode_label.pack(pady=(10, 0), padx=20, fill="x")
        self.appearance_mode_optionemenu = ctk.CTkOptionMenu(self, values=["System", "Dark", "Light"],
                                                             command=self.callbacks.get('on_appearance_change'))
        self.appearance_mode_optionemenu.pack(pady=(0, 10), padx=20, fill="x")
        self.appearance_mode_optionemenu.set("System")

        # Inspector Section (Bottom)
        self.inspector_container = ctk.CTkFrame(self, fg_color="transparent")
        self.inspector_container.pack(side="bottom", fill="x", padx=20, pady=(0, 10))

        self.copy_all_btn = ctk.CTkButton(self.inspector_container, text="COPY ALL VALUES", command=self.callbacks.get('on_copy_all'), 
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

    def update_info_table(self, data):
        if not hasattr(self, "_info_labels"):
            self._info_labels = {}
            self._info_empty_label = None

        if not data:
            for lbls in self._info_labels.values():
                lbls[0].grid_remove()
                lbls[1].grid_remove()
            
            if not self._info_empty_label:
                self._info_empty_label = ctk.CTkLabel(self.info_grid_frame, text="HOVER OVER IMAGE", font=ctk.CTkFont(family="Consolas", size=11), text_color="#777777")
                self._info_empty_label.grid(row=0, column=0, columnspan=2, sticky="ew")
            else:
                self._info_empty_label.grid()
            return

        if self._info_empty_label:
            self._info_empty_label.grid_remove()

        for i, (key, val) in enumerate(data.items()):
            if key not in self._info_labels:
                k_lbl = ctk.CTkLabel(self.info_grid_frame, text=f"{key}:", font=ctk.CTkFont(family="Consolas", size=10, weight="bold"), 
                                     text_color="#aaaaaa", anchor="w")
                v_lbl = ctk.CTkLabel(self.info_grid_frame, text=val, font=ctk.CTkFont(family="Consolas", size=10), 
                                     text_color="#3498db", anchor="w")
                self._info_labels[key] = (k_lbl, v_lbl)
            
            k_lbl, v_lbl = self._info_labels[key]
            v_lbl.configure(text=val)
            k_lbl.grid(row=i, column=0, sticky="w", padx=(0, 10))
            v_lbl.grid(row=i, column=1, sticky="w")
            
        # Remove any labels that are no longer in data
        for key in list(self._info_labels.keys()):
            if key not in data:
                k_lbl, v_lbl = self._info_labels.pop(key)
                k_lbl.destroy()
                v_lbl.destroy()

    def update_inspect_table(self, data):
        for child in self.pixel_inspect_frame.winfo_children():
            child.destroy()
        for child in self.poly_inspect_frame.winfo_children():
            child.destroy()
        
        if not data:
            self.pixel_placeholder = ctk.CTkLabel(self.pixel_inspect_frame, text="CLICK ON IMAGE TO INSPECT", font=ctk.CTkFont(family="Consolas", size=11), text_color="#777777")
            self.pixel_placeholder.pack(pady=10)
            self.poly_placeholder = ctk.CTkLabel(self.poly_inspect_frame, text="CLICK ON IMAGE TO INSPECT", font=ctk.CTkFont(family="Consolas", size=11), text_color="#777777")
            self.poly_placeholder.pack(pady=10)
            self.copy_all_btn.configure(state="disabled")
            return

        self.copy_all_btn.configure(state="normal")
        ctk.CTkLabel(self.pixel_inspect_frame, text="PIXEL LEVEL", font=ctk.CTkFont(size=10, weight="bold"), text_color="#777777").pack(pady=(5, 0))
        pixel_grid = ctk.CTkFrame(self.pixel_inspect_frame, fg_color="transparent")
        pixel_grid.pack(pady=5, padx=10, fill="x")
        
        ctk.CTkLabel(self.poly_inspect_frame, text="POLY LEVEL", font=ctk.CTkFont(size=10, weight="bold"), text_color="#777777").pack(pady=(5, 0))
        poly_grid = ctk.CTkFrame(self.poly_inspect_frame, fg_color="transparent")
        poly_grid.pack(pady=5, padx=10, fill="x")

        pixel_keys = ["RGB", "Normals", "Depth", "HUD"]
        poly_keys = ["MatID", "MatList", "MatFlags", "WorldPos", "TexHash", "PolyCnt"]

        p_row, py_row = 0, 0
        for key, val in data.items():
            if key in pixel_keys:
                grid, row = pixel_grid, p_row
                p_row += 1
            else:
                grid, row = poly_grid, py_row
                py_row += 1
                
            k_lbl = ctk.CTkLabel(grid, text=f"{key}:", font=ctk.CTkFont(family="Consolas", size=10, weight="bold"), text_color="#aaaaaa", anchor="w")
            k_lbl.grid(row=row, column=0, sticky="w", padx=(0, 10))
            v_lbl = ctk.CTkLabel(grid, text=val, font=ctk.CTkFont(family="Consolas", size=10), text_color="#2ecc71", anchor="w")
            v_lbl.grid(row=row, column=1, sticky="w")
