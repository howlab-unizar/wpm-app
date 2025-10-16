import os, json, datetime
from dateutil import parser as dtparser
import dash
import dash_ag_grid as dag
import dash_bootstrap_components as dbc
from dash import dcc, html, Input, Output, callback, Patch, State, no_update
from pathlib import Path

from processing.tasks.retrievedata_task import get_files
from processing.config import settings
from processing.actions_handler import stop_pipeline, continue_pipeline, execute_pipeline

# Registrar la página y obtener archivos no procesados
dash.register_page(
    __name__,
    path_template="/trabajos",
    title="Trabajos",
    name="Trabajos"
)

# Inicializar estado
datos_no_procesados = get_files(processed=False)

error_modal = dbc.Modal(
    id="error-modal",
    is_open=False,
    centered=True,
    backdrop=True,
    keyboard=True,
    size="md",
    children=[
        dbc.ModalHeader(dbc.ModalTitle("No se pudo generar el informe"), close_button=True),
        dbc.ModalBody(id="error-modal-body"),
        dbc.ModalFooter(dbc.Button("Cerrar", id="error-modal-close", n_clicks=0, className="ms-auto")),
    ],
)

last_error_store = dcc.Store(id="error-last-shown", storage_type="session")
error_poll       = dcc.Interval(id="error-poll", interval=1000, n_intervals=0)
app_start_store  = dcc.Store(id="app-start", data=datetime.datetime.now().isoformat(timespec="seconds"))

# Definir las columnas del grid
columnDefs = [
    {"headerName": "ID", "field": "id", "width": 160},
    {"headerName": "Nombre", "field": "nombre", "width": 175},
    {"headerName": "Medico", "field": "medico", "width": 175},
    {"headerName": "Fecha", "field": "fecha", "width": 175},
    {"headerName": "Descarga a Binario", "field": "descarga_binario", "width": 175},
    {"headerName": "Procesado primario", "field": "procesado_primario", "width": 175},
    {"headerName": "Segmentado", "field": "segmentado", "width": 175},
    {"headerName": "Análisis bioseñales", "field": "analisis_bioseñales", "width": 175},
    {"headerName": "Análisis movimiento", "field": "analisis_movimiento", "width": 180},
    {"headerName": "Informe", "field": "informe", "cellRenderer": "ReportLink", "width": 180},
    {"headerName": "Acciones", "field": "actions", "cellRenderer": "ButtonGroupRenderer", "width": 375}
]

def layout(patientsNotProcessed=datos_no_procesados, **kwargs):
    """
    Define el layout de la página de inicio.

    Args:
    patientsNotProcessed (list): Lista de pacientes no procesados.

    Returns:
    html.Div: Elementos HTML que conforman la página.
    """
    return html.Div([
        html.H2('Trabajos del Día Actual'),
        html.Button('Actualizar', id='refresh-no-procesados-button', className='refresh-button'),
        html.Button('Nuevo Proceso', id='new-process-button', className='new-process-button'),
        dcc.Input(id="filtro-grid", placeholder="filtrar..."),
        html.Div([
            dag.AgGrid(
                id='no-procesados-grid',
                columnDefs=columnDefs,
                rowData=patientsNotProcessed,
                defaultColDef={"resizable": True, "sortable": True, "filter": True},
                style={"height": "100%", "width": "100%"},
                className="ag-theme-alpine",
                dashGridOptions={"rowSelection": "single", "rowDeselection": True, "suppressCellFocus": True}
            ),
            # Botón oculto que “recibe” los clics de fuera del grid
            html.Button(id="outside-click", style={"display": "none"})
        ], className='table-container'),
        dcc.Interval(id='intervalo-actualizacion', interval=15000, n_intervals=0),
        dcc.Location(id='url-navigate'),  # Componente para manejar la redirección
        html.Div(id='row-content'),
        last_error_store,
        error_poll,
        app_start_store,
        error_modal
    ], className='content')

# Callback: refrescar datos

@callback(
    Output('no-procesados-grid', 'rowData'),
    Input('intervalo-actualizacion', 'n_intervals'),
    Input('refresh-no-procesados-button', 'n_clicks')
)
def update_data(_interval, _clicks):
    return get_files(processed=False)

@callback(
    Output("no-procesados-grid", "dashGridOptions"),
    Input("filtro-grid", "value")
)
def update_filter(filter_value):
    """
    Actualiza el filtro del grid.

    Args:
    filter_value (str): Valor del filtro.

    Returns:
    Patch: Nuevas opciones de filtro.
    """
    newFilter = Patch()
    newFilter['quickFilterText'] = filter_value
    return newFilter


# Callback: manejar acciones de los botones en la grid
@callback(
    Output('row-content', 'children'),
    Input('no-procesados-grid', 'cellRendererData')
)
def handle_actions(cellRendererData):
    if not cellRendererData or 'value' not in cellRendererData:
        return ''
    info   = cellRendererData['value']
    pid    = info.get('patientId')
    action = info.get('action')
    if action == 'stopProcess':
        return stop_pipeline(pid)
    if action == 'continueProcess':
        return continue_pipeline(pid, info, settings.base_directory)
    if action == 'executeProcess':
        return execute_pipeline(pid, info, settings.base_directory)
    return '❓ Acción no soportada.'

@callback(
    Output('url-navigate', 'pathname'),
    [Input('new-process-button', 'n_clicks')]
)
def navigate_to_new_patient_page(n_clicks):
    """
    Maneja la redirección a la página de datos de pacientes al hacer clic en Nuevo Proceso.

    Args:
    n_clicks (int): Número de clics en el botón de nuevo proceso.

    Returns:
    str or dash.no_update: Redirección a la página de datos de pacientes o no actualizar la URL.
    """
    if n_clicks:
        return '/datos-pacientes'

    return dash.no_update

@callback(
    Output("error-modal", "is_open"),
    Output("error-modal-body", "children"),
    Output("error-last-shown", "data"),
    Input("error-poll", "n_intervals"),
    State("no-procesados-grid", "rowData"),
    State("error-last-shown", "data"),
    State("app-start", "data"),
    State("error-modal", "is_open"),
    prevent_initial_call=False
)
def open_modal_on_error_signal(_tick, rows, last_shown, app_start_iso, is_open):
    # Si YA está abierto, no lo cierres en los siguientes ticks
    if is_open:
        return no_update, no_update, last_shown

    if not rows:
        return no_update, no_update, last_shown

    # Parse de la hora de carga de la página
    if dtparser:
        try:
            app_start = dtparser.isoparse(app_start_iso)
        except Exception:
            app_start = datetime.now()
    else:
        # fallback sin dateutil
        try:
            app_start = datetime.fromisoformat(app_start_iso)
        except Exception:
            app_start = datetime.now()

    # Recorre todas las filas buscando una señal NUEVA
    for row in rows:
        pid = row.get("id")
        fecha_raw = str(row.get("fecha", ""))            # 'YYYY-MM-DD' tal cual en la tabla
        fecha_dir = fecha_raw.replace("-", ".")          # para rutas de disco
        base = Path(os.getcwd()) / "Datos_pacientes" / pid / f"{pid}_{fecha_dir}" / "03_bio"
        sig = base / "ui_error_signal.json"
        err = base / "analisis_movimiento_error.json"
        if not sig.exists() or not err.exists():
            continue

        # Lee timestamp de la señal
        try:
            data_sig = json.loads(sig.read_text(encoding="utf-8"))
            ts = data_sig.get("ts")
        except Exception:
            ts = None

        key = f"{pid}:{ts}" if ts else None

        # ts como datetime
        if dtparser and ts:
            try:
                ts_dt = dtparser.isoparse(ts)
            except Exception:
                ts_dt = None
        else:
            try:
                ts_dt = datetime.fromisoformat(ts) if ts else None
            except Exception:
                ts_dt = None

        # Abrir SOLO si es posterior a carga y distinto al último mostrado
        if ts_dt and ts_dt > app_start and key != last_shown:
            data = json.loads(err.read_text(encoding="utf-8"))

            # --------- AQUÍ construyes el cuerpo del modal ----------
            body = html.Div([
                html.P(data.get("message", "Error durante el análisis de movimiento.")),
                html.Hr(),
                html.Strong("Qué hacer (troubleshooting):"),
                html.P(data.get("hint", "Revise el log de R y reintente.")),
                html.A(
                    "Ver log de R",
                    href=f"/log/{pid}/{fecha_raw}",   # <---- usa la ruta Flask nueva
                    target="_blank"
                ),
                # (opcional) ver JSON de error:
                # html.Br(),
                # html.A("Ver JSON de error", href=f"/log/json/{pid}/{fecha_raw}", target="_blank")
            ])
            # --------------------------------------------------------

            return True, body, key

    # Sin señales nuevas: no cambies nada
    return no_update, no_update, last_shown

@callback(
    Output("error-modal", "is_open", allow_duplicate=True),
    Input("error-modal-close", "n_clicks"),
    prevent_initial_call=True
)
def close_error_modal(n):
    if not n:
        return no_update
    return False