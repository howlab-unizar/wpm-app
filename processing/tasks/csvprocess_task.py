import csv
from pathlib import Path
from datetime import datetime, timedelta
from processing.utils import create_path, create_empty_file
import os

def run_segmentation(file):
    outputFile = file.replace(".csv", "_processed.csv")
    print(outputFile)
    # Abrir el archivo de entrada CSV en modo lectura
    with open(file, newline='', encoding='utf-8-sig') as input:
        # Abrir el archivo de salida CSV en modo escritura
        reader = csv.DictReader(input)
        intervalo_mov = []
        intervalo_temp = []
        intervalo_hr = []
        start = None

        for row in reader:
            try:
                date = datetime.fromtimestamp(int(row['dateTime']) / 1000)

            except:
                date = datetime.strptime(row['dateTime'], '%Y-%m-%d %H:%M:%S.%f')
            #intervalo = date - (date - datetime.min)% timedelta(minutes = intervalosMinutos)

            if start is None:
                start = round_interval(date, 5)

            if row['bodySurface_temp'] != '':
                intervalo_temp.append({
                    'dateTime': row['dateTime'],
                    'bodySurface_temp': row['bodySurface_temp'],
                    'ambient_temp': row['ambient_temp']
                })

            if (date - start) >= timedelta(minutes= 5):
                write_segment_csv(start, intervalo_mov, file, 'movimiento')
                write_segment_csv(start, intervalo_temp, file, 'temperatura')
                write_segment_csv(start, intervalo_hr, file, 'hr')
                intervalo_temp = []
                intervalo_mov = []
                intervalo_hr = []
                start = round_interval(date, 5)

            intervalo_mov.append({
                'dateTime': row['dateTime'],
                'acc_x': row['acc_x'],
                'acc_y': row['acc_y'],
                'acc_z': row['acc_z'],
                'gyr_x': row['gyr_x'],
                'gyr_y': row['gyr_y'],
                'gyr_z': row['gyr_z']
            })

            intervalo_hr.append({
                'dateTime': row['dateTime'],
                'hr_raw': row['hr_raw'],
                'hr': row['hr']
            })

        if intervalo_mov:
            write_segment_csv(start, intervalo_mov, file, 'movimiento')
        if intervalo_temp:
            write_segment_csv(start, intervalo_temp, file, 'temperatura')
        if intervalo_hr:
            write_segment_csv(start, intervalo_hr, file, 'hr')

def round_interval(time, min):
    roundedMinute = round(time.minute / min) * min
    roundedHour = time.hour
    if roundedMinute >= 60:
        roundedMinute -= 60
        roundedHour += 1
    return time.replace(hour = roundedHour, minute = roundedMinute, second = 0, microsecond= 0)

def write_segment_csv(start, rows, file, dato):
    dateDir = os.path.dirname(os.path.dirname(file))
    min = '00',
    hour = '00'

    if start.minute < 10: 
        min = f"0{str(start.minute)}"
    else:
        min = str(start.minute)

    if start.hour < 10: 
        hour = f"0{str(start.hour)}"
    else:
        hour = str(start.hour)

    if not os.path.exists(os.path.join(dateDir, "02_seg", start.strftime('%Y.%m.%d'), hour)):
        create_path(2, patient="", folder_name="", carpeta_dia= "", start= start)

    csvFile = f"{dato}_{min}.csv"
    csvDir = Path(dateDir) / "02_seg" / start.strftime('%Y.%m.%d') / hour / csvFile
    print(csvDir)

    if not os.path.exists(csvDir):
        create_empty_file(csvDir)
    fieldnames = rows[0].keys() if rows else []

    with open(csvDir, mode = 'w', newline='') as output:
        writer = csv.DictWriter(output, fieldnames= fieldnames)
        writer.writeheader()
        writer.writerows(rows)