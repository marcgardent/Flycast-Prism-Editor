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
        self.geometry("1200x850")

        # Application State
        self.current_exr_data = {}
        self.available_channels = []
        self.image_size = (0, 0)
        self.last_numpy_image = None
        self.full_pil_image = None
        self.current_view_mode = "Composite (RGB)"
        self.magnifier_size = 200  # Size of the UI widget
        self.display_size = (0, 0)
        self.default_dir = user_pictures_dir()

        # UI Layout
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # --- SIDEBAR ---
        self.sidebar = ctk.CTkFrame(self, width=280, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)

        self.logo_label = ctk.CTkLabel(self.sidebar, text="FLYCAST G-BUFFER", font=ctk.CTkFont(size=20, weight="bold"))
        self.logo_label.pack(pady=(20, 20), padx=20)

        self.open_button = ctk.CTkButton(self.sidebar, text="OPEN EXR", command=self.open_file, fg_color="#2c3e50",
                                         hover_color="#34495e")
        self.open_button.pack(pady=10, padx=20, fill="x")

        # Tools Section
        ctk.CTkLabel(self.sidebar, text="TOOLS", font=ctk.CTkFont(size=12, weight="bold")).pack(pady=(20, 5))
        self.magnifier_var = ctk.BooleanVar(value=True)
        self.magnifier_switch = ctk.CTkSwitch(self.sidebar, text="Magnifier (1:1)", variable=self.magnifier_var)
        self.magnifier_switch.pack(pady=5, padx=20, anchor="w")

        # Composite Modes Section
        ctk.CTkLabel(self.sidebar, text="COMPOSITE MODES", font=ctk.CTkFont(size=12, weight="bold")).pack(pady=(20, 5))

        self.composite_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.composite_frame.pack(fill="x", padx=10)

        self.add_view_button(self.composite_frame, "Composite (RGB)")
        self.add_view_button(self.composite_frame, "Normal Map")
        self.add_view_button(self.composite_frame, "Albedo + AO")

        # Individual Channels Section
        ctk.CTkLabel(self.sidebar, text="INDIVIDUAL CHANNELS", font=ctk.CTkFont(size=12, weight="bold")).pack(
            pady=(20, 5))

        self.channels_scroll = ctk.CTkScrollableFrame(self.sidebar, height=300, fg_color="transparent")
        self.channels_scroll.pack(fill="both", expand=True, padx=10, pady=5)
        self.channel_buttons = []

        # Info Console
        self.info_box = ctk.CTkTextbox(self.sidebar, height=120, font=ctk.CTkFont(size=11), fg_color="#1a1a1a")
        self.info_box.pack(side="bottom", fill="x", padx=15, pady=15)
        self.info_box.insert("0.0", "Waiting for file...")

        # --- DISPLAY AREA ---
        self.image_container = ctk.CTkFrame(self, fg_color="#101010", corner_radius=0)
        self.image_container.grid(row=0, column=1, sticky="nsew")

        self.display_label = ctk.CTkLabel(self.image_container, text="", cursor="crosshair")
        self.display_label.place(relx=0.5, rely=0.5, anchor="center")

        # Magnifier Overlay
        self.magnifier_label = ctk.CTkLabel(self.image_container, text="", fg_color="transparent",
                                            width=self.magnifier_size, height=self.magnifier_size)
        self.magnifier_label.place_forget()

        # Events
        self.image_container.bind("<Configure>", self.on_resize)
        self.display_label.bind("<Motion>", self.update_magnifier)
        self.display_label.bind("<Leave>", lambda e: self.magnifier_label.place_forget())

    def add_view_button(self, parent, text):
        btn = ctk.CTkButton(parent, text=text, command=lambda t=text: self.update_view_mode(t),
                            anchor="w", height=32, fg_color="transparent", border_width=1)
        btn.pack(fill="x", pady=2)
        return btn

    def log(self, text, clear=False):
        if clear: self.info_box.delete("0.0", "end")
        self.info_box.insert("end", f"{text}\n")
        self.info_box.see("end")

    def open_file(self):
        path = filedialog.askopenfilename(
            initialdir=self.default_dir,
            filetypes=[("OpenEXR Files", "*.exr")]
        )
        if not path: return

        try:
            input_file = oiio.ImageInput.open(path)
            if not input_file: raise Exception(f"Error: {oiio.geterror()}")

            spec = input_file.spec()
            self.image_size = (spec.width, spec.height)
            data = input_file.read_image("half")
            input_file.close()

            self.current_exr_data = {name: data[:, :, i] for i, name in enumerate(spec.channelnames)}
            self.available_channels = spec.channelnames

            self.log(f"File: {os.path.basename(path)}", clear=True)
            self.log(f"Resolution: {spec.width}x{spec.height}")

            # Rebuild channel buttons
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
            messagebox.showerror("Error", str(e))

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

    def update_magnifier(self, event):
        if not self.magnifier_var.get() or self.full_pil_image is None:
            self.magnifier_label.place_forget()
            return

        # Coordinates relative to the displayed image label
        x, y = event.x, event.y
        disp_w, disp_h = self.display_size

        # Map to original resolution
        orig_w, orig_h = self.full_pil_image.size
        orig_x = int((x / disp_w) * orig_w)
        orig_y = int((y / disp_h) * orig_h)

        # For 1:1 view, we crop a square of 'magnifier_size' from the original image
        m_half = self.magnifier_size // 2
        left = max(0, orig_x - m_half)
        top = max(0, orig_y - m_half)
        right = min(orig_w, orig_x + m_half)
        bottom = min(orig_h, orig_y + m_half)

        try:
            # Create 1:1 crop
            crop = self.full_pil_image.crop((left, top, right, bottom))

            # Since it's 1:1, we don't resize the image contents, but the widget
            # needs a fixed size. We pad the crop if it's smaller than the widget (at edges)
            zoomed = Image.new("RGB", (self.magnifier_size, self.magnifier_size), (0, 0, 0))
            # Calculate paste position in the magnifier window if we are near borders
            paste_x = max(0, m_half - orig_x)
            paste_y = max(0, m_half - orig_y)
            zoomed.paste(crop, (paste_x, paste_y))

            # Draw crosshair in the center of the magnifier
            draw = ImageDraw.Draw(zoomed)
            mid = self.magnifier_size // 2
            line_len = 8
            # Draw crosshair (black background for contrast)
            for color, width in [("black", 3), ("white", 1)]:
                draw.line([(mid - line_len, mid), (mid + line_len, mid)], fill=color, width=width)
                draw.line([(mid, mid - line_len), (mid, mid + line_len)], fill=color, width=width)

            # Add a border to the magnifier
            zoomed = ImageOps.expand(zoomed, border=2, fill='#3498db')

            zoom_ctk = ctk.CTkImage(light_image=zoomed, dark_image=zoomed,
                                    size=(self.magnifier_size + 4, self.magnifier_size + 4))
            self.magnifier_label.configure(image=zoom_ctk)

            # Position magnifier with offset
            mx = x + self.display_label.winfo_x() + 25
            my = y + self.display_label.winfo_y() + 25

            # Boundary check
            if mx + self.magnifier_size > self.image_container.winfo_width():
                mx -= (self.magnifier_size + 50)
            if my + self.magnifier_size > self.image_container.winfo_height():
                my -= (self.magnifier_size + 50)

            self.magnifier_label.place(x=mx, y=my)
        except Exception:
            self.magnifier_label.place_forget()


def main():
    app = FlycastViewer()
    app.mainloop()


if __name__ == "__main__":
    main()