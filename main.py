import sys
import os
import customtkinter as ctk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
import numpy as np
import OpenImageIO as oiio


class FlycastViewer(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Flycast GBuffer Viewer")
        self.geometry("1100x800")

        # État de l'application
        self.current_exr_data = {}  # Stockage des channels numpy
        self.available_channels = []
        self.image_size = (0, 0)

        # UI Layout
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Sidebar
        self.sidebar = ctk.CTkFrame(self, width=250, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")

        self.logo_label = ctk.CTkLabel(self.sidebar, text="FLYCAST G-BUFFER", font=ctk.CTkFont(size=18, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 20))

        self.open_button = ctk.CTkButton(self.sidebar, text="Ouvrir EXR", command=self.open_file)
        self.open_button.grid(row=1, column=0, padx=20, pady=10)

        # Sélections de vues
        self.view_label = ctk.CTkLabel(self.sidebar, text="Modes de Vue Composites:", font=ctk.CTkFont(weight="bold"))
        self.view_label.grid(row=2, column=0, padx=20, pady=(20, 5))

        self.mode_menu = ctk.CTkOptionMenu(self.sidebar,
                                           values=["Complet (RGB)", "Normal Map", "Albedo + AO"],
                                           command=self.update_display)
        self.mode_menu.grid(row=3, column=0, padx=20, pady=10)

        self.chan_label = ctk.CTkLabel(self.sidebar, text="Canaux Individuels:", font=ctk.CTkFont(weight="bold"))
        self.chan_label.grid(row=4, column=0, padx=20, pady=(20, 5))

        self.single_chan_menu = ctk.CTkOptionMenu(self.sidebar,
                                                  values=["Aucun"],
                                                  command=self.display_single_channel)
        self.single_chan_menu.grid(row=5, column=0, padx=20, pady=10)

        # Infos techniques
        self.info_box = ctk.CTkTextbox(self.sidebar, height=200, width=210, font=ctk.CTkFont(size=11))
        self.info_box.grid(row=6, column=0, padx=20, pady=20)
        self.info_box.insert("0.0", "En attente de fichier...")

        # Zone d'affichage
        self.image_container = ctk.CTkScrollableFrame(self, corner_radius=0, fg_color="transparent")
        self.image_container.grid(row=0, column=1, padx=5, pady=5, sticky="nsew")

        self.display_label = ctk.CTkLabel(self.image_container, text="")
        self.display_label.pack(expand=True, fill="both")

    def log(self, text, clear=False):
        if clear: self.info_box.delete("0.0", "end")
        self.info_box.insert("end", f"{text}\n")

    def open_file(self):
        path = filedialog.askopenfilename(filetypes=[("OpenEXR Files", "*.exr")])
        if not path:
            return

        try:
            input_file = oiio.ImageInput.open(path)
            if not input_file:
                raise Exception(f"Impossible d'ouvrir le fichier: {oiio.geterror()}")

            spec = input_file.spec()
            self.image_size = (spec.width, spec.height)

            # Lecture de tous les canaux
            data = input_file.read_image("half")
            input_file.close()

            # Mapping des noms de canaux
            self.current_exr_data = {}
            self.available_channels = spec.channelnames

            for i, name in enumerate(spec.channelnames):
                self.current_exr_data[name] = data[:, :, i]

            self.log(f"Fichier: {os.path.basename(path)}", clear=True)
            self.log(f"Résolution: {spec.width}x{spec.height}")
            self.log(f"Canaux: {len(self.available_channels)}")

            # Mise à jour du menu des canaux
            self.single_chan_menu.configure(values=self.available_channels)
            self.update_display("Complet (RGB)")

        except Exception as e:
            messagebox.showerror("Erreur de lecture", str(e))

    def update_display(self, mode):
        if not self.current_exr_data: return

        w, h = self.image_size
        img_np = np.zeros((h, w, 3), dtype=np.float32)

        if mode == "Complet (RGB)":
            # Reconstruction Albedo.R, G, B
            for i, c in enumerate(['Albedo.R', 'Albedo.G', 'Albedo.B']):
                if c in self.current_exr_data:
                    img_np[:, :, i] = self.current_exr_data[c]

        elif mode == "Normal Map":
            # Normal.X, Y, Z (Mappage -1,1 vers 0,1 pour affichage)
            for i, c in enumerate(['Normal.X', 'Normal.Y', 'Normal.Z']):
                if c in self.current_exr_data:
                    img_np[:, :, i] = (self.current_exr_data[c] + 1.0) / 2.0

        elif mode == "Albedo + AO":
            # Multiplication Albedo par SSAO.AO
            ao = self.current_exr_data.get('SSAO.AO', np.ones((h, w)))
            for i, c in enumerate(['Albedo.R', 'Albedo.G', 'Albedo.B']):
                if c in self.current_exr_data:
                    img_np[:, :, i] = self.current_exr_data[c] * ao

        self.render_numpy(img_np)

    def display_single_channel(self, channel_name):
        if channel_name not in self.current_exr_data: return

        chan_data = self.current_exr_data[channel_name]
        # On duplique sur les 3 canaux pour faire du gris
        img_np = np.stack([chan_data, chan_data, chan_data], axis=-1)

        # Cas spécial pour Material.ID : on peut vouloir le coloriser ou le normaliser
        if channel_name == "Material.ID":
            self.log("Note: Material.ID visualisé en RAW [0-1]")

        self.render_numpy(img_np)

    def render_numpy(self, img_np):
        # Clipping et conversion en 8 bits pour PIL
        img_np = np.clip(img_np * 255, 0, 255).astype(np.uint8)
        pil_img = Image.fromarray(img_np)

        # Redimensionnement auto pour la fenêtre si trop grand
        max_w, max_h = 1200, 800
        ratio = min(max_w / pil_img.width, max_h / pil_img.height)
        if ratio < 1:
            new_size = (int(pil_img.width * ratio), int(pil_img.height * ratio))
            pil_img = pil_img.resize(new_size, Image.LANCZOS)

        ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=pil_img.size)
        self.display_label.configure(image=ctk_img, text="")


def main():
    app = FlycastViewer()
    app.mainloop()


if __name__ == "__main__":
    main()