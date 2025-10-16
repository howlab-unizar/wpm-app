from dash import Dash, html, dcc, Input, Output, callback, State
import dash

app = Dash(__name__, suppress_callback_exceptions=True, use_pages=True, pages_folder="pages")

index_page = html.Div([
    html.H2('Index Page'),
    dcc.Dropdown(
        id='patient-dropdown',
        options=[
            {'label': '000000001', 'value': '000000001'},
            {'label': '000000002', 'value': '000000002'},
            {'label': '000000003', 'value': '000000003'}
        ],
        placeholder='Select a patient ID'
    ),
    html.Button('Go to Patient Page', id='go-to-patient-page'),
])

# Update the URL based on the selected patient ID and button click
@callback(
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

# Display the appropriate page content based on the URL
@callback(
    Output('page-content', 'children'),
    Input('url', 'pathname')
)
def display_page(pathname):
    if pathname.startswith('/patient/'):
        # Delegate the page rendering to Dash Pages
        return dash.page_container
    return index_page

if __name__ == '__main__':
    app.run_server(debug=True)