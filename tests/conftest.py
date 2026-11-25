import os
import sys

import pytest
import pymupdf

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app.model.converters import is_word_available  # noqa: E402

requires_word = pytest.mark.skipif(
    not is_word_available(), reason="Microsoft Word no disponible en este equipo"
)


@pytest.fixture
def tmp_image(tmp_path):
    """Imagen PNG apaisada de 300x200 px."""
    path = tmp_path / "foto.png"
    pix = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 300, 200), False)
    pix.set_rect(pix.irect, (200, 30, 30))
    pix.save(str(path))
    return str(path)


@pytest.fixture
def tmp_pdf(tmp_path):
    """PDF real de 3 páginas con texto."""
    path = tmp_path / "base.pdf"
    doc = pymupdf.open()
    for i in range(3):
        page = doc.new_page(width=612, height=792)
        page.insert_text((72, 72), f"Página {i + 1}")
    doc.save(str(path))
    doc.close()
    return str(path)


@pytest.fixture
def tmp_docx(tmp_path):
    """Documento Word de 2 páginas generado con python-docx."""
    docx = pytest.importorskip("docx")
    path = tmp_path / "informe.docx"
    document = docx.Document()
    document.add_paragraph("Primera página del informe.")
    document.add_page_break()
    document.add_paragraph("Segunda página del informe.")
    document.save(str(path))
    return str(path)
