import os

import pymupdf
from PyQt6.QtCore import QThread, pyqtSignal

from ..model.converters import (
    IMAGE_EXTENSIONS, WORD_EXTENSIONS,
    WordConverter, ConversionError, WordNotAvailableError,
    convert_image_to_pdf_bytes,
)

BATCH_SIZE = 20  # Páginas por lote emitido


class PDFLoaderThread(QThread):
    """Hilo de carga: convierte lo que no sea PDF (imágenes, Word) a bytes PDF,
    y emite las páginas en lotes para retroalimentación progresiva."""
    conversion_started = pyqtSignal(str, int, int)             # (path, file_num, total_files)
    file_started       = pyqtSignal(str, int, int, int, object)  # (path, total_pages, file_num, total_files, pdf_bytes|None)
    page_batch_ready   = pyqtSignal(str, list, int, int)       # (path, batch, pages_done, total_pages)
    finished_all       = pyqtSignal()
    error_occurred     = pyqtSignal(str)

    def __init__(self, file_paths, preconverted=None):
        super().__init__()
        self.file_paths = file_paths
        self.preconverted = dict(preconverted or {})  # path -> pdf_bytes ya en caché del modelo
        self.is_running = True

    def run(self):
        total_files = len(self.file_paths)
        word = None
        word_unavailable = False

        try:
            for file_num, file_path in enumerate(self.file_paths, start=1):
                if not self.is_running:
                    break
                name = os.path.basename(file_path)
                ext = os.path.splitext(file_path)[1].lower()
                pdf_bytes = self.preconverted.get(file_path)

                try:
                    if pdf_bytes is None and ext in WORD_EXTENSIONS:
                        if word_unavailable:
                            continue
                        self.conversion_started.emit(file_path, file_num, total_files)
                        if word is None:
                            word = WordConverter().__enter__()
                        pdf_bytes = word.to_pdf_bytes(file_path)
                    elif pdf_bytes is None and ext in IMAGE_EXTENSIONS:
                        pdf_bytes = convert_image_to_pdf_bytes(file_path)

                    if pdf_bytes is not None:
                        doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
                    else:
                        doc = pymupdf.open(file_path)
                    total_pages = len(doc)

                    self.file_started.emit(file_path, total_pages, file_num, total_files, pdf_bytes)

                    # Todas las fuentes ya son PDF (las imágenes/Word fueron
                    # convertidas a páginas Carta), así que una escala fija basta.
                    matrix = pymupdf.Matrix(0.2, 0.2)
                    batch = []
                    for i in range(total_pages):
                        if not self.is_running:
                            break
                        page = doc.load_page(i)
                        pix = page.get_pixmap(matrix=matrix)
                        batch.append((pix.tobytes("png"), i + 1))

                        if len(batch) >= BATCH_SIZE or i == total_pages - 1:
                            self.page_batch_ready.emit(file_path, batch[:], i + 1, total_pages)
                            batch = []

                    doc.close()

                except WordNotAvailableError as e:
                    word_unavailable = True
                    self.error_occurred.emit(str(e))
                except ConversionError as e:
                    self.error_occurred.emit(str(e))
                except Exception as e:
                    self.error_occurred.emit(f"Error en {name}: {e}")
        finally:
            if word is not None:
                try:
                    word.__exit__(None, None, None)
                except Exception:
                    pass

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
