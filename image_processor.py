import numpy as np
from PIL import Image

class ImageProcessor:
    @staticmethod
    def get_available_composite_modes(available_channels):
        modes = []
        if all(c in available_channels for c in ['Albedo.R', 'Albedo.G', 'Albedo.B']):
            modes.append("Composite (RGB)")
        if all(c in available_channels for c in ['Normal.X', 'Normal.Y', 'Normal.Z']):
            modes.append("Normal Map")
        if any(c in available_channels for c in ['Albedo.R', 'Albedo.G', 'Albedo.B']) and 'SSAO.AO' in available_channels:
            modes.append("Albedo + AO")
        return modes

    @staticmethod
    def process_view_mode(mode, image_size, exr_data):
        w, h = image_size
        img_np = np.zeros((h, w, 3), dtype=np.float32)

        if mode == "Composite (RGB)":
            for i, c in enumerate(['Albedo.R', 'Albedo.G', 'Albedo.B']):
                if c in exr_data: img_np[:, :, i] = exr_data[c]

        elif mode == "Normal Map":
            for i, c in enumerate(['Normal.X', 'Normal.Y', 'Normal.Z']):
                if c in exr_data:
                    img_np[:, :, i] = (exr_data[c] + 1.0) / 2.0

        elif mode == "Albedo + AO":
            ao = exr_data.get('SSAO.AO', np.ones((h, w)))
            for i, c in enumerate(['Albedo.R', 'Albedo.G', 'Albedo.B']):
                if c in exr_data: img_np[:, :, i] = exr_data[c] * ao
        
        elif mode == "Material.ID":
            if 'Material.ID' in exr_data:
                mat_ids = (exr_data['Material.ID'] * 255.0).astype(np.uint8)
                # A simple color hash to visualize IDs
                r = (mat_ids * 13) & 255
                g = (mat_ids * 47) & 255
                b = (mat_ids * 101) & 255
                img_np = np.stack([r, g, b], axis=-1).astype(np.float32) / 255.0

        elif mode in exr_data:
            chan = exr_data[mode]
            img_np = np.stack([chan, chan, chan], axis=-1)

        return np.clip(img_np * 255, 0, 255).astype(np.uint8)

    @staticmethod
    def get_pixel_raw_values(mode, px, py, exr_data):
        if not exr_data: return "N/A"
        try:
            if mode == "Composite (RGB)":
                res = []
                for c in ['Albedo.R', 'Albedo.G', 'Albedo.B']:
                    if c in exr_data: res.append(f"{exr_data[c][py, px]:.3f}")
                return f"RGB({', '.join(res)})"
            elif mode == "Normal Map":
                res = []
                for c in ['Normal.X', 'Normal.Y', 'Normal.Z']:
                    if c in exr_data: res.append(f"{exr_data[c][py, px]:.3f}")
                return f"RawNorm({', '.join(res)})"
            
            elif mode == "Material.ID":
                if "Material.ID" not in exr_data: return "N/A"
                val = exr_data["Material.ID"][py, px]
                mat_id = int(round(val * 255.0))

                list_type_map = {
                    0: "Opaque", 1: "Opaque Mod", 2: "Translucent", 
                    3: "Translucent Mod", 4: "Punch-Through"
                }
                
                list_type_val = (mat_id >> 5) & 0b111
                has_texture = (mat_id >> 4) & 1
                is_gouraud = (mat_id >> 3) & 1
                has_bumpmap = (mat_id >> 2) & 1
                fog_ctrl = mat_id & 0b11

                list_type_str = list_type_map.get(list_type_val, f"Unknown ({list_type_val})")

                return (f"ID: {mat_id} | "
                        f"List: {list_type_str} | "
                        f"Tex: {'Y' if has_texture else 'N'} | "
                        f"Gouraud: {'Y' if is_gouraud else 'N'} | "
                        f"Bump: {'Y' if has_bumpmap else 'N'} | "
                        f"Fog: {fog_ctrl}")

            elif mode in exr_data:
                val = exr_data[mode][py, px]
                return f"{val:.4f}"
        except Exception:
            pass
        return "N/A"
