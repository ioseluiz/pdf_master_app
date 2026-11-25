import glob
import os
import tempfile

import pytest
import pymupdf

from app.model import converters
from app.model.converters import (
    ConversionError, WordConverter, convert_image_to_pdf_bytes, needs_conversion,
    LETTER_LANDSCAPE, LETTER_PORTRAIT,
)
from tests.conftest import requires_word


def test_needs_conversion():
    assert needs_conversion("a.docx")
    assert needs_conversion("a.DOC")
    assert needs_conversion("a.JPG")
    assert not needs_conversion("a.pdf")
    assert not needs_conversion("a.xlsx")


def test_image_to_pdf_landscape(tmp_image):
    data = convert_image_to_pdf_bytes(tmp_image)
    assert data.startswith(b"%PDF")
    doc = pymupdf.open(stream=data, filetype="pdf")
    assert len(doc) == 1
    w, h = doc[0].rect.width, doc[0].rect.height
    assert (round(w), round(h)) == LETTER_LANDSCAPE
    assert len(doc[0].get_images()) == 1
    doc.close()


def test_image_to_pdf_portrait(tmp_path):
    path = tmp_path / "vertical.png"
    pix = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 100, 400), False)
    pix.set_rect(pix.irect, (10, 10, 200))
    pix.save(str(path))
    doc = pymupdf.open(stream=convert_image_to_pdf_bytes(str(path)), filetype="pdf")
    assert (round(doc[0].rect.width), round(doc[0].rect.height)) == LETTER_PORTRAIT
    doc.close()


def test_missing_file_raises_without_launching_word(tmp_path, monkeypatch):
    launched = []
    monkeypatch.setattr(WordConverter, "_ensure_word", lambda self: launched.append(1))
    with WordConverter() as wc:
        with pytest.raises(ConversionError) as info:
            wc.to_pdf_bytes(str(tmp_path / "no_existe.docx"))
    assert "No se encontró" in str(info.value)
    assert not launched


def test_word_not_available_message(monkeypatch, tmp_docx):
    monkeypatch.setattr(converters, "is_word_available", lambda: False)
    with WordConverter() as wc:
        with pytest.raises(converters.WordNotAvailableError) as info:
            wc.to_pdf_bytes(tmp_docx)
    assert "Word no está instalado" in str(info.value)


@requires_word
def test_docx_to_pdf(tmp_docx):
    import pythoncom
    before_dirs = set(glob.glob(os.path.join(tempfile.gettempdir(), "pdfmaster_*")))
    ifaces_before = pythoncom._GetInterfaceCount()

    with WordConverter() as wc:
        data = wc.to_pdf_bytes(tmp_docx)
        tmpdir = wc._tmpdir
        assert os.path.isdir(tmpdir)

    assert data.startswith(b"%PDF")
    doc = pymupdf.open(stream=data, filetype="pdf")
    assert len(doc) == 2
    assert "Primera página" in doc[0].get_text()
    assert "Segunda página" in doc[1].get_text()
    doc.close()

    # Sin basura: ni temp dir, ni bloqueo ~$ junto al origen, ni referencias COM vivas.
    assert not os.path.exists(tmpdir)
    assert set(glob.glob(os.path.join(tempfile.gettempdir(), "pdfmaster_*"))) == before_dirs
    assert not glob.glob(os.path.join(os.path.dirname(tmp_docx), "~$*"))
    assert pythoncom._GetInterfaceCount() == ifaces_before


@requires_word
def test_docx_reuses_single_word_instance(tmp_docx):
    with WordConverter() as wc:
        wc.to_pdf_bytes(tmp_docx)
        first = wc._word
        wc.to_pdf_bytes(tmp_docx)
        assert wc._word is first


@requires_word
def test_docx_forward_slash_path(tmp_docx):
    """Qt entrega rutas con '/', que Word COM rechaza si no se normalizan."""
    with WordConverter() as wc:
        data = wc.to_pdf_bytes(tmp_docx.replace("\\", "/"))
    assert data.startswith(b"%PDF")
