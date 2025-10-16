# processing/tasks/retrievedata_task.py
import os, re, glob, json
import shutil
from datetime import datetime, date
from pathlib import Path
from processing.config import settings
from processing.utils import load_json

# Base de pacientes
BASE = Path(settings.base_directory) / 'Datos_pacientes'
prev_digits = ''

def get_patient_ids():
    return [d.name for d in BASE.iterdir() if d.is_dir()]

def get_patient_age(birth_date):
    day, month, year = map(int, birth_date.split("/"))
    birth_date = date(year, month, day)
    today = date.today()

    # Calcular la edad comparando los años
    age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
    return age

def validate_manual_date(manual_value):
    """
    Función para validar y formatear fechas en formato DD/MM/YYYY.

    Args:
        manual_value (str): Fecha ingresada por el usuario.

    Returns:
        tuple: (fecha_formateada, None si es válida o None si es inválida, dict con estilo de visibilidad)
    """
    global prev_digits
    if not manual_value:  # Si el usuario borra el campo
        return "", None, {"display": "none", "height": "40px"}  # Borra y oculta el calendario

    manual_value = re.sub(r"\D", "", manual_value)  # Elimina caracteres no numéricos

    if len(prev_digits) < len(manual_value):
        # Aplica el formato DD/MM/YYYY
        if len(manual_value) >= 2:
            manual_value = manual_value[:2] + "/" + manual_value[2:]
        if len(manual_value) >= 5:
            manual_value = manual_value[:5] + "/" + manual_value[5:]
    else:
        actual_value = re.sub(r"\D", "", manual_value)  # Elimina caracteres no numéricos
        low = 0
        not_last = False
        for i in range(min(len(actual_value), len(prev_digits))):
            if actual_value[i] != prev_digits[i] and low == 0:
                not_last = True
                if len(actual_value) < len(prev_digits):
                    if i < 2:
                        if len(actual_value) == 7:
                            manual_value = actual_value[:1] + "/" + actual_value[1:3] + "/" + actual_value[3:]
                        else:
                            manual_value = "/" + actual_value[:2] + "/" + actual_value[2:]
                    elif i < 4:
                        if len(actual_value) == 7:
                            manual_value = actual_value[:2] + "/" + actual_value[2:3] + "/" + actual_value[3:]
                        else:
                            manual_value = actual_value[:2] + "/" + "/" + actual_value[2:]
                    else:
                        manual_value = actual_value[:2] + "/" + actual_value[2:4] + "/" + actual_value[4:]
                    low += 1
                    break
                else:
                    manual_value = actual_value[:2] + "/" + actual_value[2:4] + "/" + actual_value[4:]

        if len(actual_value) < len(prev_digits) and not_last == False:
            if len(actual_value) <= 2:
                manual_value = actual_value[:2] + "/"
                if len(actual_value) == 0:
                    manual_value = ""
            elif len(actual_value) <= 4:
                manual_value = actual_value[:2] + "/" + actual_value[2:] + "/"
            else:
                manual_value = actual_value[:2] + "/" + actual_value[2:4] + "/" + actual_value[4:]

    prev_digits = re.sub(r"\D", "", manual_value)

    # Si la fecha está completa, validarla
    if len(manual_value) == 10:
        try:
            day, month, year = map(int, manual_value.split("/"))
            actual_year = date.today().year

            # Validaciones
            if not (1 <= day <= 31):
                raise ValueError("Día inválido")
            if not (1 <= month <= 12):
                raise ValueError("Mes inválido")
            if not (1900 <= year <= actual_year):
                raise ValueError("Año inválido")

            return manual_value, None, {"display": "none"}  # Fecha válida, oculta el calendario
        except ValueError:
            return "", None, {"display": "none"}  # Borra la fecha inválida y abre el calendario

    return manual_value, None, {"display": "none"}  # Sigue formateando sin cerrar

# Estado de ficheros

def read_phase_status(name: str, ses: Path) -> str:
    sub = {
        'start_bin':           '00_bin',
        'bin2csv':             '01_raw',
        'seg_csv':             '02_seg',
        'bio_analisis':        '03_bio',
        'analisis_movimiento': '03_bio',
        'create_report':       '05_rep'
    }[name]
    log = ses / sub / f"{name}.json"
    if not log.exists():
        return "Not Available"
    data = json.loads(log.read_text())
    return data.get("status") or "UNKNOWN"

# Recogida de datos

def get_patient_data(folder: Path, patient: str, folder_str: str) -> dict:
    f = folder / f"{patient}_{folder_str}.json"
    return load_json(f)

def get_files(processed: bool) -> list[dict]:
    out = []
    today = date.today()

    for pdir in BASE.iterdir():
        if not pdir.is_dir():
            continue

        patient_id = pdir.name

        for ses in pdir.iterdir():
            if not ses.is_dir():
                continue
            parts = ses.name.split('_', 1)
            if len(parts) != 2:
                continue
            folder_str = parts[1]
            ymd = folder_str.split('.')
            if len(ymd) != 3:
                continue
            date_str = f"{ymd[0]}-{ymd[1]}-{ymd[2]}"

            data = get_patient_data(ses, patient_id, folder_str)
            if not data:
                continue
            registro_date = datetime.strptime(data['fecha_registro'], '%Y.%m.%d').date()

            # lee estado de cada fase
            bin_status  = read_phase_status('start_bin', ses)
            raw_status  = read_phase_status('bin2csv', ses)
            seg_status  = read_phase_status('seg_csv', ses)       # si tus fases se llaman distinto, ajusta
            bio_status  = read_phase_status('bio_analisis', ses)
            move_status = read_phase_status('analisis_movimiento', ses)
            rep_status  = read_phase_status('create_report', ses)

            done = all(s == 'SUCCESS' for s in (bin_status, raw_status, seg_status, bio_status, move_status))
            include = (done and processed and registro_date < today) or ((not done or registro_date == today) and not processed)
            if not include:
                continue

            out.append({
                'id':                 patient_id,
                'nombre':             data.get('nombre') or '---',
                'medico':             data.get('nombre_medico') or '---',
                'fecha':              date_str,
                'descarga_binario':   bin_status,
                'procesado_primario': raw_status,
                'segmentado':         seg_status,
                'analisis_bioseñales':bio_status,
                'analisis_movimiento':move_status,
                'informe':            rep_status,
                'process':            'Continuar' if not done else ''
            })
    return out

def delete_patient(patient_id: str) -> bool:
    """
    Elimina por completo el paciente
    Devuelve True si elimina algo, False si no existe
    """
    root = BASE / patient_id
    if root.exists():
        shutil.rmtree(root)
        return True
    return False