import json
import os
from hud_compositor import HudCompositor, Anchor

class HudConfig:
    @staticmethod
    def _validate_zone(zone, index):
        """Validates a single HUD zone dictionary."""
        # Required fields check
        for field in ["name", "w", "h", "source", "mapping"]:
            if field not in zone:
                raise KeyError(f"'{field}' is missing")
        
        for field in ["x", "y"]:
            if field not in zone["source"]:
                raise KeyError(f"source.'{field}' is missing")
            if field not in zone["mapping"]:
                raise KeyError(f"mapping.'{field}' is missing")
        
        if "anchor" not in zone["mapping"]:
            raise KeyError("mapping.'anchor' is missing")

    @staticmethod
    def load(file_path, image_size):
        """
        Loads HUD zones from a JSON file and converts virtual coordinates to pixel coordinates.
        Returns a list of HUD rectangle dictionaries.
        """
        with open(file_path, "r") as f:
            data = json.load(f)
        
        if "hud_zones" not in data:
            raise KeyError("hud_zones")

        orig_w, orig_h = image_size
        v_scale = 480.0 / orig_h
        
        v_anchors = HudCompositor.get_anchor_table(orig_w, orig_h)
        v_anchors = {k: (v[0] * v_scale, v[1] * v_scale) for k, v in v_anchors.items()}
        source_anchor_vpos = v_anchors[Anchor.SCREEN_CENTER]

        new_hud_rects = []
        for i, zone in enumerate(data["hud_zones"]):
            try:
                HudConfig._validate_zone(zone, i)

                v_w = zone["w"]
                v_h = zone["h"]
                
                # Convert source back
                vsx = zone["source"]["x"] + source_anchor_vpos[0]
                vsy = zone["source"]["y"] + source_anchor_vpos[1]
                
                # Convert destination back
                anchor_name = zone["mapping"]["anchor"]
                try:
                    anchor_enum = Anchor[anchor_name]
                except KeyError:
                    raise ValueError(f"Invalid anchor name: '{anchor_name}'")
                    
                dest_anchor_vpos = v_anchors[anchor_enum]
                vdx = zone["mapping"]["x"] + dest_anchor_vpos[0]
                vdy = zone["mapping"]["y"] + dest_anchor_vpos[1]
                
                new_rect = {
                    "name": zone["name"],
                    "sx": vsx / v_scale,
                    "sy": vsy / v_scale,
                    "dx": vdx / v_scale,
                    "dy": vdy / v_scale,
                    "w": v_w / v_scale,
                    "h": v_h / v_scale,
                    "anchor": anchor_enum,
                    "zen": zone.get("zen_mode", False)
                }
                new_hud_rects.append(new_rect)
            except (KeyError, ValueError) as e:
                zone_name = zone.get("name", "Unnamed")
                raise RuntimeError(f"Zone #{i} ('{zone_name}'): {e}")
        
        return new_hud_rects

    @staticmethod
    def export(hud_rects, image_size, existing_path=None):
        """
        Converts pixel coordinates to virtual coordinates and returns a JSON-serializable dictionary.
        """
        orig_w, orig_h = image_size
        v_scale = 480.0 / orig_h
        
        # Anchors in Virtual Space
        v_anchors = HudCompositor.get_anchor_table(orig_w, orig_h)
        v_anchors = {k: (v[0] * v_scale, v[1] * v_scale) for k, v in v_anchors.items()}
        
        source_anchor_vpos = v_anchors[Anchor.SCREEN_CENTER]
        
        hud_zones = []
        for r in hud_rects:
            vsx, vsy = r["sx"] * v_scale, r["sy"] * v_scale
            src_x = int(round(vsx - source_anchor_vpos[0]))
            src_y = int(round(vsy - source_anchor_vpos[1]))
            
            vdx, vdy = r["dx"] * v_scale, r["dy"] * v_scale
            anchor_enum = r["anchor"]
            if isinstance(anchor_enum, str): anchor_enum = Anchor[anchor_enum]
            
            dest_anchor_vpos = v_anchors[anchor_enum]
            map_x = int(round(vdx - dest_anchor_vpos[0]))
            map_y = int(round(vdy - dest_anchor_vpos[1]))
            
            zone = {
                "name": r["name"],
                "w": int(round(r["w"] * v_scale)),
                "h": int(round(r["h"] * v_scale)),
                "zen_mode": r.get("zen", False),
                "source": {
                    "x": src_x,
                    "y": src_y,
                    "anchor": "SCREEN_CENTER"
                },
                "mapping": {
                    "x": map_x,
                    "y": map_y,
                    "anchor": anchor_enum.name
                }
            }
            hud_zones.append(zone)
            
        export_data = {
            "safe_zone": {"w": 640, "h": 480},
            "hud_zones": hud_zones
        }
        
        # Smart Save: Preserve other keys if existing_path is provided
        if existing_path and os.path.exists(existing_path):
            try:
                with open(existing_path, "r") as f:
                    existing_data = json.load(f)
                existing_data.update(export_data)
                export_data = existing_data
            except Exception:
                # Fallback to pure export if reading fails
                pass

        return export_data

    @staticmethod
    def save(data, file_path):
        """Writes JSON data to a file."""
        with open(file_path, "w") as f:
            json.dump(data, f, indent=2)
