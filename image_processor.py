import numpy as np
from PIL import Image

class ImageProcessor:
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
            elif mode in exr_data:
                val = exr_data[mode][py, px]
                if mode == "Material.ID":
                    mat_id = int(round(val * 255.0))
                    return f"ID: {mat_id} (Val: {val:.4f})"
                return f"{val:.4f}"
        except Exception:
            pass
        return "N/A"
