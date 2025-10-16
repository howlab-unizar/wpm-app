import dash
from dash import html, dcc, Input, Output, dash_table
import os
import re
import glob
import shutil
import pandas as pd
from datetime import datetime
from pydantic import BaseModel
from dotenv import load_dotenv
import plotly.express as px

class AppConfig(BaseModel):
    directorio: str
    intervalo_actualizacion_segundos: int

def cargar_configuracion():
    load_dotenv("conf.env")
    return{
        "directorio": os.getenv("DIRECTORIO"),
        "intervalo_actualizacion_segundos": int(os.getenv("INTERVALO_ACTUALIZACION_SEGUNDOS"))
    }

def validar_configuracion(config_data):
    return AppConfig(**config_data)

# Initialize the Dash app
app = dash.Dash(__name__, use_pages= True)

# Get config
config_data = cargar_configuracion()
configuracion = validar_configuracion(config_data)

directorio = configuracion.directorio
intervalo = configuracion.intervalo_actualizacion_segundos

# Set up an empty DataFrame for the table
empty_df = pd.DataFrame(columns=[
    'Patient ID', 'Date', 'Bin Status', 'First Process', 
    'Segmentation', 'Biosignal Analysis', 'Movement Analysis', 'Report'
])

# Set the layout of the app
app.layout = html.Div([
    html.H1("Processing Status"),
    dash_table.DataTable(
        id = 'status-table',
        columns = [{"name": i, "id": i} for i in empty_df.columns],
        data = empty_df.to_dict('records'),
        style_table = {'overflowX': 'auto'},
        style_cell = {'textAlign': 'left'},
        style_data_conditional = [
            {'if': {'row_index': 'odd'}, 'backgroundColor': 'rgb(248, 248, 248)'},
            {'if': {'column_id': 'Patient ID'}, 'width': '15%'},
            {'if': {'column_id': 'Date'}, 'width': '15%'},
        ],
        sort_action='native'
    ),
    dcc.Interval(
        id = 'interval-component',
        interval = intervalo*1000,  # in milliseconds, update every 10 seconds
        n_intervals = 0
    ),
    dcc.Location(id = 'url', refresh = False),
    html.Div(id = 'page-content')
])

# Callback to update the table data and handle sorting
@app.callback(
    Output('status-table', 'data'),
    [Input('interval-component', 'n_intervals'),
     Input('status-table', 'sort_by')]
)
def update_table_data(n_intervals, sort_by):
    # Update the table data based on interval
    data = get_files()

    # Check if the callback was triggered by sorting
    ctx = dash.callback_context
    if ctx.triggered and ctx.triggered[0]['prop_id'] == 'status-table.sort_by':
        if sort_by:
            if len(sort_by):
                if sort_by[0]['column_id'] == 'Patient ID':
                    data.sort(key=lambda x: x['Patient ID'])
                elif sort_by[0]['column_id'] == 'Date':
                    data.sort(key=lambda x: datetime.strptime(x['Date'], '%Y/%m/%d'))

    return data

# Function to get file status and populate the table
def get_files():
    global binStatus
    global rawStatus
    global segStatus
    global directorio
    patronArchivos = r'^(\d{9})_(\d{4})\.(\d{2})\.(\d{2})\.BIN$'  # patrón del nombre de los archivos XXXXXXXXX_YYYY.MM.DD.BIN
    patronCarpetas = r'^(\d{9})_(\d{4})\.(\d{2})\.(\d{2})$'

    data = []
    bucketPath = os.path.join(directorio, "_bucket")
    os.chdir(bucketPath)

    for carpetas in os.listdir(directorio): # Directorio principal
        matchPacientFolder = re.match(r'^(\d{9})', carpetas) # Comprobar que pacientes tienen carpetas

        if matchPacientFolder:
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
                    data.append(dict(zip(empty_df.columns, fila)))

    return data

# Run the app
if __name__ == '__main__':
    app.run_server(debug=True)
