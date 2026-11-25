import pymupdf

from app.model.converters import convert_image_to_pdf_bytes
from app.model.pdf_manager import PDFModel
from tests.conftest import requires_word


def test_register_converted_then_load(tmp_image):
    model = PDFModel()
    model.register_converted_pdf(tmp_image, convert_image_to_pdf_bytes(tmp_image))
    model.load_pdf(tmp_image)
    assert model.get_page_count() == 1
    assert model.get_page_image(0).startswith(b"\x89PNG")
    assert model.get_page_label(0).endswith("Pág 1")


def test_ensure_converted_fallback_for_image(tmp_image):
    model = PDFModel()
    model.load_pdf(tmp_image)  # sin registro previo: el modelo convierte solo
    assert model.has_converted_pdf(tmp_image)
    assert model.get_page_count() == 1


def test_load_pdf_real(tmp_pdf):
    model = PDFModel()
    model.load_pdf(tmp_pdf)
    assert model.get_page_count() == 3
    assert not model.has_converted_pdf(tmp_pdf)


def test_reorder_and_save_mixed(tmp_pdf, tmp_image, tmp_path):
    model = PDFModel()
    model.load_pdf(tmp_pdf)
    model.load_pdf(tmp_image)
    model.rotate_page(3, clockwise=True)
    out = tmp_path / "final.pdf"

    msg = model.reorder_and_save([3, 0, 2], str(out), quality='standard')

    assert "correctamente" in msg
    doc = pymupdf.open(str(out))
    assert len(doc) == 3
    assert doc[0].rotation == 90
    assert "Página 1" in doc[1].get_text()
    assert "Página 3" in doc[2].get_text()
    doc.close()


def test_clear_resets_everything(tmp_image):
    model = PDFModel()
    model.load_pdf(tmp_image)
    model.get_page_image(0)
    model.clear()
    assert model.get_page_count() == 0
    assert not model.has_converted_pdf(tmp_image)


@requires_word
def test_docx_in_model_and_merge(tmp_pdf, tmp_docx, tmp_path):
    model = PDFModel()
    model.load_pdf(tmp_docx)  # ensure_converted abre Word de forma síncrona
    model.load_pdf(tmp_pdf)
    assert model.get_page_count() == 5

    out = tmp_path / "mixto.pdf"
    model.reorder_and_save([2, 0, 1, 3, 4], str(out), quality='high')
    doc = pymupdf.open(str(out))
    assert len(doc) == 5
    assert "Página 1" in doc[0].get_text()
    assert "Primera página" in doc[1].get_text()
    doc.close()
