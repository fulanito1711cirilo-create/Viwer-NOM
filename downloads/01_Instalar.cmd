@echo off
setlocal
cd /d "%~dp0"
chcp 65001 >nul
set "NOM_PYTHON="
call :buscar_runtime
if defined NOM_PYTHON goto instalar_programa
where py.exe >nul 2>&1
if errorlevel 1 goto usar_winget
echo Falta el runtime Python 3.12. Intentando instalarlo con el gestor Python...
py install 3.12
call :buscar_runtime
if defined NOM_PYTHON goto instalar_programa
:usar_winget
where winget >nul 2>&1
if errorlevel 1 goto falta_python
echo Instalando Python 3.12 mediante winget...
winget install --exact --id Python.Python.3.12 --source winget --accept-package-agreements --accept-source-agreements --disable-interactivity
call :buscar_runtime
if defined NOM_PYTHON goto instalar_programa
goto falta_python
:instalar_programa
"%NOM_PYTHON%" "%~dp0windows\instalar.py"
set "NOM_EXIT=%ERRORLEVEL%"
goto finalizar
:buscar_runtime
set "NOM_PYTHON="
rem Exige una ruta real emitida por Python; algunos gestores devuelven 0 sin runtime.
for /f "delims=" %%P in ('py -3.12 -c "import sys; assert sys.version_info[:2] == (3,12) and sys.maxsize > 2**32; print(sys.executable)" 2^>nul') do if exist "%%P" set "NOM_PYTHON=%%P"
if defined NOM_PYTHON exit /b 0
if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" set "NOM_PYTHON=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
if defined NOM_PYTHON exit /b 0
if exist "%ProgramFiles%\Python312\python.exe" set "NOM_PYTHON=%ProgramFiles%\Python312\python.exe"
exit /b 0
:falta_python
echo No se encontro un runtime Python 3.12 utilizable.
echo Abre CMD y ejecuta: py install 3.12
echo Despues comprueba: py -3.12 --version
echo Alternativa oficial: https://www.python.org/downloads/windows/
echo Cierra esta ventana y vuelve a ejecutar 01_Instalar.cmd tras instalar Python.
set "NOM_EXIT=1"
:finalizar
if not "%NOM_EXIT%"=="0" echo No se completo la instalacion. Revisa los mensajes anteriores.
pause
exit /b %NOM_EXIT%
