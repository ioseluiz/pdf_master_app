import os
import fitz  # PyMuPDF
from PyQt6.QtCore import QThread, pyqtSignal

BATCH_SIZE = 20  # Páginas por lote emitido


class PDFLoaderThread(QThread):
    """Hilo de carga: emite las páginas en lotes para retroalimentación progresiva."""
    file_started    = pyqtSignal(str, int, int, int)  # (path, total_pages, file_num, total_files)
    page_batch_ready = pyqtSignal(str, list, int, int) # (path, batch, pages_done, total_pages)
    finished_all    = pyqtSignal()
    error_occurred  = pyqtSignal(str)

    def __init__(self, file_paths):
        super().__init__()
        self.file_paths = file_paths
        self.is_running = True

    def run(self):
        total_files = len(self.file_paths)
        for file_num, file_path in enumerate(self.file_paths, start=1):
            if not self.is_running:
                break
            try:
                doc = fitz.open(file_path)
                total_pages = len(doc)

                self.file_started.emit(file_path, total_pages, file_num, total_files)

                # Los PDFs se renderizan a escala fija 0.2 (dimensiones ~612pt -> ~122px).
                # Las imágenes (dimensiones en píxeles crudos) necesitan un factor de
                # escala dinámico para producir una miniatura de tamaño comparable,
                # en vez de renderizarse a su resolución nativa (lento y pesado).
                is_image = not doc.is_pdf
                target_thumb_width = 130

                batch = []
                for i in range(total_pages):
                    if not self.is_running:
                        break
                    page = doc.load_page(i)
                    if is_image:
                        scale = target_thumb_width / page.rect.width
                        matrix = fitz.Matrix(scale, scale)
                    else:
                        matrix = fitz.Matrix(0.2, 0.2)
                    pix = page.get_pixmap(matrix=matrix)
                    batch.append((pix.tobytes("png"), i + 1))

                    if len(batch) >= BATCH_SIZE or i == total_pages - 1:
                        self.page_batch_ready.emit(file_path, batch[:], i + 1, total_pages)
                        batch = []

                doc.close()

            except Exception as e:
                self.error_occurred.emit(f"Error en {os.path.basename(file_path)}: {e}")

        self.finished_all.emit()

    def stop(self):
        self.is_running = False


class PDFSaverThread(QThread):
    """Hilo encargado de optimizar y guardar el PDF final."""
    finished = pyqtSignal(bool, str)  # (éxito, mensaje)

    def __init__(self, model, order, path, quality):
        super().__init__()
        self.model = model
        self.order = order
        self.path = path
        self.quality = quality

    def run(self):
        try:
            result_msg = self.model.reorder_and_save(self.order, self.path, self.quality)
            self.finished.emit(True, result_msg)
        except Exception as e:
            self.finished.emit(False, str(e))
