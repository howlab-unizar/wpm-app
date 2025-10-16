# dash_app/app.py
import os
import logging
import threading, time, requests, webbrowser
import dash_bootstrap_components as dbc
from dash import Dash, dcc, html, Input, Output, callback
import dash
from flask import send_from_directory, abort
from processing.config import settings

directorio = settings.base_directory
datos_pacientes = os.path.join(os.getcwd(), "Datos_pacientes")

app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP], use_pages=True, suppress_callback_exceptions=True, update_title=None)
server = app.server

# Rutas para servir PDF e imprimir inline
def _formatted_date(d):
    return d.replace('-', '.')

@server.route('/report-file/<patient_id>/<patient_date>')
def serve_report_file(patient_id, patient_date):
    """
    Sirve el PDF ya generado en:
      Datos_pacientes/<patient_id>/<patient_id>_<fecha_formateada>/05_rep/
    """
    formatted = _formatted_date(patient_date)
    pdf_dir = os.path.join(
        datos_pacientes,
        patient_id,
        f"{patient_id}_{formatted}",
        "05_rep"
    )
    filename = f"report_{patient_id}_{formatted}.pdf"
    return send_from_directory(pdf_dir, filename, as_attachment=False)


@server.route('/report-print/<patient_id>/<patient_date>')
def serve_report_print(patient_id, patient_date):
    src = f"/report-file/{patient_id}/{patient_date}"
    return f'''
    <!DOCTYPE html>
    <html>
      <head>
        <meta charset="utf-8">
        <title>Imprimir Informe</title>
        <style>
          /* Asegura que solo se vea el iframe en pantalla */
          html, body {{ margin:0; height:100%; overflow:hidden; }}
          #pdfFrame {{ width:100%; height:100%; border:none; }}
        </style>
      </head>
      <body>
        <iframe id="pdfFrame" src="{src}"></iframe>
        <script>
          let hasPrinted = false;
          function doPrint() {{
            if (hasPrinted) return;
            hasPrinted = true;
            const iframe = document.getElementById('pdfFrame');
            // Aseguramos foco en el iframe
            iframe.contentWindow.focus();
            // Imprime SOLO el PDF dentro del iframe
            iframe.contentWindow.print();
          }}

          const iframe = document.getElementById('pdfFrame');
          iframe.addEventListener('load', () => {{
            // Espera un segundo tras cargar
            setTimeout(doPrint, 1000);
          }});
          // Fallback: forzar a los 5s si fallara
          setTimeout(doPrint, 5000);
        </script>
      </body>
    </html>
    '''


# Sobrescribe plantilla HTML para splash screen
app.index_string = '''<!DOCTYPE html>
<html><head>{%metas%}<title>{%title%}</title>{%favicon%}{%css%}
<style>#loading-overlay{position:fixed;top:0;left:0;width:100%;height:100%;background:white;display:flex;align-items:center;justify-content:center;z-index:9999;font-family:sans-serif;font-size:1.5em;}</style>
</head><body>
<div id="loading-overlay">Cargando aplicación…</div>
<div id="react-entry-point">{%app_entry%}</div><footer>{%config%}{%scripts%}{%renderer%}
<script>window.addEventListener('load',()=>{var ov=document.getElementById('loading-overlay');if(ov){ov.style.display='none';}});</script>
</footer></body></html>'''

tabs = html.Div(
    [
        dcc.Tabs(id= 'tabs', value= 'nada', children=[
            dcc.Tab(label= 'Trabajos', value= 'tab-trabajos', className= 'tab-style'),
            dcc.Tab(label= 'Histórico', value= 'tab-historico', className= 'tab-style')
        ], className= 'custom-tabs'),
    ], className= 'tabs'
)

app.layout = html.Div([
        dcc.Location(id="url-tabs", refresh= "callback-nav"),
        html.Div(id= 'page-content', children = [
            html.Div([tabs, dash.page_container], className = 'main')
    ]),
])


# Sincronización tabs ↔ URL
@callback(Output('url-tabs', 'href'), Input('tabs', 'value'))
def update_tab_href(value):
    if value == "tab-trabajos":
        return "/trabajos"
    elif value == "tab-historico":
        return "/historico"


@app.callback(Output('tabs', 'value'), Input('url-tabs', 'pathname'))
def display_page(path):
    if path == '/trabajos':
        return 'tab-trabajos'
    elif path == '/historico':
        return 'tab-historico'
    elif path == '/':
        return 'tab-trabajos'

def _patient_bio_dir(patient_id: str, patient_date: str) -> str:
    """
    Devuelve la ruta .../Datos_pacientes/<ID>/<ID>_<YYYY.MM.DD>/03_bio
    patient_date llega como 'YYYY-MM-DD' desde la UI.
    """
    formatted = patient_date.replace("-", ".")
    return os.path.join(datos_pacientes, patient_id, f"{patient_id}_{formatted}", "03_bio")

@server.route("/log/<patient_id>/<patient_date>")
def serve_move_log(patient_id, patient_date):
    """
    Sirve el archivo de log de R:
    .../03_bio/analisis_movimiento_r.log
    """
    bio_dir = _patient_bio_dir(patient_id, patient_date)
    logfile = "analisis_movimiento_r.log"
    path = os.path.join(bio_dir, logfile)
    if not os.path.exists(path):
        abort(404)
    # text/plain para que el navegador lo muestre
    return send_from_directory(bio_dir, logfile, mimetype="text/plain", as_attachment=False)

@server.route("/log/json/<patient_id>/<patient_date>")
def serve_move_error_json(patient_id, patient_date):
    """
    Sirve .../03_bio/analisis_movimiento_error.json (útil para depurar).
    """
    bio_dir = _patient_bio_dir(patient_id, patient_date)
    jfile = "analisis_movimiento_error.json"
    path = os.path.join(bio_dir, jfile)
    if not os.path.exists(path):
        abort(404)
    return send_from_directory(bio_dir, jfile, mimetype="application/json", as_attachment=False)

# Limpia selección en NO PROCESADOS
app.clientside_callback(
    """
    function(n_clicks) {
        if (!n_clicks) { return window.dash_clientside.no_update; }
        return [];
    }
    """,
    Output("no-procesados-grid", "selectedRows"),
    Input("outside-click", "n_clicks"),
    prevent_initial_call=True
)

# Limpia selección en PROCESADOS
app.clientside_callback(
    """
    function(n_clicks) {
        if (!n_clicks) { return window.dash_clientside.no_update; }
        return [];
    }
    """,
    Output("procesados-grid", "selectedRows"),
    Input("outside-click", "n_clicks"),
    prevent_initial_call=True
)

if __name__ == '__main__':
    # Oculta logs werkzeug
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)
    import sys

    log.addHandler(logging.StreamHandler(sys.stderr))


    # Launch server + auto-open browser
    def run_server():
        app.run_server(debug=False, use_reloader=False)


    threading.Thread(target=run_server, daemon=True).start()
    url = 'http://127.0.0.1:8050/'
    for _ in range(60):
        try:
            if requests.get(url, timeout=1).status_code == 200:
                webbrowser.open(url)
                break
        except:
            time.sleep(0.5)
    threading.Event().wait()
