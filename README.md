# App de Monitorización

## Tabla de Contenidos

- [Instalación](#instalación)
- [Uso](#uso)
- [Estructura de Archivos](#estructura-de-archivos)

## Instalación

### Requisitos Previos

- **Python 3.7 o superior**: Asegúrate de tener Python instalado. Si no lo tienes, puedes descargarlo desde [python.org](https://www.python.org/downloads/).
  - Asegúrate de agregar Python al PATH durante la instalación.
  - **Nota**: La versión actual de Python (>=3.13) no es compatible con la versión seleccionada de numpy, por lo que se recomienda usar versiones entre 3.10 y 3.12.
- **pip**: Asegúrate de tener `pip` instalado, ya que es necesario para instalar las dependencias de Python.
- **R 4.3.3 o superior**: Puedes descargarlo desde [CRAN](https://cran.r-project.org/). Asegúrate de seleccionar la versión para Windows.

### Instalación de Python
1. Descarga Python desde [python.org](https://www.python.org/downloads/).
2. Durante la instalación, marca la opción de **Add to PATH** para agregar Python al PATH automáticamente.
3. Verifica que Python se haya instalado correctamente ejecutando (escribir en una terminal de comandos - CMD):
    ```bash
    python --version
    pip --version
    ```
*Nota*: Para abrir una terminal de comandos, escribir en el buscador del sistema (buscador del PC): CMD y lanzarlo. También puede llamarse *Símbolo del sistema*.

### Instalación de R
1. **Descargar R**: Accede a la web oficial de R [CRAN](https://cran.r-project.org/).

2. **Seleccionar la versión de R**:
   - Haz clic en **Download R for Windows** en la página principal.
   - Haz clic en el enlace **'base'**.
   - Accede a las versiones previas en el enlace de **Previous releases**.
   - Descarga la versión de R para Windows (recomendado: R 4.3.3 o superior).
3. **Instalación de R**:
   - Abre el archivo descargado y sigue las instrucciones de instalación por defecto. Es recomendable instalar R en el directorio predeterminado (por ejemplo, 'C:\Program Files\R\R-4.x.x').
4. **Configurar R en la Variable de Entorno PATH**:
   - Ve a **Configuración avanzada del sistema**:
     - Haz clic derecho en **Este equipo / Mi PC** en el explorador de archivos y selecciona **Propiedades**.
     - Selecciona **Configuración avanzada del sistema** en el menú lateral.
     - Haz clic en el botón **Variables de entorno**.
   - En la sección de **Variables del sistema**, busca la variable 'Path' y haz clic en **Editar**.
   - Haz clic en **Nuevo** y agrega la ruta al directorio 'bin' dentro de la instalación de R, por ejemplo:
     ```
     C:\Program Files\R\R-4.x.x\bin
     ```
     #### *Nota*: No escribir esta misma dirección de ejemplo, se recomienda encarecidamente buscar la localización de la ruta de instalación de R (parecida a la del ejemplo) y copiar la ruta 'bin' propia.
   - Guarda los cambios y cierra todas las ventanas.

5. **Verificar la instalación de R**:
   - Abre una terminal de comandos (CMD) y ejecuta:
     ```bash
     R --version
     ```
   - Se debe observar la versión instalada de R si todo ha sido configurado correctamente.

### Instalar librerías de R
Se necesita la instalación de los paquetes "data.table" y "GGIR".
1. Abre una terminal de comandos (CMD) y ejecuta:
    ```bash
    r
    ```
2. Con el terminal de R abierto instala los paquetes ejecutando los siguientes comandos:
    ```bash
    install.packages("data.table")
    install.packages("GGIR")
    install.packages("GGIRread")
    ```
Una vez instalados ambos paquetes, pueden ser utilizados. En el caso de necesitar una versión diferente del GGIR se
puede seguir el siguiente procedimiento (**Nota**: Instalar la versión actual de GGIR (paso anterior) previamente para una insalación correcta de la versión previa deseada):
1. En la terminal de R elimina la librería GGIR para evitar problemas en la instalación:
    ```bash
    remove.packages("GGIR")
    ```
2. Instala el paquete remotes y usalo para instalar una versión específica:
    ```bash
    install.packages("remotes")
    remotes::install_version("GGIR", version = "3.1-0")
    ```
3. Verifica que se haya instalado correctamente la versión específica ejecutando:
    ```bash
    library("GGIR")
    packageVersion("GGIR")
    ```
   
### Instalación de Git
***Nota**: Este paso no es necesario si ya se dispone del código fuente de la aplicación (carpeta con la propia aplicación)*
1. Descargar Git desde [git-scm.com](https://git-scm.com).
   - Acceder al apartado de descargas en la página principal (Downloads).
   - Seleccionar la versión para Windows.
   - Descargar desde el apartado **Standalone Installer** la versión de **64-bit Git for Windows Setup**.
2. Instala Git seleccionando las opciones por defecto, asegurándote de agregarlo al PATH (lo hace por defecto).

### Instalación de Visual Studio Build Tools
Para compilar algunas dependencias en Windows, será necesario instalar las **Visual Studio Build Tools**.
1. Descarga desde [Visual Studio Build Tools](https://visualstudio.microsoft.com/es/visual-cpp-build-tools/).
2. Durante la instalación, selecciona **Desarrollo para el escritorio con C++** y aseguráte de incluir el **MSVC Compiler** y **CMake** (La opción lo hace por defecto).
3. Verifica que las herramientas estén correctamente instaladas en el PATH. En caso de que no estén incluidas, añadir al PATH la dirección de la instalación:
    ```bash
    C:\Program Files\Microsoft Visual Studio\{Version}\BuildTools\VC\Tools\MSVC\{Version}\bin\Hostx64\x64
    ```
   #### *Nota*: No escribir esta misma dirección de ejemplo, se recomienda encarecidamente buscar la localización de la ruta de instalación (parecida a la del ejemplo) y copiar la ruta propia.

### Pasos

1. Clona el repositorio:
    ```bash
    git clone https://github.com/howlab-unizar/wpm-app.git
    cd turepositorio
    ```
    ***Nota***: El comando "cd turepositorio" se debe ejecutar en cualquiera de los casos (aunque ya se disponga del código fuente). "turepositorio" será el directorio en el que se encuentre el código fuente y aplicación.

2. Instala los paquetes necesarios:

    ```bash
    pip install -r requirements.txt
    ```

## Uso

### Ejecutar la Aplicación

Para iniciar la aplicación Dash, abre una consola de comandos en la carpeta donde tengas el código fuente de la aplicación (por ejemplo C:\Users\usuario\Desktop\aplicacion-de-monitorizacion-main, si estuviera en el escritorio) y ejecuta:

```powershell
python -m dash_app.app
```

Al lanzar la aplicación, se generará una carpeta "_bucket" (en el caso de que esta no exista) de manera automática. En ella se debe copiar/mover el archivo .bin con los datos del reloj.

***Nota*: en el código, se encuentra un archivo .bat que permite lanzar automáticamente la aplicación, haciendo doble click en el mismo. Para que funcione, la aplicación debe encontrarse en una carpeta aplicacion-de-monitorizacion dentro del escritorio del usuario (por ejemplo C:\Users\usuario\Desktop\aplicacion-de-monitorizacion)**

**Si se utiliza el archivo .bat para lanzar la aplicación, se debe esperar hasta que la aplicación aparezca cargada adecuadamente, puede tardar unos segundos.**

**Acceder al Dashboard**
Abre tu navegador web y visita http://127.0.0.1:8050 para acceder al dashboard.

**Generar Informes**
Haz clic en los enlaces en las tablas de datos para generar y ver informes en PDF para pacientes individuales.

Para poder seleccionar dónde descargar los archivos será necesario configurar el navegador para ello, en la configuración del navegador tendrá que seleccionar Preguntar dónde se guardará cada archivo descargado.
