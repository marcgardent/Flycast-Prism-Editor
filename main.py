import sys
import os
import threading
import customtkinter as ctk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk, ImageOps, ImageDraw
import numpy as np
import OpenImageIO as oiio
from platformdirs import user_pictures_dir

# Liste des canaux définis dans le référentiel technique Flycast
STANDARD_CHANNELS = [
    'Albedo.R', 'Albedo.G', 'Albedo.B',
    'Normal.X', 'Normal.Y', 'Normal.Z',
    'Depth.Z', 'Material.ID', 'SSAO.AO'
]


class FlycastViewer(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Flycast G-Buffer Viewer")
        self.geometry("1500x900")

        # État de l'application
        self.current_exr_data = {}
        self.available_channels = []
        self.image_size = (0, 0)
        self.last_numpy_image = None
        self.full_pil_image = None
        self.current_view_mode = "Composite (RGB)"
        self.magnifier_size = 240
        self.display_size = (0, 0)
        self.default_dir = user_pictures_dir()
        self.current_pixel_value = "N/A"

        # Gestion du chargement et annulation
        self.is_loading = False
        self.cancel_event = threading.Event()

        # Configuration de la grille
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # --- BARRE LATÉRALE (SIDEBAR) ---
        self.sidebar = ctk.CTkFrame(self, width=350, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)

        self.logo_label = ctk.CTkLabel(self.sidebar, text="FLYCAST G-BUFFER", font=ctk.CTkFont(size=22, weight="bold"))
        self.logo_label.pack(pady=(25, 20), padx=20)

        self.open_button = ctk.CTkButton(self.sidebar, text="OUVRIR EXR", command=self.open_file,
                                         fg_color="#2c3e50", hover_color="#34495e", height=40)
        self.open_button.pack(pady=10, padx=20, fill="x")

        # Section Inspecteur
        ctk.CTkLabel(self.sidebar, text="INSPECTEUR (CLIC IMAGE)", font=ctk.CTkFont(size=13, weight="bold")).pack(
            pady=(25, 5))
        self.inspect_entry = ctk.CTkEntry(self.sidebar, placeholder_text="Valeur copiée ici...", height=35)
        self.inspect_entry.pack(pady=5, padx=20, fill="x")

        # Section Outils
        ctk.CTkLabel(self.sidebar, text="OUTILS", font=ctk.CTkFont(size=13, weight="bold")).pack(pady=(25, 5))
        self.magnifier_var = ctk.BooleanVar(value=True)
        self.magnifier_switch = ctk.CTkSwitch(self.sidebar, text="Loupe Pixel-Perfect (1:1)",
                                              variable=self.magnifier_var)
        self.magnifier_switch.pack(pady=5, padx=20, anchor="w")

        # Modes Composites
        ctk.CTkLabel(self.sidebar, text="MODES COMPOSITES", font=ctk.CTkFont(size=13, weight="bold")).pack(pady=(25, 5))
        self.composite_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.composite_frame.pack(fill="x", padx=15)
        self.add_view_button(self.composite_frame, "Composite (RGB)")
        self.add_view_button(self.composite_frame, "Normal Map")
        self.add_view_button(self.composite_frame, "Albedo + AO")

        # Liste des canaux avec distinction de couleur
        ctk.CTkLabel(self.sidebar, text="CANAUX (BLEU = STANDARD)", font=ctk.CTkFont(size=13, weight="bold")).pack(
            pady=(25, 5))
        self.channels_scroll = ctk.CTkScrollableFrame(self.sidebar, height=350, fg_color="transparent")
        self.channels_scroll.pack(fill="both", expand=True, padx=15, pady=5)
        self.channel_buttons = []

        # Console
        self.info_box = ctk.CTkTextbox(self.sidebar, height=120, font=ctk.CTkFont(size=11), fg_color="#1a1a1a",
                                       text_color="#aaaaaa")
        self.info_box.pack(side="bottom", fill="x", padx=20, pady=20)
        self.info_box.insert("0.0", "En attente de chargement...")

        # --- ZONE D'AFFICHAGE ---
        self.image_container = ctk.CTkFrame(self, fg_color="#050505", corner_radius=0)
        self.image_container.grid(row=0, column=1, sticky="nsew")

        self.display_label = ctk.CTkLabel(self.image_container, text="", cursor="crosshair")
        self.display_label.place(relx=0.5, rely=0.5, anchor="center")

        # Overlay de chargement
        self.loading_overlay = ctk.CTkFrame(self.image_container, fg_color="#1a1a1a", corner_radius=10, border_width=2,
                                            border_color="#3498db")
        self.loading_label = ctk.CTkLabel(self.loading_overlay, text="TRAITEMENT EN COURS...",
                                          font=ctk.CTkFont(size=14, weight="bold"))
        self.loading_label.pack(pady=(20, 10), padx=30)
        self.progress_bar = ctk.CTkProgressBar(self.loading_overlay, orientation="horizontal", width=250)
        self.progress_bar.pack(pady=(0, 15), padx=30)
        self.progress_bar.configure(mode="indeterminate")

        # Bouton Annuler
        self.cancel_button = ctk.CTkButton(self.loading_overlay, text="ANNULER", command=self.cancel_loading,
                                           fg_color="#c0392b", hover_color="#e74c3c", width=100, height=28)
        self.cancel_button.pack(pady=(0, 20))

        self.magnifier_label = ctk.CTkLabel(self.image_container, text="", fg_color="transparent")
        self.value_info_label = ctk.CTkLabel(self.image_container, text="", font=ctk.CTkFont(size=12, weight="bold"),
                                             fg_color="#3498db", text_color="white", corner_radius=4)

        self.hide_loading()
        self.magnifier_label.place_forget()
        self.value_info_label.place_forget()

        self.image_container.bind("<Configure>", self.on_resize)
        self.display_label.bind("<Motion>", self.update_magnifier)
        self.display_label.bind("<Button-1>", self.on_image_click)
        self.display_label.bind("<Leave>", self.hide_magnifier)

        # Propre fermeture
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def add_view_button(self, parent, text):
        btn = ctk.CTkButton(parent, text=text, command=lambda t=text: self.safe_update_view_mode(t),
                            anchor="w", height=35, fg_color="transparent", border_width=1, border_color="#444444")
        btn.pack(fill="x", pady=3)
        return btn

    def log(self, text, clear=False):
        if clear: self.info_box.delete("0.0", "end")
        self.info_box.insert("end", f"> {text}\n")
        self.info_box.see("end")

    def show_loading(self, message="TRAITEMENT EN COURS..."):
        self.is_loading = True
        self.cancel_event.clear()
        self.loading_label.configure(text=message)
        self.open_button.configure(state="disabled", text="PATIENTEZ...")
        self.loading_overlay.place(relx=0.5, rely=0.5, anchor="center")
        self.progress_bar.start()

    def hide_loading(self):
        self.is_loading = False
        self.open_button.configure(state="normal", text="OUVRIR EXR")
        self.loading_overlay.place_forget()
        self.progress_bar.stop()

    def cancel_loading(self):
        if self.is_loading:
            self.cancel_event.set()
            self.log("Demande d'annulation envoyée...")

    def on_closing(self):
        self.cancel_event.set()
        self.destroy()

    def hide_magnifier(self, event=None):
        self.magnifier_label.place_forget()
        self.value_info_label.place_forget()

    def open_file(self):
        if self.is_loading: return

        path = filedialog.askopenfilename(
            initialdir=self.default_dir,
            filetypes=[("OpenEXR Files", "*.exr")]
        )
        if not path: return

        self.show_loading("CHARGEMENT DE L'EXR...")
        threading.Thread(target=self._load_exr_thread, args=(path,), daemon=True).start()

    def _load_exr_thread(self, path):
        """Fonction exécutée en arrière-plan pour ne pas bloquer l'UI"""
        try:
            input_file = oiio.ImageInput.open(path)
            if not input_file:
                raise Exception(f"Impossible d'ouvrir le fichier : {oiio.geterror()}")

            if self.cancel_event.is_set():
                input_file.close()
                self.after(0, self._on_load_cancelled)
                return

            spec = input_file.spec()
            w, h = spec.width, spec.height

            # Lecture des données
            raw_data = input_file.read_image("half")
            input_file.close()

            if raw_data is None:
                raise Exception("Erreur lors de la lecture des pixels du fichier EXR.")

            if self.cancel_event.is_set():
                self.after(0, self._on_load_cancelled)
                return

            # Extraction des canaux
            channels_data = {name: raw_data[:, :, i] for i, name in enumerate(spec.channelnames)}
            available_channels = spec.channelnames

            self.after(0, lambda: self._on_load_success(path, w, h, channels_data, available_channels))

        except Exception as e:
            # Gestion explicite de l'erreur pour éviter le blocage infini
            self.after(0, lambda err=str(e): self._on_load_error(err))

    def _on_load_cancelled(self):
        self.hide_loading()
        self.log("Chargement annulé.")

    def _on_load_success(self, path, w, h, channels_data, available_channels):
        self.image_size = (w, h)
        self.current_exr_data = channels_data
        self.available_channels = available_channels

        self.log(f"Fichier : {os.path.basename(path)}", clear=True)
        self.log(f"Résolution : {w}x{h}")

        for btn in self.channel_buttons: btn.destroy()
        self.channel_buttons = []

        for name in sorted(self.available_channels):
            is_std = name in STANDARD_CHANNELS
            bg_color = "#2980b9" if is_std else "#34495e"

            btn = ctk.CTkButton(self.channels_scroll,
                                text=f" {'★' if is_std else ' '} {name}",
                                command=lambda n=name: self.safe_update_view_mode(n),
                                anchor="w", height=30,
                                fg_color=bg_color)
            btn.pack(fill="x", pady=2)
            self.channel_buttons.append(btn)

        self.hide_loading()
        self.update_view_mode("Composite (RGB)")

    def _on_load_error(self, error_msg):
        self.hide_loading()
        self.log(f"ERREUR : {error_msg}")
        messagebox.showerror("Erreur Critique", f"Le chargement a échoué :\n{error_msg}")

    def safe_update_view_mode(self, mode):
        """Lance la mise à jour de la vue avec un petit loader si nécessaire"""
        if not self.current_exr_data or self.is_loading: return
        self.show_loading(f"CALCUL : {mode}")
        # On utilise after(10) pour laisser l'UI afficher le loader avant de lancer le calcul lourd
        self.after(10, lambda: self._process_view_mode(mode))

    def _process_view_mode(self, mode):
        try:
            self.update_view_mode(mode)
        finally:
            self.hide_loading()

    def update_view_mode(self, mode):
        self.current_view_mode = mode
        w, h = self.image_size
        img_np = np.zeros((h, w, 3), dtype=np.float32)

        if mode == "Composite (RGB)":
            for i, c in enumerate(['Albedo.R', 'Albedo.G', 'Albedo.B']):
                if c in self.current_exr_data: img_np[:, :, i] = self.current_exr_data[c]

        elif mode == "Normal Map":
            for i, c in enumerate(['Normal.X', 'Normal.Y', 'Normal.Z']):
                if c in self.current_exr_data:
                    img_np[:, :, i] = (self.current_exr_data[c] + 1.0) / 2.0

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
        if self.last_numpy_image is not None and not self.is_loading:
            self.refresh_image_display()

    def refresh_image_display(self):
        if self.last_numpy_image is None: return

        cont_w = self.image_container.winfo_width()
        cont_h = self.image_container.winfo_height()
        if cont_w < 50 or cont_h < 50: return

        self.full_pil_image = Image.fromarray(self.last_numpy_image)
        img_w, img_h = self.full_pil_image.size
        ratio = min(cont_w / img_w, cont_h / img_h)

        self.display_size = (int(img_w * ratio), int(img_h * ratio))

        if self.display_size[0] > 0 and self.display_size[1] > 0:
            resized_pil = self.full_pil_image.resize(self.display_size, Image.Resampling.LANCZOS)
            ctk_img = ctk.CTkImage(light_image=resized_pil, dark_image=resized_pil, size=self.display_size)
            self.display_label.configure(image=ctk_img)

    def get_pixel_raw_values(self, px, py):
        if not self.current_exr_data: return "N/A"
        try:
            if self.current_view_mode == "Composite (RGB)":
                res = []
                for c in ['Albedo.R', 'Albedo.G', 'Albedo.B']:
                    if c in self.current_exr_data: res.append(f"{self.current_exr_data[c][py, px]:.3f}")
                return f"RGB({', '.join(res)})"
            elif self.current_view_mode == "Normal Map":
                res = []
                for c in ['Normal.X', 'Normal.Y', 'Normal.Z']:
                    if c in self.current_exr_data: res.append(f"{self.current_exr_data[c][py, px]:.3f}")
                return f"RawNorm({', '.join(res)})"
            elif self.current_view_mode in self.current_exr_data:
                val = self.current_exr_data[self.current_view_mode][py, px]
                if self.current_view_mode == "Material.ID":
                    mat_id = int(round(val * 255.0))
                    return f"ID: {mat_id} (Val: {val:.4f})"
                return f"{val:.4f}"
        except Exception:
            pass
        return "N/A"

    def on_image_click(self, event):
        if self.current_pixel_value != "N/A":
            display_text = f"{self.current_view_mode}: {self.current_pixel_value}"
            self.inspect_entry.delete(0, "end")
            self.inspect_entry.insert(0, display_text)
            self.log(f"Inspecté : {display_text}")

    def update_magnifier(self, event):
        if not self.magnifier_var.get() or self.full_pil_image is None or self.is_loading:
            self.hide_magnifier()
            return

        x, y = event.x, event.y
        disp_w, disp_h = self.display_size
        orig_w, orig_h = self.full_pil_image.size
        orig_x = int((x / disp_w) * orig_w)
        orig_y = int((y / disp_h) * orig_h)

        if 0 <= orig_x < orig_w and 0 <= orig_y < orig_h:
            self.current_pixel_value = self.get_pixel_raw_values(orig_x, orig_y)
        else:
            self.current_pixel_value = "N/A"

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
            length = 12
            for color, width in [("black", 3), ("white", 1)]:
                draw.line([(mid - length, mid), (mid + length, mid)], fill=color, width=width)
                draw.line([(mid, mid - length), (mid, mid + length)], fill=color, width=width)

            zoomed = ImageOps.expand(zoomed, border=2, fill='#3498db')
            zoom_ctk = ctk.CTkImage(light_image=zoomed, dark_image=zoomed,
                                    size=(self.magnifier_size + 4, self.magnifier_size + 4))

            self.magnifier_label.configure(image=zoom_ctk)
            self.value_info_label.configure(text=f" {self.current_pixel_value} ")

            mx = x + self.display_label.winfo_x() + 40
            my = y + self.display_label.winfo_y() + 40

            if mx + self.magnifier_size > self.image_container.winfo_width():
                mx -= (self.magnifier_size + 80)
            if my + self.magnifier_size > self.image_container.winfo_height():
                my -= (self.magnifier_size + 80)

            self.magnifier_label.place(x=mx, y=my)
            info_y = my + self.magnifier_size + 15 if my + self.magnifier_size + 50 < self.image_container.winfo_height() else my - 35
            self.value_info_label.place(x=mx, y=info_y)
        except Exception:
            self.hide_magnifier()


def main():
    app = FlycastViewer()
    app.mainloop()


if __name__ == "__main__":
    main()