import os
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import QApplication
from .workers import PDFLoaderThread, PDFSaverThread
from ..model.pdf_manager import IMAGE_EXTENSIONS

ITEMS_PER_FLUSH = 5   # Items del widget creados por tick del timer (~30fps)
SUPPORTED_EXTENSIONS = {'.pdf'} | IMAGE_EXTENSIONS


class MainController:
    def __init__(self):
        self.model = None
        self.view = None
        self.loader_thread = None
        self.saver_thread = None
        self._loading_base_index = {}  # filepath -> índice base en modelo al inicio de carga
        self._page_queue = []          # [(img_bytes, label, original_index)] pendientes de mostrar
        self._progress_state = None    # (done, total, label) más reciente del worker
        self._loading_finished = False

        # Timer que vacía la cola a ritmo controlado sin bloquear la UI
        self._flush_timer = QTimer()
        self._flush_timer.setInterval(33)  # ~30 fps
        self._flush_timer.timeout.connect(self._flush_page_queue)

    def set_model(self, model):
        self.model = model

    def set_view(self, view):
        self.view = view

    # --- CARGA DE ARCHIVOS ---
    def handle_add_pdf(self):
        files = self.view.show_file_dialog()
        if files:
            self.add_files_by_paths(files)

    def handle_dropped_files(self, file_paths):
        valid_files = [f for f in file_paths if os.path.splitext(f)[1].lower() in SUPPORTED_EXTENSIONS]
        if valid_files:
            self.add_files_by_paths(valid_files)

    def add_files_by_paths(self, file_list):
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)

        if self.loader_thread and self.loader_thread.isRunning():
            self.view.show_message("Ocupado", "Espere a que termine la carga actual.")
            QApplication.restoreOverrideCursor()
            return

        self._loading_base_index = {}
        self._page_queue = []
        self._progress_state = None
        self._loading_finished = False

        self.loader_thread = PDFLoaderThread(file_list)
        self.loader_thread.file_started.connect(self.on_file_started)
        self.loader_thread.page_batch_ready.connect(self.on_page_batch_ready)
        self.loader_thread.finished_all.connect(self.on_loading_finished)
        self.loader_thread.error_occurred.connect(
            lambda err: self.view.show_message("Error de carga", err, "error")
        )
        self.loader_thread.start()
        self._flush_timer.start()

    def on_file_started(self, file_path, total_pages, file_num, total_files):
        """Registra metadatos del archivo y muestra el progreso inicial."""
        try:
            self._loading_base_index[file_path] = self.model.get_page_count()
            self.model.load_pdf(file_path)
        except Exception as e:
            self.view.show_message(
                "Error de carga",
                f"No se pudo cargar {os.path.basename(file_path)}:\n{e}",
                "error"
            )
            self._loading_base_index.pop(file_path, None)
            return

        filename = os.path.basename(file_path)
        label = f"Archivo {file_num}/{total_files}: {filename} — {total_pages} páginas"
        self.view.show_progress(0, total_pages, label)

    def on_page_batch_ready(self, file_path, pages_data, pages_done, total_pages):
        """Encola miniaturas y actualiza el estado de progreso (no toca la UI directamente)."""
        if file_path not in self._loading_base_index:
            return

        base_index = self._loading_base_index[file_path]
        filename = os.path.basename(file_path)
        start_index = base_index + (pages_done - len(pages_data))

        for i, (img_bytes, page_num) in enumerate(pages_data):
            label = f"{filename}\nPág {page_num}"
            if len(filename) > 15:
                label = f"{filename[:12]}...\nPág {page_num}"
            self._page_queue.append((img_bytes, label, start_index + i))

        percent = int(pages_done / total_pages * 100)
        self._progress_state = (
            pages_done, total_pages,
            f"{filename}: {pages_done}/{total_pages} páginas ({percent}%)"
        )

    def _flush_page_queue(self):
        """Vacía la cola de miniaturas a ritmo controlado sin bloquear el event loop."""
        batch = self._page_queue[:ITEMS_PER_FLUSH]
        del self._page_queue[:ITEMS_PER_FLUSH]

        for img_bytes, label, original_index in batch:
            self.view.pages_list.add_pdf_page(img_bytes, label, original_index)

        if self._progress_state and not self._loading_finished:
            done, total, label = self._progress_state
            self.view.show_progress(done, total, label)

        if self._loading_finished and not self._page_queue:
            self._flush_timer.stop()

    def on_loading_finished(self):
        """Worker terminó — ocultar progress bar y restaurar cursor.
        El timer sigue vaciando la cola en segundo plano sin mostrar progreso."""
        self._loading_finished = True
        self._loading_base_index = {}
        QApplication.restoreOverrideCursor()
        self.view.show_progress_complete()

    # --- EDICIÓN ---
    def handle_rotate_left(self):
        self._rotate_selected_pages(clockwise=False)

    def handle_rotate_right(self):
        self._rotate_selected_pages(clockwise=True)

    def _rotate_selected_pages(self, clockwise):
        list_widget = self.view.pages_list
        selected_items = list_widget.selectedItems()
        if not selected_items:
            return

        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        for item in selected_items:
            original_index = item.data(Qt.ItemDataRole.UserRole + 1)
            self.model.rotate_page(original_index, clockwise)
            new_img = self.model.get_page_image(original_index)
            list_widget.update_item_image_data(list_widget.row(item), new_img)
        QApplication.restoreOverrideCursor()

    def handle_delete_page(self):
        indices_to_delete = self.view.get_selected_indices()
        if not indices_to_delete:
            return
        for idx in indices_to_delete:
            self.model.delete_page(idx)
        self.view.pages_list.remove_pages_by_original_index(indices_to_delete)

    def handle_clear(self):
        self.model.clear()
        self.view.pages_list.clear()

    # --- GUARDADO ASÍNCRONO ---
    def handle_save_pdf(self):
        if self.model.get_page_count() == 0:
            self.view.show_message("Aviso", "No hay páginas para guardar.")
            return

        path = self.view.show_save_dialog()
        if not path:
            return

        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        self.view.setEnabled(False)

        current_order = self.view.get_current_order()
        quality = self.view.get_selected_quality_code()

        self.saver_thread = PDFSaverThread(self.model, current_order, path, quality)
        self.saver_thread.finished.connect(self.on_save_finished)
        self.saver_thread.start()

    def on_save_finished(self, success, message):
        QApplication.restoreOverrideCursor()
        self.view.setEnabled(True)
        if success:
            if "Advertencia" in message:
                self.view.show_message("Guardado con Avisos", message, "info")
            else:
                self.view.show_message("Éxito", message)
        else:
            self.view.show_message("Error Fatal", f"No se pudo guardar: {message}", "error")
