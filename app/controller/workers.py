import os
import fitz  # PyMuPDF
from PyQt5.QtCore import QThread, pyqtSignal

class PDFLoaderThread(QThread):
    """Hilo encargado de cargar y renderizar páginas sin bloquear la UI."""
    file_processed = pyqtSignal(str, list) # (ruta_archivo, lista_paginas)
    finished_all = pyqtSignal()
    error_occurred = pyqtSignal(str)

    def __init__(self, file_paths):
        super().__init__()
        self.file_paths = file_paths
        self.is_running = True

    def run(self):
        for file_path in self.file_paths:
            if not self.is_running:
                break
            
            try:
                doc = fitz.open(file_path)
                page_data = []

                for i in range(len(doc)):
                    if not self.is_running:
                        break
                    
                    page = doc.load_page(i)
                    
                    # Renderizamos a baja resolución (0.3) para velocidad y memoria
                    pix = page.get_pixmap(matrix=fitz.Matrix(0.3, 0.3))
                    
                    # Guardamos bytes y número de página humano (i + 1)
                    page_data.append((pix.tobytes("png"), i + 1))

                doc.close()
                
                # Emitimos resultado parcial por archivo
                if self.is_running:
                    self.file_processed.emit(file_path, page_data)

            except Exception as e:
                self.error_occurred.emit(f"Error en {file_path}: {str(e)}")

        self.finished_all.emit()

    def stop(self):
        self.is_running = False

class PDFSaverThread(QThread):
    """Hilo encargado de optimizar y guardar el PDF final."""
    finished = pyqtSignal(bool, str) # (Éxito?, Mensaje)

    def __init__(self, model, order, path, quality):
        super().__init__()
        self.model = model
        self.order = order
        self.path = path
        self.quality = quality

    def run(self):
        try:
            # Ejecutamos la operación pesada del modelo aquí
            result_msg = self.model.reorder_and_save(self.order, self.path, self.quality)
            self.finished.emit(True, result_msg)
        except Exception as e:
            self.finished.emit(False, str(e))