import numpy as np
from PIL import Image
from constants import Channels  # Import the Channels class


class ImageProcessor:
    @staticmethod
    def get_available_composite_modes(available_channels):
        modes = []
        if all(c in available_channels for c in [Channels.ALBEDO_R, Channels.ALBEDO_G, Channels.ALBEDO_B]):
            modes.append("Composite (RGB)")
        if all(c in available_channels for c in [Channels.NORMAL_X, Channels.NORMAL_Y, Channels.NORMAL_Z]):
            modes.append("Normal Map")
        if all(c in available_channels for c in [Channels.HUD_R, Channels.HUD_G, Channels.HUD_B, Channels.HUD_A]):
            modes.append("HUD (RGBA)") # New mode
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

        elif mode == "HUD (RGBA)": # New mode with alpha blending
            hud_r = exr_data.get(Channels.HUD_R, np.zeros((h, w), dtype=np.float32))
            hud_g = exr_data.get(Channels.HUD_G, np.zeros((h, w), dtype=np.float32))
            hud_b = exr_data.get(Channels.HUD_B, np.zeros((h, w), dtype=np.float32))
            hud_a = exr_data.get(Channels.HUD_A, np.ones((h, w), dtype=np.float32)) # Default to opaque if no alpha

            # Blend with a black background using alpha: C_out = C_src * alpha + C_bg * (1 - alpha)
            # Assuming C_bg is black (0,0,0), so C_out = C_src * alpha
            img_np[:, :, 0] = hud_r * hud_a
            img_np[:, :, 1] = hud_g * hud_a
            img_np[:, :, 2] = hud_b * hud_a

        elif mode == Channels.MATERIAL_ID:
            if Channels.MATERIAL_ID in exr_data:
                # Material.ID is now a native 32-bit unsigned integer
                mat_ids = exr_data[Channels.MATERIAL_ID].astype(np.uint32)

                # Official hashColor function translated to NumPy
                # Added & 0xFFFFFFFF for 32-bit integer precision as in GLSL
                h = (mat_ids * 2654435761) & 0xFFFFFFFF

                r = ((h >> 16) & 255).astype(np.float32) / 255.0
                g = ((h >> 8) & 255).astype(np.float32) / 255.0
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
                # Depth.Z is already 32-bit float with Reverse-Z mapping (0.0=Far, 1.0=Near)
                # So, the channel itself is the normalized value for grayscale display.
                img_np = np.stack([chan, chan, chan], axis=-1)

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
            elif mode == "HUD (RGBA)": # New mode
                res = []
                for c in [Channels.HUD_R, Channels.HUD_G, Channels.HUD_B, Channels.HUD_A]:
                    if c in exr_data: res.append(f"{exr_data[c][py, px]:.3f}")
                return f"HUD({', '.join(res)})"

            elif mode == Channels.MATERIAL_ID:
                if Channels.MATERIAL_ID not in exr_data: return "N/A"
                val = exr_data[Channels.MATERIAL_ID][py, px]
                # Material.ID is now a native 32-bit unsigned integer
                mat_id = int(val)

                # New bit layout:
                # Bit 7: Presence
                # Bits 6-4: List Type
                # Bit 3: Texture
                # Bit 2: Gouraud
                # Bit 1: BumpMap
                # Bit 0: Fog

                presence_bit = (mat_id >> 7) & 1
                list_type_val = (mat_id >> 4) & 0b111  # Bits 6-4 (3 bits)
                has_texture = (mat_id >> 3) & 1        # Bit 3 (1 bit)
                is_gouraud = (mat_id >> 2) & 1         # Bit 2 (1 bit)
                has_bumpmap = (mat_id >> 1) & 1        # Bit 1 (1 bit)
                fog_ctrl = mat_id & 1                  # Bit 0 (1 bit)

                list_type_map = {
                    0: "Opaque", 1: "Opaque Mod", 2: "Translucent",
                    3: "Translucent Mod", 4: "Punch-Through"
                }
                
                list_type_str = list_type_map.get(list_type_val, f"Unknown ({list_type_val})")

                presence_str = "Present" if presence_bit else "Background"

                return (f"ID: {mat_id} | "
                        f"Presence: {presence_str} | "
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
