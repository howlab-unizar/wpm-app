import dash
from dash import dcc, html

dash.register_page(__name__, path="/")


def layout(**kwargs):
    return html.Div([
        dcc.Location(id="home-redirect", refresh=True),
    ], id="home-redirect-container")


from dash import clientside_callback, Input, Output

clientside_callback(
    "function() { window.location.replace('/trabajos'); return ''; }",
    Output("home-redirect-container", "children"),
    Input("home-redirect-container", "id"),
)
