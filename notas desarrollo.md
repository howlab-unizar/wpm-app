## Estructura de archivos

- **assets/**: Contiene archivos JavaScript personalizados para Dash AG Grid.
  - `style.css` : Define la apariencia de los componentes.
  - `dashAgGridComponentFunctions.js`: Define los renderizadores de celdas personalizados.
- **pages/**: Contiene las páginas de la aplicación Dash.
  - `inicio.py`: Página para mostrar datos no procesados.
  - `processed.py`: Página para mostrar datos procesados.
  - `report.py`: Página para generar y mostrar informes de pacientes.
  - `pacientes.py` : Página con el formulario de datos de los distintos pacientes.
- **utils/**: Contiene funciones auxiliares y de procesamiento.
  - `retrievedata.py`: Funciones para recuperar datos.
  - `pre_process.py`: Funciones para el procesamiento previo de los datos.
  - `process.py`: Funciones encargadas de las distintas fases de procesamiento de datos.
  - `Gestionador.py`: Funciones de procesados de bioseñales.
  - `csvprocess.py`: Funciones de segmentado de archivos .csv.
  - `bin2csv.py` : Funciones para el parse de .BIN a .csv.
  - `analisis_movimiento.R` : Script de prodesado de señales de movimiento.
- **app.py**: Archivo principal de la aplicación Dash.
- **requirements.txt**: Lista de dependencias del proyecto.
- **README.md**: Archivo de documentación del proyecto.

### Notas
- Se recomendó instalar numpy versión 1.26.4 debido a un error de importación con pandas ==> revisar dependencias (pasar requirements a poetry).