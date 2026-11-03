@echo off
REM Genera dist\Balidaf.exe (ejecutar desde la raiz del repo con el venv activo)
cd /d "%~dp0\.."
python -m pip install -r requirements-dev.txt
pyinstaller --noconfirm --clean Balidaf.spec
echo.
echo Ejecutable generado en dist\Balidaf.exe
