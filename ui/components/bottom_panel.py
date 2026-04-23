import customtkinter as ctk

class BottomPanelComponent(ctk.CTkFrame):
    def __init__(self, master, callbacks, **kwargs):
        super().__init__(master, height=280, corner_radius=0, border_width=1, border_color="#222222", **kwargs)
        self.callbacks = callbacks
        self.pack_propagate(False) # Keep fixed height
        self._setup_ui()

    def _setup_ui(self):
        self.bottom_tabs = ctk.CTkTabview(self)
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
        
        self.pixel_req_btn = ctk.CTkButton(tab_pixel, text="EVALUATE", command=lambda: self.callbacks.get('on_eval_pixel', lambda x: None)(self.pixel_req_entry.get("0.0", "end")), width=120)
        self.pixel_req_btn.pack(side="right", padx=10, pady=10)
        
        # Setup Poly Request Tab
        self.poly_req_entry = ctk.CTkTextbox(tab_poly, font=ctk.CTkFont(family="Consolas", size=12), border_width=1, border_color="#333333")
        self.poly_req_entry.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        self.poly_req_entry.insert("0.0", "# Enter Poly Request here...\n")
        
        self.poly_req_btn = ctk.CTkButton(tab_poly, text="EVALUATE", command=lambda: self.callbacks.get('on_eval_poly', lambda x: None)(self.poly_req_entry.get("0.0", "end")), width=120)
        self.poly_req_btn.pack(side="right", padx=10, pady=10)

        self.poly_clear_btn = ctk.CTkButton(tab_poly, text="CLEAR", command=self.callbacks.get('on_clear_mask'), width=80, fg_color="#C0392B", hover_color="#922B21")
        self.poly_clear_btn.pack(side="right", padx=10, pady=10)

    def log(self, text, clear=False):
        if clear: self.info_box.delete("0.0", "end")
        self.info_box.insert("end", f"> {text}\n")
        self.info_box.see("end")
        print(text)
