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
        """Applies the official Flycast hashColor algorithm."""
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
    def get_pixel_raw_values(px, py, exr_data):
        if not exr_data: return {}
        try:
            data = {}

            # 1. Albedo RGB
            if all(c in exr_data for c in [Channels.ALBEDO_R, Channels.ALBEDO_G, Channels.ALBEDO_B]):
                r, g, b = exr_data[Channels.ALBEDO_R][py, px], exr_data[Channels.ALBEDO_G][py, px], exr_data[Channels.ALBEDO_B][py, px]
                data["RGB"] = f"({r:.3f}, {g:.3f}, {b:.3f})"

            # 2. Normal Map
            if all(c in exr_data for c in [Channels.NORMAL_X, Channels.NORMAL_Y, Channels.NORMAL_Z]):
                nx, ny, nz = exr_data[Channels.NORMAL_X][py, px], exr_data[Channels.NORMAL_Y][py, px], exr_data[Channels.NORMAL_Z][py, px]
                data["Normals"] = f"({nx:.3f}, {ny:.3f}, {nz:.3f})"

            # 3. Depth
            if Channels.DEPTH_Z in exr_data:
                z = exr_data[Channels.DEPTH_Z][py, px]
                data["Depth"] = f"{z:.6f}"

            # 4. Material ID
            if Channels.MATERIAL_ID in exr_data:
                val = int(exr_data[Channels.MATERIAL_ID][py, px])
                data["MatID"] = str(val)

            # 5. HUD
            if all(c in exr_data for c in [Channels.HUD_R, Channels.HUD_G, Channels.HUD_B, Channels.HUD_A]):
                hr, hg, hb, ha = exr_data[Channels.HUD_R][py, px], exr_data[Channels.HUD_G][py, px], exr_data[Channels.HUD_B][py, px], exr_data[Channels.HUD_A][py, px]
                data["HUD"] = f"({hr:.2f}, {hg:.2f}, {hb:.2f}, {ha:.2f})"

            # 6. Metadata
            if all(c in exr_data for c in [Channels.METADATA_WORLDPOS_X, Channels.METADATA_WORLDPOS_Y, Channels.METADATA_WORLDPOS_Z]):
                px_val = exr_data[Channels.METADATA_WORLDPOS_X][py, px]
                py_val = exr_data[Channels.METADATA_WORLDPOS_Y][py, px]
                pz_val = exr_data[Channels.METADATA_WORLDPOS_Z][py, px]
                data["WorldPos"] = f"({px_val:.2f}, {py_val:.2f}, {pz_val:.2f})"
            
            if Channels.METADATA_TEXTURE_HASH in exr_data:
                th = int(exr_data[Channels.METADATA_TEXTURE_HASH][py, px])
                data["TexHash"] = f"0x{th:08X}"
            
            if Channels.METADATA_POLY_COUNT in exr_data:
                pc = int(exr_data[Channels.METADATA_POLY_COUNT][py, px])
                data["PolyCnt"] = str(pc)

            return data

        except Exception as e:
            print(f"Picker Error: {e}")
        return {}
    @staticmethod
    def get_pixel_metadata(px, py, exr_data):
        """Retrieves all metadata for Poly Routing."""
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
