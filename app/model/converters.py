"""Conversores de formatos no-PDF a bytes PDF.

Módulo sin dependencias de Qt para poder usarse desde el modelo, desde el
hilo de carga y desde las pruebas.

- Imágenes: se incrustan en una página Carta con PyMuPDF.
- Word (.docx/.doc): se exporta con Microsoft Word vía COM (pywin32).
  MuPDF no abre documentos Word; sin Word instalado se lanza
  WordNotAvailableError con un mensaje claro.
"""
import csv
import gc
import io
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import uuid

import pymupdf

IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.bmp', '.tif', '.tiff'}
WORD_EXTENSIONS = {'.docx', '.doc'}
CONVERTIBLE_EXTENSIONS = IMAGE_EXTENSIONS | WORD_EXTENSIONS

# Tamaño de página estándar Carta (Letter), en puntos.
LETTER_PORTRAIT = (612, 792)
LETTER_LANDSCAPE = (792, 612)

# --- Constantes de Word/Office (enteros: sin makepy/gencache) ---
WD_EXPORT_FORMAT_PDF = 17                  # WdExportFormat.wdExportFormatPDF
WD_EXPORT_OPTIMIZE_FOR_PRINT = 0           # WdExportOptimizeFor
WD_EXPORT_ALL_DOCUMENT = 0                 # WdExportRange
WD_EXPORT_DOCUMENT_CONTENT = 0             # WdExportItem (sin marcas de revisión)
WD_EXPORT_CREATE_NO_BOOKMARKS = 0          # WdExportCreateBookmarks
WD_DO_NOT_SAVE_CHANGES = 0                 # WdSaveOptions
WD_ALERTS_NONE = 0                         # WdAlertLevel
MSO_AUTOMATION_SECURITY_FORCE_DISABLE = 3  # MsoAutomationSecurity
WD_ERR_PASSWORD_INCORRECT = 5408           # Error de Word: contraseña incorrecta

# HRESULTs relevantes (como enteros con signo, tal como los expone pywin32)
CO_E_CLASSSTRING = -2147221005
REGDB_E_CLASSNOTREG = -2147221164
DISP_E_EXCEPTION = -2147352567
RPC_S_SERVER_UNAVAILABLE = -2147023174
RPC_E_DISCONNECTED = -2147417848
RPC_E_CALL_REJECTED = -2147418111
RPC_E_SERVERCALL_RETRYLATER = -2147417846

_HRESULT_WORD_MISSING = {CO_E_CLASSSTRING, REGDB_E_CLASSNOTREG}
_HRESULT_WORD_GONE = {RPC_S_SERVER_UNAVAILABLE, RPC_E_DISCONNECTED}
_HRESULT_WORD_BUSY = {RPC_E_CALL_REJECTED, RPC_E_SERVERCALL_RETRYLATER}

# Contraseña inventada: para archivos sin protección Word la ignora; para
# archivos protegidos lanza el error 5408 en lugar de mostrar un diálogo modal.
_NONSENSE_PASSWORD = "pdfmaster-no-password-§"

MSG_WORD_NOT_AVAILABLE = (
    "Microsoft Word no está instalado o no está registrado. "
    "Instale Word para agregar documentos .docx/.doc."
)


class ConversionError(RuntimeError):
    """Fallo de conversión con mensaje listo para mostrar al usuario."""


class WordNotAvailableError(ConversionError):
    """Microsoft Word no está disponible en este equipo."""


def needs_conversion(filepath):
    return os.path.splitext(filepath)[1].lower() in CONVERTIBLE_EXTENSIONS


def is_word_available():
    """Comprueba en el registro si Word.Application está registrado (sin lanzar COM)."""
    if sys.platform != 'win32':
        return False
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, r"Word.Application\CLSID"):
            return True
    except OSError:
        return False


# ---------------------------------------------------------------------------
# Imágenes
# ---------------------------------------------------------------------------
def convert_image_to_pdf_bytes(filepath):
    """Convierte una imagen en un PDF de una página, ajustada a tamaño Carta
    preservando su proporción (sin recorte ni deformación)."""
    pix = pymupdf.Pixmap(filepath)
    img_w, img_h = pix.width, pix.height
    pix = None

    page_w, page_h = LETTER_LANDSCAPE if img_w > img_h else LETTER_PORTRAIT
    scale = min(page_w / img_w, page_h / img_h)
    fit_w, fit_h = img_w * scale, img_h * scale
    x0, y0 = (page_w - fit_w) / 2, (page_h - fit_h) / 2
    rect = pymupdf.Rect(x0, y0, x0 + fit_w, y0 + fit_h)

    doc = pymupdf.open()
    page = doc.new_page(width=page_w, height=page_h)
    page.insert_image(rect, filename=filepath)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


# ---------------------------------------------------------------------------
# Word (COM)
# ---------------------------------------------------------------------------
def _winword_pids():
    """PIDs de WINWORD.EXE en ejecución (vía tasklist, sin ventana de consola)."""
    try:
        creationflags = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
        result = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq WINWORD.EXE", "/FO", "CSV", "/NH"],
            capture_output=True, text=True, stdin=subprocess.DEVNULL,
            creationflags=creationflags, timeout=15,
        )
    except Exception:
        return set()
    pids = set()
    for row in csv.reader(io.StringIO(result.stdout)):
        if len(row) >= 2 and row[0].strip().upper() == 'WINWORD.EXE':
            try:
                pids.add(int(row[1]))
            except ValueError:
                pass
    return pids


def _strip_mark_of_the_web(src_path, tmpdir):
    """Si el archivo trae Zone.Identifier (descargado de Internet), Word lo abriría
    en Vista Protegida. Se copia a temp y se elimina el flujo alterno."""
    ads = src_path + ":Zone.Identifier"
    try:
        has_motw = os.path.exists(ads)
    except Exception:
        has_motw = False
    if not has_motw:
        return src_path
    dst = os.path.join(tmpdir, os.path.basename(src_path))
    shutil.copyfile(src_path, dst)
    try:
        os.remove(dst + ":Zone.Identifier")
    except OSError:
        pass
    return dst


def _translate_com_error(exc, src_path):
    """Convierte un pywintypes.com_error en ConversionError con mensaje en español."""
    name = os.path.basename(src_path)
    hresult = getattr(exc, 'hresult', None)
    excepinfo = getattr(exc, 'excepinfo', None) or ()

    if hresult in _HRESULT_WORD_MISSING:
        return WordNotAvailableError(MSG_WORD_NOT_AVAILABLE)
    if hresult in _HRESULT_WORD_GONE:
        return ConversionError(
            f"Word no respondió al convertir {name} (tiempo agotado). El archivo se omitió."
        )
    if hresult == DISP_E_EXCEPTION and len(excepinfo) >= 6:
        scode = excepinfo[5] or 0
        if (scode & 0xFFFF) == WD_ERR_PASSWORD_INCORRECT:
            return ConversionError(
                f"El documento {name} está protegido con contraseña y no se puede convertir."
            )
        text = (excepinfo[2] or '').strip() or (getattr(exc, 'strerror', '') or '')
        return ConversionError(f"Word no pudo abrir {name}: {text}")
    detail = getattr(exc, 'strerror', None) or str(exc)
    return ConversionError(f"Word no pudo convertir {name}: {detail}")


class WordConverter:
    """Convierte documentos Word a PDF con una instancia propia y oculta de Word.

    Uso (siempre dentro del mismo hilo):
        with WordConverter() as wc:
            pdf_bytes = wc.to_pdf_bytes(ruta)

    - Crea Word con DispatchEx (instancia NUEVA; Dispatch se engancharía al Word
      abierto del usuario y Quit() le cerraría sus documentos).
    - La instancia se crea de forma perezosa en la primera conversión y se
      cierra al salir del bloque `with`.
    - Un watchdog mata el proceso WINWORD propio si una llamada COM se queda
      bloqueada (p. ej. un diálogo modal inesperado) más de `timeout_s`.
    """

    def __init__(self, timeout_s=180.0, busy_retries=3):
        self.timeout_s = timeout_s
        self.busy_retries = busy_retries
        self._word = None
        self._pid = None
        self._tmpdir = None
        self._killed = False

    # --- ciclo de vida ---
    def __enter__(self):
        import pythoncom
        pythoncom.CoInitialize()
        self._tmpdir = tempfile.mkdtemp(prefix="pdfmaster_")
        self._word = None
        self._pid = None
        self._killed = False
        return self

    def __exit__(self, exc_type, exc, tb):
        import pythoncom
        try:
            if self._word is not None and not self._killed:
                try:
                    # Si el usuario abrió documentos en nuestra instancia oculta
                    # (doble clic en el Explorador), se la entregamos visible en
                    # vez de cerrarle su trabajo.
                    if self._word.Documents.Count:
                        self._word.Visible = True
                    else:
                        self._word.Quit(SaveChanges=WD_DO_NOT_SAVE_CHANGES)
                except Exception:
                    pass
        finally:
            self._word = None
            self._pid = None
            gc.collect()
            if self._tmpdir:
                shutil.rmtree(self._tmpdir, ignore_errors=True)
                self._tmpdir = None
            pythoncom.CoUninitialize()
        return False

    def _ensure_word(self):
        if self._word is not None:
            return
        if not is_word_available():
            raise WordNotAvailableError(MSG_WORD_NOT_AVAILABLE)
        import pywintypes
        from win32com.client import DispatchEx
        before = _winword_pids()
        try:
            word = DispatchEx("Word.Application")
        except pywintypes.com_error as e:
            raise _translate_com_error(e, "Word") from None
        new_pids = _winword_pids() - before
        self._pid = next(iter(new_pids), None)
        self._killed = False
        word.Visible = False
        word.DisplayAlerts = WD_ALERTS_NONE
        word.AutomationSecurity = MSO_AUTOMATION_SECURITY_FORCE_DISABLE
        self._word = word

    def _kill_word(self):
        """Watchdog: termina el proceso WINWORD propio para desbloquear la llamada COM."""
        pid = self._pid
        self._killed = True
        if pid is None:
            return
        try:
            import win32api
            import win32con
            handle = win32api.OpenProcess(win32con.PROCESS_TERMINATE, False, pid)
            try:
                win32api.TerminateProcess(handle, 1)
            finally:
                win32api.CloseHandle(handle)
        except Exception:
            try:
                creationflags = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
                subprocess.run(["taskkill", "/PID", str(pid), "/F"],
                               capture_output=True, stdin=subprocess.DEVNULL,
                               creationflags=creationflags, timeout=15)
            except Exception:
                pass

    # --- conversión ---
    def to_pdf_bytes(self, src_path):
        name = os.path.basename(src_path)
        if not os.path.isfile(src_path):
            raise ConversionError(f"No se encontró el archivo {name}.")

        import pywintypes

        attempts = 0
        while True:
            attempts += 1
            self._ensure_word()
            try:
                return self._export_once(src_path)
            except pywintypes.com_error as e:
                if self._killed:
                    # El watchdog mató Word: descartar la instancia muerta para que
                    # el siguiente archivo relance Word limpio.
                    self._word = None
                    self._pid = None
                    self._killed = False
                    raise ConversionError(
                        f"Word no respondió al convertir {name} (tiempo agotado). "
                        "El archivo se omitió."
                    ) from None
                hresult = getattr(e, 'hresult', None)
                if hresult in _HRESULT_WORD_BUSY and attempts < self.busy_retries:
                    time.sleep(1.0)
                    continue
                if hresult in _HRESULT_WORD_GONE:
                    self._word = None
                    self._pid = None
                raise _translate_com_error(e, src_path) from None

    def _export_once(self, src_path):
        src = _strip_mark_of_the_web(src_path, self._tmpdir)
        out = os.path.join(self._tmpdir, f"{uuid.uuid4().hex}.pdf")

        timer = threading.Timer(self.timeout_s, self._kill_word)
        timer.daemon = True
        timer.start()
        doc = None
        try:
            doc = self._word.Documents.Open(
                FileName=src,
                ConfirmConversions=False,
                ReadOnly=True,
                AddToRecentFiles=False,
                PasswordDocument=_NONSENSE_PASSWORD,
                Visible=False,
                OpenAndRepair=False,
                NoEncodingDialog=True,
            )
            doc.ExportAsFixedFormat(
                OutputFileName=out,
                ExportFormat=WD_EXPORT_FORMAT_PDF,
                OpenAfterExport=False,
                OptimizeFor=WD_EXPORT_OPTIMIZE_FOR_PRINT,
                Range=WD_EXPORT_ALL_DOCUMENT,
                Item=WD_EXPORT_DOCUMENT_CONTENT,
                IncludeDocProps=True,
                KeepIRM=False,  # No propagar etiquetas de sensibilidad (PDF cifrado)
                CreateBookmarks=WD_EXPORT_CREATE_NO_BOOKMARKS,
                DocStructureTags=False,
                BitmapMissingFonts=True,
                UseISO19005_1=False,
            )
        finally:
            timer.cancel()
            if doc is not None:
                try:
                    doc.Close(SaveChanges=WD_DO_NOT_SAVE_CHANGES)
                except Exception:
                    pass
                doc = None
            if src != src_path:
                try:
                    os.remove(src)
                except OSError:
                    pass

        with open(out, "rb") as f:
            data = f.read()
        try:
            os.remove(out)
        except OSError:
            pass
        if not data.startswith(b"%PDF"):
            raise ConversionError(
                f"Word generó un archivo inválido al convertir {os.path.basename(src_path)}."
            )
        return data


def convert_word_to_pdf_bytes(filepath, timeout_s=180.0):
    """Conversión puntual de un solo documento Word (abre y cierra Word)."""
    with WordConverter(timeout_s=timeout_s) as wc:
        return wc.to_pdf_bytes(filepath)
