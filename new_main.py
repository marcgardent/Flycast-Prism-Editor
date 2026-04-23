import sys
import customtkinter as ctk

from ui.main_window import MainWindow
from controllers.main_controller import MainController
from controllers.interaction_controller import InteractionController
from controllers.hud_controller import HUDController

class FlycastApp:
    def __init__(self):
        # We need to create the UI but also pass callbacks to it. 
        # A common pattern is to create the controller first, but the controller needs the UI.
        # We use a two-step initialization.
        
        # 1. Define the callback dictionary that the UI will use
        self.callbacks = {}
        
        # 2. Instantiate the UI components with the empty/partial callbacks dict
        self.ui = MainWindow(self.callbacks)
        
        # 3. Instantiate controllers
        self.main_ctrl = MainController(self.ui)
        self.interaction_ctrl = InteractionController(self.main_ctrl)
        self.hud_ctrl = HUDController(self.main_ctrl)
        
        # 4. Populate the callbacks that UI components expect
        self.callbacks['on_open_click'] = self.main_ctrl.on_open_click
        self.callbacks['on_cancel'] = self.main_ctrl.on_cancel
        self.callbacks['on_resize'] = lambda event: self.main_ctrl.refresh_image_display()
        
        # Interaction callbacks
        self.callbacks['on_mouse_down'] = self.interaction_ctrl.on_mouse_down
        self.callbacks['on_mouse_move'] = self.interaction_ctrl.on_mouse_move
        self.callbacks['on_mouse_drag'] = self.interaction_ctrl.on_mouse_move
        self.callbacks['on_mouse_up'] = self.interaction_ctrl.on_mouse_up
        self.callbacks['on_mouse_leave'] = self.interaction_ctrl.on_mouse_leave
        
        # Missing Sidebar buttons
        self.callbacks['on_copy_all'] = lambda: self.main_ctrl.log("TODO: on_copy_all")
        self.callbacks['on_copy_poly_json'] = lambda: self.main_ctrl.log("TODO: on_copy_poly_json")
        
        # Others can be added here...
        # self.callbacks['on_tab_changed'] = ...
        
        # Global CTK Theme
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")
        
    def run(self):
        self.ui.mainloop()

if __name__ == "__main__":
    # Handle DPI awareness before creating UI
    try:
        if sys.platform.startswith("win"):
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        pass

    try:
        ctk.DrawEngine.preferred_drawing_method = "circle_shapes"
    except AttributeError:
        pass

    app = FlycastApp()
    app.run()
