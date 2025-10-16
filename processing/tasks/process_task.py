# howlab_processing/tasks/process_task.py
import asyncio
import time, os
from pathlib import Path
from processing.config import settings
from processing.utils import create_path
from processing.tasks.bin2csv_task import run_bin2csv
from processing.tasks.csvprocess_task import run_segmentation
from processing.tasks.analisis_ritmo_task import get_rhythm
from processing.tasks.move_analysis_task import movement_analysis

async def bin2csv(record, only_this_step: bool = False):
    # record es dict con 'id', 'fecha', etc.
    patient = record['id']
    date_str = record['fecha']
    folder = f"{patient}_{date_str.replace('-', '.')}"
    datos_paciente = os.path.join(os.getcwd(), "Datos_pacientes", patient, folder)
    work_dir = Path(settings.base_directory) / patient / folder

    # fase bin2csv
    create_path(1, patient, folder)
    raw_status = "RUNNING"

    start_time = time.time()
    conversion_result = await asyncio.to_thread(run_bin2csv, os.path.join(datos_paciente, '00_bin', f"{folder}.BIN"),
                                                os.path.join(datos_paciente, '01_raw', f"{folder}.csv"))
    end_time = time.time()
    elapsed_time = end_time - start_time
    print(f'Conversion to CSV time: {elapsed_time}')
    raw_status = "OK" if conversion_result == 0 else "Error"

    #if not only_this_step:
    #    await seg_csv(record)

async def seg_csv(record, only_this_step: bool = False):
    patient = record['id']
    date_str = record['fecha']
    folder = f"{patient}_{date_str.replace('-', '.')}"
    datos_paciente = os.path.join(os.getcwd(), "Datos_pacientes", patient, folder)
    work_dir = Path(settings.base_directory) / patient / folder

    create_path(2, patient, folder)
    seg_status = "Started"

    # Ejecutar segmentación y actualizar estado
    start_time = time.time()
    try:
        await asyncio.to_thread(run_segmentation, os.path.join(datos_paciente, '01_raw', f"{folder}.csv"))
        end_time = time.time()
        elapsed_time = end_time - start_time
        print(f'CSV segmentation time: {elapsed_time}')
        seg_status = "OK"
    except Exception:
        seg_status = "ERROR"

    #if not only_this_step:
    #    await bio_analisis(record)

async def bio_analisis(record, only_this_step: bool = False):
    patient = record['id']
    date_str = record['fecha']
    folder = f"{patient}_{date_str.replace('-', '.')}"
    datos_paciente = os.path.join(os.getcwd(), "Datos_pacientes", patient, folder)
    work_dir = Path(settings.base_directory) / patient / folder

    create_path(3, patient, folder)
    bio_status = "Started"

    start_time = time.time()
    await asyncio.to_thread(get_rhythm, os.path.join(datos_paciente))
    end_time = time.time()
    elapsed_time = end_time - start_time
    print(f'Rhythm Analysis time: {elapsed_time}')

    #if not only_this_step:
    #    await move_analisis(record)

async def move_analisis(record, only_this_step: bool = False):
    patient = record['id']
    date_str = record['fecha']
    folder = f"{patient}_{date_str.replace('-', '.')}"
    datos_paciente = os.path.join(os.getcwd(), "Datos_pacientes", patient, folder)
    work_dir = Path(settings.base_directory) / patient / folder

    create_path(3, patient, folder)
    move_status = "Started"

    start_time = time.time()
    r_script = Path(settings.base_directory).parent / "processing" / "tasks" / 'analisis_movimiento.R'
    await asyncio.to_thread(movement_analysis, r_script, datos_paciente, patient)
    end_time = time.time()
    elapsed_time = end_time - start_time
    print(f'Movement Analysis time: {elapsed_time}')

    # await create_report(record)

async def create_report(record):
    patient = record['id']
    date_str = record['fecha']
    folder = f"{patient}_{date_str.replace('-', '.')}"
    datos_paciente = os.path.join(os.getcwd(), "Datos_pacientes", patient, folder)
    work_dir = Path(settings.base_directory) / patient / folder

    create_path(5, patient, folder)
