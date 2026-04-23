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
        
        # Link controllers to main controller so they can cross-reference
        self.main_ctrl.interaction_ctrl = self.interaction_ctrl
        self.main_ctrl.hud_ctrl = self.hud_ctrl
        
        # 4. Populate the callbacks that UI components expect
        self.callbacks['on_open_click'] = self.main_ctrl.on_open_click
        self.callbacks['on_cancel'] = self.main_ctrl.on_cancel
        self.callbacks['on_resize'] = lambda event=None: self.main_ctrl.refresh_image_display()
        
        # Interaction callbacks
        self.callbacks['on_mouse_down'] = self.interaction_ctrl.on_mouse_down
        self.callbacks['on_mouse_move'] = self.interaction_ctrl.on_mouse_move
        self.callbacks['on_mouse_drag'] = self.interaction_ctrl.on_mouse_move
        self.callbacks['on_mouse_up'] = self.interaction_ctrl.on_mouse_up
        self.callbacks['on_mouse_leave'] = self.interaction_ctrl.on_mouse_leave
        
        # Missing Sidebar buttons
        self.callbacks['on_copy_all'] = lambda: self.main_ctrl.log("TODO: on_copy_all")
        self.callbacks['on_copy_poly_json'] = lambda: self.main_ctrl.log("TODO: on_copy_poly_json")
        
        # Requests
        self.callbacks['on_eval_poly'] = self.main_ctrl.on_eval_poly
        self.callbacks['on_eval_pixel'] = self.main_ctrl.on_eval_pixel
        self.callbacks['on_clear_mask'] = self.main_ctrl.on_clear_mask
        
        # View mode change
        self.callbacks['on_view_mode_change'] = self.main_ctrl.safe_update_view_mode
        
        # HUD Compositor callbacks
        self.callbacks['on_hud_workspace_changed'] = self.hud_ctrl.on_workspace_changed
        self.callbacks['on_hud_select'] = self.hud_ctrl.select_hud_rect
        self.callbacks['on_hud_rename'] = self.hud_ctrl.rename_selected_rect
        self.callbacks['on_hud_zen_toggle'] = self.hud_ctrl.toggle_zen_mode
        self.callbacks['on_hud_delete'] = self.hud_ctrl.delete_selected_rect
        self.callbacks['on_hud_load'] = self.hud_ctrl.load_hud_json
        self.callbacks['on_hud_save'] = self.hud_ctrl.save_hud_json
        self.callbacks['on_hud_save_as'] = self.hud_ctrl.save_hud_json_as
        
        # UI Tab change
        self.callbacks['on_tab_changed'] = lambda: self.main_ctrl.refresh_image_display()
        self.callbacks['on_space'] = self.hud_ctrl.toggle_workspace
        
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
