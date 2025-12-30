import fitz  # PyMuPDF
import io
import os

class PDFModel:
    def __init__(self):
        self.current_doc = fitz.open()
        # Lista para rastrear el origen: [(nombre_archivo, numero_pagina_original), ...]
        self.page_mapping = [] 

    def load_pdf(self, filepath):
        """Carga un PDF, lo fusiona y registra el origen de sus páginas."""
        new_doc = fitz.open(filepath)
        filename = os.path.basename(filepath)
        page_count = len(new_doc)
        
        self.current_doc.insert_pdf(new_doc)
        
        for i in range(page_count):
            self.page_mapping.append((filename, i + 1))
            
        new_doc.close()

    def get_page_count(self):
        return len(self.current_doc)

    def get_page_image(self, page_index):
        if page_index < 0 or page_index >= len(self.current_doc):
            return None
        page = self.current_doc.load_page(page_index)
        pix = page.get_pixmap(matrix=fitz.Matrix(0.5, 0.5))
        return pix.tobytes("png")

    def get_page_label(self, index):
        """Genera la etiqueta asegurando que el número de página quede visible."""
        if 0 <= index < len(self.page_mapping):
            fname, pnum = self.page_mapping[index]
            
            # 1. Truncamos SOLO el nombre si es muy largo (ej: más de 15 caracteres)
            # Esto evita que el nombre ocupe dos líneas y empuje el número fuera
            if len(fname) > 15:
                fname = fname[:12] + "..."
            
            # 2. Forzamos el salto de línea (\n)
            # Así: Línea 1 = Nombre (posiblemente cortado)
            #      Línea 2 = Pág X (Siempre visible)
            return f"{fname}\nPág {pnum}"
            
        return f"Pág {index + 1}"

    def reorder_and_save(self, new_order_indices, output_path):
        new_doc = fitz.open()
        for index in new_order_indices:
            new_doc.insert_pdf(self.current_doc, from_page=index, to_page=index)
        new_doc.save(output_path)
        new_doc.close()

    def delete_page(self, index):
        self.current_doc.delete_page(index)
        if 0 <= index < len(self.page_mapping):
            self.page_mapping.pop(index)

    def rotate_page(self, page_index, clockwise=True):
        if page_index < 0 or page_index >= len(self.current_doc):
            return
        page = self.current_doc[page_index]
        current_rot = page.rotation
        if clockwise:
            new_rot = (current_rot + 90) % 360
        else:
            new_rot = (current_rot - 90) % 360
        page.set_rotation(new_rot)