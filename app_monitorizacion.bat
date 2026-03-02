@echo off
set root=%USERPROFILE%\Desktop\aplicacion-de-monitorizacion
cd /d "%root%"
echo Iniciando aplicacion Dash...

REM (Opcional) Activar el entorno virtual si existe
if exist .venv\Scripts\activate (
    call .venv\Scripts\activate
)

REM Ejecutar la aplicación
python -m dash_app.app 2>nul

exit