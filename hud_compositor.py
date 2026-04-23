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
    def draw_dotted_line(draw, p1, p2, color="white", width=1, dash_length=5):
        x1, y1 = p1
        x2, y2 = p2
        dist = ((x2 - x1)**2 + (y2 - y1)**2)**0.5
        if dist == 0: return
        
        dx, dy = (x2 - x1) / dist, (y2 - y1) / dist
        for i in range(0, int(dist), dash_length * 2):
            start = (x1 + dx * i, y1 + dy * i)
            end = (x1 + dx * min(dist, i + dash_length), y1 + dy * min(dist, i + dash_length))
            draw.line([start, end], fill=color, width=width)

    @staticmethod
    def draw_dotted_rect(draw, rect, color="white", width=1, dash_length=5):
        x1, y1, x2, y2 = rect
        # Draw 4 segments
        HudCompositor.draw_dotted_line(draw, (x1, y1), (x2, y1), color, width, dash_length)
        HudCompositor.draw_dotted_line(draw, (x2, y1), (x2, y2), color, width, dash_length)
        HudCompositor.draw_dotted_line(draw, (x2, y2), (x1, y2), color, width, dash_length)
        HudCompositor.draw_dotted_line(draw, (x1, y2), (x1, y1), color, width, dash_length)

    @staticmethod
    def draw_diamond(draw, center, size=10, color="green", fill=None):
        x, y = center
        points = [
            (x, y - size), # Top
            (x + size, y), # Right
            (x, y + size), # Bottom
            (x - size, y)  # Left
        ]
        draw.polygon(points, outline=color, fill=fill, width=2)

    @staticmethod
    def draw_overlay(pil_image, user_rects=None, selected_idx=-1, mode="SOURCE"):
        # On crée une nouvelle image avec du padding pour que les losanges aux bords soient visibles
        padded_img = ImageOps.expand(pil_image, border=HudCompositor.PADDING, fill=(10, 10, 10)) # Fond très sombre pour le padding
        draw = ImageDraw.Draw(padded_img)
        
        orig_w, orig_h = pil_image.size
        p = HudCompositor.PADDING
        
        # Scale line thickness based on resolution to keep it consistent
        base_h = 1080.0
        scale_factor = max(1.0, orig_h / base_h)
        line_w = int(round(3 * scale_factor))
        thin_w = int(round(1 * scale_factor))
        diamond_size = int(round(12 * scale_factor))
        handle_size = int(round(6 * scale_factor))
        
        # 1. Safe Zone Rectangle (SOURCE only)
        if mode == "SOURCE":
            scale = orig_h / HudCompositor.VIRT_H
            safeW = HudCompositor.VIRT_W * scale
            safeX = (orig_w - safeW) / 2.0
            
            rect = [safeX + p, p, safeX + safeW + p, orig_h + p]
            draw.rectangle(rect, outline="#00ff00", width=line_w)
        
        # 2. Anchors (DESTINATION only)
        anchors = HudCompositor.get_anchor_table(orig_w, orig_h)
        if mode == "DESTINATION":
            for anchor, pos in anchors.items():
                draw_pos = (pos[0] + p, pos[1] + p)
                
                # Check if this anchor is assigned to the selected rectangle
                is_active_anchor = False
                if selected_idx != -1:
                    active_r = user_rects[selected_idx]
                    if active_r.get("anchor") == anchor:
                        is_active_anchor = True
                
                if "SAFE_ZONE" in anchor.name:
                    color = "#00ff00" # Green
                else:
                    color = "#9b59b6" # Purple
                
                fill_color = color if is_active_anchor else None
                HudCompositor.draw_diamond(draw, draw_pos, size=diamond_size, color=color, fill=fill_color)
            
        # 3. User Rectangles
        if user_rects:
            # Overlap detection
            overlapping_indices = set()
            for i in range(len(user_rects)):
                for j in range(i + 1, len(user_rects)):
                    r1, r2 = user_rects[i], user_rects[j]
                    x1 = r1["sx"] if mode == "SOURCE" else r1["dx"]
                    y1 = r1["sy"] if mode == "SOURCE" else r1["dy"]
                    x2 = r2["sx"] if mode == "SOURCE" else r2["dx"]
                    y2 = r2["sy"] if mode == "SOURCE" else r2["dy"]
                    
                    if not (x1 + r1["w"] <= x2 or x2 + r2["w"] <= x1 or 
                            y1 + r1["h"] <= y2 or y2 + r2["h"] <= y1):
                        overlapping_indices.add(i)
                        overlapping_indices.add(j)

            for i, r in enumerate(user_rects):
                is_selected = (i == selected_idx)
                is_overlapping = (i in overlapping_indices)
                is_zen = r.get("zen", False)
                
                # Color Coding
                if is_zen:
                    color = "#1abc9c" if is_selected else "#3498db" # Teal if selected, Blue otherwise
                else:
                    color = "#f1c40f" if is_selected else "#e67e22" # Yellow if selected, Orange otherwise
                
                width = line_w if is_selected else thin_w * 2
                
                # Use sx/sy for SOURCE, dx/dy for DESTINATION
                if mode == "SOURCE":
                    rx, ry = r["sx"] + p, r["sy"] + p
                else:
                    rx, ry = r["dx"] + p, r["dy"] + p
                    
                rw, rh = r["w"], r["h"]
                
                # Draw border (dotted if overlapping)
                if is_overlapping:
                    HudCompositor.draw_dotted_rect(draw, [rx, ry, rx + rw, ry + rh], color=color, width=width)
                else:
                    draw.rectangle([rx, ry, rx + rw, ry + rh], outline=color, width=width)
                
                # Draw name
                draw.text((rx + 5, ry + 5), r.get("name", f"Rect {i}"), fill=color)
                
                # Connection line to anchor (DESTINATION mode only) - now for ALL rects
                if mode == "DESTINATION" and r.get("anchor"):
                    anchor_name = r["anchor"]
                    if isinstance(anchor_name, str):
                         anchor_name = Anchor[anchor_name]
                    
                    anchor_pos = anchors.get(anchor_name)
                    if anchor_pos:
                        ap = (anchor_pos[0] + p, anchor_pos[1] + p)
                        # Draw dotted line from rectangle center to anchor
                        rect_center = (rx + rw/2, ry + rh/2)
                        # Slightly different look for non-selected to avoid clutter? 
                        # Let's keep same color but maybe thinner if not selected
                        l_width = thin_w * 2 if is_selected else thin_w
                        HudCompositor.draw_dotted_line(draw, rect_center, ap, color=color, width=l_width)

                # Draw handles if selected
                if is_selected:
                    if mode == "SOURCE":
                        h_size = 6
                        handles = [
                            (rx, ry), (rx + rw, ry), 
                            (rx, ry + rh), (rx + rw, ry + rh)
                        ]
                        for hx, hy in handles:
                            draw.rectangle([hx - handle_size, hy - handle_size, hx + handle_size, hy + handle_size], fill=color)
            
        return padded_img
