import customtkinter as ctk

class NavSidebarComponent(ctk.CTkFrame):
    def __init__(self, master, callbacks, **kwargs):
        super().__init__(master, width=320, corner_radius=0, border_width=1, border_color="#222222", **kwargs)
        self.callbacks = callbacks
        self._setup_ui()

    def _setup_ui(self):
        # Composite Modes
        ctk.CTkLabel(self, text="COMPOSITE MODES", font=ctk.CTkFont(size=13, weight="bold")).pack(pady=(20, 5))
        self.composite_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.composite_frame.pack(fill="x", padx=10)
        
        # Tabview
        self.tabview = ctk.CTkTabview(self, width=300, command=self.callbacks.get('on_tab_changed'))
        self.tabview.pack(pady=(10, 20), padx=10, fill="both", expand=True)

        self.gbuffer_tab = self.tabview.add("G-Buffer Viewer")
        self.poly_routing_tab = self.tabview.add("Poly Routing")
        self.hud_compositor_tab = self.tabview.add("HUD Compositor")

        # Configure tabs
        self.tabview.tab("G-Buffer Viewer").grid_columnconfigure(0, weight=1)
        self.tabview.tab("Poly Routing").grid_columnconfigure(0, weight=1)
        self.tabview.tab("HUD Compositor").grid_columnconfigure(0, weight=1)
        
        self._setup_poly_routing_tab()
        self._setup_hud_compositor_tab()
        self._setup_gbuffer_tab()

    def _setup_poly_routing_tab(self):
        ctk.CTkLabel(self.poly_routing_tab, text="ANNOTATION", font=ctk.CTkFont(size=11, weight="bold")).pack(pady=(10, 0), padx=20, anchor="w")
        self.poly_name_entry = ctk.CTkEntry(self.poly_routing_tab, height=30)
        self.poly_name_entry.insert(0, "my annotation")
        self.poly_name_entry.pack(pady=(0, 10), padx=15, fill="x")
        self.poly_name_entry.bind("<KeyRelease>", lambda e: self.callbacks.get('on_poly_name_change', lambda: None)())

        ctk.CTkLabel(self.poly_routing_tab, text="ROUTING JSON (AUTO-UPDATE)", font=ctk.CTkFont(size=11, weight="bold")).pack(pady=(10, 0), padx=20, anchor="w")
        self.poly_json_box = ctk.CTkTextbox(self.poly_routing_tab, height=150, font=ctk.CTkFont(family="Courier", size=12))
        self.poly_json_box.pack(pady=(0, 10), padx=15, fill="x")

        self.copy_json_button = ctk.CTkButton(self.poly_routing_tab, text="COPY JSON", command=lambda: self.callbacks.get('on_copy_poly_json', lambda: None)())
        self.copy_json_button.pack(pady=10, padx=15, fill="x")

    def _setup_hud_compositor_tab(self):
        self.hud_mode_btn = ctk.CTkSegmentedButton(self.hud_compositor_tab, values=["SOURCE", "DESTINATION"],
                                                  command=lambda v: self.callbacks.get('on_hud_workspace_changed', lambda x: None)(v),
                                                  height=35, font=ctk.CTkFont(weight="bold"))
        self.hud_mode_btn.set("SOURCE")
        self.hud_mode_btn.pack(pady=15, padx=15, fill="x")

        self.hud_list_frame = ctk.CTkScrollableFrame(self.hud_compositor_tab, height=220, fg_color="#1e1e1e", corner_radius=8)
        self.hud_list_frame.pack(fill="x", padx=10, pady=5)
        
        self.hud_name_var = ctk.StringVar()
        self.hud_name_entry = ctk.CTkEntry(self.hud_compositor_tab, textvariable=self.hud_name_var, placeholder_text="Rectangle name...")
        self.hud_name_entry.pack(pady=5, padx=15, fill="x")
        self.hud_name_var.trace_add("write", lambda *args: self.callbacks.get('on_hud_rename', lambda: None)())

        self.hud_zen_var = ctk.BooleanVar()
        self.hud_zen_checkbox = ctk.CTkCheckBox(self.hud_compositor_tab, text="Zen Mode", 
                                               variable=self.hud_zen_var, command=lambda: self.callbacks.get('on_hud_zen_toggle', lambda: None)())
        self.hud_zen_checkbox.pack(pady=5, padx=15, anchor="w")

        self.delete_rect_btn = ctk.CTkButton(self.hud_compositor_tab, text="DELETE", command=lambda: self.callbacks.get('on_hud_delete', lambda: None)(), fg_color="#c0392b", hover_color="#e74c3c")
        self.delete_rect_btn.pack(pady=5, padx=15, fill="x")
        self.delete_rect_btn.configure(state="disabled")

        self.hud_path_label = ctk.CTkLabel(self.hud_compositor_tab, text="No file opened", 
                                          font=ctk.CTkFont(size=10), text_color="#777777", wraplength=180)
        self.hud_path_label.pack(pady=(10, 0), padx=15, fill="x")

        self.load_hud_btn = ctk.CTkButton(self.hud_compositor_tab, text="LOAD JSON", command=lambda: self.callbacks.get('on_hud_load', lambda: None)())
        self.load_hud_btn.pack(pady=5, padx=15, fill="x")

        self.save_hud_btn = ctk.CTkButton(self.hud_compositor_tab, text="SAVE", command=lambda: self.callbacks.get('on_hud_save', lambda: None)())
        self.save_hud_btn.pack(pady=5, padx=15, fill="x")
        self.save_hud_btn.configure(state="disabled")

        self.save_as_hud_btn = ctk.CTkButton(self.hud_compositor_tab, text="SAVE AS", command=lambda: self.callbacks.get('on_hud_save_as', lambda: None)())
        self.save_as_hud_btn.pack(pady=(5, 10), padx=15, fill="x")

    def _setup_gbuffer_tab(self):
        ctk.CTkLabel(self.gbuffer_tab, text="CHANNELS (BLUE = STANDARD)", font=ctk.CTkFont(size=13, weight="bold")).pack(pady=(25, 5))
        self.channels_scroll = ctk.CTkScrollableFrame(self.gbuffer_tab, height=350, fg_color="transparent")
        self.channels_scroll.pack(fill="both", expand=True, padx=15, pady=5)
