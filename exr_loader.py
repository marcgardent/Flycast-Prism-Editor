import threading
import OpenImageIO as oiio
import numpy as np # Import numpy
from image_processor import ImageProcessor
from constants import Channels # Import the Channels class

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

            if self.on_progress:
                self.on_progress(f"EXR Spec: {w}x{h}, {spec.nchannels} channels")
                for i, name in enumerate(spec.channelnames):
                    # Get the format for each channel using str() on TypeDesc object
                    channel_format = str(spec.channelformats[i])
                    self.on_progress(f"  Channel {i}: {name} (Format: {channel_format})")

            # Read image with native data types
            raw_data_dict = {}
            for i, name in enumerate(spec.channelnames):
                if self.cancel_event.is_set():
                    input_file.close()
                    self.on_cancelled()
                    return
                
                # Get the native format for the current channel
                native_format = spec.channelformats[i]
                
                # Read each channel individually, requesting its native format
                channel_array = input_file.read_image(chbegin=i, chend=i+1, format=native_format)
                
                if channel_array is None:
                    raise Exception(f"Erreur lors de la lecture du canal {name}.")
                
                # Squeeze to remove the channel dimension if it's 1
                channel_array = channel_array.squeeze()

                # --- Diagnostic logs for Material.ID ---
                if name == Channels.MATERIAL_ID and self.on_progress:
                    self.on_progress(f"  Material.ID raw array dtype: {channel_array.dtype}")
                    # Log a sample value from the array (e.g., top-left corner)
                    if channel_array.size > 0:
                        self.on_progress(f"  Material.ID sample (0,0) before astype: {channel_array[0,0]}")
                # --- End Diagnostic logs ---

                # Explicitly convert Material.ID to uint32 (this might be redundant if native_format works, but safe)
                if name == Channels.MATERIAL_ID:
                    raw_data_dict[name] = channel_array.astype(np.uint32)
                else:
                    raw_data_dict[name] = channel_array

            input_file.close()

            if self.cancel_event.is_set():
                self.on_cancelled()
                return

            channels_data = raw_data_dict
            available_channels = list(raw_data_dict.keys())
            
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
