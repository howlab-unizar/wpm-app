import dash
from dash import dcc, html, callback, Input, Output, State

import plotly.express as px
import plotly.graph_objects as go

import pandas as pd
import numpy as np
import os, glob, time
import json
from datetime import datetime, timedelta
import base64
import math

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

import pymupdf

from processing.utils import create_path, purge_patient_data
from processing.config import settings

# Página que muestra el informe del paciente con los datos recopilados en la sesión X
dash.register_page(
    __name__,
    path_template="/report/<patient_id>/<fecha>",  # En el URL queda registrado el número de paciente y el informe del día al que se quiere acceder.
    title="Informe de Evaluación",
    name="Informe de Evaluación"
)

# Cambiar el directorio para que se configure al iniciar la aplicación
directorio = settings.base_directory

figures = []
dataPath = ''

Dias = ['Lunes', 'Martes', 'Miércoles','Jueves', 'Viernes', 'Sábado','Domingo', 'Promedio diario']
moderada, moderada_unbt = [], []
vigorosa, vigorosa_unbt = [], []

sedentary_hours = 0

# Estilos
container_style = {
    "padding": "5px",
    #"background-color": "#f9f9f9",
    "margin-bottom": "5px",
    "border-top": "4px solid #228B22"  # Línea verde entre secciones
}
title_style = {"color": "#228B22", "text-align": "center", "font-size": "28px"}  # Verde oscuro
section_title_style = {"color": "#003366", "font-weight": "bold", "font-size": "20px", "margin-bottom": "10px",  "margin-top": "10px"}
data_style = {"display": "flex", "justify-content": "space-between", "gap": "10px", "align-items": "center", "font-size": "20px"}

def cargar_datos_json(patient_id, fecha):
    """Carga los datos del paciente desde un archivo JSON."""
    formattedDate = fecha.replace('-', '.')
    json_filepath = os.path.join(directorio, "Datos_pacientes", patient_id, f'{patient_id}_{formattedDate}', f"{patient_id}_{formattedDate}.json")
    move_json_filepath = os.path.join(directorio, "Datos_pacientes", patient_id, f'{patient_id}_{formattedDate}',
                                 "03_bio", "R", "output", "output_00_bin", "results", "resultado_estructurado.json")
    print(move_json_filepath)
    # Verificar si el archivo JSON existe
    if not os.path.exists(json_filepath):
        print(f"⚠️ Archivo JSON no encontrado: {json_filepath}")
        return {}

    if not os.path.exists(move_json_filepath):
        print(f"⚠️ Archivo JSON no encontrado: {move_json_filepath}")
        return {}

    # Leer el JSON
    with open(json_filepath, 'r', encoding='utf-8') as file:
        datos_paciente = json.load(file)

    with open(move_json_filepath, 'r', encoding='utf-8') as file:
        datos_movimiento = json.load(file)

    return datos_paciente, datos_movimiento

def find_value(datos_move, name):
    return next(
        (item['value'] for item in datos_move if item['name'] == name),
        None
    )

# Funciones de Componentes
def get_datos_paciente(datos):
    return html.Div([
        html.H3("DATOS PACIENTE", style=section_title_style),
        html.Div([
            html.Div(f"CODIGO: {datos.get('id_paciente', 'N/A')}"),
            html.Div(f"EDAD: {datos.get('edad', 'N/A')}"),
            html.Div(f"SEXO: {datos.get('sexo', 'N/A')}"),
        ], style=data_style, className="data-style")
    ], style=container_style, className="data-container")

def get_datos_evaluacion(datos_move):
    valid_days = find_value(datos_move, 'total_valid_days')
    valid_days_wd = find_value(datos_move, 'valid_weekdays')
    valid_days_we = find_value(datos_move, 'valid_weekends')
    evaluation_dates = find_value(datos_move, 'dates')
    date_ini = evaluation_dates[0]
    date_end = evaluation_dates[-1]

    return html.Div([
        html.Div([
            html.H3("FECHAS EVALUACIÓN:", style=section_title_style, className="section-title"),
            html.Div(f"FECHA INICIO: {datetime.strptime(date_ini, "%Y-%m-%d").strftime('%d/%m/%Y')}"),
            html.Div(f"FECHA FINALIZACIÓN: {datetime.strptime(date_end, "%Y-%m-%d").strftime('%d/%m/%Y')}")
        ], style=data_style, className="data-style"),
        html.Div([
            html.H3("DÍAS VÁLIDOS:", style=section_title_style, className="section-title"),
            html.Div(f"TOTALES: {valid_days}"),
            html.Div(f"ENTRE SEMANA: {valid_days_wd}"),
            html.Div(f"FIN DE SEMANA: {valid_days_we}")
        ], style=data_style, className="data-style"),
    ], style=container_style, className="data-container")

def _fmt_hm(v):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return ""
    total_min = int(round(float(v) * 60))
    if total_min < 60:
        return f"{total_min}'"
    h, m = divmod(total_min, 60)
    return f"{h} h" + (f" {m}'" if m else "")

def get_habitos_actividad_fisica(datos, datos_move):
    lig_week = round(find_value(datos_move, 'lig_week_min'))
    mod_week = round(find_value(datos_move, 'mod_week_min'))
    vig_week = round(find_value(datos_move, 'vig_week_min'))

    mod_vig_total = round(find_value(datos_move, 'guidelines_min'))
    mod_vig_eff = round(find_value(datos_move, 'guidelines_perc'), 2)

    lig_daily = find_value(datos_move, 'lig_day_min')
    mod_daily = find_value(datos_move, 'mod_day_min')
    vig_daily = find_value(datos_move, 'vig_day_min')
    days_analysed = find_value(datos_move, 'days_analysed')

    pasos = find_value(datos_move, 'steps_day_total')
    pasos_1_39 = find_value(datos_move, 'steps_day_1_39spm')
    pasos_40_99 = find_value(datos_move, 'steps_day_40_99spm')
    pasos_100 = find_value(datos_move, 'steps_day_100spm')

    data_af = {
        'intensidad': ['Ligera', 'Moderada', 'Vigorosa'],
        'values': [lig_week, mod_week, vig_week]
    }
    data_afmv = {
        'porcentaje': ['AFMV'],
        'values': [mod_vig_total]
    }

    # Build DataFrame and transform to number (the 'NA' and None are now NaN)
    df = pd.DataFrame({
        'day': days_analysed,
        'lig': lig_daily,
        'mod': mod_daily,
        'vig': vig_daily,
        'steps': pasos,
        'steps1': pasos_1_39,
        'steps2': pasos_40_99,
        'steps3': pasos_100
    })
    df['lig'] = pd.to_numeric(df['lig'], errors='coerce')
    df['mod'] = pd.to_numeric(df['mod'], errors='coerce')
    df['vig'] = pd.to_numeric(df['vig'], errors='coerce')
    df['steps'] = pd.to_numeric(df['steps'], errors='coerce')
    df['steps1'] = pd.to_numeric(df['steps1'], errors='coerce')
    df['steps2'] = pd.to_numeric(df['steps2'], errors='coerce')
    df['steps3'] = pd.to_numeric(df['steps3'], errors='coerce')

    # Reorder from Monday to Sunday
    day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    dias_es = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    df['day'] = pd.Categorical(df['day'],
                                       categories=day_order,
                                       ordered=True)

    df_grouped = df.groupby('day', as_index=True, observed=False).mean(numeric_only=True)
    df_grouped = df_grouped.reindex(day_order)

    # Extract final lists
    lig_sorted = df_grouped['lig'].tolist()
    mod_sorted = df_grouped['mod'].tolist()
    vig_sorted = df_grouped['vig'].tolist()
    steps_sorted = df_grouped['steps'].tolist()
    steps1_sorted = df_grouped['steps1'].tolist()
    steps2_sorted = df_grouped['steps2'].tolist()
    steps3_sorted = df_grouped['steps3'].tolist()

    def _avg(x):
        try:
            return float(find_value(datos_move, x))
        except (TypeError, ValueError):
            return np.nan

    lig_sorted.append(_avg('lig_week_avg'))
    mod_sorted.append(_avg('mod_week_avg'))
    vig_sorted.append(_avg('vig_week_avg'))
    steps_sorted.append(_avg('steps_total_week_avg'))
    steps1_sorted.append(_avg('steps_1_39spm_week_avg'))
    steps2_sorted.append(_avg('steps_40_99spm_week_avg'))
    steps3_sorted.append(_avg('steps_100spm_week_avg'))

    dias_local = dias_es + ["Promedio diario"]

    data_af_w = {
        'dia': dias_local,
        'Ligera': lig_sorted,
        'Moderada': mod_sorted,
        'Vigorosa': vig_sorted,
        'Pasos': steps_sorted,
        'Incidentales': steps1_sorted,
        'Intensidad ligera': steps2_sorted,
        'Intensidad moderada-vigorosa': steps3_sorted
    }

    df_af = pd.DataFrame(data_af)
    df_afmv = pd.DataFrame(data_afmv)
    df_af_w = pd.DataFrame(data_af_w)

    cols_num = ['Ligera', 'Moderada', 'Vigorosa',
                'Pasos', 'Incidentales', 'Intensidad ligera', 'Intensidad moderada-vigorosa']
    for c in cols_num:
        df_af_w[c] = pd.to_numeric(df_af_w[c], errors='coerce')  # "NA" -> NaN

    df_af_w['dia'] = pd.Categorical(df_af_w['dia'], categories=dias_local, ordered=True)

    totales = df_af_w[['Ligera', 'Moderada', 'Vigorosa']].sum(axis=1, skipna=True)
    max_total = float(totales.max(skipna=True) or 0.0)

    # Calculate max value of AFMV
    max_val = df_afmv['values'].max()
    y_limit = 300 if max_val <= 300 else math.ceil(max_val / 50) * 50

    bar_af = px.bar(df_af,x='intensidad', y='values',
                    title='Tiempo semanal empleado en actividad física por intensidad',
                    labels={'intensidad':'Intensidad de actividad física', 'values':'Tiempo acumulado semanal (min)'},
                    color='intensidad',
                    color_discrete_map={'Ligera': '#c8e6c9', 'Moderada': '#81c784', 'Vigorosa': '#388e3c'},  # Colores
                    text=data_af['values'],
                    )

    bar_af.update_traces(textposition="outside")
    bar_af.update_layout(
        title_font_size=20,  # Reducimos el tamaño de la fuente del título
        title_x=0.5,  # Centramos el título
        margin=dict(l=10, r=10, t=54, b=10),  # Ajustamos márgenes
        font=dict(size=12, family="Verdana, sans-serif"),
        height=320,
        legend=dict(
            title='Intensidad',
            orientation="v",
            x=1.02,
            y=1,
            font=dict(size=12, family="Verdana, sans-serif"),
            bgcolor="rgba(0,0,0,0)",
            borderwidth=0)
    )

    # 2) Permite que el texto fuera del eje se dibuje
    bar_af.update_traces(
        cliponaxis=False,  # no recorta etiquetas fuera del área de ejes
        selector={'type': 'bar'}
    )

    bar_af.update_yaxes(range=[0, max(df_af['values']) * 1.08])

    bar_afmv = px.bar(df_afmv, x='porcentaje', y='values',
                    title='Cumplimiento de la recomendación de<br>actividad física de la OMS',
                    labels={'porcentaje':'Actividad física moderada - vigorosa', 'values':'Tiempo acumulado semanal (min)'},
                    text=[f"{v} min, ({mod_vig_eff}%<span style='color:white'>*</span>)" for v in data_afmv['values']],
                    )

    bar_afmv.update_traces(
        textposition="auto",  # Deja que Plotly elija la mejor posición (centro si cabe)
        insidetextanchor="middle",  # Centra verticalmente el texto dentro de la barra
        textfont=dict(color="white"),  # Opcional: mejora legibilidad
        marker_color=['#718E3E' if v > 150 else 'red'
                      for v in df_afmv['values']]
    )

    bar_afmv.add_hrect(y0=0, y1=150, line_width=0, fillcolor="#FA8072", opacity=0.5, layer="below") # Rosa claro
    bar_afmv.add_hrect(y0=150, y1=300, line_width=0, fillcolor="#90EE90", opacity=0.5, layer="below") # Verde oscuro
    bar_afmv.add_hline(y=150, line_width=1, line_dash="dash", fillcolor="black")
    bar_afmv.update_yaxes(
        range=[0, y_limit],
        tick0=0,
        dtick=50     # marcas cada 50 unidades
    )

    if max_val > 300:
        bar_afmv.add_hrect(
            y0=300,
            y1=y_limit,
            line_width=0,
            fillcolor='#FFE082',  # amarillo pastel suave
            opacity=0.5,
            layer='below'
        )

    bar_afmv.update_layout(
        title_font_size=20,  # Reducimos tamaño del título
        title_x=0.5,
        height=320,
        font=dict(size=12, family="Verdana, sans-serif"),
        margin=dict(l=10, r=10, t=80, b=10),
    )

    bar_afd = px.bar(df_af_w, x='dia', y=['Ligera', 'Moderada', 'Vigorosa'],
                     title='Tiempo diario empleado en actividad física por intensidad',
                     labels={'dia': 'Día de la semana y promedio diario', 'value': 'Tiempo acumulado diario (min)'},
                     color_discrete_map={'Ligera': '#c8e6c9', 'Moderada': '#81c784', 'Vigorosa': '#388e3c'},
                     category_orders={'dia': dias_local}
                     )
    bar_afd.update_traces(selector={'name': 'Ligera'}, textposition="none")
    bar_afd.update_traces(selector={'name': 'Moderada'}, textposition="none")
    bar_afd.update_traces(selector={'name': 'Vigorosa'}, textposition="none")

    totales = df_af_w[['Ligera', 'Moderada', 'Vigorosa']].sum(axis=1)
    max_total = totales.max()

    bar_afd.update_layout(
        title_font_size=20,  # Reducimos tamaño del título
        title_x=0.5,
        margin=dict(l=10, r=10, t=40, b=10),
        height=320,
        font=dict(size=12, family="Verdana, sans-serif"),
        uniformtext_minsize=12,  # tamaño de fuente mínimo (px)
        uniformtext_mode='show',  # si no cabe, se oculta en vez de encoger
        yaxis=dict(
            range=[0, max_total * 1.16],  # 10% de espacio adicional arriba
            title="Tiempo acumulado diario (min)"
        ),
        legend=dict(
            title='Intensidad',
            orientation="v",
            x=1.02,
            y=1,
            font=dict(size=12, family="Verdana, sans-serif"),
            bgcolor="rgba(0,0,0,0)",
            borderwidth=0)
    )

    # Desactivar textos automáticos
    bar_afd.update_traces(text="", selector={'type': 'bar'})

    bar_afd.update_traces(
        texttemplate="%{y:.0f} min",  # texto “123'”
        textposition="auto",  # intenta dentro; si no cabe lo saca fuera
        insidetextanchor="middle",  # ancla el texto al centro vertical del segmento
        insidetextfont=dict(size=12, color="black"),
        outsidetextfont=dict(size=12, color="black"),
        selector={'type': 'bar'})

    # Ahora reajusta SOLO la serie “Moderada” para empujar su texto hacia abajo:
    bar_afd.update_traces(
        selector={'name': 'Moderada'},
        textposition="auto",  # forzamos dentro
        insidetextanchor="end",  # anclar al inicio del área de la barra (su base)
        textfont=dict(size=12, color="black")
    )

    bar_steps = px.bar(df_af_w, x='dia', y=['Incidentales', 'Intensidad ligera', 'Intensidad moderada-vigorosa'],
                     title='Cantidad de pasos diarios realizados por cadencia',
                     labels={'dia': 'Día de la semana y promedio diario', 'value': 'Cantidad de pasos por cadencia'},
                     color_discrete_map={'Incidentales': '#c8e6c9', 'Intensidad ligera': '#81c784', 'Intensidad moderada-vigorosa': '#388e3c'},
                     category_orders={'dia': dias_local}
                     )
    bar_steps.update_traces(selector={'name': 'Incidentales'}, textposition="none")
    bar_steps.update_traces(selector={'name': 'Intensidad ligera'}, textposition="none")
    bar_steps.update_traces(selector={'name': 'Intensidad moderada-vigorosa'}, textposition="none")

    totales = df_af_w[['Incidentales', 'Intensidad ligera', 'Intensidad moderada-vigorosa']].sum(axis=1)
    max_total = totales.max()

    bar_steps.update_layout(
        title_font_size=20,  # Reducimos tamaño del título
        title_x=0.5,
        margin=dict(l=10, r=10, t=40, b=10),
        height=320,
        font=dict(size=12, family="Verdana, sans-serif"),
        uniformtext_minsize=12,  # tamaño de fuente mínimo (px)
        uniformtext_mode='show',  # si no cabe, se oculta en vez de encoger
        yaxis=dict(
            range=[0, max_total * 1.16],  # 10% de espacio adicional arriba
            title="Cantidad de pasos por cadencia"
        ),
        legend=dict(
            title='Pasos',
            orientation="v",
            x=1.02,
            y=1,
            font=dict(size=12, family="Verdana, sans-serif"),
            bgcolor="rgba(0,0,0,0)",
            borderwidth=0)
    )

    # Desactivar textos automáticos
    bar_steps.update_traces(text="", selector={'type': 'bar'})

    bar_steps.update_traces(
        texttemplate="%{y:.0f}",
        textposition="auto",  # intenta dentro; si no cabe lo saca fuera
        insidetextanchor="middle",  # ancla el texto al centro vertical del segmento
        insidetextfont=dict(size=12, color="black"),
        outsidetextfont=dict(size=12, color="black"),
        selector={'type': 'bar'})

    # Ahora reajusta SOLO la serie “Moderada” para empujar su texto hacia abajo:
    bar_afd.update_traces(
        selector={'name': 'Intensidad ligera'},
        textposition="auto",  # forzamos dentro
        insidetextanchor="end",  # anclar al inicio del área de la barra (su base)
        textfont=dict(size=12, color="black")
    )

    n_dias_fuerza = datos.get('n_dias_fuerza', '-')
    n_dias_equilibrio = datos.get('n_dias_equilibrio', '-')

    n_dias_equilibrio = int(n_dias_equilibrio) if str(n_dias_equilibrio).isdigit() else "-"
    n_dias_fuerza = int(n_dias_fuerza) if str(n_dias_fuerza).isdigit() else "-"

    check_si_cumple_fuerza = "☒" if n_dias_fuerza >= 2 else "☐"
    check_no_cumple_fuerza = "☒" if n_dias_fuerza < 2 else "☐"

    if isinstance(n_dias_equilibrio, int) and datos.get('edad') >= 65:
        check_si_cumple_equilibrio = "☒" if n_dias_equilibrio >= 3 else "☐"
        check_no_cumple_equilibrio = "☒" if n_dias_equilibrio < 3 else "☐"
    else:
        check_si_cumple_equilibrio = "☐"
        check_no_cumple_equilibrio = "☐"

    return html.Div([
        html.Table([
            html.Tbody([
                html.Tr([
                    html.Th("HÁBITOS DE ACTIVIDAD FÍSICA SEMANAL",
                            colSpan=2, className="table-titles",
                            style={"background-color": "#81c784", "text-align": "center",
                                   "font-size": "20px", "font-weight": "bold", "padding": "10px",
                                   "border": "1px solid black", "color": "#003366"})
                ]),
                html.Tr([
                    html.Td(
                        dcc.Graph(figure=bar_af, style={"width": "100%", "height": "100%"}),
                        style={
                            "width": "60%",
                            "height": "100%",  # <-- que la celda sea 100% de su contenedor
                            "padding": "10px",
                            "border": "1px solid black",
                            #"border-bottom": "none",
                            "boxSizing": "border-box"  # para que padding y border no desborde
                        }
                    ),
                    html.Td(
                        dcc.Graph(figure=bar_afmv, style={"width": "100%", "height": "100%"}),
                        style={
                            "width": "40%",
                            "height": "100%",  # <-- que la celda sea 100% de su contenedor
                            "padding": "10px",
                            "border": "1px solid black",
                            #"border-bottom": "none",
                            "boxSizing": "border-box"  # para que padding y border no desborde
                        }
                    ),
                ]),
                html.Tr([
                    html.Td(
                        "Este gráfico presenta el tiempo semanal empleado en actividad física a diferentes "
                        "intensidades (intesidad ligera, moderada y vigorosa).",
                        style={"text-align": "left", "font-size": "18px", "font-family": "Verdana, sans-serif", "padding": "10px", "border-left": "1px solid black",
                               "border-right": "1px solid black", "lineHeight": "1.4"}),
                    html.Td([
                        html.Span("Este gráfico presenta el cumplimiento de la recomendación de actividad física de la OMS (Organización Mundial de la Salud)."),
                        html.Br(),
                        html.Span("("),
                        html.Span("*", style={'color': 'red', 'fontWeight': 'bold'}),
                        html.Span(") Grado de cumplimiento de las recomendaciones de la OMS."),
                        ], style={"text-align": "left", "font-size": "18px", "font-family": "Verdana, sans-serif", "padding": "10px", "border-left": "1px solid black",
                                  "border-right": "1px solid black", "lineHeight": "1.4"})
                ]),
                html.Tr([
                    html.Td([
                        html.Ul([
                            html.Li("La actividad física de intensidad ligera"
                                    " se trata de actividades como pasear, bañarse y otras actividades de la vida diaria que al "
                                    "realizarlas no suponen un aumento notable del ritmo cardíaco ni de la respiración."),

                            html.Li("La actividad física de intensidad moderada aumentará su ritmo cardíaco y le hará respirar más "
                                    "rápido.  Algunos ejemplos de actividades de intensidad moderada pueden ser caminar a paso "
                                    "ligero, natación, bailar, pescar, pasear en bicicleta."),

                            html.Li("La actividad física de intensidad vigorosa hará que respire fuerte y rápido, y "
                                      "prácticamente no pueda mantener una conversación. Ejemplos de actividades de esta intensidad "
                                      "pueden ser correr y otras actividades deportivas como tenis, ciclismo, fútbol, montañismo,"
                                      " baloncesto, entrenamientos de alta intensidad.")
                        ], style={"listStyleType": "disc",
                                  "paddingLeft": "20px",
                                  "marginTop": "0px",
                                  "marginBottom": "0px",
                                  "lineHeight": "1.4",
                                  "font-size": "18px",
                                  "font-family": "Verdana, sans-serif"
                                  })
                    ], colSpan=2, style={"text-align": "left", "font-size": "18px", "font-family": "Verdana, sans-serif", "padding": "10px", "lineHeight": "1.4",
                           "border-left": "1px solid black", "border-right": "1px solid black", "border-top": "1px solid black"}),
                ]),
                html.Tr(
                    html.Th("HÁBITOS DE ACTIVIDAD FÍSICA DIARIA",
                            colSpan=2, className="table-titles",
                            style={"background-color": "#81c784", "text-align": "center",
                                   "font-size": "20px", "font-weight": "bold", "padding": "10px",
                                   "border": "1px solid black", "color": "#003366"})
                ),
                html.Td(
                    dcc.Graph(figure=bar_afd, style={"width": "100%", "height": "100%"}),
                    colSpan=2,
                    style={
                        "width": "100%",
                        "height": "100%",         # <-- que la celda sea 100% de su contenedor
                        "padding": "10px",
                        "border": "1px solid black",
                        "border-bottom": "none",
                        "boxSizing": "border-box" # para que padding y border no desborde
                    }
                ),
                html.Tr([
                    html.Td([
                        "Este gráfico recoge el tiempo de actividad física diaria semanal (promedio diario) y cada día de la"
                        " semana en diferentes intensidades de actividad (ligera, moderada y vigorosa)."
                    ], colSpan=2,
                        style={"text-align": "left", "font-size": "18px", "font-family": "Verdana, sans-serif", "padding": "10px", "lineHeight": "1.4",
                               "border-left": "1px solid black", "border-right": "1px solid black"})
                ]),
                html.Tr(
                    # apply the page break on this row
                    style={
                        "pageBreakBefore": "always",
                        "breakBefore": "page"
                    },
                    children=[
                        html.Td(
                            dcc.Graph(figure=bar_steps, style={"width": "100%", "height": "100%"}),
                            colSpan=2,
                            style={
                                "width": "100%",
                                "height": "100%",         # <-- que la celda sea 100% de su contenedor
                                "padding": "10px",
                                "border": "1px solid black",
                                "border-bottom": "none",
                                "boxSizing": "border-box" # para que padding y border no desborde
                            }
                        )
                    ]
                ),
                html.Tr([
                    html.Td([
                        html.Span("Este gráfico recoge el número de pasos incidentales (cadencia entre 0 y 49 ppm),"
                                  " el número de pasos a intensidad ligera (entre 50 y 99 ppm) y el número de pasos"
                                  " a intensidad moderada-vigorosa (cadencia por encima de 99 ppm)."),
                        html.Br(),
                        html.Span(
                            "* ppm = pasos por minuto"
                            ),
                    ], colSpan=2,
                        style={"text-align": "left", "font-size": "18px", "font-family": "Verdana, sans-serif", "padding": "10px", "lineHeight": "1.4",
                               "border-left": "1px solid black", "border-right": "1px solid black"})
                ])
            ])
        ], style={"width": "102%", "border": "1px solid black", "border-collapse": "collapse",
                  "margin-bottom": "0px"}),
        html.Table([
            html.Tbody([
                html.Tr([
                    html.Th("DATOS DE ENTRENAMIENTO",
                            colSpan=2, className="table-titles",
                            style={"background-color": "#81c784", "text-align": "center",
                                   "font-size": "20px", "font-weight": "bold", "padding": "10px",
                                   "border": "1px solid black", "color": "#003366"})
                ]),
                html.Tr([
                    html.Td([
                        html.Table([
                            html.Tbody([
                                html.Tr([
                                    html.Td("Nº de días que realiza entrenamiento de fuerza:",
                                            style={"text-align": "left", "font-size": "18px", "font-family": "Verdana, sans-serif", "padding": "10px", "width": "28%", "lineHeight": "1.4"}),
                                    html.Td(f"{n_dias_fuerza}",
                                            style={"text-align": "left", "width": "50px", "padding": "10px", "font-size": "18px", "font-family": "Verdana, sans-serif"}),
                                    html.Td("Cumple recomendación de la OMS",
                                            style={"text-align": "center", "width": "30%", "padding": "10px", "font-size": "18px", "font-family": "Verdana, sans-serif"}),
                                    html.Td(f"{check_si_cumple_fuerza} Sí  {check_no_cumple_fuerza} No",
                                            style={"text-align": "left", "width": "400px", "padding": "10px", "font-size": "18px", "font-family": "Verdana, sans-serif"})
                                ])
                            ] + ([
                                html.Tr([
                                    html.Td([
                                                "Nº de días que realiza entrenamiento de equilibrio:",
                                                html.Br(),
                                                "(Solo mayores de > 65 años)"],
                                            style={"text-align": "left",
                                                   "padding": "10px",
                                                   "width": "28%", "font-size": "18px", "font-family": "Verdana, sans-serif", "lineHeight": "1.4"}),
                                    html.Td(f"{n_dias_equilibrio}",
                                            style={"text-align": "left",
                                                   "width": "50px",
                                                   "padding": "10px", "font-size": "18px", "font-family": "Verdana, sans-serif"}),
                                    html.Td(
                                        "Cumple recomendación de la OMS",
                                        style={"text-align": "center", "width": "30%",
                                               "padding": "10px", "font-size": "18px", "font-family": "Verdana, sans-serif"}),
                                    html.Td(
                                        f"{check_si_cumple_equilibrio} Sí  {check_no_cumple_equilibrio} No",
                                        style={"text-align": "left",
                                               "width": "500px",
                                               "padding": "10px", "font-size": "18px", "font-family": "Verdana, sans-serif"}),
                                ])
                            ] if n_dias_equilibrio != "-" else []))
                        ], style={"width": "100%", "border-collapse": "collapse"})
                    ], colSpan=2, style={"padding": "10px", "border": "1px solid black"})
                ])
            ])
        ], style={"width": "102%", "border": "1px solid black", "border-collapse": "collapse", "margin-bottom": "0px"})
    ], style=container_style)

def _to_float(x, default=np.nan):
    try:
        return float(x)
    except (TypeError, ValueError):
        return default

def _week_avg_or_mean(datos_move, week_key, daily_key):
    """Devuelve el promedio semanal si existe; si no, la media de la serie diaria (ignorando 'NA')."""
    v = _to_float(find_value(datos_move, week_key))*7
    if np.isfinite(v):
        return v
    daily = find_value(datos_move, daily_key) or []
    daily = pd.to_numeric(daily, errors='coerce')  # "NA" -> NaN
    if len(daily):
        m = float(np.nanmean(daily))
        return m if np.isfinite(m) else np.nan
    return np.nan

def get_recomendaciones_fisicas(datos, datos_move):
    mod_vig_total = round(find_value(datos_move, 'guidelines_min'))
    pasos = find_value(datos_move, 'steps_total_week_avg')
    min_steps = 35000
    # Obtén pasos semanales como número robusto
    actual_steps = _week_avg_or_mean(
        datos_move,
        week_key='steps_total_week_avg',
        daily_key='steps_day_total'
    )
    if not np.isfinite(actual_steps):
        actual_steps = 0.0  # valor seguro para no romper comparaciones

    afmv_min = 150
    afmv_min_low = 100
    afmv_min_very_low = 50
    afmv_actual = mod_vig_total

    recommended_strength_days = 2
    n_dias_fuerza = datos.get('n_dias_fuerza', '-')

    recommended_balance_days = 3
    n_dias_equilibrio = datos.get('n_dias_equilibrio', '-')
    n_dias_equilibrio = int(n_dias_equilibrio) if str(n_dias_equilibrio).isdigit() else "-"

    if afmv_actual >= afmv_min:
        cardio_message = (
            f"Usted cumple la recomendación de la Organización Mundial de la Salud (OMS) de realizar al menos entre entre {afmv_min} y {afmv_min*2}"
            f" minutos de actividad física de intensidad moderada a la semana. Trate de mantener su nivel actual de actividad física o en caso"
            f" de no llegar a {afmv_min*2} minutos a la semana (o {"{:,}".format(min_steps*2).replace(",", ".")} pasos) trate de  incrementarlo hasta esa cantidad o más, para obtener beneficios"
            f" adicionales para su salud. Respecto al número de pasos, se recomienda aumentar su número total, pero si su salud lo permite, es más favorable"
            f" si dicho aumento se produce en el número de pasos de intensidad moderada-vigorosa (caminar rápido). Si dispone de podómetro o dispositivo"
            f" que le registre el número de pasos diarios, puede resultarle de utilidad para controlar su evolución y mejorar.")

    elif actual_steps >= min_steps:
        cardio_message = (
            f"Usted cumple con la recomendación de realizar al menos {"{:,}".format(min_steps).replace(",", ".")} pasos a la semana, pero no cumple con la recomendación de la Organización Mundial de la"
            f" Salud (OMS) de realizar al menos entre {afmv_min} y {afmv_min*2} minutos a la semana de actividad física de intensidad moderada. Esto significa que usted realiza caminando una"
            f" cantidad apreciable de actividad física que es beneficiosa para su salud, sin embargo, sería deseable que realizase alguna actividad"
            f" de mayor intensidad a lo largo de la semana, lo que supondría beneficios adicionales para su salud. Respecto al número de pasos, se recomienda un"
            f" número total de al menos {"{:,}".format(min_steps*2).replace(",", ".")} pasos, o más si es posible, pero si su salud lo permite, es más favorable si dicho aumento se produce en el número"
            f" de pasos de intensidad moderada-vigorosa (caminar rápido). Si dispone de podómetro o dispositivo que le registre el número de pasos diarios, puede"
            f" resultarle de utilidad para controlar su evolución y mejorar.")

    elif afmv_actual > afmv_min_low:
        cardio_message = html.Div([
            html.P([
                f"Su nivel de actividad física cardiovascular actual es “",
                html.U("BAJO"),
                f"”. Usted no cumple la recomendación de la Organización Mundial de la Salud (OMS) "
                f"de realizar entre {afmv_min} y {afmv_min * 2} minutos de actividad física de intensidad moderada a la semana.",
                html.Br(), html.Br(),

                html.B(html.U("Recomendación básica:")),
                f" Dado su nivel de actividad física actual, le recomendamos incrementar su actividad física de intensidad moderada al menos a “",
                html.U(f"{afmv_min} minutos"), f"” a la semana, o bien caminar más de “", html.U(f"{"{:,}".format(min_steps).replace(",", ".")} pasos"), f"” a la semana."
                f"Respecto al número de pasos, se recomienda aumentar su número total, pero si su salud lo permite, es más favorable si dicho aumento se produce en el número de pasos"
                f" de intensidad moderada-vigorosa (caminar rápido). Si dispone de podómetro o dispositivo que le registre el número de pasos diarios, puede resultarle de utilidad"
                f" para controlar su evolución y mejorar.",
                html.Br(), html.Br(),

                html.B(html.U("Recomendación avanzada:")),
                f" Una vez alcanzada la recomendación anterior, le proponemos que trate de alcanzar “", html.U(f"{afmv_min_low*2} minutos"),
                f"” a la semana de actividad física moderada o bien caminar más de “", html.U(f"{"{:,}".format(47000).replace(",", ".")} pasos"), f"” a la semana.",
                html.Br(), html.Br(),

                html.B(html.U("Recomendación óptima:")),
                f" Para conseguir mayores beneficios para su salud, le invitamos a que de forma progresiva y a medio plazo llegue a alcanzar “",
                html.U(f"{afmv_min*2} minutos"), f"” de actividad física moderada a la semana o bien a caminar más de “", html.U(f"{"{:,}".format(min_steps*2).replace(",", ".")} pasos"),
                f"” a la semana. Si alcanza ese nivel de actividad física los beneficios para su salud se incrementarán notablemente."
            ], style={"white-space": "pre-line"})  # Permite que los saltos de línea funcionen correctamente
        ])
    elif afmv_actual > afmv_min_very_low:
        cardio_message = html.Div([
            html.P([
                f"Su nivel de actividad física cardiovascular actual es “",
                html.U("MUY BAJO"),
                f"”. Usted no cumple la recomendación de la Organización Mundial de la Salud (OMS) "
                f"de realizar entre {afmv_min} y {afmv_min * 2} minutos de actividad física de intensidad moderada a la semana.",
                html.Br(), html.Br(),

                html.B(html.U("Recomendación básica:")),
                f" Dado su nivel de actividad física actual, le recomendamos incrementar su actividad física de intensidad moderada al menos a “",
                html.U(f"{afmv_min_low} minutos"), f"” a la semana, o bien caminar más de “",
                html.U(f"{"{:,}".format(23500).replace(",", ".")} pasos"), f"” a la semana. Respecto al número de pasos, se recomienda"
                f" aumentar su número total, pero si su salud lo permite, es más favorable si dicho aumento se produce en el número de pasos de"
                f" intensidad moderada-vigorosa (caminar rápido). Si dispone de podómetro o dispositivo que le registre el número de pasos diarios,"
                f" puede resultarle de utilidad para controlar su evolución y mejorar.",
                html.Br(), html.Br(),

                html.B(html.U("Recomendación avanzada:")),
                f" Una vez alcanzada la recomendación anterior, le proponemos que trate de alcanzar “",
                html.U(f"{afmv_min} minutos"),
                f"” a la semana de actividad física moderada o bien caminar más de“",
                html.U(f"{"{:,}".format(min_steps).replace(",", ".")} pasos"), f"” a la semana.",
                html.Br(), html.Br(),

                html.B(html.U("Recomendación óptima:")),
                f" Para conseguir mayores beneficios para su salud, le invitamos a que de forma progresiva y a medio plazo llegue a alcanzar “",
                html.U(f"{afmv_min_low * 2} minutos"), f"” de actividad física moderada a la semana o bien a caminar más de “",
                html.U(f"{"{:,}".format(47000).replace(",", ".")} pasos"),
                f"” a la semana. Si alcanza ese nivel de actividad física los beneficios para su salud se incrementarán notablemente."
            ], style={"white-space": "pre-line"})  # Permite que los saltos de línea funcionen correctamente
        ])
    elif afmv_actual <= afmv_min_very_low:
        cardio_message = html.Div([
            html.P([
                f"Su nivel de actividad física cardiovascular actual es “",
                html.U("EXTREMADAMENTE BAJO"),
                f"”. Usted no cumple la recomendación de la Organización Mundial de la Salud (OMS) "
                f"de realizar entre {afmv_min} y {afmv_min * 2} minutos de actividad física de intensidad moderada a la semana.",
                html.Br(), html.Br(),

                html.B(html.U("Recomendación básica:")),
                f" Dado su nivel de actividad física actual, le recomendamos incrementar su actividad física de intensidad moderada al menos a “",
                html.U(f"{int(afmv_min/2)} minutos"), f"” a la semana, o bien caminar más de “",
                html.U(f"{"{:,}".format(int(min_steps/2)).replace(",", ".")} pasos"), f"” a la semana. Respecto al número de pasos, se"
                f" recomienda aumentar su número total, pero si su salud lo permite, es más favorable si dicho aumento se produce en el número de"
                f" pasos de intensidad moderada-vigorosa (caminar rápido). Si dispone de podómetro o dispositivo que le registre el número de pasos"
                f" diarios, puede resultarle de utilidad para controlar su evolución y mejorar.",
                html.Br(), html.Br(),

                html.B(html.U("Recomendación avanzada:")),
                f" Una vez alcanzada la recomendación anterior, le proponemos que trate de alcanzar “",
                html.U(f"{afmv_min_low} minutos"),
                f"” a la semana de actividad física moderada o bien caminar más de “",
                html.U(f"{"{:,}".format(23500).replace(",", ".")} pasos"), f"” a la semana.",
                html.Br(), html.Br(),

                html.B(html.U("Recomendación óptima:")),
                f" Para conseguir mayores beneficios para su salud, le invitamos a que de forma progresiva y a medio plazo llegue a alcanzar “",
                html.U(f"{afmv_min} minutos"), f"” de actividad física moderada a la semana o bien a caminar más de “",
                html.U(f"{"{:,}".format(min_steps).replace(",", ".")} pasos"),
                f"” a la semana. Si alcanza ese nivel estará cumpliendo la recomendación mínima de la OMS y los beneficios para su salud se incrementarán notablemente."
            ], style={"white-space": "pre-line"})  # Permite que los saltos de línea funcionen correctamente
        ])
    else:
        cardio_message = ""

    if n_dias_fuerza == 0:
        strength_message = (
            f"Las actividades de fortalecimiento muscular tienen beneficios sobre la salud, de ahí que la Organización Mundial de la Salud aconseje realizar al menos"
            f" {recommended_strength_days} días a la semana de estas actividades a intensidad moderada o superior, que involucren a todos los principales grupos musculares."
            f" Si no tiene experiencia previa en este tipo de actividades se recomienda que acuda a profesionales deportivos cualificados.")
    elif n_dias_fuerza == 1:
        strength_message = (
            f"Se le aconseja incrementar a al menos {recommended_strength_days} días a la semana de actividades de fortalecimiento muscular de intensidad moderada o superior"
            f" que involucren a todos los principales grupos musculares. Si desea seguir progresando en el fortalecimiento muscular se recomienda que acuda a profesionales cualificados.")
    else:
        strength_message = (
            f"Es importante que mantenga los días a la semana de actividades de fortalecimiento muscular o incluso los incremente, realizando dichas actividades a intensidad"
            f" moderada o superior e involucrando a todos los principales grupos musculares. Si desea seguir progresando en el fortalecimiento muscular se recomienda que acuda"
            f" a profesionales deportivos cualificados.")

    if n_dias_equilibrio == "-":
        balance_message = "-"
    elif n_dias_equilibrio == 0:
        balance_message = (
            f"Los ejercicios de equilibrio tienen beneficios sobre la salud, de ahí que la Organización Mundial de la Salud aconseje realizarlo {recommended_balance_days} o más días a la"
            f" semana, pudiéndose combinar en la misma sesión con los ejercicios de fortalecimiento muscular y de capacidad aeróbica. Es por ello, que es importante que comience a incorporar"
            f" ejercicios de equilibrio en su rutina semanal, al menos {recommended_balance_days-1} veces por semana y alcanzando, si es posible, {recommended_balance_days} o más. Si no"
            f" tiene experiencia previa en este tipo de actividades se recomienda que acuda a profesionales deportivos cualificados.")
    elif n_dias_equilibrio <= 2:
        balance_message = (
            f"Le recomendamos aumentar la frecuencia de sus ejercicios de equilibrio a al menos {recommended_balance_days} días por semana, pudiéndose combinar en la misma sesión con"
            f" los ejercicios de fortalecimiento muscular y de capacidad aeróbica. Esto ayudará a mejorar su estabilidad y reducir el riesgo de caídas.")
    else:
        balance_message = (
            f"Su nivel actual de entrenamiento de equilibrio es adecuado. Mantenga esta rutina y considere incluir variaciones o incrementar el desafío según su capacidad.")

    return html.Div([
        html.Table([
            html.Tbody([
                html.Tr([
                    html.Th("RECOMENDACIONES PERSONALIZADAS SOBRE LA ACTIVIDAD FÍSICA",
                            colSpan=2, className="table-titles",
                            style={"background-color": "#81c784", "text-align": "center",
                                   "font-size": "20px", "font-weight": "bold", "padding": "10px",
                                   "border": "1px solid black", "color": "#003366"})
                ]),
                html.Tr([
                    html.Td([
                        html.H3("RECOMENDACIÓN DE ACTIVIDAD FÍSICA CARDIOVASCULAR",
                                style={"font-weight": "bold", "font-size": "20px", "margin-bottom": "10px",
                                       "margin-top": "10px", "margin-left": "10px"},
                                className="section-title"),
                        html.Span([cardio_message],
                                  style={"margin-left": "10px", "margin-right": "10px", "margin-bottom": "10px",
                                         "display": "block", "lineHeight": "1.4", "font-size": "18px", "font-family": "Verdana, sans-serif"})
                    ])
                ], style={"border": "1px solid black"}),
                html.Tr([
                    html.Td([
                        html.H3("RECOMENDACIÓN DE ACTIVIDAD FÍSICA DE FUERZA",
                                style={"font-weight": "bold", "font-size": "20px", "margin-bottom": "10px",
                                       "margin-top": "10px", "margin-left": "10px"},
                                className="section-title"),
                        html.Span([strength_message],
                                  style={"margin-left": "10px", "margin-right": "10px", "margin-bottom": "10px",
                                         "display": "block", "lineHeight": "1.4", "font-size": "18px", "font-family": "Verdana, sans-serif"})
                    ])
                ], style={"border": "1px solid black"})
            ] + ([
                html.Tr([
                    html.Td([
                        html.H3("RECOMENDACIÓN DE ACTIVIDAD FÍSICA DE EQUILIBRIO (sólo si es mayor de 65 años)",
                                style={"font-weight": "bold", "font-size": "20px", "margin-bottom": "10px",
                                       "margin-top": "10px", "margin-left": "10px"},
                                className="section-title"),
                        html.Span([balance_message],
                                  style={"margin-left": "10px", "margin-right": "10px", "margin-bottom": "10px",
                                         "display": "block", "lineHeight": "1.4", "font-size": "18px", "font-family": "Verdana, sans-serif"})
                    ])
                ], style={"border": "1px solid black"})
            ] if n_dias_equilibrio != "-" else []))
        ], style={"width": "102%", "border": "1px solid black", "border-collapse": "collapse", "margin-bottom": "0px"})
    ], style={"padding": "5px", "margin-bottom": "0px"})

def get_comportamiento_sedentario(datos_move):
    global sedentary_hours
    dur_day_total_in_min = find_value(datos_move, 'dur_day_IN_unbt_min')
    dur_day_in_bts_60_min = find_value(datos_move, 'dur_day_IN_bts_60_min')
    days_analysed = find_value(datos_move, 'days_analysed')

    # Build DataFrame and transform to number (the 'NA' and None are now NaN)
    df = pd.DataFrame({
        'day': days_analysed,
        'total': pd.to_numeric(dur_day_total_in_min, errors='coerce'),
        'sed': pd.to_numeric(dur_day_in_bts_60_min, errors='coerce'),
    })

    # Reorder from Monday to Sunday
    day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    dias_es = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    df['day'] = pd.Categorical(df['day'],
                                       categories=day_order,
                                       ordered=True)

    df_grouped = df.groupby('day', as_index=True, observed=False).mean(numeric_only=True)
    df_grouped = df_grouped.reindex(day_order)

    # Extract final lists
    total_sorted = df_grouped['total'].tolist()
    sed_60_sorted = df_grouped['sed'].tolist()

    avg_unbt_h = _to_float(find_value(datos_move, 'sb_unbt_week_avg'))  # puede ser "NA"/None
    avg_bts_h = _to_float(find_value(datos_move, 'sb_bts_week_avg'))
    total_sorted.append(avg_unbt_h * 60 if np.isfinite(avg_unbt_h) else np.nan)
    sed_60_sorted.append(avg_bts_h * 60 if np.isfinite(avg_bts_h) else np.nan)

    dias_local = dias_es + ["Promedio diario"]

    interrumpido = [max(t - p, 0) for t, p in zip(total_sorted, sed_60_sorted)]
    df_sedentario = pd.DataFrame({
        'Día': dias_local,
        'Prolongado': sed_60_sorted,
        'Con interrupciones': total_sorted
    })

    for c in ['Prolongado', 'Con interrupciones']:
        df_sedentario[c] = pd.to_numeric(df_sedentario[c], errors='coerce')
    df_sedentario['Día'] = pd.Categorical(df_sedentario['Día'], categories=dias_local, ordered=True)

    last_unbt = total_sorted[-1] if len(total_sorted) else np.nan
    last_bts = sed_60_sorted[-1] if len(sed_60_sorted) else np.nan
    sedentary_hours = round(float((last_unbt + last_bts) / 60) if np.isfinite(last_unbt) and np.isfinite(last_bts) else 0.0, 2)

    bar_sed = px.bar(df_sedentario, x='Día', y=['Con interrupciones', 'Prolongado'],
                     title="Comportamiento sedentario diario",
                     labels={'Día': 'Día de la semana y promedio diario', 'value': 'Tiempo sedentario (min)', 'variable': 'Tipo de sedentarismo'},
                     color_discrete_map={
                         'Con interrupciones': '#81c784',  # Verde moderado
                         'Prolongado': '#FF4500'  # Rojo intenso
                     },
                     category_orders={'Día': dias_local}
                     )

    totales_min = df_sedentario[['Con interrupciones', 'Prolongado']].sum(axis=1, skipna=True)
    y_max_min = float(np.nanmax(totales_min)) if len(totales_min) else 0.0
    y_max_min = max(720.0, y_max_min)  # al menos 12 h
    y_max_min = math.ceil(y_max_min / 60.0) * 60.0  # redondea a la hora superior
    y_max_min += 60.0  # 1 h de margen visual

    # Verde < 7h (420 min)
    bar_sed.add_hrect(y0=0, y1=min(420, int(y_max_min)), fillcolor="lightgreen", opacity=0.3, layer="below", line_width=0)
    # Naranja 7–9h (420–540 min)
    bar_sed.add_hrect(y0=min(420, int(y_max_min)), y1=min(540, int(y_max_min)), fillcolor="orange", opacity=0.3, layer="below", line_width=0)
    # Rojo > 9h (540+ min)
    if y_max_min > 540:
        bar_sed.add_hrect(y0=540, y1=y_max_min, fillcolor="red", opacity=0.3, layer="below", line_width=0)

    ticks = list(range(0, int(y_max_min)+1, 60))
    bar_sed.update_yaxes(
        range=[0, y_max_min],
        tickvals=ticks,
        ticktext=[f"{t // 60}" for t in ticks],
        title_text="Tiempo (horas)"
    )

    bar_sed.update_traces(width=0.65)
    bar_sed.update_layout(
        barmode='stack',
        bargap=0.2,
        bargroupgap=0.1,
        title_x=0.5,
        title_font_size=20,
        margin=dict(l=20, r=20, t=40, b=20),
        height=320,
        legend=dict(
            title='Tipo de sedentarismo',
            orientation="v",
            x=1.02,
            y=1,
            font=dict(size=12, family="Verdana, sans-serif"),
            bgcolor="rgba(0,0,0,0)",
            borderwidth=0
        )
    )
    for trace in bar_sed.data:
        # convierto cada valor de 'y' (minutos) a horas
        trace.customdata = [v / 60 for v in trace.y]

    # Textos por serie (en el mismo orden que las columnas del px.bar)
    txt_con = [_fmt_hm(v/60) for v in df_sedentario["Con interrupciones"]]
    txt_pro = [_fmt_hm(v/60) for v in df_sedentario["Prolongado"]]

    # Asignar texto a cada traza del bar apilado (el orden en px.bar es y=['Con interrupciones','Prolongado'])
    bar_sed.data[0].text = txt_con  # Con interrupciones
    bar_sed.data[1].text = txt_pro  # Prolongado

    bar_sed.update_traces(
        texttemplate="%{text}",
        textposition="auto",
        insidetextanchor="middle",
        insidetextfont=dict(size=12, color="black"),
        outsidetextfont=dict(size=12, color="black"),
        selector={'type': 'bar'}
    )

    graph_sed = dcc.Graph(figure=bar_sed,
                          style={"width": "100%", "height": "400px"})

    total_hours = sedentary_hours
    min_recommended_hours = 7
    max_recommended_hours = 9

    extended_time = 90
    max_extended_time = 120

    if total_hours < min_recommended_hours:
        first_sedentary_message = html.Div([
            html.P([
                f"Su tiempo promedio de sedentarismo diario total es ", html.B("ACEPTABLE"),
                f". Se recomienda no aumentarlo y si es posible, reducirlo, ya que menor tiempo de sedentarismo es mejor para su salud.",
            ], style={"white-space": "pre-line"})  # Permite que los saltos de línea funcionen correctamente
        ])
    elif total_hours <= max_recommended_hours:
        first_sedentary_message = html.Div([
            html.P([
                f"Su tiempo promedio de sedentarismo diario total es ", html.B("MEJORABLE"),
                f" y se recomienda reducirlo por debajo de las {min_recommended_hours} horas diarias, si es posible, ya que menor tiempo de sedentarismo es mejor para su salud.",
            ], style={"white-space": "pre-line"})  # Permite que los saltos de línea funcionen correctamente
        ])
    else:
        first_sedentary_message = html.Div([
            html.P([
                f"Su tiempo promedio de sedentarismo diario total es ", html.B("DEMASIADO ELEVADO"),
                f". Se recomienda reducirlo por debajo de las {min_recommended_hours} horas diarias, si es posible, ya que menor tiempo de sedentarismo es mejor para su salud.",
            ], style={"white-space": "pre-line"})  # Permite que los saltos de línea funcionen correctamente
        ])

    if extended_time < max_extended_time:
        second_sedentary_message = html.Div([
            html.P([
                f"Sus periodos de sedentarismo de forma continuada (más de 60 minutos seguidos en posición sentada o tumbada) son ", html.B("ACEPTABLES"),
                f", si bien se recomienda intentar reducirlos por debajo de {int(max_extended_time/2)} minutos, ya que periodos de sedentarismo continuado más cortos son menos perjudiciales"
                f" para su salud. Para ello, se aconseja romper los periodos de sedentarismo al menos cada {int(max_extended_time/2)} minutos, sentándose y levantándose de la silla varias veces"
                f" y realizando periodos cortos de ejercicio  (3-5 minutos) que incluyan actividades, al menos de intensidad ligera, como puede ser caminar y/o movilidad articular antes de volver"
                f" a la posición sedentaria.",
            ], style={"white-space": "pre-line"})  # Permite que los saltos de línea funcionen correctamente
        ])
    else:
        second_sedentary_message = html.Div([
            html.P([
                f"Sus periodos de sedentarismo de forma continuada (más de {int(max_extended_time/2)} minutos seguidos en posición sedentaria) son ", html.B("DEMASIADO ELEVADOS"),
                f", y se recomienda intentar reducirlos por debajo de {int(max_extended_time/2)} minutos, ya que periodos de sedentarismo continuado más cortos son menos perjudiciales para su salud."
                f" Para ello, se aconseja romper los periodos de sedentarismo al menos cada {int(max_extended_time/2)} minutos, sentándose y levantándose de la silla varias veces y realizando periodos"
                f" cortos de ejercicio (3-5 minutos) que incluyan actividades, al menos de intensidad ligera, como puede ser caminar y/o movilidad articular antes de volver a la posición sedentaria.",
            ], style={"white-space": "pre-line"})  # Permite que los saltos de línea funcionen correctamente
        ])

    return html.Div([
        html.Table([
            html.Tbody([
                html.Tr([
                    html.Th("HÁBITOS DIARIOS DE COMPORTAMIENTO SEDENTARIO",
                            colSpan=2, className="table-titles",
                            style={"background-color": "#81c784", "text-align": "center",
                                   "font-size": "20px", "font-weight": "bold", "padding": "10px",
                                   "border": "1px solid black", "color": "#003366"})
                ]),
                html.Tr([
                    html.Td(
                        dcc.Graph(figure=bar_sed, style={"width": "100%", "height": "100%"}),
                        colSpan=2,
                        style={
                            "width": "100%",
                            "height": "100%",  # <-- que la celda sea 100% de su contenedor
                            "padding": "10px",
                            "border": "1px solid black",
                            "border-bottom": "none",
                            "boxSizing": "border-box"  # para que padding y border no desborde
                        }
                    )
                ]),
                html.Tr([
                    html.Td([
                        html.Span("Este gráfico presenta el tiempo dedicado a actividades sedentarias semanalmente (promedio diario) y cada día de la semana."
                        " Presenta información sobre tiempo sedentario total, tiempo en sedentarismo prolongado (periodos de más de 60 minutos "
                        "continuados) y tiempo sedentario con interrupciones (periodos de menos de 60 minutos continuados)."),
                        html.Br(),html.Br(),
                        html.Span("El comportamiento sedentario es cualquier comportamiento que hacemos despiertos "
                                  "donde el gasto energético es muy bajo y se realizan en posición sentada, reclinada "
                                  "o acostada. La mayoría de los trabajos de oficina, conducir y ver la televisión "
                                  "son ejemplos de estos comportamientos.")
                    ], colSpan=2,
                        style={"text-align": "left", "lineHeight": "1.4", "font-size": "18px", "font-family": "Verdana, sans-serif", "padding": "10px",
                               "border-left": "1px solid black", "border-right": "1px solid black", "border-bottom": "1px solid black"})
                ]),
                #html.Tr([
                #    html.Td("", colSpan=2, style={"page-break-before": "always", "border": "none", "padding": "0px"})
                #]),
                html.Tr([
                    html.Th("RECOMENDACIONES PERSONALIZADAS SOBRE EL TIEMPO SEDENTARIO",
                            colSpan=2, className="table-titles",
                            style={"background-color": "#81c784", "text-align": "center",
                                   "font-size": "20px", "font-weight": "bold", "padding": "10px",
                                   "border-left": "1px solid black", "border-right": "1px solid black", "border-bottom": "1px solid black", "color": "#003366"})
                ]),
                html.Tr([
                    html.Td([
                        html.Span([first_sedentary_message],
                                  style={"margin-left": "10px", "margin-right": "10px", "margin-bottom": "25px",
                                         "display": "block", "lineHeight": "1.4", "font-size": "18px", "font-family": "Verdana, sans-serif"}),
                        html.Span([second_sedentary_message],
                                  style={"margin-left": "10px", "margin-right": "10px", "margin-bottom": "10px",
                                         "display": "block", "lineHeight": "1.4", "font-size": "18px", "font-family": "Verdana, sans-serif"})
                    ])
                ], style={"border": "1px solid black"}),
            ])
        ], style={"width": "102%", "border": "1px solid black", "border-collapse": "collapse", "margin-bottom": "0px"})
    ], style={"padding": "5px", "margin-bottom": "0px"})

def marcar_celda(texto, mod_vig_total,  min_fisica, max_fisica, min_sedentarismo, max_sedentarismo):
    """ Marca con un * la celda correspondiente a la combinación actual de actividad física y sedentarismo """
    global sedentary_hours
    actual_minutes_physical = mod_vig_total
    if min_fisica <= actual_minutes_physical < max_fisica and min_sedentarismo <= sedentary_hours < max_sedentarismo:
        return html.B(f"{texto.upper()} *")  # Agrega el asterisco solo a la celda correcta
    return texto

def riesgo_comb_act_fisica_sedentarismo(datos_move):
    global sedentary_hours
    mod_total = find_value(datos_move, 'mod_week_avg')
    vig_total = find_value(datos_move, 'vig_week_avg')
    mod_vig_total = round(mod_total + vig_total, 2)

    actual_hours_sedentary = sedentary_hours
    min_hours_sedentary = 4
    mid_hours_sedentary = 6
    max_hours_sedentary = 8

    actual_minutes_physical = mod_vig_total
    min_minutes_physical = 5
    mid_minutes_physical = 30
    max_minutes_physical = 60

    if actual_minutes_physical < min_minutes_physical and actual_hours_sedentary > max_hours_sedentary:
        title_comb_message = "ROJO: Riesgo “ALTO” (Incremento del riesgo mayor al 45%)"
        background_color = "#FF0000"
        text_color = "white"
        combination_message = html.Div([
            html.P([
                f"El nivel de riesgo para su salud asociado a sus hábitos de actividad física y sedentarismo es “", html.B(html.U("ALTO")),
                f"”. Para comenzar a disminuir su riesgo, usted debería o bien reducir el tiempo que pasa realizando actividades sedentarias a menos de {max_hours_sedentary} horas al día o bien"
                f" incrementar su nivel de actividad física moderada-vigorosa en más de {min_minutes_physical} minutos al día (o ambas cosas a la vez). También contribuirá a reducir su riesgo evitar largos periodos"
                f" de sedentarismo introduciendo interrupciones con actividad física ligera (como caminar brevemente). Si quiere reducir su riesgo en mayor medida, incremente más"
                f" esos niveles de actividad física y reduzca más su sedentarismo. Se recomienda no aumentarlo y si es posible, reducirlo, ya que menor tiempo de sedentarismo es mejor para su salud.",
            ], style={"white-space": "pre-line"})  # Permite que los saltos de línea funcionen correctamente
        ])
    elif actual_minutes_physical < min_minutes_physical and actual_hours_sedentary >= min_hours_sedentary:
        title_comb_message = "ROJO: Riesgo “MODERADO-ALTO” (Incremento del riesgo del 30 al 45%)"
        background_color = "#FF0000"
        text_color = "white"
        combination_message = html.Div([
            html.P([
                f"El nivel de riesgo para su salud asociado a sus hábitos de actividad física y sedentarismo es “", html.B(html.U("MODERADO-ALTO")),
                f"”. Para comenzar a disminuir su riesgo usted debería o bien reducir el tiempo que pasa realizando actividades sedentarias a menos de {min_hours_sedentary} horas al día o bien incrementar"
                f" su nivel de actividad física moderada-vigorosa por encima de {min_minutes_physical} minutos al día (o ambas cosas a la vez). También contribuirá a reducir su riesgo evitar largos periodos de sedentarismo"
                f" introduciendo interrupciones con actividad física ligera (como caminar brevemente). Si quiere reducir su riesgo en mayor medida, incremente más esos niveles de actividad física y reduzca"
                f" más su sedentarismo.",
            ], style={"white-space": "pre-line"})  # Permite que los saltos de línea funcionen correctamente
        ])
    elif (actual_minutes_physical < min_minutes_physical and actual_hours_sedentary < min_hours_sedentary) or (actual_minutes_physical < mid_minutes_physical and actual_hours_sedentary >= min_hours_sedentary):
        title_comb_message = "NARANJA: Riesgo “MODERADO” (Incremento del riesgo del 15 al 30%)"
        background_color = "#FFA500"
        text_color = "black"
        combination_message = html.Div([
            html.P([
                f"El nivel de riesgo para su salud asociado a sus hábitos de actividad física y sedentarismo es “", html.B(html.U("MODERADO")),
                f"”. Para comenzar a disminuir su riesgo usted debería o bien reducir el tiempo que pasa realizando actividades sedentarias a menos de {min_hours_sedentary} horas al día o bien incrementar su"
                f" nivel de actividad física moderada-vigorosa por encima de {mid_minutes_physical} minutos al día (o ambas cosas a la vez). Evitar largos periodos de sedentarismo introduciendo interrupciones con actividad física"
                f" ligera (como caminar brevemente) también tendrá efectos beneficiosos en su salud. Si quiere reducir su riesgo en mayor medida, incremente más esos niveles de actividad física y reduzca más su sedentarismo.",
            ], style={"white-space": "pre-line"})  # Permite que los saltos de línea funcionen correctamente
        ])
    elif (actual_minutes_physical < mid_minutes_physical and actual_hours_sedentary < min_hours_sedentary) or (actual_minutes_physical <= max_minutes_physical and actual_hours_sedentary >= min_hours_sedentary):
        title_comb_message = "AMARILLO: Riesgo “BAJO-MODERADO” (Incremento del riesgo del 1 al 15%)"
        background_color = "#FFFF99"
        text_color = "black"
        combination_message = html.Div([
            html.P([
                f"El nivel de riesgo para su salud asociado a sus hábitos de actividad física y sedentarismo es “", html.B(html.U("BAJO-MODERADO")),
                f"”. Aunque su riesgo no es muy alto, si usted quisiera disminuirlo más, debería reducir el tiempo que pasa realizando actividades sedentarias a menos de {min_hours_sedentary} horas al día o incrementar"
                f" su nivel de actividad física moderada-vigorosa por encima de {max_minutes_physical} minutos al día (o ambas cosas a la vez). Evitar largos periodos de sedentarismo introduciendo interrupciones con actividad física ligera"
                f" (como caminar brevemente) también tendrá efectos beneficiosos en su salud. Si quiere reducir su riesgo en mayor medida, incremente más esos niveles de actividad física y reduzca más su sedentarismo.",
            ], style={"white-space": "pre-line"})  # Permite que los saltos de línea funcionen correctamente
        ])
    elif actual_minutes_physical <= max_minutes_physical and actual_hours_sedentary < min_hours_sedentary:
        title_comb_message = "VERDE: Riesgo “BAJO” (Sin riesgo incrementado)"
        background_color = "#90EE90"
        text_color = "black"
        combination_message = html.Div([
            html.P([
                f"El nivel de riesgo para su salud asociado a sus hábitos de actividad física y sedentarismo es “", html.B(html.U("BAJO")),
                f"”. ¡ENHORABUENA! Mantenga su bajo nivel de sedentarismo y mantenga o aumente su nivel actual de actividad física.",
            ], style={"white-space": "pre-line"})  # Permite que los saltos de línea funcionen correctamente
        ])
    else:
        title_comb_message = "VERDE: Riesgo “BAJO” (Sin riesgo incrementado)"
        background_color = "#90EE90"
        text_color = "black"
        combination_message = html.Div([
            html.P([
                f"El nivel de riesgo para su salud asociado a sus hábitos de actividad física y sedentarismo es “", html.B(html.U("BAJO")),
                f"”. ¡ENHORABUENA! Mantenga sus altos niveles de actividad física diaria, sin aumentar el tiempo de sedentarismo o incluso reduciéndolo.",
            ], style={"white-space": "pre-line"})  # Permite que los saltos de línea funcionen correctamente
        ])

    return html.Div([
        html.Table([
            html.Tbody([
                html.Tr([
                    html.Th("RIESGO COMBINADO DE ACTIVIDAD FÍSICA Y SEDENTARISMO",
                            colSpan=5, className="table-titles",
                            style={"background-color": "#81c784", "text-align": "center",
                                   "font-size": "20px", "font-weight": "bold", "padding": "10px",
                                   "border": "1px solid black", "color": "#003366"})
                ]),
                html.Tr([
                    html.Td("Minutos de actividad física moderada-vigorosa por día",
                            style={"text-align": "center", "border": "1px solid black", "padding": "5px", "lineHeight": "1.4", "font-size": "18px", "font-family": "Verdana, sans-serif"}),
                    html.Td("< 4 horas de sedentarismo", style={"background-color": "#D9D9D9", "text-align": "center",
                                                                "border": "1px solid black", "padding": "5px", "width": "20%", "lineHeight": "1.4", "font-size": "18px", "font-family": "Verdana, sans-serif"}),
                    html.Td("4-6 horas de sedentarismo", style={"background-color": "#D9D9D9", "text-align": "center",
                                                                "border": "1px solid black", "padding": "5px", "width": "20%", "lineHeight": "1.4", "font-size": "18px", "font-family": "Verdana, sans-serif"}),
                    html.Td("6-8 horas de sedentarismo", style={"background-color": "#D9D9D9", "text-align": "center",
                                                                "border": "1px solid black", "padding": "5px", "width": "20%", "lineHeight": "1.4", "font-size": "18px", "font-family": "Verdana, sans-serif"}),
                    html.Td("> 8 horas de sedentarismo", style={"background-color": "#D9D9D9", "text-align": "center",
                                                                "border": "1px solid black", "padding": "5px", "width": "20%", "lineHeight": "1.4", "font-size": "18px", "font-family": "Verdana, sans-serif"})
                ], style={"border": "1px solid black", "height": "65px"}),
                html.Tr([
                    html.Td("Más de 60 minutos", style={"border": "1px solid black", "text-align": "center", "padding": "5px",
                                                        "font-weight": "bold", "lineHeight": "1.4", "font-size": "18px", "font-family": "Verdana, sans-serif"}),
                    html.Td(marcar_celda("Bajo", actual_minutes_physical, max_minutes_physical, float("inf"), 0, min_hours_sedentary), style={"background-color": "#90EE90", "border": "1px solid black",
                                           "text-align": "center", "padding": "5px", "lineHeight": "1.4", "font-size": "18px", "font-family": "Verdana, sans-serif"}),
                    html.Td(marcar_celda("Bajo", actual_minutes_physical, max_minutes_physical, float("inf"), min_hours_sedentary, mid_hours_sedentary), style={"background-color": "#90EE90", "border": "1px solid black",
                                           "text-align": "center", "padding": "5px", "lineHeight": "1.4", "font-size": "18px", "font-family": "Verdana, sans-serif"}),
                    html.Td(marcar_celda("Bajo", actual_minutes_physical, max_minutes_physical, float("inf"), mid_hours_sedentary, max_hours_sedentary), style={"background-color": "#90EE90", "border": "1px solid black",
                                           "text-align": "center", "padding": "5px", "lineHeight": "1.4", "font-size": "18px", "font-family": "Verdana, sans-serif"}),
                    html.Td(marcar_celda("Bajo", actual_minutes_physical, max_minutes_physical, float("inf"), max_hours_sedentary, float("inf")), style={"background-color": "#90EE90", "border": "1px solid black",
                                           "text-align": "center", "padding": "5px", "lineHeight": "1.4", "font-size": "18px", "font-family": "Verdana, sans-serif"})
                ], style={"border": "1px solid black", "height": "64px"}),
                html.Tr([
                    html.Td("30-60 minutos", style={"border": "1px solid black", "text-align": "center", "padding": "5px",
                                                    "font-weight": "bold", "lineHeight": "1.4", "font-size": "18px", "font-family": "Verdana, sans-serif"}),
                    html.Td(marcar_celda("Bajo", actual_minutes_physical, mid_minutes_physical, max_minutes_physical, 0, min_hours_sedentary), style={"background-color": "#90EE90", "border": "1px solid black",
                                           "text-align": "center", "padding": "5px", "lineHeight": "1.4", "font-size": "18px", "font-family": "Verdana, sans-serif"}),
                    html.Td(marcar_celda("Bajo - moderado", actual_minutes_physical, mid_minutes_physical, max_minutes_physical, min_hours_sedentary, mid_hours_sedentary), style={"background-color": "#FFFF99", "border": "1px solid black",
                                                    "text-align": "center", "padding": "5px", "lineHeight": "1.4", "font-size": "18px", "font-family": "Verdana, sans-serif"}),
                    html.Td(marcar_celda("Bajo - moderado", actual_minutes_physical, mid_minutes_physical, max_minutes_physical, mid_hours_sedentary, max_hours_sedentary), style={"background-color": "#FFFF99", "border": "1px solid black",
                                                    "text-align": "center", "padding": "5px", "lineHeight": "1.4", "font-size": "18px", "font-family": "Verdana, sans-serif"}),
                    html.Td(marcar_celda("Bajo - moderado", actual_minutes_physical, mid_minutes_physical, max_minutes_physical, max_hours_sedentary, float("inf")), style={"background-color": "#FFFF99", "border": "1px solid black",
                                                    "text-align": "center", "padding": "5px", "lineHeight": "1.4", "font-size": "18px", "font-family": "Verdana, sans-serif"})
                ], style={"border": "1px solid black", "height": "64px"}),
                html.Tr([
                    html.Td("5-29 minutos", style={"border": "1px solid black", "text-align": "center", "padding": "5px",
                                                   "font-weight": "bold", "lineHeight": "1.4", "font-size": "18px", "font-family": "Verdana, sans-serif"}),
                    html.Td(marcar_celda("Bajo - moderado", actual_minutes_physical, min_minutes_physical, mid_minutes_physical, 0, min_hours_sedentary), style={"background-color": "#FFFF99", "border": "1px solid black",
                                                    "text-align": "center", "padding": "5px", "lineHeight": "1.4", "font-size": "18px", "font-family": "Verdana, sans-serif"}),
                    html.Td(marcar_celda("Moderado", actual_minutes_physical, min_minutes_physical, mid_minutes_physical, min_hours_sedentary, mid_hours_sedentary), style={"background-color": "#FFA500", "border": "1px solid black",
                                               "text-align": "center", "padding": "5px", "lineHeight": "1.4", "font-size": "18px", "font-family": "Verdana, sans-serif"}),
                    html.Td(marcar_celda("Moderado", actual_minutes_physical, min_minutes_physical, mid_minutes_physical, mid_hours_sedentary, max_hours_sedentary), style={"background-color": "#FFA500", "border": "1px solid black",
                                               "text-align": "center", "padding": "5px", "lineHeight": "1.4", "font-size": "18px", "font-family": "Verdana, sans-serif"}),
                    html.Td(marcar_celda("Moderado", actual_minutes_physical, min_minutes_physical, mid_minutes_physical, max_hours_sedentary, float("inf")), style={"background-color": "#FFA500", "border": "1px solid black",
                                               "text-align": "center", "padding": "5px", "lineHeight": "1.4", "font-size": "18px", "font-family": "Verdana, sans-serif"})
                ], style={"border": "1px solid black", "height": "64px"}),
                html.Tr([
                    html.Td("Menos de 5 minutos", style={"border": "1px solid black", "text-align": "center", "padding": "5px",
                                                         "font-weight": "bold", "lineHeight": "1.4", "font-size": "18px", "font-family": "Verdana, sans-serif"}),
                    html.Td(marcar_celda("Moderado", actual_minutes_physical, 0, min_minutes_physical, 0, min_hours_sedentary), style={"background-color": "#FFA500", "border": "1px solid black",
                                               "text-align": "center", "padding": "5px", "lineHeight": "1.4", "font-size": "18px", "font-family": "Verdana, sans-serif"}),
                    html.Td(marcar_celda("Moderado - alto", actual_minutes_physical, 0, min_minutes_physical, min_hours_sedentary, mid_hours_sedentary), style={"background-color": "#FF0000", "border": "1px solid black",
                                                      "text-align": "center", "padding": "5px", "color": "white", "lineHeight": "1.4", "font-size": "18px", "font-family": "Verdana, sans-serif"}),
                    html.Td(marcar_celda("Moderado - alto", actual_minutes_physical, 0, min_minutes_physical, mid_hours_sedentary, max_hours_sedentary), style={"background-color": "#FF0000", "border": "1px solid black",
                                                      "text-align": "center", "padding": "5px", "color": "white", "lineHeight": "1.4", "font-size": "18px", "font-family": "Verdana, sans-serif"}),
                    html.Td(marcar_celda("Alto", actual_minutes_physical, 0, min_minutes_physical, max_hours_sedentary, float("inf")), style={"background-color": "#FF0000", "border": "1px solid black",
                                           "text-align": "center", "padding": "5px", "color": "white", "lineHeight": "1.4", "font-size": "18px", "font-family": "Verdana, sans-serif"})
                ], style={"border": "1px solid black", "height": "64px"}),
                html.Tr([
                    html.Td([
                        html.Span(
                            html.B("Esta tabla muestra su nivel de riesgo cardiovascular en función de la combinación de sus hábitos de actividad física moderada-vigorosa y sedentarismo."))
                    ], colSpan=5,
                        style={"text-align": "left", "lineHeight": "1.4", "font-size": "18px", "font-family": "Verdana, sans-serif", "padding": "10px",
                               "border-left": "1px solid black", "border-right": "1px solid black",
                               "border-bottom": "1px solid black"})
                ]),
                html.Tr([
                    html.Td("", colSpan=2, style={"page-break-before": "always", "border": "none", "padding": "0px"})
                ]),
                html.Tr([
                    html.Th("RECOMENDACIÓN PERSONALIZADA SOBRE EL RIESGO COMBINADO",
                            colSpan=5, className="table-titles",
                            style={"background-color": "#81c784", "text-align": "center",
                                   "font-size": "20px", "font-weight": "bold", "padding": "10px",
                                   "border-left": "1px solid black", "border-right": "1px solid black", "border-bottom": "1px solid black", "color": "#003366"})
                ]),
                html.Tr([
                    html.Td(title_comb_message,
                            colSpan=5,
                            style={"background-color": background_color,  # Rojo fuerte
                                   "color": text_color,  # Texto en blanco para mejor contraste
                                   "text-align": "center",
                                   "font-size": "20px",
                                   "font-weight": "bold",
                                   "padding": "10px",
                                   "border-left": "1px solid black",
                                   "border-right": "1px solid black",
                                   "border-bottom": "1px solid black"
                                                    "border-collapse-collapse", })
                ]),
                html.Tr([
                    html.Td([
                        html.Span([combination_message],
                                  style={"margin-left": "10px", "margin-right": "10px", "margin-bottom": "-2px", "margin-top": "-2px",
                                         "display": "block", "lineHeight": "1.4", "font-size": "18px", "font-family": "Verdana, sans-serif"})
                    ], colSpan=5)
                ], style={"border": "1px solid black"}),
            ])
        ], style={"width": "102%", "border": "1px solid black", "border-collapse": "collapse", "margin-bottom": "0px", "margin-top": "0px"})
    ], style={"padding": "5px", "margin-bottom": "-2px", "margin-top": "-2px"})

def _as_list(x):
    return [] if x is None else list(x)

def _align_lengths(*seqs):
    seqs = [_as_list(s) for s in seqs]
    m = min(len(s) for s in seqs if isinstance(s, list) and len(s) > 0)
    return [s[:m] for s in seqs]

def _infer_days_from_dates(dates, target_len=None):
    """
    A partir de la lista de 'dates' (YYYY-MM-DD) genera una secuencia contigua
    de días de la semana en inglés (Monday..Sunday). Si 'target_len' se indica,
    se ajusta la longitud al objetivo:
        - Si hay más días de los necesarios, recorta por la izquierda (conserva los más recientes).
        - Si hay menos, rellena hacia delante.
    """
    if not dates or not isinstance(dates, list):
        return None

    try:
        d0 = datetime.strptime(dates[0], "%Y-%m-%d")
        dN = datetime.strptime(dates[-1], "%Y-%m-%d")
    except Exception:
        return None

    n = (dN - d0).days + 1
    full_dates = [(d0 + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(n)]
    days = [datetime.strptime(d, "%Y-%m-%d").strftime("%A") for d in full_dates]

    if target_len is not None:
        if len(days) > target_len:
            # Conserva los más recientes
            days = days[:target_len]
        elif len(days) < target_len:
            # Rellena hacia delante
            last_date = datetime.strptime(full_dates[-1], "%Y-%m-%d")
            extra = target_len - len(days)
            days += [(last_date + timedelta(days=i+1)).strftime("%A") for i in range(extra)]

    return days

def get_sleep_habits(datos, datos_move):
    patient_age = datos.get('edad')

    total_sueno = find_value(datos_move, 'sleep_day')
    waso = find_value(datos_move, 'waso_day')
    eficiencia = find_value(datos_move, 'eff_day')
    days_analysed = find_value(datos_move, 'days_analysed')
    dates = find_value(datos_move, 'dates')

    days_from_dates = _infer_days_from_dates(dates, target_len=len(total_sueno) if total_sueno else None)

    if days_from_dates:
        days_analysed = days_from_dates

    # Alinea longitudes (soporta 4, 5, 6… noches)
    days_analysed, total_sueno, waso, eficiencia = _align_lengths(
        days_analysed, total_sueno, waso, eficiencia
    )

    # Build DataFrame and transform to number (the 'NA' and None are now NaN)
    df = pd.DataFrame({
        'day': days_analysed,
        'total_sleep': total_sueno,
        'waso': waso,
        'eficiencia': eficiencia,
    })
    df['total_sleep'] = pd.to_numeric(df['total_sleep'], errors='coerce')
    df['waso'] = pd.to_numeric(df['waso'], errors='coerce')
    df['eficiencia'] = pd.to_numeric(df['eficiencia'], errors='coerce')

    # Reorder from Monday to Sunday
    day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    dias_es = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    df['day'] = pd.Categorical(df['day'], categories=day_order, ordered=True)

    # Group per day and calculate the mean, ignoring NaN
    df_grouped = df.groupby('day', as_index=True, observed=False).mean(numeric_only=True)
    df_grouped = df_grouped.reindex(day_order)

    # Extract final lists
    total_sorted = df_grouped['total_sleep'].tolist()
    waso_sorted = df_grouped['waso'].tolist()
    eficiencia_sorted = df_grouped['eficiencia'].tolist()

    total_sorted.append(_to_float(find_value(datos_move, 'sleep_week_avg')))
    waso_sorted.append(_to_float(find_value(datos_move, 'waso_week_avg')))
    eficiencia_sorted.append(_to_float(find_value(datos_move, 'eff_week_avg')))

    dias_local = dias_es + ["Promedio diario"]

    df_sueno = pd.DataFrame({
        'Día': dias_local,
        'Sueño sin interrupción': total_sorted,
        'Interrupciones del sueño': waso_sorted,
        'Eficiencia': eficiencia_sorted
    })

    for c in ['Sueño sin interrupción', 'Interrupciones del sueño', 'Eficiencia']:
        df_sueno[c] = pd.to_numeric(df_sueno[c], errors='coerce')
    df_sueno['Día'] = pd.Categorical(df_sueno['Día'], categories=dias_local, ordered=True)

    sleep_avg = total_sorted[-1] if len(total_sorted) else np.nan
    sleep_hours = float(sleep_avg) if sleep_avg is not None else np.nan
    actual_sleep_hours = sleep_hours if np.isfinite(sleep_hours) else 0.0
    min_sleep_hours = 7
    max_sleep_hours = 8 if patient_age >= 65 else 9

    bar_sleep = px.bar(df_sueno, x='Día', y=["Sueño sin interrupción", "Interrupciones del sueño"],
                     labels={"value": "Duración del sueño (h)", "variable": "Tipo de sueño", "Día": "Día de la semana y promedio diario"},
                     title="Duración del sueño diario",
                     color_discrete_map={
                         "Sueño sin interrupción": "#81c784", # 76c7c0 - turquesa
                         "Interrupciones del sueño": "#FF4500" #a569bd - morado
                     },
                     text_auto=False,
                     category_orders={'Día': dias_local}
                     )
    bar_sleep.add_hrect(y0=0, y1=7, fillcolor="red", opacity=0.3, layer="below", line_width=0)
    bar_sleep.add_hrect(y0=min_sleep_hours, y1=max_sleep_hours, fillcolor="lightgreen", opacity=0.3, layer="below", line_width=0)
    bar_sleep.add_hrect(y0=max_sleep_hours, y1=12, fillcolor="red", opacity=0.3, layer="below", line_width=0)

    bar_sleep.add_hline(y=min_sleep_hours, line_dash="dash", line_color="red")
    bar_sleep.add_hline(y=max_sleep_hours, line_dash="dash", line_color="green")

    bar_sleep.add_trace(go.Scatter(
        x=[None], y=[None],
        mode='lines',
        line=dict(color="red", dash="dash"),
        name="Mín. recomendada (7h)"
    ))

    bar_sleep.add_trace(go.Scatter(
        x=[None], y=[None],
        mode='lines',
        line=dict(color="green", dash="dash"),
        name=f"Máx. recomendada ({max_sleep_hours}h)"
    ))

    for dia, eff in zip(df_sueno['Día'], df_sueno['Eficiencia']):
        if pd.isna(eff):
            texto = "<b>---</b>"
        else:
            texto = f"<b>{float(eff):.0f}%</b>"

        bar_sleep.add_annotation(
            x=dia,
            y=0,
            text=texto,
            showarrow=False,
            yshift=-10,
            font=dict(size=12, color="black"),
            xanchor="center"
        )

    bar_sleep.add_annotation(
        x=1.01,  # un poco fuera del área de trazado
        y=-0.4,  # alineado a la línea y=0 del eje Y
        xref="paper",  # coordenada X relativa al lienzo
        yref="y",  # coordenada Y en unidades de datos
        text="<b>Eficiencia</b>",
        showarrow=False,
        font=dict(size=12, color="black"),
        xanchor="left",  # ancla el texto por la izquierda
        yanchor="middle"  # centrar verticalmente sobre y=0
    )

    bar_sleep.update_yaxes(
        tickvals=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12],
        ticktext=[f"{v}" for v in [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]],
        title_text="Tiempo (horas)"
    )

    bar_sleep.update_traces(
        width=0.65,
        selector={'type': 'bar'}
    )
    bar_sleep.update_layout(
        barmode='stack',
        bargap=0.2,
        bargroupgap=0.1,
        title_font_size=20,
        title_x=0.5,
        margin=dict(l=10, r=10, t=40, b=10),
        height=300,
        legend=dict(
            title='Tipo de sueño',
            orientation="v",
            x=1.02,
            y=1,
            font=dict(size=14),
            bgcolor="rgba(0,0,0,0)",
            borderwidth=0)
    )

    # Textos por serie (en el mismo orden que las columnas del px.bar)
    txt_sin = [_fmt_hm(v) for v in df_sueno["Sueño sin interrupción"]]
    txt_waso = [_fmt_hm(v) for v in df_sueno["Interrupciones del sueño"]]

    # Asignar texto a cada traza del bar apilado
    bar_sleep.data[0].text = txt_sin  # Sueño sin interrupción
    bar_sleep.data[1].text = txt_waso  # Interrupciones del sueño

    bar_sleep.update_traces(
        texttemplate="%{text}",
        textposition="auto",  # intenta dentro; si no cabe lo saca fuera
        insidetextanchor="middle",  # ancla el texto al centro vertical del segmento
        insidetextfont=dict(size=14, color="black"),
        outsidetextfont=dict(size=14, color="black"),
        selector={'type': 'bar'})
    graph_sleep = dcc.Graph(figure=bar_sleep,
                          style={"width": "100%", "height": "400px"})

    sleep_commentaries = html.Div(
        html.Ul(
            [
                html.Li("Evite realizar ejercicio físico intenso a últimas horas de la tarde-noche."),
                html.Li("Establezca una rutina relajante a la hora de acostarse."),
                html.Li("Utilice su cama sólo para dormir y tener sexo."),
                html.Li(f"Haga que su dormitorio sea tranquilo y relajante. "),
                html.Li(f"Mantén la habitación a una temperatura agradable y fresca."),
                html.Li(f"Limite la exposición a la luz brillante durante las noches."),
                html.Li(f"Apague los dispositivos electrónicos al menos 30 minutos antes de acostarse."),
                html.Li(f"No coma copiosamente antes de acostarse."),
                html.Li(f"Si tiene hambre por la noche, coma un refrigerio ligero y saludable."),
                html.Li(f"Evite consumir cafeína por la tarde o por la noche."),
                html.Li(f"Evite consumir alcohol antes de acostarse."),
                html.Li(f"Reduzca la ingesta de líquidos antes de acostarse."),
                html.Li(f"Mantenga un horario de sueño constante."),
                html.Li(f"Levántese a la misma hora todos los días, incluso los fines de semana o durante las vacaciones."),
                html.Li(f"Establezca una hora de acostarse que sea lo suficientemente temprana para poder dormir al menos entre {min_sleep_hours} y {max_sleep_hours} horas."),
                html.Li("No se vaya a la cama a menos que tenga sueño."),
                html.Li("Si no se duerme después de 20 minutos, salga de la cama y realice una actividad tranquila sin mucha exposición a la luz."),
                html.Li("Es especialmente importante no usar aparatos electrónicos."),
            ],
            style={
                "lineHeight": "1.5",  # 1.5 veces la altura de la fuente → más espacio
                "paddingLeft": "1.2rem",  # margen a la izquierda para las viñetas
                "listStyleType": "disc",  # tipo de viñeta (disc, circle, square…)
                "fontStyle": "italic",
            }
        )
    )

    if min_sleep_hours <= actual_sleep_hours <= max_sleep_hours:
        sleep_message = html.Div([
            html.P([
                f"Se le aconseja continuar con su rutina de sueño  actual manteniendo su duración y promoviendo"
                f" una higiene del sueño adecuada, considerando los consejos indicados a continuación:",
                html.Br(),

                sleep_commentaries
            ], style={"white-space": "pre-line"})  # Permite que los saltos de línea funcionen correctamente
        ])
    elif actual_sleep_hours < min_sleep_hours:
        sleep_message = html.Div([
            html.P([
                f"Intente aumentar la duración del sueño hasta el rango recomendado para mantener una buena salud"
                f" ({min_sleep_hours}-{max_sleep_hours} horas). Si considera que la falta de horas de sueño está"
                f" afectando a su salud consúltelo con su médico. Se recomienda tener una higiene del sueño"
                f" adecuada, considerando los consejos indicados a continuación:",
                html.Br(),

                sleep_commentaries
            ], style={"white-space": "pre-line"})  # Permite que los saltos de línea funcionen correctamente
        ])
    else:
        sleep_message = html.Div([
            html.P([
                f"Intente reducir la duración del sueño hasta el rango recomendado ({min_sleep_hours}-{max_sleep_hours} horas), dado que hay"
                f" evidencia cientifica que indica que un exceso de horas de sueño puede afectar negativamente a la"
                f" salud. Si considera que en su caso el exceso de horas sueño esta afectando a su salud consulte"
                f" con su médico al respecto. Se recomienda tener una higiene del sueño adecuada, considerando los"
                f" consejos indicados a continuación:",
                html.Br(),

                sleep_commentaries
            ], style={"white-space": "pre-line"})  # Permite que los saltos de línea funcionen correctamente
        ])

    return html.Div([
        html.Table([
            html.Tbody([
                html.Tr([
                    html.Th("HÁBITOS DIARIOS DE SUEÑO",
                            colSpan=5, className="table-titles",
                            style={"background-color": "#81c784", "text-align": "center",
                                   "font-size": "20px", "font-weight": "bold", "padding": "10px",
                                   "border": "1px solid black", "color": "#003366"})
                ]),
                html.Tr([
                    html.Td(
                        dcc.Graph(figure=bar_sleep, style={"width": "100%", "height": "100%"}),
                        colSpan=2,
                        style={
                            "width": "100%",
                            "height": "100%",  # <-- que la celda sea 100% de su contenedor
                            "padding": "10px",
                            "border": "1px solid black",
                            "border-bottom": "none",
                            "boxSizing": "border-box"  # para que padding y border no desborde
                        }
                    )
                ]),
                html.Tr([
                    html.Td([
                            "Este gráfico muestra su tiempo de sueño y su tiempo de sueño efectivo (sin interrupciones)."
                            " La cifra debajo de las barras representa su eficiencia de sueño (%). La eficiencia del sueño es"
                            " un indicador cuantitativo de la calidad del sueño. Se refiere al porcentaje de tiempo que una persona pasa "
                            "dormida en relación con el tiempo total que permanece en la cama, intentando dormir."
                    ], colSpan=2,
                        style={"text-align": "left", "lineHeight": "1.4", "font-size": "18px", "font-family": "Verdana, sans-serif", "padding": "10px",
                               "border-left": "1px solid black", "border-right": "1px solid black", "margin-bottom": "-2px", "margin-top": "-2px",
                               "border-bottom": "1px solid black"})
                ]),
            ])
        ], style={"width": "102%", "border": "1px solid black", "border-collapse": "collapse", "margin-bottom": "-2px", "margin-top": "-2px"}),
        html.Table([
            html.Tbody([
                html.Tr([
                    html.Th("RECOMENDACIÓN PERSONALIZADA SOBRE EL SUEÑO",
                            colSpan=5, className="table-titles",
                            style={"background-color": "#81c784", "text-align": "center",
                                   "font-size": "20px", "font-weight": "bold", "padding": "10px",
                                   "border-left": "1px solid black", "border-right": "1px solid black",
                                   "border-bottom": "1px solid black", "color": "#003366"})
                ]),
                html.Tr([
                    html.Td([
                        html.Span([sleep_message],
                                  style={"margin-left": "10px", "margin-right": "10px", "margin-bottom": "-2px", "margin-top": "-2px",
                                         "display": "block", "lineHeight": "1.4", "font-size": "18px", "font-family": "Verdana, sans-serif"}),
                    ])
                ])
            ])
        ], style={"width": "102%", "border": "1px solid black", "border-collapse": "collapse", "margin-bottom": "0px"})
    ], style={"padding": "5px", "margin-bottom": "0px"})

def layout(patient_id=None, fecha=None, render_mode="web", **kwargs):
    global dataPath

    if patient_id is None:
        return html.Div("No se proporcionó ID de paciente")

    formattedDate = fecha.replace('-', '.')  # Dar formato correcto a la fecha para que corresponda con la carpeta
    dataPath = directorio / "Datos_pacientes" / patient_id / f"{patient_id}_{formattedDate}"
    datos_paciente, datos_movimiento = cargar_datos_json(patient_id, fecha)  # Cargar datos desde el JSON

    print(f"Paciente: {patient_id}, Fecha: {fecha}")

    if not (dataPath / "05_rep" / "create_report.json").exists():
        create_path(5, patient_id, f"{patient_id}_{formattedDate}")

    status_file = dataPath / "05_rep" / "create_report.json"
    try:
        if status_file.exists():
            data = json.loads(status_file.read_text())
        else:
            data = {"name": "create_report"}
            # Modificar campos
        data["status"] = "SUCCESS"
        data["timestamp"] = time.time()
        # Sobrescribir fichero
        status_file.write_text(json.dumps(data))
    except Exception as e:
        # Si algo falla al leer/escribir el JSON, podemos imprimir o manejar el error
        print(f"Error al forzar estado SUCCESS en create_report.json: {e}")

    return html.Div([
        dcc.Location(id="url", refresh=False),  # Agregado para obtener la URL
        dcc.Interval(id="generate-pdf-timer", interval=3000, n_intervals=0, max_intervals=1),
        # Lanza el callback tras 5s
        html.Div(id="pdf-status"),  # Aquí se mostrará el estado del PDF
        html.Button('Descargar Informe (PDF)', id='download-pdf-btn', className="no-print", style={"margin-bottom": "10px"}),
        dcc.Download(id="download-pdf"),
        html.A(
            html.Button(
                'Imprimir Informe (PDF)',
                id="print-pdf-btn",
                className="no-print",
                style={"margin-left": "10px", "margin-bottom": "10px"}
            ),
            href=f'/report-print/{patient_id}/{fecha}',
            target='_blank',  # abre en pestaña nueva donde se ejecuta window.print()
        ),
        html.H1("Informe de Evaluación Personalizada de Actividad Física", style=title_style),
        get_datos_paciente(datos_paciente),
        get_datos_evaluacion(datos_movimiento),
        html.Hr(style={"border": "2px solid #228B22", "margin-top": "0px", "opacity": "1" }),
        html.H3("INFORME DE ESTILO DE VIDA", style={"color": "#003366", "font-weight": "bold", "font-size": "20px", "padding-left": "16px", "margin-bottom": "10px", "margin-top": "10px"}),
        get_habitos_actividad_fisica(datos_paciente, datos_movimiento),
        get_recomendaciones_fisicas(datos_paciente, datos_movimiento),
        get_comportamiento_sedentario(datos_movimiento),
        riesgo_comb_act_fisica_sedentarismo(datos_movimiento),
        get_sleep_habits(datos_paciente, datos_movimiento),
    ])

def generate_pdf(patient_id, patient_date):
    """
    Convierte una URL en un PDF usando Selenium y Chrome DevTools Protocol.
    Usa base64 en lugar de fromhex() para evitar errores de conversión.
    """
    url = f"http://127.0.0.1:8050/report/{patient_id}/{patient_date}?pdf=1"

    formatted_date = patient_date.replace('-', '.')
    output_pdf = os.path.join(dataPath, "05_rep", f"report_{patient_id}_{formatted_date}.pdf")

    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--remote-debugging-port=9222")
    driver_dir = os.path.dirname(ChromeDriverManager().install())
    # busca el .exe dentro de esa carpeta
    exe_path = glob.glob(os.path.join(driver_dir, '*.exe'))[0]
    service = Service(exe_path)
    driver = webdriver.Chrome(service=service, options=chrome_options)

    try:
        print(f"🌐 Abriendo {url}...")
        driver.set_window_size(1175, 100)
        driver.get(url)

        # Esperar hasta que los gráficos de Plotly estén cargados completamente
        wait = WebDriverWait(driver, 30)
        wait.until(EC.presence_of_element_located((By.CLASS_NAME, "js-plotly-plot")))

        print(f"📄 Generando PDF en {output_pdf}...")

        # Obtener el PDF en base64 en vez de hexadecimal
        pdf = driver.execute_cdp_cmd("Page.printToPDF",
    {
                "format": "A4",
                "scale": 0.88,               # 80% del tamaño original
                "printBackground": False,    # incluye fondos y colores
                "marginTop": 0.4,           # en pulgadas
                "marginBottom": 0.2,
                "marginLeft": 0.4,
                "marginRight": 0.4
            })

        if not pdf or "data" not in pdf:
            raise ValueError("Chrome DevTools no devolvió datos válidos para el PDF.")

        # Convertir de base64 a bytes y guardar el PDF
        pdf_data = base64.b64decode(pdf['data'])
        with open(output_pdf, "wb") as f:
            f.write(pdf_data)

        print(f"✅ PDF guardado en: {output_pdf}")
        return output_pdf

    except Exception as e:
        print(f"❌ Error al generar PDF: {e}")

    finally:
        driver.quit()

def add_page_numbers(pdf_path):
    """
    Agrega números de página a un PDF existente.
    """
    doc = pymupdf.open(pdf_path)
    total_pages = len(doc)

    for i, page in enumerate(doc):
        page_number = f"Página {i + 1} de {total_pages}"
        text_rect = pymupdf.Rect(50, page.rect.height - 30, page.rect.width - 50,
                              page.rect.height - 10)  # Posición del número de página
        page.insert_textbox(text_rect, page_number, fontsize=10, color=(0, 0, 0), align=2)  # Centrado

    temp_pdf_path = pdf_path.replace(".pdf", "_temp.pdf")  # Ruta temporal

    doc.save(temp_pdf_path)
    doc.close()

    os.remove(pdf_path)
    os.rename(temp_pdf_path, pdf_path)
    print(f"✅ PDF con números de página guardado en: {pdf_path}")
    print("✅ Proceso completado.")
    return pdf_path

@callback(
    Output("pdf-status", "children"),
    Input("generate-pdf-timer", "n_intervals"),
    State("url", "pathname"),
    State("url", "search"),
    prevent_initial_call=True  # No se ejecuta hasta que pase el tiempo del Interval
)
def generate_pdf_on_load(n_intervals, pathname, search):
    if not pathname:
        return "Error: No se pudo obtener la ruta del informe."

    if search and "pdf=1" in search:
        return dash.no_update

    patient_id = pathname.split('/')[-2]
    patient_date = pathname.split('/')[-1]

    pdf_path = generate_pdf(patient_id, patient_date)

    if pdf_path and os.path.exists(pdf_path):
        add_page_numbers(pdf_path)

        if getattr(settings, "purge_after_pdf", False):
            try:
                purge_patient_data(dataPath)
                print("Purga de datos completada tras generar PDF.")
            except Exception as e:
                print(f"Error purgando datos: {e}")

    return dash.no_update

@callback(
    Output("download-pdf", "data"),
    Input("download-pdf-btn", "n_clicks"),
    State("_pages_location", "pathname"),
    prevent_initial_call=True
)
def download_pdf(n_clicks, pathname):
    if not pathname:
        return dash.no_update

    patient_id = pathname.split('/')[-2]
    patient_date = pathname.split('/')[-1]
    formatted_date = patient_date.replace('-', '.')

    # Generar el PDF con Selenium + Chrome
    pdf_path = generate_pdf(patient_id, patient_date)

    if pdf_path and os.path.exists(pdf_path):
        pdf_with_pages = add_page_numbers(pdf_path)

        if getattr(settings, "purge_after_pdf", False):
            try:
                purge_patient_data(dataPath)
                print("Purga de datos completada tras generar PDF.")
            except Exception as e:
                print(f"Error purgando datos: {e}")

        with open(pdf_with_pages, "rb") as f:
            pdf_content = f.read()
        return dcc.send_bytes(pdf_content, filename=f"report_{patient_id}_{formatted_date}.pdf")

    return dash.no_update  # No hacer nada si hay error

