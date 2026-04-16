import threading
import OpenImageIO as oiio
from image_processor import ImageProcessor

class EXRLoader:
    def __init__(self, on_success, on_error, on_cancelled, on_progress=None):
        self.on_success = on_success
        self.on_error = on_error
        self.on_cancelled = on_cancelled
        self.on_progress = on_progress
        self.cancel_event = threading.Event()

    def load(self, path):
        self.cancel_event.clear()
        thread = threading.Thread(target=self._load_thread, args=(path,), daemon=True)
        thread.start()

    def cancel(self):
        self.cancel_event.set()

    def _load_thread(self, path):
        try:
            if self.on_progress:
                self.on_progress("Lecture du fichier EXR...")
            input_file = oiio.ImageInput.open(path)
            if not input_file:
                raise Exception(f"Impossible d'ouvrir le fichier : {oiio.geterror()}")

            if self.cancel_event.is_set():
                input_file.close()
                self.on_cancelled()
                return

            spec = input_file.spec()
            w, h = spec.width, spec.height

            # Lecture des données
            raw_data = input_file.read_image("half")
            input_file.close()

            if raw_data is None:
                raise Exception("Erreur lors de la lecture des pixels du fichier EXR.")

            if self.cancel_event.is_set():
                self.on_cancelled()
                return

            # Extraction des canaux
            if self.on_progress:
                self.on_progress("Extraction des canaux...")
            channels_data = {name: raw_data[:, :, i] for i, name in enumerate(spec.channelnames)}
            available_channels = spec.channelnames
            
            # Pre-calcul des images composites et par canal
            precomputed_images = {}
            modes_to_compute = ImageProcessor.get_available_composite_modes(available_channels)
            modes_to_compute.extend(available_channels)
            
            total_modes = len(modes_to_compute)
            for i, mode in enumerate(modes_to_compute):
                if self.cancel_event.is_set():
                    self.on_cancelled()
                    return
                if self.on_progress:
                    self.on_progress(f"Pré-calcul : {mode} ({i+1}/{total_modes})...")
                
                # Precompute the view mode 
                precomputed_images[mode] = ImageProcessor.process_view_mode(mode, (w, h), channels_data)

            self.on_success(path, w, h, channels_data, available_channels, precomputed_images)

        except Exception as e:
            self.on_error(str(e))
