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
        """Manejador para el botón Agregar (diálogo)."""
        files = self.view.show_file_dialog()
        if files:
            self.add_files_by_paths(files)

    def handle_dropped_files(self, file_paths):
        """Manejador para archivos soltados (Drag & Drop)."""
        # Filtramos solo archivos PDF para evitar errores
        pdf_files = [f for f in file_paths if f.lower().endswith('.pdf')]
        
        if not pdf_files:
            # Opcional: Mostrar aviso si soltaron algo que no es PDF
            # self.view.show_message("Aviso", "Solo se admiten archivos PDF.")
            return

        self.add_files_by_paths(pdf_files)

    def add_files_by_paths(self, file_list):
        """Método auxiliar reutilizable para cargar una lista de rutas."""
        added = False
        for f in file_list:
            try:
                self.model.load_pdf(f)
                added = True
            except Exception as e:
                self.view.show_message("Error", f"No se pudo cargar {f}\n{str(e)}", "error")
        
        # Solo refrescamos si al menos uno se cargó con éxito
        if added:
            self._refresh_preview()

    def handle_rotate_left(self):
        self._rotate_selected_pages(clockwise=False)

    def handle_rotate_right(self):
        self._rotate_selected_pages(clockwise=True)

    def _rotate_selected_pages(self, clockwise):
        """Lógica común para rotar."""
        # Obtenemos los items seleccionados directamente del widget
        list_widget = self.view.pages_list
        selected_items = list_widget.selectedItems()

        if not selected_items:
            return

        for item in selected_items:
            # 1. Averiguar qué página del PDF es (Índice Original)
            original_index = item.data(Qt.UserRole + 1)
            
            # 2. Rotar en el modelo
            self.model.rotate_page(original_index, clockwise)
            
            # 3. Obtener la NUEVA imagen generada (rotada)
            new_img = self.model.get_page_image(original_index)
            
            # 4. Actualizar la vista inmediatamente
            current_row = list_widget.row(item)
            list_widget.update_item_image_data(current_row, new_img)

    def handle_delete_page(self):
        # Obtenemos los índices visuales (fila en la grilla)
        indices_to_delete = self.view.get_selected_indices()
        
        if not indices_to_delete:
            return

        # Para mantener consistencia simple:
        # 1. Borramos del modelo
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
                # 1. Obtener el orden visual actual
                current_order = self.view.get_current_order()
                
                # Llamamos a reordenar y guardar:
                self.model.reorder_and_save(current_order, path)
                
                self.view.show_message("Éxito", "Archivo PDF guardado correctamente.")
            except Exception as e:
                self.view.show_message("Error", f"Error al guardar: {str(e)}", "error")

    def handle_clear(self):
        # Reiniciar modelo y vista
        import fitz
        self.model.current_doc = fitz.open()
        self.view.pages_list.clear()

    def _refresh_preview(self):
        """Regenera todas las miniaturas desde el modelo."""
        count = self.model.get_page_count()
        images = []
        for i in range(count):
            img = self.model.get_page_image(i)
            images.append(img)
        
        self.view.update_pages_view(images)