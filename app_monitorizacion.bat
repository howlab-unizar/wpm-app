@echo off
set root=%USERPROFILE%\Desktop\aplicacion-de-monitorizacion
cd /d "%root%"
echo Iniciando aplicación Dash...

REM (Opcional) Activar el entorno virtual si existe
if exist .venv\Scripts\activate (
    call .venv\Scripts\activate
)

REM Ejecutar la aplicación
start /b python -m dash_app.app
timeout /t 5 >nul

echo Aplicación en ejecución...
pause