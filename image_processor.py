import numpy as np
from PIL import Image
from constants import Channels # Import the Channels class

class ImageProcessor:
    @staticmethod
    def get_available_composite_modes(available_channels):
        modes = []
        if all(c in available_channels for c in [Channels.ALBEDO_R, Channels.ALBEDO_G, Channels.ALBEDO_B]):
            modes.append("Composite (RGB)")
        if all(c in available_channels for c in [Channels.NORMAL_X, Channels.NORMAL_Y, Channels.NORMAL_Z]):
            modes.append("Normal Map")
        if any(c in available_channels for c in [Channels.ALBEDO_R, Channels.ALBEDO_G, Channels.ALBEDO_B]) and Channels.SSAO_AO in available_channels:
            modes.append("Albedo + AO")
        return modes

    @staticmethod
    def process_view_mode(mode, image_size, exr_data):
        w, h = image_size
        img_np = np.zeros((h, w, 3), dtype=np.float32)

        if mode == "Composite (RGB)":
            for i, c in enumerate([Channels.ALBEDO_R, Channels.ALBEDO_G, Channels.ALBEDO_B]):
                if c in exr_data: img_np[:, :, i] = exr_data[c]

        elif mode == "Normal Map":
            for i, c in enumerate([Channels.NORMAL_X, Channels.NORMAL_Y, Channels.NORMAL_Z]):
                if c in exr_data:
                    img_np[:, :, i] = (exr_data[c] + 1.0) / 2.0

        elif mode == "Albedo + AO":
            ao = exr_data.get(Channels.SSAO_AO, np.ones((h, w)))
            for i, c in enumerate([Channels.ALBEDO_R, Channels.ALBEDO_G, Channels.ALBEDO_B]):
                if c in exr_data: img_np[:, :, i] = exr_data[c] * ao
        
        elif mode == Channels.MATERIAL_ID:
            if Channels.MATERIAL_ID in exr_data:
                mat_ids = np.round(exr_data[Channels.MATERIAL_ID] * 255.0).astype(np.uint32) # Use uint32 for hash calculation
                
                # Official hashColor function translated to NumPy
                h = mat_ids * 2654435761 # 2654435761u
                
                r = ((h >> 16) & 255).astype(np.float32) / 255.0
                g = ((h >> 8)  & 255).astype(np.float32) / 255.0
                b = (h & 255).astype(np.float32) / 255.0
                
                # Handle matID == 0u case
                zero_mask = (mat_ids == 0)
                r[zero_mask] = 0.1
                g[zero_mask] = 0.1
                b[zero_mask] = 0.1

                img_np = np.stack([r, g, b], axis=-1)

        elif mode == Channels.DEPTH_Z:
            if Channels.DEPTH_Z in exr_data:
                chan = exr_data[Channels.DEPTH_Z]
                # Normalize 1/W values to [0, 1] for grayscale display
                # Assuming 0 is far (black) and max value is near (white)
                min_val = np.min(chan)
                max_val = np.max(chan)
                
                if max_val - min_val > 1e-6: # Avoid division by zero
                    normalized_chan = (chan - min_val) / (max_val - min_val)
                else:
                    normalized_chan = np.zeros_like(chan) # All same value, show as black
                
                img_np = np.stack([normalized_chan, normalized_chan, normalized_chan], axis=-1)

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
                for c in [Channels.ALBEDO_R, Channels.ALBEDO_G, Channels.ALBEDO_B]:
                    if c in exr_data: res.append(f"{exr_data[c][py, px]:.3f}")
                return f"RGB({', '.join(res)})"
            elif mode == "Normal Map":
                res = []
                for c in [Channels.NORMAL_X, Channels.NORMAL_Y, Channels.NORMAL_Z]:
                    if c in exr_data: res.append(f"{exr_data[c][py, px]:.3f}")
                return f"RawNorm({', '.join(res)})"
            
            elif mode == Channels.MATERIAL_ID:
                if Channels.MATERIAL_ID not in exr_data: return "N/A"
                val = exr_data[Channels.MATERIAL_ID][py, px]
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
            
            elif mode == Channels.DEPTH_Z:
                if Channels.DEPTH_Z not in exr_data: return "N/A"
                val = exr_data[Channels.DEPTH_Z][py, px]
                return f"Depth (1/W): {val:.6f}"

            elif mode in exr_data:
                val = exr_data[mode][py, px]
                return f"{val:.4f}"
        except Exception:
            pass
        return "N/A"
