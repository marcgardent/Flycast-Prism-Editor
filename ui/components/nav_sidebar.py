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
        
        # Additional UI elements will be populated by controllers or dynamically
