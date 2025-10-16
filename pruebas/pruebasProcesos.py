import glob, os, re, shutil
from datetime import datetime
import tkinter as tk
from tkinter import ttk
import bin2csv, csvprocess
import multiprocessing

binStatus = "not started"
rawStatus = "not started"
segStatus = "not started"
directorio = r"C:\Users\claua\Documents\Monitorización\Directorios"
step = 0

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
            fila = (pacientID, date, binStatus, rawStatus, segStatus, 'Not Implemented', 'Not Implemented', 'Not Implemented')
            tabla.insert('', 'end', values= fila)
            
        else:
            binStatus = 'Failed'

if __name__ == "__main__":
    window = tk.Tk()
    window.geometry('1900x500')
    window.title("Monitor")

    leftFrame = tk.Frame(window, width= 20, height= 100)
    leftFrame.grid(column= 0, row= 0, sticky= tk.W, pady= 5)

    updateFilesBtn = tk.Button(leftFrame, text= "Search files", command= get_files)
    updateFilesBtn.grid(column= 0, row= 0, sticky= tk.W)

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

    proceso = multiprocessing.Process(target= get_files)
    proceso.start()
    proceso.join()

    window.mainloop()

