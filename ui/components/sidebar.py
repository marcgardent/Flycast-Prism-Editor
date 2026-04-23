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

        self.open_button = ctk.CTkButton(self, text="OPEN EXR", command=self.callbacks.get('on_open_click'),
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
