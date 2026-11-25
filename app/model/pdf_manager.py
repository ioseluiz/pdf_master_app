import os

import pymupdf

from .converters import (  # noqa: F401  (re-export para compatibilidad)
    IMAGE_EXTENSIONS, WORD_EXTENSIONS, CONVERTIBLE_EXTENSIONS,
    LETTER_PORTRAIT, LETTER_LANDSCAPE,
    convert_image_to_pdf_bytes, convert_word_to_pdf_bytes,
)


class PDFModel:
    def __init__(self):
        # Cada entrada: {'path': str, 'name': str, 'page_src': int, 'rotation': int}
        # 'path' = ruta completa al archivo fuente
        # 'page_src' = índice 0-based de la página dentro del archivo fuente
        self.pages = []
        self._doc_cache = {}  # filepath -> pymupdf.Document abierto para renderizado
        self._converted_pdf_bytes = {}  # filepath (imagen/Word) -> bytes del PDF generado

    # --- Fuentes convertidas (imágenes, Word) ---
    def register_converted_pdf(self, filepath, pdf_bytes):
        """Registra el PDF ya convertido (normalmente por el hilo de carga)."""
        self._converted_pdf_bytes[filepath] = pdf_bytes

    def has_converted_pdf(self, filepath):
        return filepath in self._converted_pdf_bytes

    def get_converted_pdf(self, filepath):
        return self._converted_pdf_bytes.get(filepath)

    def ensure_converted(self, filepath):
        """Convierte de forma síncrona si hace falta. En la app es siempre un
        acierto de caché (el worker convierte antes); permite usar el modelo
        sin Qt en pruebas."""
        if filepath in self._converted_pdf_bytes:
            return
        ext = os.path.splitext(filepath)[1].lower()
        if ext in IMAGE_EXTENSIONS:
            self._converted_pdf_bytes[filepath] = convert_image_to_pdf_bytes(filepath)
        elif ext in WORD_EXTENSIONS:
            self._converted_pdf_bytes[filepath] = convert_word_to_pdf_bytes(filepath)

    def _open_source(self, filepath):
        """Abre el documento fuente de una página: un PDF real, o el PDF generado
        a partir de una imagen o documento Word (cacheado en memoria)."""
        if filepath in self._converted_pdf_bytes:
            return pymupdf.open(stream=self._converted_pdf_bytes[filepath], filetype="pdf")
        return pymupdf.open(filepath)

    def load_pdf(self, filepath):
        self.ensure_converted(filepath)

        doc = self._open_source(filepath)
        name = os.path.basename(filepath)
        count = len(doc)
        doc.close()
        for i in range(count):
            self.pages.append({'path': filepath, 'name': name, 'page_src': i, 'rotation': 0})

    def get_page_count(self):
        return len(self.pages)

    def _get_cached_doc(self, filepath):
        if filepath not in self._doc_cache:
            self._doc_cache[filepath] = self._open_source(filepath)
        return self._doc_cache[filepath]

    def get_page_image(self, index):
        if index < 0 or index >= len(self.pages):
            return None
        entry = self.pages[index]
        doc = self._get_cached_doc(entry['path'])
        page = doc.load_page(entry['page_src'])
        mat = pymupdf.Matrix(0.2, 0.2)
        if entry['rotation']:
            mat = mat.prerotate(entry['rotation'])
        pix = page.get_pixmap(matrix=mat)
        return pix.tobytes("png")

    def get_page_label(self, index):
        if 0 <= index < len(self.pages):
            entry = self.pages[index]
            name = entry['name']
            page_num = entry['page_src'] + 1
            if len(name) > 15:
                name = name[:12] + "..."
            return f"{name}\nPág {page_num}"
        return f"Pág {index + 1}"

    def delete_page(self, index):
        if 0 <= index < len(self.pages):
            self.pages.pop(index)

    def rotate_page(self, index, clockwise=True):
        if 0 <= index < len(self.pages):
            delta = 90 if clockwise else -90
            self.pages[index]['rotation'] = (self.pages[index]['rotation'] + delta) % 360

    def clear(self):
        for doc in self._doc_cache.values():
            try:
                doc.close()
            except Exception:
                pass
        self._doc_cache.clear()
        self._converted_pdf_bytes.clear()
        self.pages.clear()

    def reorder_and_save(self, new_order_indices, output_path, quality='standard'):
        new_doc = pymupdf.open()
        open_docs = {}
        warning_msg = ""

        try:
            for index in new_order_indices:
                entry = self.pages[index]
                filepath = entry['path']

                if filepath not in open_docs:
                    open_docs[filepath] = self._open_source(filepath)

                src_doc = open_docs[filepath]
                new_doc.insert_pdf(src_doc, from_page=entry['page_src'], to_page=entry['page_src'])

                if entry['rotation']:
                    last_page = new_doc[-1]
                    new_rot = (last_page.rotation + entry['rotation']) % 360
                    last_page.set_rotation(new_rot)

            garbage_level = 0
            deflate_option = True

            if quality != 'high':
                try:
                    if quality == 'low':
                        new_doc.rewrite_images(dpi_target=72, quality=50, bitonal=False)
                        garbage_level = 4
                    else:
                        new_doc.rewrite_images(dpi_target=150, quality=75)
                        garbage_level = 3
                except Exception as e:
                    print(f"Advertencia: Falló rewrite_images ({e}). Se usará modo seguro.")
                    warning_msg = " (Sin optimización de imagen por error interno)"
                    garbage_level = 0
                    deflate_option = False
            else:
                garbage_level = 1
                deflate_option = True

            try:
                new_doc.save(output_path, garbage=garbage_level, deflate=deflate_option)
            except Exception as e:
                print(f"Error al guardar optimizado ({e}). Intentando guardado RAW...")
                try:
                    new_doc.save(output_path, garbage=0, deflate=False, clean=False)
                    warning_msg = " (Guardado en modo RAW por corrupción en archivo original)"
                except Exception as e2:
                    raise RuntimeError(f"Imposible guardar el archivo: {e2}")

        finally:
            new_doc.close()
            for doc in open_docs.values():
                try:
                    doc.close()
                except Exception:
                    pass

        return "Archivo guardado correctamente" + warning_msg
