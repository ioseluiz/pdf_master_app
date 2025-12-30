from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication
# Importamos los workers
from .workers import PDFLoaderThread, PDFSaverThread

class MainController:
    def __init__(self):
        self.model = None
        self.view = None
        # Referencias a los hilos para evitar que el recolector de basura los elimine
        self.loader_thread = None
        self.saver_thread = None

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
        pdf_files = [f for f in file_paths if f.lower().endswith('.pdf')]
        if pdf_files:
            self.add_files_by_paths(pdf_files)

    def add_files_by_paths(self, file_list):
        """Inicia la carga en segundo plano."""
        # Feedback visual: Cursor de espera
        QApplication.setOverrideCursor(Qt.WaitCursor)
        
        # Evitamos solapamiento de hilos de carga
        if self.loader_thread and self.loader_thread.isRunning():
            self.view.show_message("Ocupado", "Espere a que termine la carga actual.")
            QApplication.restoreOverrideCursor()
            return

        # Configuramos e iniciamos el hilo
        self.loader_thread = PDFLoaderThread(file_list)
        self.loader_thread.file_processed.connect(self.on_file_processed)
        self.loader_thread.finished_all.connect(self.on_loading_finished)
        self.loader_thread.error_occurred.connect(lambda err: self.view.show_message("Error", err, "error"))
        
        self.loader_thread.start()

    def on_file_processed(self, file_path, pages_data):
        """Se llama cuando un archivo ha sido procesado por el hilo."""
        try:
            # Actualizamos modelo lógico
            self.model.load_pdf(file_path)
            
            # Actualizamos vista
            import os
            filename = os.path.basename(file_path)
            # Calculamos dónde empiezan las nuevas páginas
            start_index = self.model.get_page_count() - len(pages_data)
            
            for i, (img_bytes, page_num) in enumerate(pages_data):
                # Lógica de etiqueta (Label)
                label = f"{filename}\nPág {page_num}"
                if len(filename) > 15:
                    label = f"{filename[:12]}...\nPág {page_num}"
                
                # Agregamos a la lista visual
                self.view.pages_list.add_pdf_page(img_bytes, label, start_index + i)
                
        except Exception as e:
            print(f"Error actualizando UI: {e}")

    def on_loading_finished(self):
        QApplication.restoreOverrideCursor()
        self.view.show_message("Completado", "Carga de archivos finalizada.", "info")

    # --- EDICIÓN ---
    def handle_rotate_left(self):
        self._rotate_selected_pages(clockwise=False)

    def handle_rotate_right(self):
        self._rotate_selected_pages(clockwise=True)

    def _rotate_selected_pages(self, clockwise):
        list_widget = self.view.pages_list
        selected_items = list_widget.selectedItems()
        if not selected_items: return

        QApplication.setOverrideCursor(Qt.WaitCursor)
        for item in selected_items:
            original_index = item.data(Qt.UserRole + 1)
            self.model.rotate_page(original_index, clockwise)
            # Obtenemos la nueva imagen rotada (usará la optimización 0.3 del modelo)
            new_img = self.model.get_page_image(original_index)
            
            current_row = list_widget.row(item)
            list_widget.update_item_image_data(current_row, new_img)
        QApplication.restoreOverrideCursor()

    def handle_delete_page(self):
        indices_to_delete = self.view.get_selected_indices()
        if not indices_to_delete: return

        for idx in indices_to_delete:
            self.model.delete_page(idx)
        self._refresh_preview()

    def handle_clear(self):
        import fitz
        self.model.current_doc = fitz.open()
        self.model.page_mapping = [] 
        self.view.pages_list.clear()

    def _refresh_preview(self):
        count = self.model.get_page_count()
        pages_data = []
        for i in range(count):
            pages_data.append((self.model.get_page_image(i), self.model.get_page_label(i)))
        self.view.update_pages_view(pages_data)

    # --- GUARDADO ASÍNCRONO ---
    def handle_save_pdf(self):
        if self.model.get_page_count() == 0:
            self.view.show_message("Aviso", "No hay páginas para guardar.")
            return

        path = self.view.show_save_dialog()
        if not path:
            return

        # 1. Bloqueo visual de la UI
        QApplication.setOverrideCursor(Qt.WaitCursor)
        self.view.setEnabled(False) # Evita que el usuario toque botones mientras guarda

        # 2. Recopilar datos necesarios
        current_order = self.view.get_current_order()
        quality = self.view.get_selected_quality_code()

        # 3. Iniciar el hilo de guardado
        self.saver_thread = PDFSaverThread(self.model, current_order, path, quality)
        self.saver_thread.finished.connect(self.on_save_finished)
        self.saver_thread.start()

    def on_save_finished(self, success, message):
        """Callback al terminar el guardado."""
        # 1. Restaurar la UI
        QApplication.restoreOverrideCursor()
        self.view.setEnabled(True)
        
        # 2. Mostrar mensaje al usuario
        if success:
            if "Advertencia" in message:
                self.view.show_message("Guardado con Avisos", message, "info")
            else:
                self.view.show_message("Éxito", message)
        else:
            self.view.show_message("Error Fatal", f"No se pudo guardar: {message}", "error")