import subprocess
from multiprocessing import Process
import sys, os, datetime, json
from processing.tasks.analisis_ritmo_task import get_rhythm

bio_status, move_status = "", ""

def rhythm_analysis(dir_path):
    global bio_status
    get_rhythm(dir_path)
    bio_status = "OK"

def movement_analysis(file_path, dir_path, patient_id):
    global move_status
    try:
        # Call R script
        bin_folder = os.path.join(dir_path, "00_bin")
        print(f"Archivo BIN: {bin_folder}")

        logs_dir = os.path.join(dir_path, "03_bio")
        os.makedirs(logs_dir, exist_ok=True)
        log_txt = os.path.join(logs_dir, "analisis_movimiento_r.log")
        err_json = os.path.join(logs_dir, "analisis_movimiento_error.json")
        sig_json = os.path.join(logs_dir, "ui_error_signal.json")

        process = subprocess.Popen(['Rscript', file_path, dir_path, bin_folder], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace", bufsize=1)

        # Ejecuta R y vuelca stdout+stderr a la vez en el log, línea a línea
        with open(log_txt, "w", encoding="utf-8", newline="") as lf:
            # Leer línea a línea en tiempo real
            for line in iter(process.stdout.readline, ''):
                if not line:
                    break
                print(line, end='')  # consola
                lf.write(line)  # log
            process.stdout.close()
            process.wait()

        if process.returncode == 0:
            if os.path.exists(err_json):
                os.remove(err_json)
            # limpia la señal si existiera
            if os.path.exists(sig_json):
                os.remove(sig_json)
            return  # exit code 0
        else:
            now = datetime.datetime.now().isoformat(timespec="seconds")
            data = {
                "phase": "analisis_movimiento",
                "status": "ERROR",
                "when": now,
                "message": "GGIR P1 falló (revisa el log).",
                "hint": ("Suele deberse a columnas inesperadas o BIN sin datos válidos. "
                         "Prueba a reexportar/limpiar temperatura o descartar el archivo.")
            }
            with open(err_json, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            # *** Señal para la UI: SOLO cuando ocurre el error ***
            with open(sig_json, "w", encoding="utf-8") as f:
                json.dump({"ts": now}, f)

            sys.exit(1)  # <- marca fallo al orquestador

        #update_status_file(3, dir_path, move_status, 'move')
    except subprocess.CalledProcessError as e:
        print(f"Error executing the R script: {e.stderr}")
        move_status = "ERROR"
        #update_status_file(3, dir_path, move_status, 'move')


def bio_analysis(dir_path, r_path, patient_id):
    # Create processes for get_rhythm and movement_analysis
    process_rhythm = Process(target=rhythm_analysis, args=(dir_path,))
    process_movement = Process(target=movement_analysis, args=(r_path, dir_path, patient_id,))

    # Init processes
    process_rhythm.start()
    process_movement.start()

    # Wait until both processes are finished
    process_rhythm.join()
    process_movement.join()
