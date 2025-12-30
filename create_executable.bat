@echo off
TITLE Generador Automatico PDF Master
CLS

ECHO ========================================================
ECHO      CONSTRUCTOR AUTOMATICO DE PDF MASTER APP
ECHO ========================================================
ECHO.

:: 1. COMPROBACION DEL ENTORNO VIRTUAL
:: Verificamos si la carpeta 'venv' existe. Si no, la creamos.
IF NOT EXIST "venv" (
    ECHO [!] No se detecto entorno virtual. Creando carpeta 'venv'...
    python -m venv venv
) ELSE (
    ECHO [*] Entorno virtual detectado.
)

:: 2. ACTIVACION
:: Activamos el entorno para asegurar que usamos las versiones correctas
ECHO [*] Activando entorno virtual...
CALL venv\Scripts\activate.bat

:: 3. INSTALACION DE DEPENDENCIAS
:: Esto asegura que pyinstaller y tus librerias esten instaladas
ECHO.
ECHO [*] Verificando e instalando librerias necesarias...
pip install -r requirements.txt
:: PyInstaller no esta en tu requirements.txt, asi que lo forzamos aqui
pip install pyinstaller

:: 4. LIMPIEZA PREVIA (Opcional)
:: Borramos compilaciones anteriores para evitar errores de cache
ECHO.
ECHO [*] Limpiando archivos temporales anteriores...
IF EXIST "build" RD /S /Q "build"
IF EXIST "dist" RD /S /Q "dist"

:: 5. GENERACION DEL EJECUTABLE
:: Usamos tu archivo .spec que ya tiene la configuracion perfecta
ECHO.
ECHO [*] Generando el archivo .exe (Esto puede tardar unos minutos)...
ECHO.
pyinstaller --clean --noconfirm PDFMaster_App.spec

:: 6. FINALIZACION
ECHO.
ECHO ========================================================
ECHO      PROCESO COMPLETADO
ECHO ========================================================
ECHO.
ECHO El ejecutable nuevo se encuentra en la carpeta: dist\
ECHO.
PAUSE