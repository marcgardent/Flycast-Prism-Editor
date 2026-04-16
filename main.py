import sys
import os
import customtkinter as ctk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk, ImageOps, ImageDraw
import numpy as np
import OpenImageIO as oiio
from platformdirs import user_pictures_dir


class FlycastViewer(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Flycast G-Buffer Viewer")
        self.geometry("1200x900")

        # Application State
        self.current_exr_data = {}
        self.available_channels = []
        self.image_size = (0, 0)
        self.last_numpy_image = None
        self.full_pil_image = None
        self.current_view_mode = "Composite (RGB)"
        self.magnifier_size = 200
        self.display_size = (0, 0)
        self.default_dir = user_pictures_dir()
        self.current_pixel_value = "N/A"

        # UI Layout
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # --- SIDEBAR ---
        self.sidebar = ctk.CTkFrame(self, width=280, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)

        self.logo_label = ctk.CTkLabel(self.sidebar, text="FLYCAST G-BUFFER", font=ctk.CTkFont(size=20, weight="bold"))
        self.logo_label.pack(pady=(20, 20), padx=20)

        self.open_button = ctk.CTkButton(self.sidebar, text="OUVRIR EXR", command=self.open_file, fg_color="#2c3e50",
                                         hover_color="#34495e")
        self.open_button.pack(pady=10, padx=20, fill="x")

        # Inspector Section (New)
        ctk.CTkLabel(self.sidebar, text="INSPECTEUR (CLIC IMAGE)", font=ctk.CTkFont(size=12, weight="bold")).pack(
            pady=(20, 5))
        self.inspect_entry = ctk.CTkEntry(self.sidebar, placeholder_text="Valeur copiée ici...")
        self.inspect_entry.pack(pady=5, padx=20, fill="x")

        # Tools Section
        ctk.CTkLabel(self.sidebar, text="OUTILS", font=ctk.CTkFont(size=12, weight="bold")).pack(pady=(20, 5))
        self.magnifier_var = ctk.BooleanVar(value=True)
        self.magnifier_switch = ctk.CTkSwitch(self.sidebar, text="Loupe (1:1)", variable=self.magnifier_var)
        self.magnifier_switch.pack(pady=5, padx=20, anchor="w")

        # Composite Modes Section
        ctk.CTkLabel(self.sidebar, text="MODES COMPOSITES", font=ctk.CTkFont(size=12, weight="bold")).pack(pady=(20, 5))
        self.composite_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.composite_frame.pack(fill="x", padx=10)
        self.add_view_button(self.composite_frame, "Composite (RGB)")
        self.add_view_button(self.composite_frame, "Normal Map")
        self.add_view_button(self.composite_frame, "Albedo + AO")

        # Individual Channels Section
        ctk.CTkLabel(self.sidebar, text="CANAUX INDIVIDUELS", font=ctk.CTkFont(size=12, weight="bold")).pack(
            pady=(20, 5))
        self.channels_scroll = ctk.CTkScrollableFrame(self.sidebar, height=250, fg_color="transparent")
        self.channels_scroll.pack(fill="both", expand=True, padx=10, pady=5)
        self.channel_buttons = []

        # Info Console
        self.info_box = ctk.CTkTextbox(self.sidebar, height=100, font=ctk.CTkFont(size=11), fg_color="#1a1a1a")
        self.info_box.pack(side="bottom", fill="x", padx=15, pady=15)
        self.info_box.insert("0.0", "En attente de fichier...")

        # --- DISPLAY AREA ---
        self.image_container = ctk.CTkFrame(self, fg_color="#101010", corner_radius=0)
        self.image_container.grid(row=0, column=1, sticky="nsew")

        self.display_label = ctk.CTkLabel(self.image_container, text="", cursor="crosshair")
        self.display_label.place(relx=0.5, rely=0.5, anchor="center")

        # Magnifier Overlay
        self.magnifier_label = ctk.CTkLabel(self.image_container, text="", fg_color="transparent",
                                            width=self.magnifier_size, height=self.magnifier_size)

        # Value Text Overlay (Dynamic info next to magnifier)
        self.value_info_label = ctk.CTkLabel(self.image_container, text="", font=ctk.CTkFont(size=11, weight="bold"),
                                             fg_color="#2c3e50", text_color="white", corner_radius=4)

        self.magnifier_label.place_forget()
        self.value_info_label.place_forget()

        # Events
        self.image_container.bind("<Configure>", self.on_resize)
        self.display_label.bind("<Motion>", self.update_magnifier)
        self.display_label.bind("<Button-1>", self.on_image_click)
        self.display_label.bind("<Leave>", self.hide_magnifier)

    def add_view_button(self, parent, text):
        btn = ctk.CTkButton(parent, text=text, command=lambda t=text: self.update_view_mode(t),
                            anchor="w", height=32, fg_color="transparent", border_width=1)
        btn.pack(fill="x", pady=2)
        return btn

    def log(self, text, clear=False):
        if clear: self.info_box.delete("0.0", "end")
        self.info_box.insert("end", f"{text}\n")
        self.info_box.see("end")

    def hide_magnifier(self, event=None):
        self.magnifier_label.place_forget()
        self.value_info_label.place_forget()

    def open_file(self):
        path = filedialog.askopenfilename(
            initialdir=self.default_dir,
            filetypes=[("OpenEXR Files", "*.exr")]
        )
        if not path: return

        try:
            input_file = oiio.ImageInput.open(path)
            if not input_file: raise Exception(f"Erreur: {oiio.geterror()}")

            spec = input_file.spec()
            self.image_size = (spec.width, spec.height)
            data = input_file.read_image("half")
            input_file.close()

            self.current_exr_data = {name: data[:, :, i] for i, name in enumerate(spec.channelnames)}
            self.available_channels = spec.channelnames

            self.log(f"Fichier: {os.path.basename(path)}", clear=True)
            self.log(f"Résolution: {spec.width}x{spec.height}")

            for btn in self.channel_buttons: btn.destroy()
            self.channel_buttons = []

            for name in self.available_channels:
                btn = ctk.CTkButton(self.channels_scroll, text=name,
                                    command=lambda n=name: self.update_view_mode(n),
                                    anchor="w", height=28, font=ctk.CTkFont(size=11),
                                    fg_color="#34495e")
                btn.pack(fill="x", pady=1)
                self.channel_buttons.append(btn)

            self.update_view_mode("Composite (RGB)")

        except Exception as e:
            messagebox.showerror("Erreur", str(e))

    def update_view_mode(self, mode):
        if not self.current_exr_data: return
        self.current_view_mode = mode

        w, h = self.image_size
        img_np = np.zeros((h, w, 3), dtype=np.float32)

        if mode == "Composite (RGB)":
            for i, c in enumerate(['Albedo.R', 'Albedo.G', 'Albedo.B']):
                if c in self.current_exr_data: img_np[:, :, i] = self.current_exr_data[c]

        elif mode == "Normal Map":
            for i, c in enumerate(['Normal.X', 'Normal.Y', 'Normal.Z']):
                if c in self.current_exr_data: img_np[:, :, i] = (self.current_exr_data[c] + 1.0) / 2.0

        elif mode == "Albedo + AO":
            ao = self.current_exr_data.get('SSAO.AO', np.ones((h, w)))
            for i, c in enumerate(['Albedo.R', 'Albedo.G', 'Albedo.B']):
                if c in self.current_exr_data: img_np[:, :, i] = self.current_exr_data[c] * ao

        elif mode in self.current_exr_data:
            chan = self.current_exr_data[mode]
            img_np = np.stack([chan, chan, chan], axis=-1)

        self.last_numpy_image = np.clip(img_np * 255, 0, 255).astype(np.uint8)
        self.refresh_image_display()

    def on_resize(self, event=None):
        if self.last_numpy_image is not None:
            self.refresh_image_display()

    def refresh_image_display(self):
        if self.last_numpy_image is None: return

        cont_w = self.image_container.winfo_width()
        cont_h = self.image_container.winfo_height()

        if cont_w < 10 or cont_h < 10: return

        self.full_pil_image = Image.fromarray(self.last_numpy_image)
        img_w, img_h = self.full_pil_image.size
        ratio = min(cont_w / img_w, cont_h / img_h)

        self.display_size = (int(img_w * ratio), int(img_h * ratio))

        if self.display_size[0] > 0 and self.display_size[1] > 0:
            resized_pil = self.full_pil_image.resize(self.display_size, Image.Resampling.LANCZOS)
            ctk_img = ctk.CTkImage(light_image=resized_pil, dark_image=resized_pil, size=self.display_size)
            self.display_label.configure(image=ctk_img)

    def get_pixel_raw_values(self, px, py):
        """Récupère les vraies valeurs flottantes de l'EXR pour un pixel donné."""
        if not self.current_exr_data: return "N/A"

        values = []
        if self.current_view_mode == "Composite (RGB)":
            for c in ['Albedo.R', 'Albedo.G', 'Albedo.B']:
                if c in self.current_exr_data: values.append(f"{self.current_exr_data[c][py, px]:.3f}")
            return f"RGB({', '.join(values)})"

        elif self.current_view_mode == "Normal Map":
            for c in ['Normal.X', 'Normal.Y', 'Normal.Z']:
                if c in self.current_exr_data: values.append(f"{self.current_exr_data[c][py, px]:.3f}")
            return f"XYZ({', '.join(values)})"

        elif self.current_view_mode in self.current_exr_data:
            val = self.current_exr_data[self.current_view_mode][py, px]
            return f"{val:.4f}"

        return "N/A"

    def on_image_click(self, event):
        if self.current_pixel_value != "N/A":
            display_text = f"[{self.current_view_mode}] {self.current_pixel_value}"
            self.inspect_entry.delete(0, "end")
            self.inspect_entry.insert(0, display_text)

    def update_magnifier(self, event):
        if not self.magnifier_var.get() or self.full_pil_image is None:
            self.hide_magnifier()
            return

        x, y = event.x, event.y
        disp_w, disp_h = self.display_size

        orig_w, orig_h = self.full_pil_image.size
        orig_x = int((x / disp_w) * orig_w)
        orig_y = int((y / disp_h) * orig_h)

        # Update current value for the label and click event
        if 0 <= orig_x < orig_w and 0 <= orig_y < orig_h:
            self.current_pixel_value = self.get_pixel_raw_values(orig_x, orig_y)
        else:
            self.current_pixel_value = "N/A"

        # Zoom 1:1 Logic
        m_half = self.magnifier_size // 2
        left = max(0, orig_x - m_half)
        top = max(0, orig_y - m_half)
        right = min(orig_w, orig_x + m_half)
        bottom = min(orig_h, orig_y + m_half)

        try:
            crop = self.full_pil_image.crop((left, top, right, bottom))
            zoomed = Image.new("RGB", (self.magnifier_size, self.magnifier_size), (0, 0, 0))
            paste_x = max(0, m_half - orig_x)
            paste_y = max(0, m_half - orig_y)
            zoomed.paste(crop, (paste_x, paste_y))

            draw = ImageDraw.Draw(zoomed)
            mid = self.magnifier_size // 2
            line_len = 8
            for color, width in [("black", 3), ("white", 1)]:
                draw.line([(mid - line_len, mid), (mid + line_len, mid)], fill=color, width=width)
                draw.line([(mid, mid - line_len), (mid, mid + line_len)], fill=color, width=width)

            zoomed = ImageOps.expand(zoomed, border=2, fill='#3498db')
            zoom_ctk = ctk.CTkImage(light_image=zoomed, dark_image=zoomed,
                                    size=(self.magnifier_size + 4, self.magnifier_size + 4))

            self.magnifier_label.configure(image=zoom_ctk)
            self.value_info_label.configure(text=f" {self.current_pixel_value} ")

            mx = x + self.display_label.winfo_x() + 25
            my = y + self.display_label.winfo_y() + 25

            if mx + self.magnifier_size > self.image_container.winfo_width():
                mx -= (self.magnifier_size + 50)
            if my + self.magnifier_size > self.image_container.winfo_height():
                my -= (self.magnifier_size + 50)

            self.magnifier_label.place(x=mx, y=my)
            # Place info text below or above magnifier
            info_y = my + self.magnifier_size + 10 if my + self.magnifier_size + 40 < self.image_container.winfo_height() else my - 30
            self.value_info_label.place(x=mx, y=info_y)

        except Exception:
            self.hide_magnifier()


def main():
    app = FlycastViewer()
    app.mainloop()


if __name__ == "__main__":
    main()