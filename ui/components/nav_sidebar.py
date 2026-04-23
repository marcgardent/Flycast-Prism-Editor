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
        
        self.composite_buttons = {}
        from constants import Channels
        self.composite_buttons["Composite (RGB)"] = self._add_view_button(self.composite_frame, "Composite (RGB)")
        self.composite_buttons["Normal Map"] = self._add_view_button(self.composite_frame, "Normal Map")
        self.composite_buttons["HUD (RGBA)"] = self._add_view_button(self.composite_frame, "HUD (RGBA)")
        self.composite_buttons["Metadata"] = self._add_view_button(self.composite_frame, Channels.COMBINED_METADATA)
        
        # Tabview
        self.tabview = ctk.CTkTabview(self, width=300, command=lambda: self.callbacks.get('on_tab_changed', lambda: None)())
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
        self.channel_buttons = []

    def _add_view_button(self, parent, text):
        btn = ctk.CTkButton(parent, text=text, command=lambda t=text: self.callbacks.get('on_view_mode_change', lambda m: None)(t),
                            anchor="w", height=38, fg_color="transparent", border_width=1, 
                            border_color="#3d3d3d", hover_color="#2c3e50", font=ctk.CTkFont(size=12))
        btn.pack(fill="x", pady=4)
        return btn

    def update_channel_buttons(self, available_channels, standard_channels):
        for btn in self.channel_buttons:
            btn.destroy()
        self.channel_buttons = []

        for name in sorted(available_channels):
            is_std = name in standard_channels
            bg_color = "#2980b9" if is_std else "#34495e"
            btn = ctk.CTkButton(self.channels_scroll, text=f" {'★' if is_std else ' '} {name}",
                                command=lambda n=name: self.callbacks.get('on_view_mode_change', lambda m: None)(n),
                                anchor="w", height=30, fg_color=bg_color)
            btn.pack(fill="x", pady=2)
            self.channel_buttons.append(btn)

    def update_hud_list(self, hud_rects, selected_rect_idx):
        for child in self.hud_list_frame.winfo_children():
            child.destroy()
        
        for i, r in enumerate(hud_rects):
            is_sel = (i == selected_rect_idx)
            btn = ctk.CTkButton(self.hud_list_frame, text=r["name"], 
                                fg_color="#f1c40f" if is_sel else "transparent",
                                text_color="white" if is_sel else "#aaaaaa",
                                hover_color="#f39c12" if is_sel else "#333333",
                                anchor="w", height=28,
                                command=lambda idx=i: self.callbacks.get('on_hud_select', lambda x: None)(idx))
            btn.pack(fill="x", pady=1)
