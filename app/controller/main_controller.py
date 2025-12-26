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
            for f in files:
                try:
                    self.model.load_pdf(f)
                except Exception as e:
                    self.view.show_message("Error", f"No se pudo cargar {f}\n{str(e)}", "error")
            
            self._refresh_preview()

    def handle_rotate_left(self):
        self._rotate_selected_pages(clockwise=False)

    def handle_rotate_right(self):
        self._rotate_selected_pages(clockwise=True)

    def _rotate_selected_pages(self, clockwise):
        """Lógica común para rotar."""
        # Obtenemos los items seleccionados directamente del widget
        # No usamos 'get_selected_indices' simple porque necesitamos acceso al objeto item
        list_widget = self.view.pages_list
        selected_items = list_widget.selectedItems()

        if not selected_items:
            return

        for item in selected_items:
            # 1. Averiguar qué página del PDF es (Índice Original)
            # Recuerda: custom_widgets define ROLE_ORIGINAL_INDEX = Qt.UserRole + 1
            original_index = item.data(Qt.UserRole + 1)
            
            # 2. Rotar en el modelo
            self.model.rotate_page(original_index, clockwise)
            
            # 3. Obtener la NUEVA imagen generada (rotada)
            new_img = self.model.get_page_image(original_index)
            
            # 4. Actualizar la vista inmediatamente
            # Necesitamos la fila visual actual para decirle al widget cuál actualizar
            current_row = list_widget.row(item)
            list_widget.update_item_image_data(current_row, new_img)

    def handle_delete_page(self):
        # Obtenemos los índices visuales (fila en la grilla)
        indices_to_delete = self.view.get_selected_indices()
        
        if not indices_to_delete:
            return

        # En este enfoque simplificado, como el modelo y la vista deben sincronizarse,
        # y PyMuPDF borra por índice, es más seguro reconstruir el PDF
        # o borrar del modelo inmediatamente.
        
        # Para mantener consistencia simple:
        # 1. Borramos del modelo (se requiere cuidado con índices cambiantes)
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
                
                # Nota: Como el usuario puede haber arrastrado items,
                # `current_order` contiene los índices de cómo están las páginas
                # en el modelo actualmente.
                
                # Sin embargo, DraggableListWidget solo cambia la visualización.
                # Al guardar, le decimos al modelo: "Toma las páginas en este orden y guárdalas".
                
                # Como el modelo ya se actualizó al borrar páginas, los índices en la vista (0 a N)
                # deberían coincidir con lo que ve el usuario si reordenamos.
                
                # El truco: La vista tiene items. Cada item tiene data oculta con el índice.
                # Pero si borramos, los índices cambian. 
                # Estrategia robusta: Guardar lo que está en pantalla.
                
                # Simplificación para este ejercicio:
                # El modelo tiene las páginas. La vista tiene el orden deseado de esas páginas.
                # Al arrastrar y soltar, cambiamos el orden en la UI.
                
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