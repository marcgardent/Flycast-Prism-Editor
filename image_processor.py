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
        
        # Combined Metadata Mode
        metadata_channels = [
            Channels.METADATA_WORLDPOS_X, Channels.METADATA_WORLDPOS_Y, Channels.METADATA_WORLDPOS_Z,
            Channels.METADATA_TEXTURE_HASH, Channels.METADATA_POLY_COUNT
        ]
        if any(c in available_channels for c in metadata_channels):
            modes.append(Channels.COMBINED_METADATA)

        return modes

    @staticmethod
    def _apply_hash_color(ids_array):
        """Applique l'algorithme de hashColor officiel Flycast."""
        # ids_array should be a numpy array (uint32 or uint64)
        ids_32 = ids_array.astype(np.uint32)
        
        # Multiplicative hash
        h = (ids_32 * 2654435761) & 0xFFFFFFFF

        r = ((h >> 16) & 255).astype(np.float32) / 255.0
        g = ((h >> 8) & 255).astype(np.float32) / 255.0
        b = (h & 255).astype(np.float32) / 255.0

        # Handle zero case (background)
        zero_mask = (ids_32 == 0)
        r[zero_mask] = 0.1
        g[zero_mask] = 0.1
        b[zero_mask] = 0.1

        return np.stack([r, g, b], axis=-1)

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
                img_np = ImageProcessor._apply_hash_color(exr_data[Channels.MATERIAL_ID])

        elif mode == Channels.METADATA_TEXTURE_HASH:
            if Channels.METADATA_TEXTURE_HASH in exr_data:
                img_np = ImageProcessor._apply_hash_color(exr_data[Channels.METADATA_TEXTURE_HASH])

        elif mode == Channels.COMBINED_METADATA:
            # Combined Hash calculation
            h_acc = np.zeros((h, w), dtype=np.uint32)
            
            # WorldPos: Combine bits of X, Y, Z
            for c in [Channels.METADATA_WORLDPOS_X, Channels.METADATA_WORLDPOS_Y, Channels.METADATA_WORLDPOS_Z]:
                if c in exr_data:
                    # Crucial: Ensure float32 before view as uint32 to avoid size mismatch with float16 (half)
                    h_acc ^= exr_data[c].astype(np.float32).view(np.uint32)
            
            # Texture Hash (u32)
            if Channels.METADATA_TEXTURE_HASH in exr_data:
                h_acc ^= exr_data[Channels.METADATA_TEXTURE_HASH].astype(np.uint32)
            
            # Poly Count
            if Channels.METADATA_POLY_COUNT in exr_data:
                h_acc ^= exr_data[Channels.METADATA_POLY_COUNT].astype(np.uint32)
            
            img_np = ImageProcessor._apply_hash_color(h_acc)

        elif mode == Channels.DEPTH_Z:
            if Channels.DEPTH_Z in exr_data:
                chan = exr_data[Channels.DEPTH_Z]
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
                val = int(exr_data[Channels.MATERIAL_ID][py, px])
                
                presence_bit = (val >> 7) & 1
                list_type_val = (val >> 4) & 0b111
                has_texture = (val >> 3) & 1
                is_gouraud = (val >> 2) & 1
                has_bumpmap = (val >> 1) & 1
                fog_ctrl = val & 1

                list_type_map = {0: "Opaque", 1: "Opaque Mod", 2: "Translucent", 3: "Translucent Mod", 4: "Punch-Through"}
                list_type_str = list_type_map.get(list_type_val, f"Unknown ({list_type_val})")
                presence_str = "Present" if presence_bit else "Background"

                return (f"ID: {val} | List: {list_type_str} | Tex: {'Y' if has_texture else 'N'} | "
                        f"Gouraud: {'Y' if is_gouraud else 'N'} | Bump: {'Y' if has_bumpmap else 'N'} | Fog: {fog_ctrl}")

            elif mode == Channels.METADATA_TEXTURE_HASH:
                if Channels.METADATA_TEXTURE_HASH not in exr_data: return "N/A"
                val = exr_data[Channels.METADATA_TEXTURE_HASH][py, px]
                return f"TexHash: 0x{int(val):08X}"

            elif mode == Channels.COMBINED_METADATA:
                parts = []
                # Pos
                p_x = exr_data.get(Channels.METADATA_WORLDPOS_X, [None]*py)[py, px] if Channels.METADATA_WORLDPOS_X in exr_data else None
                p_y = exr_data.get(Channels.METADATA_WORLDPOS_Y, [None]*py)[py, px] if Channels.METADATA_WORLDPOS_Y in exr_data else None
                p_z = exr_data.get(Channels.METADATA_WORLDPOS_Z, [None]*py)[py, px] if Channels.METADATA_WORLDPOS_Z in exr_data else None
                if p_x is not None: parts.append(f"Pos:({p_x:.2f}, {p_y:.2f}, {p_z:.2f})")
                
                # Tex
                if Channels.METADATA_TEXTURE_HASH in exr_data:
                    t_h = exr_data[Channels.METADATA_TEXTURE_HASH][py, px]
                    parts.append(f"Tex:0x{int(t_h):08X}")
                
                # Poly
                if Channels.METADATA_POLY_COUNT in exr_data:
                    p_c = int(exr_data[Channels.METADATA_POLY_COUNT][py, px])
                    parts.append(f"Poly:{p_c}")
                
                return " | ".join(parts) if parts else "N/A"

            elif mode == Channels.DEPTH_Z:
                if Channels.DEPTH_Z not in exr_data: return "N/A"
                val = exr_data[Channels.DEPTH_Z][py, px]
                return f"Depth (1/W): {val:.6f}"

            elif mode in exr_data:
                val = exr_data[mode][py, px]
                return f"{val:.4f}"
        except Exception as e:
            print(f"Picker Error: {e}")
        return "N/A"
    @staticmethod
    def get_pixel_metadata(px, py, exr_data):
        """Récupère toutes les métadonnées pour le Poly Routing."""
        if not exr_data: return None
        
        metadata = {}
        # WorldPos
        if all(c in exr_data for c in [Channels.METADATA_WORLDPOS_X, Channels.METADATA_WORLDPOS_Y, Channels.METADATA_WORLDPOS_Z]):
            metadata["x"] = float(exr_data[Channels.METADATA_WORLDPOS_X][py, px])
            metadata["y"] = float(exr_data[Channels.METADATA_WORLDPOS_Y][py, px])
            metadata["z"] = float(exr_data[Channels.METADATA_WORLDPOS_Z][py, px])
        
        # PolyCount
        if Channels.METADATA_POLY_COUNT in exr_data:
            metadata["count"] = int(exr_data[Channels.METADATA_POLY_COUNT][py, px])
            
        # TextureHash
        if Channels.METADATA_TEXTURE_HASH in exr_data:
            val = int(exr_data[Channels.METADATA_TEXTURE_HASH][py, px])
            metadata["texHash"] = f"0x{val:08X}"
            
        return metadata
