# utils.py
import json, shutil
from datetime import datetime
from pathlib import Path
from processing.config import settings

def create_path(step: int, patient: str, folder_name: str, carpeta_dia: str = None, start: datetime = None) -> Path:
    """
    Crea la carpeta para el paso `step` dentro de:
      base_directory/Datos_pacientes/patient/folder_name/
    para step 2 ("02_seg"), si se proporciona `start` o `carpeta_dia`, crea subcarpetas de fecha y hora:
      .../02_seg/YYYY.MM.DD/HH

    Args:
        step: 0->00_bin,1->01_raw,2->02_seg,3->03_bio,5->05_rep
        patient: ID del paciente
        folder_name: nombre de la carpeta de sesión (p.ej. "P001_2025.05.29")
        carpeta_dia: ruta alternativa a usar si start no dado (raíz de sesión)
        start: datetime para segmentación con subcarpeta de fecha y hora
    Returns:
        Path al directorio creado
    """
    folder_map = {0: '00_bin', 1: '01_raw', 2: '02_seg', 3: '03_bio', 5: '05_rep'}
    step_folder = folder_map.get(step)
    if not step_folder:
        raise ValueError(f"Paso inválido: {step}")

    base = Path(settings.base_directory) / 'Datos_pacientes' / patient / folder_name / step_folder
    #base.mkdir(parents=True, exist_ok=True)

    # Si es segmentación y se solicita subcarpeta por fecha/hora
    if step == 2:
        if start:
            date_str = start.strftime('%Y.%m.%d')
            hour_str = f"{start.hour:02}"
            sub = base / date_str / hour_str
            #sub.mkdir(parents=True, exist_ok=True)
            return sub
        elif carpeta_dia:
            # carpeta_dia es la ruta raíz de la sesión
            # extraer fecha/hora desde carpeta_dia path
            # si no se proporciona start, solo devuelve base
            return base
    return base

def create_empty_file(file_path: Path):
    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text('')
    except Exception as e:
        print(f"Error creando {file_path}: {e}")

def load_json(path: Path) -> dict:
    return json.loads(path.read_text()) if path.exists() else {}

def purge_patient_data(session_root: Path, data_dirs=('00_bin','01_raw','02_seg','03_bio'), keep_reports_dir='05_rep'):
    """
    Elimina, dentro de la sesión `session_root`, cualquier archivo NO .json
    que esté dentro de 00_bin/01_raw/02_seg/03_bio (recursivo).
    No borra nada dentro de 05_rep (conserva el PDF generado).
    No elimina carpetas, solo archivos.
    """
    session_root = Path(session_root)
    if not session_root.exists():
        return

    # 1) Purgar data_dirs (completo excepto .json)
    for d in data_dirs:
        base = session_root / d
        if not base.exists():
            continue
        for path in base.rglob('*'):
            if path.is_file():
                # conserva solo .json
                if path.suffix.lower() != '.json':
                    try:
                        path.unlink()
                    except Exception as e:
                        print(f"[purge_patient_data] No se pudo borrar {path}: {e}")