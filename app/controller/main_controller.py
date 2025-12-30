from PyQt5.QtCore import Qt

class MainController:
    def __init__(self):
        self.model = None
        self.view = None

    def set_model(self, model):
        self.model = model

    def set_view(self, view):
        self.view = view

    def handle_add_pdf(self):
        files = self.view.show_file_dialog()
        if files:
            self.add_files_by_paths(files)

    def handle_dropped_files(self, file_paths):
        pdf_files = [f for f in file_paths if f.lower().endswith('.pdf')]
        if not pdf_files:
            return
        self.add_files_by_paths(pdf_files)

    def add_files_by_paths(self, file_list):
        added = False
        for f in file_list:
            try:
                self.model.load_pdf(f)
                added = True
            except Exception as e:
                self.view.show_message("Error", f"No se pudo cargar {f}\n{str(e)}", "error")
        
        if added:
            self._refresh_preview()

    def handle_rotate_left(self):
        self._rotate_selected_pages(clockwise=False)

    def handle_rotate_right(self):
        self._rotate_selected_pages(clockwise=True)

    def _rotate_selected_pages(self, clockwise):
        list_widget = self.view.pages_list
        selected_items = list_widget.selectedItems()

        if not selected_items:
            return

        for item in selected_items:
            original_index = item.data(Qt.UserRole + 1)
            self.model.rotate_page(original_index, clockwise)
            new_img = self.model.get_page_image(original_index)
            
            current_row = list_widget.row(item)
            list_widget.update_item_image_data(current_row, new_img)

    def handle_delete_page(self):
        indices_to_delete = self.view.get_selected_indices()
        if not indices_to_delete:
            return

        for idx in indices_to_delete:
            self.model.delete_page(idx)
            
        self._refresh_preview()

    def handle_save_pdf(self):
        if self.model.get_page_count() == 0:
            self.view.show_message("Aviso", "No hay páginas para guardar.")
            return

        path = self.view.show_save_dialog()
        if path:
            try:
                # 1. Obtenemos el orden visual
                current_order = self.view.get_current_order()
                
                # 2. Obtenemos la calidad seleccionada por el usuario
                quality = self.view.get_selected_quality_code()
                
                # 3. Guardamos pasando ambos parámetros
                self.model.reorder_and_save(current_order, path, quality=quality)
                
                self.view.show_message("Éxito", "Archivo PDF guardado correctamente.")
            except Exception as e:
                self.view.show_message("Error", f"Error al guardar: {str(e)}", "error")

    def handle_clear(self):
        import fitz
        self.model.current_doc = fitz.open()
        self.model.page_mapping = [] 
        self.view.pages_list.clear()

    def _refresh_preview(self):
        count = self.model.get_page_count()
        pages_data = []
        for i in range(count):
            img = self.model.get_page_image(i)
            label = self.model.get_page_label(i)
            pages_data.append((img, label))
        
        self.view.update_pages_view(pages_data)