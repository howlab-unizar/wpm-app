import dash
import dash_ag_grid as dag
from dash import dcc, html, Input, Output, callback, Patch, State

from processing.tasks.retrievedata_task import get_files, delete_patient

# Registrar la página y obtener archivos procesados
dash.register_page(
    __name__,
    path_template="/historico",
    title="Histórico",
    name="Histórico"
)

# Definir las columnas del grid
columnDefs = [
    {"headerName": "ID", "field": "id"},
    {"headerName": "Nombre", "field": "nombre"},
    {"headerName": "Médico", "field": "medico"},
    {"headerName": "Fecha", "field": "fecha"},
    {"headerName": "Informe", "field": "informe", "cellRenderer": "ReportLink", "width": 180},
    {"headerName": "Acciones", "field": "delete_process", "cellRenderer": "DeleteButton"}
]

def layout(**kwargs):
    """
    Define el layout de la página de datos procesados.

    Returns:
    html.Div: Elementos HTML que conforman la página.
    """
    patients_processed = get_files(processed=True)
    return html.Div([
        html.H2('Histórico'),
        html.Button('Actualizar', id='refresh-processed-button', className='refresh-button'),
        dcc.Input(id="filtro-grid", placeholder="filtrar..."),
        html.Div([
            dag.AgGrid(
                id='procesados-grid',
                columnDefs=columnDefs,
                rowData=patients_processed,
                defaultColDef={"resizable": True, "sortable": True, "filter": True},
                style={"flex": "1", "height": "100%", "width": "100%"},
                className="ag-theme-alpine",
                dashGridOptions={"rowSelection": "single", "rowDeselection": True, "suppressCellFocus": True}
            ),
            # Botón oculto que “recibe” los clics de fuera del grid
            html.Button(id="outside-click", style={"display": "none"})
        ], className='table-container'),
        html.Div(id='procesados-content'),
    ], className='content')

@callback(
    Output('procesados-grid', 'rowData'),
    [Input('refresh-processed-button', 'n_clicks'),
     Input('procesados-grid', 'cellRendererData')],
    prevent_initial_call=True
)
def update_or_delete_data(n_clicks, cellRendererData):
    """
    Actualiza la lista de pacientes procesados o elimina un paciente.

    Args:
    n_clicks (int): Número de veces que se ha pulsado el botón de actualización.
    cellRendererData (dict): Información del botón de eliminar proceso.

    Returns:
    list: Lista actualizada de pacientes procesados.
    """
    ctx = dash.callback_context

    if not ctx.triggered:
        return get_files(processed=True)

    triggered_id = ctx.triggered[0]['prop_id'].split('.')[0]

    # Si se hizo clic en "Actualizar"
    if triggered_id == 'refresh-processed-button':
        print(" Refrescando lista de pacientes procesados...")

    # Si se presionó el botón de eliminar
    elif triggered_id == 'procesados-grid' and isinstance(cellRendererData, dict):
        action_data = cellRendererData.get("value", {})
        action = action_data.get("action")
        patient_id = action_data.get("patientId")  # Asegurar que el ID está en `patientId`
        if action == 'deletePatient' and patient_id:
            print(f"Eliminando paciente: {patient_id}")
            ok = delete_patient(patient_id)
            if not ok:
                print(f"No se encontró {patient_id} para eliminar.")

    return get_files(processed=True)

@callback(
    Output("procesados-grid", "dashGridOptions"),
    Input("filtro-grid", "value")
)
def update_filter(filter_value):
    """
    Actualiza el filtro del grid de pacientes procesados.

    Args:
    filter_value (str): Valor del filtro.

    Returns:
    Patch: Nuevas opciones de filtro.
    """
    newFilter = Patch()
    newFilter['quickFilterText'] = filter_value
    return newFilter