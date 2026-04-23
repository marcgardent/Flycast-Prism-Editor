import os
from platformdirs import user_pictures_dir

class AppState:
    def __init__(self):
        # Application State
        self.current_exr_data = {}
        self.available_channels = []
        self.image_size = (0, 0)
        self.last_numpy_image = None
        self.view_cache = {}
        self.full_pil_image = None
        self.current_view_mode = "Composite (RGB)"
        self.magnifier_size = 240
        self.display_size = (0, 0)
        self.default_dir = user_pictures_dir()
        self.current_pixel_value = "N/A"
        self.last_clicked_event = None
        self.is_loading = False
        self.expression_mask = None

        # HUD Compositor State
        self.hud_rects = []
        self.selected_rect_idx = -1
        self.drag_mode = None # None, 'move', 'nw', 'ne', 'sw', 'se'
        self.drag_start_orig = None
        self.drag_rect_start = None
        self.hud_workspace = "SOURCE"
        self.current_hud_path = None
