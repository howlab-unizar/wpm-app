import dash
from dash import dcc, html, Input, Output, callback

dash.register_page(
    __name__, 
    path_template="/patient/<patient_ID>",
    title= "patient",
    name= "patient")

def layout(patient_ID=None, **kwargs):
    return html.Div([
        html.H1(f'Patient {patient_ID} Page'),
        dcc.Dropdown(['Movement', 'Temperature', 'Heart Rate'], 'Movement', id='data-dropdown'),
        html.Div(id='patient-content'),
        html.Br(),
        dcc.Link('Go back to home', href='/index'),
    ])

@callback(
    Output('patient-content', 'children'),
    Input('data-dropdown', 'value')
)
def data_dropdown(value):
    return f'You have selected {value}'