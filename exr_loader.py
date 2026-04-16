import threading
import OpenImageIO as oiio

class EXRLoader:
    def __init__(self, on_success, on_error, on_cancelled):
        self.on_success = on_success
        self.on_error = on_error
        self.on_cancelled = on_cancelled
        self.cancel_event = threading.Event()

    def load(self, path):
        self.cancel_event.clear()
        thread = threading.Thread(target=self._load_thread, args=(path,), daemon=True)
        thread.start()

    def cancel(self):
        self.cancel_event.set()

    def _load_thread(self, path):
        try:
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
            channels_data = {name: raw_data[:, :, i] for i, name in enumerate(spec.channelnames)}
            available_channels = spec.channelnames

            self.on_success(path, w, h, channels_data, available_channels)

        except Exception as e:
            self.on_error(str(e))
