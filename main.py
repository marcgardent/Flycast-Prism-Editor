import sys
import customtkinter as ctk
from tkinter import filedialog
from PIL import Image, ImageTk
import numpy as np


# Note: Initialiser OpenImageIO ou PyEXR ici selon le choix final

class FlycastViewer(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Flycast GBuffer Viewer")
        self.geometry("1000x700")

        # Configuration de la grille
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Sidebar pour les contrôles
        self.sidebar = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")

        self.logo_label = ctk.CTkLabel(self.sidebar, text="FLYCAST GBUFFER", font=ctk.CTkFont(size=16, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        self.open_button = ctk.CTkButton(self.sidebar, text="Open EXR", command=self.open_file)
        self.open_button.grid(row=1, column=0, padx=20, pady=10)

        self.channel_label = ctk.CTkLabel(self.sidebar, text="Channels:")
        self.channel_label.grid(row=2, column=0, padx=20, pady=(20, 0))

        self.channel_menu = ctk.CTkOptionMenu(self.sidebar, values=["Albedo", "Normals", "Depth", "Specular"])
        self.channel_menu.grid(row=3, column=0, padx=20, pady=10)

        # Zone d'affichage de l'image
        self.image_container = ctk.CTkFrame(self, corner_radius=0)
        self.image_container.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")

        self.display_label = ctk.CTkLabel(self.image_container, text="No image loaded")
        self.display_label.pack(expand=True)

    def open_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("EXR files", "*.exr")])
        if file_path:
            # Logique de chargement EXR à implémenter ici
            print(f"Loading: {file_path}")
            self.display_label.configure(text=f"Loaded: {file_path.split('/')[-1]}")


def main():
    app = FlycastViewer()
    app.mainloop()


if __name__ == "__main__":
    main()