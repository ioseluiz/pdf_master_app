import fitz  # PyMuPDF
import io
import os

class PDFModel:
    def __init__(self):
        self.current_doc = fitz.open()
        self.page_mapping = [] 

    def load_pdf(self, filepath):
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
        if 0 <= index < len(self.page_mapping):
            fname, pnum = self.page_mapping[index]
            if len(fname) > 15:
                fname = fname[:12] + "..."
            return f"{fname}\nPág {pnum}"
        return f"Pág {index + 1}"

    def reorder_and_save(self, new_order_indices, output_path, quality='standard'):
        """
        Guarda el PDF aplicando re-compresión de imágenes real para reducir tamaño.
        """
        new_doc = fitz.open()
        
        # 1. Copiamos las páginas en el nuevo orden
        for index in new_order_indices:
            new_doc.insert_pdf(self.current_doc, from_page=index, to_page=index)
        
        # 2. Aplicamos la optimización de imágenes según la calidad
        # rewrite_images modifica el documento en memoria re-comprimiendo las imágenes
        
        try:
            if quality == 'low':
                # BAJA: 72 DPI (Web/Email), Calidad JPG 50, escala de grises opcional
                # Esto reducirá drásticamente el tamaño si hay muchas imágenes.
                new_doc.rewrite_images(dpi_target=72, quality=50, bitonal=False)
                garbage_level = 4
                
            elif quality == 'standard':
                # STANDARD: 150 DPI (Pantalla buena), Calidad JPG 75
                # Balance entre peso y legibilidad.
                new_doc.rewrite_images(dpi_target=150, quality=75)
                garbage_level = 3
                
            else: # high
                # ALTA: No tocamos las imágenes (Original).
                # Solo limpiamos metadatos básicos.
                garbage_level = 1
                
        except AttributeError:
            # Fallback por si la versión de PyMuPDF es muy antigua, aunque 1.26.7 lo soporta
            print("Aviso: 'rewrite_images' no disponible. Se guardará sin optimización de imagen.")
            garbage_level = 4 if quality == 'low' else 0

        # 3. Guardado final con limpieza de estructura
        new_doc.save(output_path, garbage=garbage_level, deflate=True)
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