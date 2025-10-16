import glob, os, re, shutil
from datetime import datetime
import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
import bin2csv, csvprocess
import pandas as pd
import pre_process

binStatus = "not started"
rawStatus = "not started"
segStatus = "not started"
directorio = r"C:\Users\claua\Documents\Monitorización\Directorios"
step = 0

def csv_to_parquet(file):
    df = pd.read_csv(file)
    filenameParquet = file.replace('.csv', '.parquet') 
    df.to_parquet(filenameParquet)

def path_search():
    global directorio
    print("aqui")
    directorio = filedialog.askdirectory(title= "Elige directorio principal")
    
def get_table_data():
    table_data = []
    for item in tabla.get_children():
        values = tabla.item(item, 'values')
        table_data.append(values)
    return table_data

def sort_by_ID():
    table_data = get_table_data()
    tabla.delete(*tabla.get_children())

    for i in range(len(table_data)):
        for j in range(len(table_data) - 1 - i):
            if table_data[j][0] > table_data[j+1][0]:
                table_data[j], table_data[j+1] = table_data[j+1], table_data[j]
    
    for row in table_data:
        tabla.insert('', 'end', values= row)

    print('sorted by ID')

def sort_by_date():
    table_data = get_table_data()
    tabla.delete(*tabla.get_children())

    table_data.sort(key= lambda x: datetime.strptime(x[1], '%d/%m/%Y'))

    for row in table_data:
        tabla.insert('', 'end', values= row)

    print('sorted by Date')

def get_files():
    global binStatus
    global rawStatus
    global segStatus
    patronArchivos = r'^(\d{9})_(\d{4})\.(\d{2})\.(\d{2})\.BIN$'  # patrón del nombre de los archivos XXXXXXXXX_YYYY.MM.DD.BIN
    patronCarpetas = r'^(\d{9})_(\d{4})\.(\d{2})\.(\d{2})$'
    bucketPath = os.path.join(directorio, "_bucket")
    os.chdir(bucketPath)

    tabla.delete(*tabla.get_children())

    for carpetas in os.listdir(directorio): # Directorio principal
        matchPacientFolder = re.match(r'^(\d{9})', carpetas) # Comprobar que pacientes tienen carpetas

        if matchPacientFolder:
            print('match pacient folder')
            pacientFolder = os.path.join(directorio, carpetas)
            
            for carpeta in os.listdir(pacientFolder): 
                matchFolder = re.match(patronCarpetas, carpeta) # Busca las carpetas de cada día
                if matchFolder:
                    pacientID = matchFolder.group(1)
                    date = f"{matchFolder.group(4)}/{matchFolder.group(3)}/{matchFolder.group(2)}"

                    binStatusDir = os.path.join(pacientFolder, carpeta,'00_bin', 'bin_status.txt')

                    if os.path.exists(binStatusDir):
                        with open(binStatusDir, 'r') as binStatusFile:
                            binStatus = binStatusFile.read().strip()
                    else:
                        binStatus = "Status File Not Found"

                    rawStatusDir = os.path.join(pacientFolder, carpeta,'01_raw', 'raw_status.txt')

                    if os.path.exists(rawStatusDir):
                        with open(rawStatusDir, 'r') as rawStatusFile:
                            rawStatus = rawStatusFile.read().strip()
                    else:
                        rawStatus = "Status File Not Found"

                    segStatusDir = os.path.join(pacientFolder, carpeta,'02_seg', 'seg_status.txt')

                    if os.path.exists(segStatusDir):
                        with open(segStatusDir, 'r') as segStatusFile:
                            segStatus = segStatusFile.read().strip()
                    else:
                        segStatus = "Status File Not Found"
                                            
            fila = (pacientID, date, binStatus, rawStatus, segStatus, 'Not Implemented', 'Not Implemented', 'Not Implemented') 
            tabla.insert('', 'end', values= fila)            

    binStatus = "Not Started"
    rawStatus = "Not Started"
    segStatus = "Not Started"              
    for file in glob.glob("*.bin"): # Si hay nuevo archivo .BIN hay que crear path entero 
        match = re.match(patronArchivos, file) # Comprueba que es el formato deseado
        binStatus = "Starting"
        if match:
            pacientID = match.group(1)
            date = f"{match.group(4)}/{match.group(3)}/{match.group(2)}"
            nombreCarpeta = os.path.splitext(file)[0]
            pre_process.create_path(0, pacientID, nombreCarpeta, file)
            fila = (pacientID, date, binStatus, rawStatus, segStatus, 'Not Implemented', 'Not Implemented', 'Not Implemented')
            tabla.insert('', 'end', values= fila)
            
        else:
            binStatus = 'Failed'

    print(binStatus)    

def get_selected_data():
    selectedItem = tabla.selection()
    if selectedItem:
        values = tabla.item(selectedItem, 'values')
        if values:
            selectedID = values[0]
            selectedDate = values[1]
            formattedDate = datetime.strptime(selectedDate, '%d/%m/%Y').strftime('%Y.%m.%d')
            file = f"{selectedID}_{formattedDate}"
            return selectedItem, selectedID, file
        
def proccess_bin2csv():
    global rawStatus

    selectedItem, ID, file = get_selected_data()
    binFile = f"{file}.BIN"
    csvFile = f"{file}.csv"
    path = os.path.join(directorio, ID, file)
    binPath = os.path.join(directorio, ID, file, "00_bin", binFile)
    csvPath = os.path.join(directorio, ID, file, "01_raw", csvFile)

    pre_process.create_path(1, ID, path)

    values = tabla.item(selectedItem, 'values')
    rawStatus = "Started"
    update_status_file(1, path)
    tabla.item(selectedItem, values=(values[0], values[1], values[2], rawStatus, "Not Started") + ("Not Implemented",) *  (len(tabla['columns']) - 3))

    create_empty_file(csvPath)

    bin2csv.bin2csv(binPath, csvPath)

    csv_to_parquet(csvPath)

    rawStatus = "OK"
    update_status_file(1, path)
    tabla.item(selectedItem, values=(values[0], values[1], values[2], rawStatus, "Not Started") + ("Not Implemented",) *  (len(tabla['columns']) - 3))
    

    print(binFile, csvFile, binPath, csvPath)

def seg_csv():
    global segStatus
    
    selectedItem, ID, file = get_selected_data()
    values = tabla.item(selectedItem, 'values')
    path = os.path.join(directorio, ID, file)
    # Actualiza estado del proceso de segmentación
    segStatus = "Started"
    update_status_file(2, path)
    tabla.item(selectedItem, values=(values[0], values[1], values[2], values[3], segStatus) + ("Not Implemented",) *  (len(tabla['columns']) - 3))
    # Realiza proceso de segmentación
    csvFile = f"{file}.csv"
    csvPath = os.path.join(directorio, ID, file, "01_raw", csvFile)
    csvprocess.seg_csv(csvPath)
    # Actualiza estado del proceso de segmentación
    segStatus = "OK"
    update_status_file(2, path)
    tabla.item(selectedItem, values=(values[0], values[1], values[2], values[3], segStatus) + ("Not Implemented",) *  (len(tabla['columns']) - 3))

def create_empty_file(filePath):
    try:
        with open(filePath, 'x'):  # 'x' asegura que el archivo no exista previamente
            print(f"Archivo '{filePath}' creado correctamente.")
    except FileExistsError:
        print(f"El archivo '{filePath}' ya existe.")
    except Exception as e:
        print(f"Ocurrió un error al crear el archivo '{filePath}': {e}")   

def update_status_file(step, path):
    global rawStatus
    global binStatus
    global segStatus

    if step == 0:
        filePath = os.path.join(path, "00_bin")
        try:
            with open(os.path.join(filePath, 'bin_status.txt'), 'w') as binStatusFile:
                                binStatusFile.write(binStatus)
        except Exception as e:
            print(f"Error con el archivo '{filePath}': {e}")

    elif step == 1:
        filePath = os.path.join(path, "01_raw")
        try:
            with open(os.path.join(filePath, 'raw_status.txt'), 'w') as rawStatusFile:
                                rawStatusFile.write(rawStatus)
        except Exception as e:
            print(f"Error con el archivo '{filePath}': {e}")

    elif step == 2:
        filePath = os.path.join(path, "02_seg")
        try:
            with open(os.path.join(filePath, "seg_status.txt"), 'w') as rawStatusFile:
                            rawStatusFile.write(segStatus)
        except Exception as e:
            print(f"Error con el archivo '{filePath}': {e}")

if __name__ == "__main__":
    window = tk.Tk()
    window.geometry('1900x500')
    window.title("Monitor")

    leftFrame = tk.Frame(window, width= 20, height= 100)
    leftFrame.grid(column= 0, row= 0, sticky= tk.W, pady= 5)

    updateFilesBtn = tk.Button(leftFrame, text= "Search files", command= get_files)
    updateFilesBtn.grid(column= 0, row= 0, sticky= tk.W)

    startBin2CsvBtn = tk.Button(leftFrame, text= "Bin2Csv", command= proccess_bin2csv)
    startBin2CsvBtn.grid(column= 0, row= 1, sticky= tk.W)

    segCsvBtn = tk.Button(leftFrame, text= "Segmentar CSV", command= seg_csv)
    segCsvBtn.grid(column= 0, row= 2, sticky= tk.W)

    tablaFrame = tk.Frame(window, width= 100, height= 500)
    tablaFrame.grid(column= 1, row= 0, sticky= tk.E, pady= 5)

    tabla = ttk.Treeview(tablaFrame)
    tabla['columns'] = ('ID', 'Fecha', 'Descarga a Binario', 'Procesado primario', 'Segmentado', 'Análisis bioseñales', 'Análisis Movimiento', 'Informe')

    # Formato de las columnas
    for column in tabla['columns']:
        tabla.column(column, anchor=tk.CENTER)

    # Encabezados de las columnas
    for column in tabla['columns']:
        if column == 'ID':
            tabla.heading(column, text= column, command=sort_by_ID)
        elif column == 'Fecha':
            tabla.heading(column, text= column, command=sort_by_date)
        else:
            tabla.heading(column, text=column)

    # Empaquetar la tabla
    tabla.grid(column= 0, row= 0, sticky= tk.E)

    choosePathBtn = tk.Button(tablaFrame, text = "Elegir directorio", command= path_search)
    choosePathBtn.grid(column= 0, row= 1, sticky= tk.S)

    get_files()

    window.mainloop()
