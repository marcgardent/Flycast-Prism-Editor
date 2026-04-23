import customtkinter as ctk

class ImageAreaComponent(ctk.CTkFrame):
    def __init__(self, master, callbacks, **kwargs):
        super().__init__(master, fg_color="#050505", corner_radius=0, **kwargs)
        self.callbacks = callbacks
        self._setup_ui()

    def _setup_ui(self):
        self.display_label = ctk.CTkLabel(self, text="", cursor="crosshair")
        self.display_label.place(relx=0.5, rely=0.5, anchor="center")

        # Bind events using late binding (lambdas)
        self.display_label.bind("<Motion>", lambda e: self.callbacks.get('on_mouse_move', lambda ev: None)(e))
        self.display_label.bind("<Button-1>", lambda e: self.callbacks.get('on_mouse_down', lambda ev: None)(e))
        self.display_label.bind("<B1-Motion>", lambda e: self.callbacks.get('on_mouse_drag', lambda ev: None)(e))
        self.display_label.bind("<ButtonRelease-1>", lambda e: self.callbacks.get('on_mouse_up', lambda ev: None)(e))
        self.display_label.bind("<Leave>", lambda e: self.callbacks.get('on_mouse_leave', lambda ev: None)(e))

        # Loading Overlay
        self.loading_overlay = ctk.CTkFrame(self, fg_color="#1a1a1a", corner_radius=15, border_width=2)
        self.loading_label = ctk.CTkLabel(self.loading_overlay, text="PROCESSING...",
                                          font=ctk.CTkFont(family="Inter", size=16, weight="bold"))
        self.loading_label.pack(pady=(20, 10), padx=30)
        self.progress_bar = ctk.CTkProgressBar(self.loading_overlay, orientation="horizontal", width=250)
        self.progress_bar.pack(pady=(0, 15), padx=30)
        self.progress_bar.configure(mode="indeterminate")

        self.cancel_button = ctk.CTkButton(self.loading_overlay, text="CANCEL", command=self.callbacks.get('on_cancel'), width=100, height=28)
        self.cancel_button.pack(pady=(0, 20))

        # Splash Screen
        self.splash_frame = ctk.CTkFrame(self, fg_color="transparent")
        import os
        from PIL import Image

        self.splash_logo = ctk.CTkLabel(self.splash_frame, text="")
        
        logo_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "assets", "logo-prism.png")
        if os.path.exists(logo_path):
            try:
                pil_logo = Image.open(logo_path)
                h = 100
                w = int(pil_logo.width * (h / pil_logo.height))
                self.logo_image = ctk.CTkImage(light_image=pil_logo, dark_image=pil_logo, size=(w, h))
                self.splash_logo.configure(image=self.logo_image)
            except Exception as e:
                pass
                
        self.splash_logo.pack(pady=20)
        
        self.splash_btn = ctk.CTkButton(self.splash_frame, text="OPEN EXR FILE", command=lambda: self.callbacks.get('on_open_click', lambda: None)(),
                                        width=300, height=60, font=ctk.CTkFont(size=16, weight="bold"))
        self.splash_btn.pack(pady=20)

        self.splash_hint = ctk.CTkLabel(self.splash_frame, text="Drag & drop or click to start", 
                                        font=ctk.CTkFont(size=12), text_color="#555555")
        self.splash_hint.pack()

    def show_loading(self, message="PROCESSING..."):
        self.loading_label.configure(text=message)
        self.loading_overlay.place(relx=0.5, rely=0.5, anchor="center")
        self.progress_bar.start()

    def hide_loading(self):
        self.loading_overlay.place_forget()
        self.progress_bar.stop()
        
    def show_splash(self):
        self.splash_frame.place(relx=0.5, rely=0.5, anchor="center")
        
    def hide_splash(self):
        self.splash_frame.place_forget()
