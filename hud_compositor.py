from PIL import ImageDraw, ImageOps
from enum import Enum, auto

class Anchor(Enum):
    SCREEN_TOP_LEFT = auto()
    SCREEN_TOP_MID = auto()
    SCREEN_TOP_RIGHT = auto()
    SCREEN_LEFT_MID = auto()
    SCREEN_CENTER = auto()
    SCREEN_RIGHT_MID = auto()
    SCREEN_BOTTOM_LEFT = auto()
    SCREEN_BOTTOM_MID = auto()
    SCREEN_BOTTOM_RIGHT = auto()
    SAFE_ZONE_TOP_LEFT = auto()
    SAFE_ZONE_TOP_MID = auto()
    SAFE_ZONE_TOP_RIGHT = auto()
    SAFE_ZONE_LEFT_MID = auto()
    SAFE_ZONE_RIGHT_MID = auto()
    SAFE_ZONE_BOTTOM_LEFT = auto()
    SAFE_ZONE_BOTTOM_MID = auto()
    SAFE_ZONE_BOTTOM_RIGHT = auto()

class HudCompositor:
    VIRT_W = 640
    VIRT_H = 480
    PADDING = 50 # Marge intérieure pour éviter le clipping des losanges

    @staticmethod
    def get_anchor_table(screenW, screenH):
        scale = screenH / HudCompositor.VIRT_H
        safeW = HudCompositor.VIRT_W * scale
        safeX = (screenW - safeW) / 2.0

        return {
            Anchor.SCREEN_TOP_LEFT:      (0, 0),
            Anchor.SCREEN_TOP_MID:       (screenW / 2.0, 0),
            Anchor.SCREEN_TOP_RIGHT:     (screenW, 0),
            Anchor.SCREEN_LEFT_MID:      (0, screenH / 2.0),
            Anchor.SCREEN_CENTER:        (screenW / 2.0, screenH / 2.0),
            Anchor.SCREEN_RIGHT_MID:     (screenW, screenH / 2.0),
            Anchor.SCREEN_BOTTOM_LEFT:   (0, screenH),
            Anchor.SCREEN_BOTTOM_MID:    (screenW / 2.0, screenH),
            Anchor.SCREEN_BOTTOM_RIGHT:  (screenW, screenH),
            Anchor.SAFE_ZONE_TOP_LEFT:     (safeX, 0),
            Anchor.SAFE_ZONE_TOP_MID:      (screenW / 2.0, 0),
            Anchor.SAFE_ZONE_TOP_RIGHT:    (safeX + safeW, 0),
            Anchor.SAFE_ZONE_LEFT_MID:     (safeX, screenH / 2.0),
            Anchor.SAFE_ZONE_RIGHT_MID:    (safeX + safeW, screenH / 2.0),
            Anchor.SAFE_ZONE_BOTTOM_LEFT:  (safeX, screenH),
            Anchor.SAFE_ZONE_BOTTOM_MID:   (screenW / 2.0, screenH),
            Anchor.SAFE_ZONE_BOTTOM_RIGHT: (safeX + safeW, screenH)
        }

    @staticmethod
    def draw_diamond(draw, center, size=10, color="green"):
        x, y = center
        points = [
            (x, y - size), # Top
            (x + size, y), # Right
            (x, y + size), # Bottom
            (x - size, y)  # Left
        ]
        draw.polygon(points, outline=color, fill=None, width=2)

    @staticmethod
    def draw_overlay(pil_image):
        # On crée une nouvelle image avec du padding pour que les losanges aux bords soient visibles
        padded_img = ImageOps.expand(pil_image, border=HudCompositor.PADDING, fill=(10, 10, 10)) # Fond très sombre pour le padding
        draw = ImageDraw.Draw(padded_img)
        
        orig_w, orig_h = pil_image.size
        p = HudCompositor.PADDING
        
        # 1. Safe Zone Rectangle (calculté sur dimensions originales, dessiné avec offset)
        scale = orig_h / HudCompositor.VIRT_H
        safeW = HudCompositor.VIRT_W * scale
        safeX = (orig_w - safeW) / 2.0
        
        rect = [safeX + p, p, safeX + safeW + p, orig_h + p]
        draw.rectangle(rect, outline="#00ff00", width=3)
        
        # 2. Anchors
        anchors = HudCompositor.get_anchor_table(orig_w, orig_h)
        
        for anchor, pos in anchors.items():
            # Offset par le padding
            draw_pos = (pos[0] + p, pos[1] + p)
            
            # Green for safe zone anchors, Purple (Mauve) for screen anchors
            if "SAFE_ZONE" in anchor.name:
                color = "#00ff00" # Green
            else:
                color = "#9b59b6" # Purple (Amethyst/Mauve)
                
            HudCompositor.draw_diamond(draw, draw_pos, size=12, color=color)
            
        return padded_img
