from dash import Dash, html, dcc, Input, Output, callback, State
import dash_ag_grid as dag
import dash
import retrievedata

app = Dash(__name__, suppress_callback_exceptions=True, use_pages=True, pages_folder="pages")

# Call the status retrieval function to get data when the app starts
patientsProcessed = retrievedata.get_files(processed="processed")
patientsNotProcessed = retrievedata.get_files(processed="not processed")
patientIDs = retrievedata.get_patient_ids()

sidebar = html.Div([
    html.H2('Sidebar'),
    dcc.Link('Patient Index', href='/index', className='sidebar-link'),
    html.Br(),
    dcc.Link('Data Processed', href='/processed', className='sidebar-link'),
    html.Br(),
    dcc.Link('Data Being Processed', href='/being-processed', className='sidebar-link'),
    html.Br(),
    dcc.Link('Data Not Processed', href='/not-processed', className='sidebar-link'),
], className='sidebar')

indexPage = html.Div([
    html.H2('Index Page'),
    dcc.Dropdown(
        id='patient-dropdown',
        options=[
            {'label': patient_id, 'value': patient_id} for patient_id in patientIDs
        ],
        placeholder='Select a patient ID'
    ),
    html.Button('Go to Patient Page', id='go-to-patient-page'),
], className='content')

# Define the data grid columns
columnDefs = [
    {"headerName": "ID", "field": "id"},
    {"headerName": "Fecha", "field": "fecha"},
    {"headerName": "Descarga a Binario", "field": "descarga_binario"},
    {"headerName": "Procesado primario", "field": "procesado_primario"},
    {"headerName": "Segmentado", "field": "segmentado"},
    {"headerName": "Análisis bioseñales", "field": "analisis_bioseñales"},
    {"headerName": "Análisis Movimiento", "field": "analisis_movimiento"},
    {"headerName": "Informe", "field": "informe"},
]

dataProcessedPage = html.Div([
    html.H2('Data Processed'),
    html.Button('Refresh Data', id='refresh-processed-button', className= 'refresh-button'),
    html.Div([
        dag.AgGrid(
            id='processed-grid',
            columnDefs=columnDefs,
            rowData = patientsProcessed,
            defaultColDef={"resizable": True, "sortable": True, "filter": True},
            style={"flex": "1", "height": "100%", "width": "100%"},
            className="ag-theme-alpine"
        ),
    ], className='table-container')
], className='content')

dataBeingProcessedPage = html.Div([
    html.H2('Data Being Processed'),
    
], className='content')

dataNotProcessedPage = html.Div([
    html.H2('Data Not Processed'),
    html.Button('Refresh Data', id='refresh-not-processed-button', className= 'refresh-button'),
    html.Div([
        dag.AgGrid(
            id='not-processed-grid',
            columnDefs=columnDefs,
            rowData= patientsNotProcessed,
            defaultColDef={"resizable": True, "sortable": True, "filter": True},
            style={"flex": "1", "height": "100%", "width": "100%"},
            className="ag-theme-alpine"
        ),
    ], className='table-container')
], className='content')

@app.callback(
    Output('processed-grid', 'rowData'),
    [Input('refresh-processed-button', 'n_clicks'),],
    prevent_initial_call=True
)
def update_data(n_clicks):
    if n_clicks is not None:
        # Call the status retrieval function to get fresh data
        patientsProcessed = retrievedata.get_files(processed="processed")
        return patientsProcessed
    else:
        # Return None if the button has not been clicked yet
        return None
    
@app.callback(
    Output('not-processed-grid', 'rowData'),
    [Input('refresh-not-processed-button', 'n_clicks'),],
    prevent_initial_call=True
)
def update_data(n_clicks):
    if n_clicks is not None:
        # Call the status retrieval function to get fresh data
        patientsNotProcessed = retrievedata.get_files(processed="not processed")
        return patientsNotProcessed
    else:
        # Return None if the button has not been clicked yet
        return None

@app.callback(
    Output('url', 'pathname'),
    Input('go-to-patient-page', 'n_clicks'),
    State('patient-dropdown', 'value')
)
def update_url(n_clicks, patient_id):
    if n_clicks is not None and patient_id is not None:
        return f'/patient/{patient_id}'
    return '/'

app.layout = html.Div([
    dcc.Location(id='url', refresh=False),
    html.Div(id='page-content')
])

@app.callback(
    Output('page-content', 'children'),
    Input('url', 'pathname')
)
def display_page(pathname):
    if pathname == '/processed':
        return html.Div([sidebar, dataProcessedPage], className='main')
    elif pathname == '/being-processed':
        return html.Div([sidebar, dataBeingProcessedPage], className='main')
    elif pathname == '/not-processed':
        return html.Div([sidebar, dataNotProcessedPage], className='main')
    elif pathname.startswith('/patient/'):
        return dash.page_container
    return html.Div([sidebar, indexPage], className='main')

if __name__ == '__main__':
    app.run_server(debug=True)
