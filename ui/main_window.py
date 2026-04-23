import customtkinter as ctk
import sys

from .components.sidebar import SidebarComponent
from .components.nav_sidebar import NavSidebarComponent
from .components.image_area import ImageAreaComponent
from .components.bottom_panel import BottomPanelComponent

class MainWindow(ctk.CTk):
    def __init__(self, callbacks):
        super().__init__()
        self.callbacks = callbacks
        
        self.title("Flycast Prism Editor")
        self.geometry("1500x900")
        self.minsize(1200, 800)

        # Scale config
        try:
            scaling_factor = self.winfo_fpixels('1i') / 96.0
            ctk.set_widget_scaling(scaling_factor)
            ctk.set_window_scaling(scaling_factor)
        except Exception:
            pass

        self.after(200, self._maximize_window)
        self._setup_grid()
        self._instantiate_components()

    def _setup_grid(self):
        self.grid_columnconfigure(0, weight=0, minsize=350)
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(2, weight=0, minsize=320)
        self.grid_rowconfigure(0, weight=1)

    def _instantiate_components(self):
        # Left Sidebar
        self.sidebar = SidebarComponent(self, self.callbacks)
        self.sidebar.pack_propagate(False)
        self.sidebar.grid(row=0, column=0, sticky="nsew")

        # Center Area
        self.center_container = ctk.CTkFrame(self, fg_color="transparent", corner_radius=0)
        self.center_container.grid(row=0, column=1, sticky="nsew")
        
        self.image_area = ImageAreaComponent(self.center_container, self.callbacks)
        self.image_area.pack(fill="both", expand=True)
        
        self.bottom_panel = BottomPanelComponent(self.center_container, self.callbacks)
        self.bottom_panel.pack(side="bottom", fill="x")

        # Right Navigation Sidebar
        self.nav_sidebar = NavSidebarComponent(self, self.callbacks)
        self.nav_sidebar.grid(row=0, column=2, sticky="nsew")

        # Initially hide sidebars for splash screen
        self.set_ui_visibility(False)
        
        self.bind("<Configure>", self.callbacks.get('on_resize'))
        self.bind("<space>", self.callbacks.get('on_space'))

    def set_ui_visibility(self, visible):
        if visible:
            self.nav_sidebar.grid()
            self.sidebar.grid()
            self.image_area.hide_splash()
        else:
            self.nav_sidebar.grid_remove()
            self.sidebar.grid_remove()
            self.image_area.show_splash()

    def _maximize_window(self):
        try:
            if sys.platform.startswith("win"):
                self.state("zoomed")
            else:
                self.attributes("-zoomed", True)
                try:
                    self.state("zoomed")
                except:
                    pass
        except Exception as e:
            print(f"Maximization failed: {e}")
