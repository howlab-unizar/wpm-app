import os
import shutil
import json

from pathlib import Path
import time
from datetime import date, datetime, timedelta
import dash
from dash import dcc, html, Input, Output, callback, State

import asyncio
import threading
import re

from processing.tasks.retrievedata_task import (get_patient_ids, get_patient_age,
                                                validate_manual_date, get_files)
from processing.config import settings
from processing.pipeline_scheduler import schedule_pipeline
from processing.utils import create_path
from processing.phases import PhaseTask
from processing.pipeline import PipelineManager
from processing.tasks.process_task import (
    bin2csv, seg_csv, bio_analisis, move_analisis
)
from processing.store import PIPELINE_STORE
#from process_manager import start_process, monitor_process

# Registrar la página y obtener IDs de pacientes
dash.register_page(
    __name__,
    path_template="/datos-pacientes",
    title="Datos de pacientes",
    name="Datos de pacientes"
)

age = 0
WATCH_DIRECTORY = settings.watch_directory

def _sanitize_patient_id(raw: str) -> str:
    # Quita espacios en extremos y convierte espacios internos en guiones bajos
    s = (raw or '').strip()
    s = re.sub(r'\s+', '_', s)
    # No permitir caracteres problemáticos para nombres de carpeta/archivo
    if any(c in s for c in r'\/:*?"<>|'):
        raise ValueError("El identificador contiene caracteres no permitidos: \\ / : * ? \" < > |")
    if not s:
        raise ValueError("El identificador no puede estar vacío.")
    return s

def layout(**kwargs):
    """
    Define el layout de la página de datos de pacientes.

    Returns:
    html.Div: Elementos HTML que conforman la página.
    """
    return html.Div([
        dcc.Location(id='url', refresh=True),  # Asegura que la página se redirija y refresque
        html.H2('Datos de pacientes'),
        html.Div(id='output-data-validation'),
        html.Button('Aceptar', id='submit-button', n_clicks=0, className='accept-button'),
        html.Button('Cancelar', id='cancel-button', n_clicks=0, className='cancel-button'),
        html.Div([
            dcc.RadioItems(
                id='patient-type',
                options=[
                    {'label': 'Nuevo Paciente', 'value': 'new'},
                    {'label': 'Paciente Existente', 'value': 'existing'}
                ],
                value='new',
                labelStyle={'display': 'block'}
            ),
            html.Div(id='formulario-paciente'),
        ], className='content'),
    ])

@callback(
    Output('formulario-paciente', 'children'),
    Input('patient-type', 'value')
)
def patient_data(patient_type):
    """
    Define el formulario de ingreso de datos del paciente dependiendo del tipo seleccionado.

    Args:
    patient_type (str): Tipo de paciente ('new' para nuevo paciente, 'existing' para paciente existente).

    Returns:
    html.Div: Elementos HTML del formulario correspondiente.
    """

    identifier_field = html.Div()

    patient_ids = get_patient_ids()

    # Evaluar qué tipo de identificador se debe mostrar
    if patient_type == 'new':
        identifier_field = html.Div([
            html.Label(['Identificador del paciente:', html.Span(' *', style={'color': 'red'})]),
            dcc.Input(id='id-paciente', type='text', value='', placeholder='Introduce un identificador', maxLength=64, autoComplete="off")
        ], style={'width': '48%', 'display': 'inline-block', 'padding': '10px'})

    elif patient_type == 'existing':
        identifier_field = html.Div([
            html.Label(['Identificador del paciente:', html.Span(' *', style={'color': 'red'})]),
            dcc.Dropdown(
                id='id-paciente',  # Seleccionar paciente para rellenar los datos.
                options=[{'label': patient_id, 'value': patient_id} for patient_id in patient_ids],
                placeholder='Seleccione un ID de paciente'
            )
        ], style={'width': '48%', 'display': 'inline-block', 'padding': '10px'})

    end_date = datetime.today()
    initial_date = end_date - timedelta(days=6)

    # Definir los campos comunes del formulario
    common_fields = html.Div([
        identifier_field,

        html.Div([
            html.Label(['Ruta del archivo:', html.Span(' *', style={'color': 'red'})]),
            dcc.Dropdown(
                id='file-dropdown',
                options=[{'label': str(dir), 'value': str(dir)} for dir in os.listdir(WATCH_DIRECTORY)],
                placeholder='Seleccione una ruta',
                style={'width': '96.75%'}
            )
        ], style={'width': '48%', 'display': 'inline-block', 'padding': '10px'}),

        html.Div([
            html.Label(['Nombre:']),
            dcc.Input(id='nombre', type='text', placeholder='Nombre del paciente')
        ], style={'width': '48%', 'display': 'inline-block', 'padding': '10px'}),

        html.Div([
            html.Label(['Fecha de Nacimiento:', html.Span(' *', style={'color': 'red'})]),
            html.Div([
                dcc.Input(id="fecha-nacimiento", type="text", placeholder="DD/MM/YYYY", maxLength=10),
                html.Button("🔽", id="abrir-calendario", n_clicks=0,
                            style={'border': 'none', 'background': 'transparent'})
            ], style={'display': 'flex', 'align-items': 'center', 'gap': '5px'}),

            # Mantener oculto el DatePickerSingle
            html.Div([
                dcc.DatePickerSingle(
                    id="fecha-picker",
                    display_format="DD/MM/YYYY",
                    min_date_allowed=date(1900, 1, 1),
                    max_date_allowed=date(2040, 12, 31),
                    date=None,  # Inicialmente vacío
                    initial_visible_month=date.today(),
                    #placeholder="Fecha",
                    with_portal=True,
                    style={'position': 'absolute', 'z-index': 1000}  # Ahora visible al abrirlo
                )
            ], id="contenedor-picker", style={'display': 'none'})
        ], style={'width': '48%', 'display': 'inline-block', 'padding': '10px'}),

        html.Div([
            html.Label(['Sexo:', html.Span(' *', style={'color': 'red'})]),
            dcc.Dropdown(
                id='sexo',
                options=[
                    {'label': 'Hombre', 'value': 'Hombre'},
                    {'label': 'Mujer', 'value': 'Mujer'},
                    {'label': 'Otro', 'value': 'Otro'}
                ],
                placeholder='Seleccione el sexo',
                style={'width': '96.75%'}
            )
        ], style={'width': '48%', 'display': 'inline-block', 'padding': '10px'}),

        #html.Div([
        #    html.Label(['Peso (kg):']),
        #    dcc.Input(id='peso', type='number', placeholder='Ej. 70', min=0)
        #], style={'width': '48%', 'display': 'inline-block', 'padding': '10px'}),

        #html.Div([
        #    html.Label(['Altura (m):']),
        #    dcc.Input(id='altura', type='number', placeholder='Ej. 1.75', min=0, step=0.01)
        #], style={'width': '48%', 'display': 'inline-block', 'padding': '10px'}),

        html.Div([
            html.Label(['Nombre del Médico:']),
            dcc.Input(id='nombre-medico', type='text', placeholder='Nombre del médico')
        ], style={'width': '48%', 'display': 'inline-block', 'padding': '10px'}),

        #html.Div([
        #    dcc.Input(type="text", style={"display": "none"}),  # Input oculto para bloquear el autocompletado
        #    html.Label(['Fechas de Evaluación:', html.Span(' *', style={'color': 'red'})]),
        #    html.Div([
        #        dcc.Input(id="fecha-ini", type="text", value=initial_date.strftime('%d/%m/%Y'),
        #                  placeholder=initial_date.strftime('%d/%m/%Y'), maxLength=10, autoComplete="off"),
        #    ], style={'display': 'flex', 'align-items': 'center', 'gap': '5px'}),

        #    dcc.Input(type="text", style={"display": "none"}),  # Input oculto para bloquear el autocompletado

        #    # Mantener oculto el DatePickerRange
        #    html.Div([
        #        dcc.DatePickerRange(
        #            id="fecha-picker-range",
        #            display_format="DD/MM/YYYY",
        #            min_date_allowed=date(1900, 1, 1),
        #            max_date_allowed=date(2040, 12, 31),
        #            start_date=None,
        #            end_date=None,
        #            start_date_placeholder_text="Inicio",
        #            end_date_placeholder_text="Fin",
        #            initial_visible_month=date.today(),
        #            with_portal=True,
        #            style={'text-align': 'center', 'width': '400px'},
        #            persistence=True  # IMPORTANTE: Mantiene el estado al recarga
        #        )
        #    ], id="contenedor-picker-range", style={'display': 'none'}),
        #], style={'width': '12%', 'display': 'inline-block', 'padding': '10px'}),

        #html.Div([
        #    html.Label([html.Br()]),
        #    html.Div([
        #        dcc.Input(id="fecha-end", type="text", value=end_date.strftime('%d/%m/%Y'),
        #                  placeholder=end_date.strftime('%d/%m/%Y'), maxLength=10, autoComplete="off"),
        #        html.Button("🔽", id="abrir-rango", n_clicks=0,
        #                    style={'border': 'none', 'background': 'transparent', 'transform': 'translateX(-20%)'}),
        #    ], style={'display': 'flex', 'align-items': 'center', 'gap': '5px'}),
        #], style={'width': '16%', 'display': 'inline-block', 'padding': '10px'}),

        html.Div([
            html.Label(['Número de días de entrenamiento de fuerza:', html.Span(' *', style={'color': 'red'})]),
            dcc.Input(id='n_dias_fuerza', type='number', min=0, step=1, disabled=False,
                      placeholder='Número de días de entrenamiento', autoComplete="off")
        ], style={'width': '48%', 'display': 'inline-block', 'padding': '10px'}),

        html.Div([
            html.Label('Número de días de entrenamiento de equilibrio (> 65 años):'),
            dcc.Input(id='n_dias_equilibrio', type='number', min=0, step=1, disabled=True,
                      placeholder='Número de días de entrenamiento', autoComplete="off")
        ], style={'width': '48%', 'display': 'inline-block', 'padding': '10px'}),

        html.Div([
            html.Label('Comentarios:'),
            dcc.Textarea(id='comentarios', placeholder='Escriba sus comentarios aquí...',
                         style={'width': '95%', 'height': 200})
        ], style={'width': '100%', 'padding': '10px'}),

        html.Div([
            html.Label('Acción con el archivo:'),
            dcc.RadioItems(
                id='file-action',
                options=[
                    {'label': 'Copiar', 'value': 'copy'},
                    {'label': 'Mover', 'value': 'move'}
                ],
                value='copy',
                labelStyle={'display': 'block'}
            )
        ], style={'width': '48%', 'display': 'inline-block', 'padding': '10px'}),
    ], style={'display': 'flex', 'flex-wrap': 'wrap'})

    return html.Div([
        html.H3('Rellene el formulario del paciente'),
        common_fields
    ], className='datos')

@callback(
    Output('n_dias_equilibrio', 'disabled'),
    Input('fecha-nacimiento', 'value'),
)
def update_training_fields(fecha_nacimiento):
    global age

    if fecha_nacimiento:
        try:
            age = get_patient_age(fecha_nacimiento)
        except (ValueError, AttributeError):
            # Si la fecha es inválida, deshabilitar el campo
            return True

        if age >= 65:
            return False # Habilitar los campos
    return True # Desabilitar los campos

@callback(
    Output("fecha-nacimiento", "value"),
    Output("fecha-picker", "date"),
    Output("contenedor-picker", "style"),
    Input("fecha-nacimiento", "value"),
    Input("fecha-picker", "date"),
    Input("abrir-calendario", "n_clicks"),
    State("contenedor-picker", "style"),
    prevent_initial_call=True
)
def manejar_fecha(valor_manual, fecha_picker, btn_click, picker_style):
    ctx = dash.callback_context
    if not ctx.triggered:
        return dash.no_update, dash.no_update, dash.no_update

    triggered_id = ctx.triggered[0]["prop_id"].split(".")[0]

    if triggered_id == "abrir-calendario":
        nuevo_estilo = {
            "display": "block" if picker_style["display"] == "none" else "none",
            "position": "relative",
            "margin": "auto",
            "text-align": "center",
            "height": "60px",
            "transform": "translateX(-48%)",
        }
        return "", None, nuevo_estilo

    elif triggered_id == "fecha-picker" and fecha_picker:
        fecha_formateada = date.fromisoformat(fecha_picker).strftime("%d/%m/%Y")
        return fecha_formateada, fecha_picker, {"display": "none"}

    elif triggered_id == "fecha-nacimiento":
        formateada, _, estilo = validate_manual_date(valor_manual)
        return formateada, None, estilo

    return dash.no_update, dash.no_update, dash.no_update

@callback(
    Output("fecha-ini", "value"),  # Sincroniza el input manual de inicio
    Output("fecha-end", "value"),  # Sincroniza el input manual de fin
    Output("fecha-picker-range", "start_date"),  # Sincroniza el calendario (inicio)
    Output("fecha-picker-range", "end_date"),  # Sincroniza el calendario (fin)
    Output("contenedor-picker-range", "style"),  # Muestra u oculta el calendario
    Input("fecha-ini", "value"),  # Entrada manual inicio
    Input("fecha-end", "value"),  # Entrada manual fin
    Input("fecha-picker-range", "start_date"),  # Selección en el calendario (inicio)
    Input("fecha-picker-range", "end_date"),  # Selección en el calendario (fin)
    Input("abrir-rango", "n_clicks"),  # Clic en el botón
    State("contenedor-picker-range", "style"),  # Estado del contenedor
    State("fecha-ini", "value"),  # Estado actual del input de inicio
    State("fecha-end", "value"),  # Estado actual del input de fin
    prevent_initial_call=True
)
def manejar_fecha_rango(valor_inicio, valor_fin, picker_inicio, picker_fin, btn_click, picker_style, estado_inicio, estado_fin):
    ctx = dash.callback_context
    if not ctx.triggered:
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update

    triggered_id = ctx.triggered[0]["prop_id"].split(".")[0]

    # Si se hizo clic en el botón para abrir/cerrar el calendario
    if triggered_id == "abrir-rango":
        nuevo_estilo = {
            "display": "block" if picker_style["display"] == "none" else "none",
            "position": "relative",
            "margin": "auto",
            "text-align": "center",
            "height": "60px",
            "transform": "translateX(-10%)",  # Desplaza el calendario hacia la izquierda
        }
        return "", "", None, None, nuevo_estilo  # Borra los inputs y muestra/oculta el DatePicker

    # Si se seleccionó una fecha en el calendario
    if triggered_id in ["fecha-picker-range"]:
        fecha_inicio_formateada = date.fromisoformat(picker_inicio).strftime("%d/%m/%Y") if picker_inicio else ""
        fecha_fin_formateada = date.fromisoformat(picker_fin).strftime("%d/%m/%Y") if picker_fin else ""

        # Solo cierra el calendario si ambas fechas han sido seleccionadas
        if picker_inicio and picker_fin:
            return fecha_inicio_formateada, fecha_fin_formateada, picker_inicio, picker_fin, {"display": "none"}

        return fecha_inicio_formateada, fecha_fin_formateada, picker_inicio, picker_fin, {"display": "block"}

    if triggered_id == "fecha-ini":
        valor_inicio, _, estilo = validate_manual_date(valor_inicio)
        return valor_inicio, dash.no_update, dash.no_update, dash.no_update, estilo

    if triggered_id == "fecha-end":
        valor_fin, _, estilo = validate_manual_date(valor_fin)
        return dash.no_update, valor_fin, dash.no_update, dash.no_update, estilo

    return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update


@callback(
    Output('output-data-validation', 'children'),
    Input('submit-button', 'n_clicks'),
    State('id-paciente', 'value'),
    State('nombre', 'value'),
    State('fecha-nacimiento', 'value'),
    State('sexo', 'value'),
    #State('peso', 'value'),
    #State('altura', 'value'),
    State('nombre-medico', 'value'),
    #State('fecha-ini', 'value'),
    #State('fecha-end', 'value'),
    State('n_dias_fuerza', 'value'),
    State('n_dias_equilibrio', 'value'),
    State('comentarios', 'value'),
    State('file-dropdown', 'value'),
    State('file-action', 'value'),
    prevent_initial_call=True
)
def validate_and_save_form(n_clicks, id_paciente, nombre, fecha_nacimiento, sexo, nombre_medico, n_dias_fuerza, n_dias_equilibrio, comentarios, filename, file_action):
    """
    Valida y guarda la información del formulario de datos del paciente.

    Args:
    n_clicks (int): Número de veces que se ha pulsado el botón de aceptar.
    id_paciente (str): Identificador único del paciente.
    nombre (str): Nombre completo del paciente.
    fecha_nacimiento (date): Fecha de nacimiento del paciente.
    sexo (str): Sexo del paciente.
    peso (float): Peso del paciente en kilogramos.
    altura (float): Altura del paciente en metros.
    nombre_medico (str): Nombre del médico responsable.
    fecha_inicio (date): Fecha de inicio de la evaluación.
    fecha_fin (date): Fecha de fin de la evaluación.
    n_dias_fuerza (int): Número de días de entrenamiento de fuerza.
    n_dias_equilibrio (int): Número de días de entrenamiento de equilibrio.
    comentarios (str): Notas adicionales sobre el paciente.
    filename (str): Nombre del archivo de datos asociado al paciente.
    file_action (str): Acción a realizar con el archivo ('copy' o 'move').

    Returns:
    str or dcc.Location: Mensaje de validación o redirección a la página de trabajos.
    """
    global age

    # Transform dates values to date format
    fecha_nacimiento = datetime.strptime(fecha_nacimiento, "%d/%m/%Y").strftime("%Y-%m-%d") if fecha_nacimiento else None
    #fecha_inicio = datetime.strptime(fecha_inicio, "%d/%m/%Y").strftime("%Y-%m-%d") if fecha_inicio else None
    #fecha_fin = datetime.strptime(fecha_fin, "%d/%m/%Y").strftime("%Y-%m-%d") if fecha_fin else None

    try:
        id_paciente = _sanitize_patient_id(id_paciente)
    except ValueError as e:
        return str(e)

    campos_obligatorios = [id_paciente, fecha_nacimiento, sexo, n_dias_fuerza, filename]

    if any(campo is None or campo == "" for campo in campos_obligatorios):
        return "Todos los campos obligatorios deben completarse."
    #elif peso is not None and peso <= 0:
    #    return "Ingrese un peso válido del paciente."
    #elif altura is not None and altura <= 0:
    #    return "Ingrese una altura válida del paciente."
    elif age >= 65 and  n_dias_equilibrio is None:
        return "Debe ingresar los días de entrenamiento de equilibrio si la edad es mayor de 65 años."
    else:
        try:
            # Verificar que el archivo sea binario
            if filename.endswith('.BIN'):
                if filename is None or not isinstance(filename, (str, os.PathLike)):
                    raise ValueError(
                        "El valor de 'filename' no es válido. Debe ser una cadena de texto (str) o PathLike.")

                file_path = os.path.join(WATCH_DIRECTORY, filename)
                
                # Verificar que el archivo exista en la ruta seleccionada
                if not os.path.isfile(file_path):
                    return "El archivo seleccionado no existe."

                if id_paciente is None or not isinstance(id_paciente, (str, os.PathLike)):
                    raise ValueError(
                        "El valor de 'id_paciente' no es válido. Debe ser una cadena de texto (str) o PathLike.")

                # Cambiar el nombre y guardar el archivo definitivo
                today = datetime.today().strftime('%Y.%m.%d')
                new_filename = f"{id_paciente}_{today}.{filename.split('.')[-1]}"

                new_dirpath = os.path.join(settings.base_directory, "Datos_pacientes", id_paciente, f'{id_paciente}_{today}')
                new_binpath = os.path.join(new_dirpath, '00_bin')
                new_filepath = os.path.join(new_dirpath, '00_bin', new_filename)
                
                os.makedirs(new_dirpath, exist_ok=True)
                os.makedirs(new_binpath, exist_ok=True)
                
                if file_action == 'copy':
                    shutil.copy(file_path, new_filepath)
                else:  # 'move'
                    shutil.move(file_path, new_filepath)

                # Ruta al directorio 00_bin
                start_json_path = Path(new_binpath) / "start_bin.json"
                # Contenido minimalista al estilo PhaseTask:
                start_data = {"name": "start_bin", "status": "SUCCESS", "timestamp": time.time()}
                # Aseguramos que exista la carpeta (debería ya existir porque acabamos de crear new_binpath)
                start_json_path.parent.mkdir(parents=True, exist_ok=True)
                # Escribimos el JSON
                start_json_path.write_text(json.dumps(start_data, indent=2))

                folder = f"{id_paciente}_{today.replace('-', '.')}"
                csv_path = create_path(1, id_paciente, folder)
                bin2csv_path = Path(csv_path) / "bin2csv.json"
                bin2csv_data = {"name": "bin2csv", "status": "PENDING", "timestamp": time.time()}
                bin2csv_path.parent.mkdir(parents=True, exist_ok=True)
                # Escribimos el JSON
                bin2csv_path.write_text(json.dumps(bin2csv_data, indent=2))

                # Guardar datos del formulario en un archivo JSON
                form_data = {
                    'id_paciente': id_paciente,
                    'nombre': nombre,
                    'fecha_nacimiento': fecha_nacimiento,
                    'edad': age,
                    'sexo': sexo,
                    #'peso': peso,
                    #'altura': altura,
                    'nombre_medico': nombre_medico,
                    #'fecha_inicio': fecha_inicio,
                    #'fecha_fin': fecha_fin,
                    'n_dias_fuerza': n_dias_fuerza,
                    'n_dias_equilibrio': n_dias_equilibrio if age >= 65 else None,
                    'comentarios': comentarios,
                    'fecha_registro': today
                }
                json_filepath = os.path.join(new_dirpath, f"{id_paciente}_{today}.json")
                with open(json_filepath, 'w') as json_file:
                    json.dump(form_data, json_file, indent=4)

                # ——— Aquí arrancamos / encolamos el pipeline ———
                info = {
                    'patientId': id_paciente,
                    'patientDate': datetime.today().strftime('%Y-%m-%d')
                }
                # schedule_pipeline devolverá un mensaje tipo “🚀 …” o “⏳ …”
                _ = schedule_pipeline(id_paciente, info)

                # Redirige a la página de Trabajos
                return dcc.Location(href='/trabajos', id='redirect')
            else:
                return "El archivo debe ser de formato .BIN."
        except Exception as e:
            return f'Ocurrió un error al procesar el archivo: {e}'

@callback(
    Output('url', 'href'),
    Input('cancel-button', 'n_clicks')
)
def redirect(n_clicks):
    """
    Maneja la redirección al cancelar el formulario.

    Args:
    n_clicks (int): Número de clics en el botón de cancelar.

    Returns:
    str or dash.no_update: Redirección a la página de inicio o no actualizar la URL.
    """
    if n_clicks > 0:
        return "/trabajos"
    return dash.no_update
