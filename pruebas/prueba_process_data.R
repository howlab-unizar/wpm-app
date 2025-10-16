process_data <- function() {
    library(data.table)
    library(GGIR)

    # Ruta del archivo CSV
    file_path <- "C:/Users/claua/Documents/Monitorización/Test/000000006_2024.02.02.csv"
    output_path <- "C:/Users/claua/Documents/Monitorización/Test/000000006_2024.02.02_resampled.csv"

    # Verificar que el archivo existe y no está vacío
    if (!file.exists(file_path) || file.info(file_path)$size == 0) {
        stop("El archivo no existe o está vacío: ", file_path)
    }

    # Leer el archivo CSV
    test <- fread(file_path, data.table = FALSE, nrow = 100)

    # Si dateTime no es POSIXct, convertirlo
    if (!inherits(test$dateTime, "POSIXct")) {
        test$dateTime <- as.POSIXct(test$dateTime / 1000, origin = "1970-01-01", tz = "UTC")
    }

    # Resamplear la temperatura
    test$ambient_temp <- nafill(test$ambient_temp, "locf")

    # Guardar el archivo resampleado
    fwrite(test, output_path, na = "", row.names = FALSE)

    # Crear una tabla de frecuencias de los tiempos
    time <- test$dateTime
    time <- as.character(trunc(time))
    table(table(time)) # sf varía de 25 a 26 Hz

    # Limpiar memoria
    rm(test); gc()

    # Ejecutar GGIR
    GGIR(mode = c(1:5),
         datadir = "C:/Users/claua/Documents/Monitorización/Test/",
         outputdir = "C:/Users/claua/Documents/Monitorización/Test/R/",
         idloc = 2,
         minimumFileSizeMB = 0,
         # parámetros de lectura
         rmc.dec = ".", rmc.firstrow.acc = 1, rmc.skip = 0,
         rmc.col.time = 1, rmc.col.acc = 2:4, rmc.col.temp = 9,
         rmc.unit.acc = "g", rmc.unit.temp = "C",
         rmc.unit.time = "POSIX", desiredtz = "UTC",
         rmc.dynamic_range = 16, rmc.sf = 25,
         rmc.check4timegaps = TRUE, rmc.doresample = TRUE, interpolationType = 1,
         rmc.noise = 0.013,
         # Actividad física
         mvpathreshold = 100,
         threshold.lig = 35, threshold.mod = 100, threshold.vig = 400,        
         boutdur.mvpa = c(1, 5, 10), boutdur.in = c(30, 60), boutdur.lig = c(10), 
         boutcriter.mvpa = 0.8, boutcriter.in = 0.9, boutcriter.lig = 0.8, 
         timewindow = c("MM"),
         save_ms5rawlevels = TRUE, save_ms5raw_without_invalid = FALSE,
         save_ms5raw_format = "RData",
         # REPORTES
         do.report = c(2, 4, 5),
         visualreport = TRUE)
}

# Descomentar para ejecutar directamente
process_data()
