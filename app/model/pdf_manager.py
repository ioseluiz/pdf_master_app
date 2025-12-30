import fitz  # PyMuPDF
import io
import os

class PDFModel:
    def __init__(self):
        self.current_doc = fitz.open()
        self.page_mapping = []  # [(nombre_archivo, numero_pagina_original), ...]

    def load_pdf(self, filepath):
        """Carga un PDF y registra el origen de sus páginas."""
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
        # Mantenemos la escala 0.3 para optimizar memoria en la vista
        pix = page.get_pixmap(matrix=fitz.Matrix(0.3, 0.3))
        return pix.tobytes("png")

    def get_page_label(self, index):
        """Genera la etiqueta para la vista."""
        if 0 <= index < len(self.page_mapping):
            fname, pnum = self.page_mapping[index]
            if len(fname) > 15:
                fname = fname[:12] + "..."
            return f"{fname}\nPág {pnum}"
        return f"Pág {index + 1}"

    def reorder_and_save(self, new_order_indices, output_path, quality='standard'):
        """
        Guarda el PDF con estrategia de 'Doble Fallback' para archivos corruptos.
        """
        new_doc = fitz.open()
        
        # 1. Construir nuevo documento
        for index in new_order_indices:
            new_doc.insert_pdf(self.current_doc, from_page=index, to_page=index)
            
        # Variables de control
        warning_msg = ""
        
        # Valores por defecto según calidad
        garbage_level = 0
        deflate_option = True

        # 2. INTENTO DE OPTIMIZACIÓN (rewrite_images)
        # Solo intentamos si no es calidad Alta
        if quality != 'high':
            try:
                if quality == 'low':
                    # 72 DPI, Calidad 50
                    new_doc.rewrite_images(dpi_target=72, quality=50, bitonal=False)
                    garbage_level = 4
                else: # standard
                    # 150 DPI, Calidad 75
                    new_doc.rewrite_images(dpi_target=150, quality=75)
                    garbage_level = 3
                    
            except Exception as e:
                # Si falla la re-compresión, abortamos optimización y bajamos a modo seguro
                print(f"Advertencia: Falló rewrite_images ({e}). Se usará modo seguro.")
                warning_msg = " (Sin optimización de imagen por error interno)"
                garbage_level = 0
                deflate_option = False # No comprimir si ya dio error
        else:
            # Calidad Alta
            garbage_level = 1
            deflate_option = True

        # 3. INTENTO DE GUARDADO (save)
        # Aquí es donde fallaba antes si garbage=4 tocaba el stream roto
        try:
            new_doc.save(output_path, garbage=garbage_level, deflate=deflate_option)
            
        except Exception as e:
            # BLOQUE DE SEGURIDAD CRÍTICO
            print(f"Error al guardar optimizado ({e}). Intentando guardado RAW...")
            try:
                # Fallback final: Guardado CRUDO.
                # garbage=0: No toca estructura.
                # deflate=False: No intenta descomprimir/recomprimir streams.
                # clean=False: No intenta sanear el PDF.
                new_doc.save(output_path, garbage=0, deflate=False, clean=False)
                warning_msg = " (Guardado en modo RAW por corrupción en archivo original)"
            except Exception as e2:
                # Si esto falla, el archivo es insalvable
                new_doc.close()
                raise RuntimeError(f"Imposible guardar el archivo: {e2}")

        new_doc.close()
        
        return "Archivo guardado correctamente" + warning_msg

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