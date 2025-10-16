# -------------------------------------------------------------------------
# Functions to manage dependencies ----------------------------------------
# -------------------------------------------------------------------------

install_cran_if_needed <- function(pkg, min_version) {
  if (!requireNamespace(pkg, quietly = TRUE)) {
    install.packages(pkg, repos = "https://cloud.r-project.org")
  } else {
    installed_ver <- as.character(packageVersion(pkg))
    if (utils::compareVersion(installed_ver, min_version) < 0) {
      install.packages(pkg, repos = "https://cloud.r-project.org")
    }
  }
}

install_github_if_needed <- function(pkg, repo, min_version) {
  if (!requireNamespace(pkg, quietly = TRUE)) {
    remotes::install_github(repo, upgrade = "never")
  } else {
    installed_ver <- as.character(packageVersion(pkg))
    if (utils::compareVersion(installed_ver, min_version) < 0) {
      remotes::install_github(repo, upgrade = "never")
    }
  }
}

verisense_count_steps <- function(input_data = runif(500,min = -1.5, max = 1.5), coeffs = c(0,0,0)) {
  # by Matthew R Patterson, mpatterson@shimmersensing.com
  ## Find peaks of RMS acceleration signal according to Gu et al, 2017 method
  # This method is based off finding peaks in the summed and squared acceleration signal
  # and then using multiple thresholds to determine if each peak is a step or an artefact.
  # An additional magnitude threshold was added to the algorithm to prevent false positives
  # in free living data.
  #
  # returns sample location of each step
  fs = 15 # temporary for now, this is manually set
  acc <- sqrt(input_data[,1]^2 + input_data[,2]^2 + input_data[,3]^2)

  if (sd(acc) < 0.025) {
    # acceleration too low, no steps
    num_seconds = round(length(acc) / fs)
    steps_per_sec = rep(0,num_seconds)
  } else {
    # Search for steps
    # Thresholds
    k <- coeffs[[1]]
    period_min <- coeffs[[2]]
    period_max <- coeffs[[3]]
    sim_thres <- coeffs[[4]]   # similarity threshold
    cont_win_size <- coeffs[[5]]  # continuity window size
    cont_thres <- coeffs[[6]]     # continuity threshold
    var_thres <- coeffs[[7]]  # variance threshold
    mag_thres <- coeffs[[8]]

    # find the peak rms value is every range of k
    half_k <- round(k/2)
    segments <- floor(length(acc) / k)
    peak_info <- matrix(NA, nrow = segments,ncol=5)
    # peak_info[,1] - peak location
    # peak_info[,2] - acc magnitude
    # peak_info[,3] - periodicity (samples)
    # peak_info[,4] - similarity
    # peak_info[,5] - continuity

    # for each segment find the peak location
    for (i in 1:segments) {
      start_idx <- (i-1) * k + 1
      end_idx <- start_idx + (k-1)
      tmp_loc_a <- which.max(acc[start_idx:end_idx])
      tmp_loc_b <- (i-1) * k + tmp_loc_a
      # only save if this is a peak value in range of -k/2:+K/2
      start_idx_ctr <- tmp_loc_b - half_k
      if (start_idx_ctr < 1) {
        start_idx_ctr <- 1
      }
      end_idx_ctr <- tmp_loc_b + half_k
      if (end_idx_ctr > length(acc)) {
        end_idx_ctr <- length(acc)
      }
      check_loc <- which.max(acc[start_idx_ctr:end_idx_ctr])
      if (check_loc == (half_k + 1)) {
        peak_info[i,1] <- tmp_loc_b
        peak_info[i,2] <- max(acc[start_idx:end_idx])
      }
    }
    peak_info <- peak_info[is.na(peak_info[,1])!=TRUE,] # get rid of na rows

    # filter peak_info[,2] based on mag_thres
    peak_info <- peak_info[peak_info[,2] > mag_thres,]
    if (length(peak_info) > 10) {  # there must be at least two steps
      num_peaks <- length(peak_info[,1])

      no_steps = FALSE
      if (num_peaks > 2) {
        # Calculate Features (periodicity, similarity, continuity)
        peak_info[1:(num_peaks-1),3] <- diff(peak_info[,1]) # calculate periodicity
        peak_info <- peak_info[peak_info[,3] > period_min,] # filter peaks based on period_min
        peak_info <- peak_info[peak_info[,3] < period_max,]   # filter peaks based on period_max
      } else {
        no_steps = TRUE
      }
    } else {
      no_steps = TRUE
    }

    if ( length(peak_info)==0 || length(peak_info) == sum(is.na(peak_info)) || no_steps == TRUE) {
      # no steps found
      num_seconds = round(length(acc) / fs)
      steps_per_sec = rep(0,num_seconds)
    } else {
      # calculate similarity
      num_peaks <- length(peak_info[,1])
      peak_info[1:(num_peaks-2),4] <- -abs(diff(peak_info[,2],2)) # calculate similarity
      peak_info <- peak_info[peak_info[,4] > sim_thres,]  # filter based on sim_thres
      peak_info <- peak_info[is.na(peak_info[,1])!=TRUE,] # previous statement can result in an NA in col-1

      # calculate continuity
      if (length(peak_info[,3]) > 5) {
        end_for <- length(peak_info[,3])-1
        for (i in cont_thres:end_for) {
          # for each bw peak period calculate acc var
          v_count <- 0 # count how many windows were over the variance threshold
          for (x in 1:cont_thres) {
            if (var(acc[peak_info[i-x+1,1]:peak_info[i-x+2,1]]) > var_thres) {
              v_count = v_count + 1
            }
          }
          if (v_count >= cont_win_size) {
            peak_info[i,5] <- 1 # set continuity to 1, otherwise, 0
          } else {
            peak_info[i,5] <- 0
          }
        }
      }
      peak_info <- peak_info[peak_info[,5]==1,1] # continuity test - only keep locations after this
      peak_info <- peak_info[is.na(peak_info)!=TRUE] # previous statement can result in an NA in col-1

      if (length(peak_info)==0) {
        # no steps found
        num_seconds = round(length(acc) / fs)
        steps_per_sec = rep(0,num_seconds)
      } else {

        # for GGIR, output the number of steps in 1 second chunks
        start_idx_vec <- seq(from=1,to=length(acc),by=fs)
        steps_per_sec <- table(factor(findInterval(peak_info, start_idx_vec), levels = seq_along(start_idx_vec)))
        steps_per_sec <- as.numeric(steps_per_sec)
      }
    }
  }

  return(steps_per_sec)
}

# -------------------------------------------------------------------------
# Principal function ------------------------------------------------------
# -------------------------------------------------------------------------

process_data <- function(root_path, bin_dir) {
    print("Initializing data processing...")
    # 1) Install / charge required packs ----------------------------------
    required_cran <- list(
      GGIRread = "1.0.4",
      jsonlite = "1.9.1",
      GGIR = "3.2.3",
      tools = "4.5.0"
    )

    required_github <- list(
      stepmetrics = list(repo = "jhmigueles/stepmetrics", min_version = "0.1.3")
    )

    # Install remotes in order to install CRAN
    if (!requireNamespace("remotes", quietly = TRUE)) {
      install.packages("remotes", repos = "https://cloud.r-project.org")
    }
    library(remotes)

    # Instalar paquetes desde CRAN
    invisible(mapply(install_cran_if_needed, names(required_cran), required_cran))

    # Instalar paquetes desde GitHub
    invisible(mapply(function(pkg, cfg) {
      install_github_if_needed(pkg, cfg$repo, cfg$min_version)
    }, names(required_github), required_github))

    library(GGIR)
    library(GGIRread)
    library(stepmetrics)
    library(jsonlite)

    # 2) Create directories structure -------------------------------------
    bio_dir <- file.path(root_path, "03_bio")
    if (!dir.exists(bio_dir)) {
        dir.create(bio_dir, recursive = TRUE)
        print(paste("'03_bio' created in: ", bio_dir))
    } else {
        print(paste("'03_bio' dir already exists: ", bio_dir))
    }
    output_dir <- file.path(bio_dir, "R/output")
    dir.create(output_dir, recursive = TRUE, showWarnings = FALSE)

    # 3) Configure steps counter for GGIR ---------------------------------
    # Parameters to detect steps (Rowlands et al.)
    step_counter =  list(FUN = verisense_count_steps,
                         parameters = c(4, 4, 20, -1.0, 4, 4, 0.01, 1.25),
                         expected_sample_rate = 15,
                         expected_unit = "g",
                         colnames = c("step_count"),
                         outputres = 1,
                         minlength = 1,
                         outputtype = "numeric",
                         aggfunction = sum,
                         timestamp = F,
                         reporttype = "event")

    # 4) Execute GGIR -----------------------------------------------------
    #suppressWarnings(dir.create("output_activity"))
    studyname = tools::file_path_sans_ext(basename(bin_dir))
    GGIR(mode = c(1:5),
         datadir = bin_dir, outputdir = output_dir,
         studyname = studyname,
         idloc = 6,
         overwrite = TRUE,
         # incluir conteo de pasos
         myfun = step_counter,
         # Sleep
         HASPT.algo = c("NotWorn", "HDCZA"),
         # Physical Activity
         part5_agg2_60seconds = TRUE,
         mvpathreshold = 100,
         threshold.lig = 35, threshold.mod = 100, threshold.vig = 400,
         boutdur.mvpa = c(3), boutdur.lig = c(3), boutdur.in = c(60),
         boutcriter.mvpa = 1,
         timewindow = c("MM"),
         save_ms5rawlevels = TRUE,
         # CLEANING
         includedaycrit = 22,
         includedaycrit.part5 = 10,
         includenightcrit = 22,
         #REPORTS
         do.report = c(2, 4, 5),
         visualreport = F,
         old_visualreport = F)

    # 5) Charge required data for the report ------------------------------
    results_dir <- file.path(output_dir)
    files = dir(results_dir, recursive = TRUE, full.names = TRUE)
    #steps = read.csv(grep("dayevent", files, value = TRUE))
    #stepsweek = read.csv(grep("_event", files, value = TRUE))
    paday = read.csv(grep("part5_daysummary_full", files, value = TRUE))
    paweek = read.csv(grep("part5_personsummary_MM", files, value = TRUE))
    sleep = read.csv(grep("nightsummary_sleep_full", files, value = TRUE))

    # Calcular métricas adicionales de pasos
    msfile = dir(file.path(results_dir, paste0("output_", studyname), "meta", "ms5.outraw"),
             full.names = T, recursive = T, pattern = ".RData$")

    mdat = NULL
    load(msfile)
    steps = mdat[, c("timestamp", "step_count")]
    steps$calendar_date = format(steps$timestamp, format = "%Y-%m-%d")
    steps_total = aggregate(step_count ~ calendar_date, data = steps, FUN = sum)
    steps_1_39spm = aggregate(step_count ~ calendar_date, data = steps, FUN = function(x) sum(x[x >= 1 & x <= 39]))
    steps_40_99spm = aggregate(step_count ~ calendar_date, data = steps, FUN = function(x) sum(x[x >= 40 & x <= 99]))
    steps_100spm = aggregate(step_count ~ calendar_date, data = steps, FUN = function(x) sum(x[x >= 100]))

    steps_summary = merge(steps_total, steps_1_39spm, by = "calendar_date",
                          suffixes = c("_total", "_1_39spm"))
    steps_summary = merge(steps_summary, steps_40_99spm, by = "calendar_date")
    names(steps_summary)[ncol(steps_summary)] = "step_count_40_99spm"
    steps_summary = merge(steps_summary, steps_100spm, by = "calendar_date")
    names(steps_summary)[ncol(steps_summary)] = "step_count_100spm+"
    paday = merge(paday, steps_summary, by = "calendar_date")

    # Total weekly
    sb_unbt_week_hrs = paweek$dur_day_IN_unbt_min_wei * 7 / 60
    sb_bts_week_hrs = paweek$dur_day_IN_bts_60_min_wei * 7 / 60
    lig_week_min = paweek$dur_day_LIG_bts_3_min_wei * 7
    mod_week_min = (paweek$dur_day_total_MOD_min_wei - paweek$dur_day_MOD_unbt_min_wei)*7
    vig_week_min = paweek$dur_day_total_VIG_min_wei * 7
    steps_total_week = paweek$steps_total_wei * 7
    guidelines_min = mod_week_min + vig_week_min
    guidelines_perc = guidelines_min / 150 * 100
    dur_day_IN_unbt_min = paday$dur_day_IN_unbt_min
    dur_day_IN_bts_60_min = paday$dur_day_IN_bts_60_min

    # Mean weekly
    sb_unbt_week_avg = sb_unbt_week_hrs / 7
    sb_bts_week_avg = sb_bts_week_hrs / 7
    lig_week_avg = lig_week_min / 7
    mod_week_avg = mod_week_min / 7
    vig_week_avg = vig_week_min / 7

    # Daily estimations:
    # Identify valid days:
    daycrit_min = 22*60
    awakecrit_min = 10*60
    daynonwear_min = paday$dur_day_spt_min*(paday$nonwear_perc_day_spt/100)
    daywear_min = paday$dur_day_spt_min - daynonwear_min
    awakenonwear_min = paday$dur_day_min*(paday$nonwear_perc_day/100)
    awakewear_min = paday$dur_day_min - awakenonwear_min
    sleepnonwear_min = sleep$sleep$fraction_night_invalid
    validday = daywear_min >= daycrit_min & awakewear_min >= awakecrit_min
    days_analysed = paday$weekday
    dates = paday$calendar_date

    names(dur_day_IN_unbt_min) = paday$weekday
    dur_day_IN_unbt_min[validday == FALSE] = NA

    names(dur_day_IN_bts_60_min) = paday$weekday
    dur_day_IN_bts_60_min[validday == FALSE] = NA

    # Ligera
    lig_day_min = paday$dur_day_LIG_bts_3_min
    names(lig_day_min) = paday$weekday
    lig_day_min[validday == FALSE] = NA

    # Moderada
    mod_day_min = paday$dur_day_total_MOD_min - paday$dur_day_MOD_unbt_min
    names(mod_day_min) = paday$weekday
    mod_day_min[validday == FALSE] = NA

    # Vigorosa
    vig_day_min = paday$dur_day_total_VIG_min
    names(vig_day_min) = paday$weekday
    vig_day_min[validday == FALSE] = NA

    # pasos por día
    steps_total = paday$step_count_total
    names(steps_total) = paday$weekday
    steps_total[validday == FALSE] = NA

    # pasos por día a una cadencia de 1-39spm
    steps_1_39spm = paday$step_count_1_39spm
    names(steps_1_39spm) = paday$weekday
    steps_1_39spm[validday == FALSE] = NA

    # pasos por día a una cadencia de 40-99spm
    steps_40_99spm = paday$step_count_40_99spm
    names(steps_40_99spm) = paday$weekday
    steps_40_99spm[validday == FALSE] = NA

    # pasos por día a una cadencia de 100spm o más
    steps_100spm = paday$`step_count_100spm+`
    names(steps_100spm) = paday$weekday
    steps_100spm[validday == FALSE] = NA

    # steps per week
    steps_total_WE = mean(steps_total[names(steps_total) %in% c("Saturday", "Sunday")], na.rm = T)
    steps_total_WD = mean(steps_total[!names(steps_total) %in% c("Saturday", "Sunday")], na.rm = T)
    paweek$steps_total_wei = (steps_total_WD*5 + steps_total_WE*2) / 7

    steps_1_39spm_WE = mean(steps_1_39spm[names(steps_1_39spm) %in% c("Saturday", "Sunday")], na.rm = T)
    steps_1_39spm_WD = mean(steps_1_39spm[!names(steps_1_39spm) %in% c("Saturday", "Sunday")], na.rm = T)
    paweek$step_count_1_39spm_wei = (steps_1_39spm_WD*5 + steps_1_39spm_WE*2) / 7

    steps_40_99spm_WE = mean(steps_40_99spm[names(steps_40_99spm) %in% c("Saturday", "Sunday")], na.rm = T)
    steps_40_99spm_WD = mean(steps_40_99spm[!names(steps_40_99spm) %in% c("Saturday", "Sunday")], na.rm = T)
    paweek$step_count_40_99spm_wei = (steps_40_99spm_WD*5 + steps_40_99spm_WE*2) / 7

    steps_100spm_WE = mean(steps_100spm[names(steps_100spm) %in% c("Saturday", "Sunday")], na.rm = T)
    steps_100spm_WD = mean(steps_100spm[!names(steps_100spm) %in% c("Saturday", "Sunday")], na.rm = T)
    paweek$`step_count_100spm+_wei` = (steps_100spm_WD*5 + steps_100spm_WE*2) / 7

    # sleep per day
    spt_day = sleep$SptDuration
    names(spt_day) = sleep$weekday
    spt_day[sleep$fraction_night_invalid > (1 - 22/24)] = NA

    sleep_day = sleep$SleepDurationInSpt
    names(sleep_day) = sleep$weekday
    sleep_day[sleep$fraction_night_invalid > (1 - 22/24)] = NA

    waso_day = sleep$WASO
    names(waso_day) = sleep$weekday
    waso_day[sleep$fraction_night_invalid > (1 - 22/24)] = NA

    eff_day = sleep_day / spt_day * 100

    # weekly sleep
    wkdays = c("Monday", "Tuesday", "Wednesday", "Thursday", "Sunday")
    wkends = c("Saturday", "Friday")

    total_valid_days <- sum(validday, na.rm = TRUE)
    valid_weekdays   <- sum(validday & paday$weekday %in% wkdays, na.rm = TRUE)
    valid_weekends   <- sum(validday & paday$weekday %in% wkends, na.rm = TRUE)

    spt_week_WD = mean(spt_day[names(spt_day) %in% wkdays], na.rm = T)*5
    spt_week_WE = mean(spt_day[names(spt_day) %in% wkends], na.rm = T)*2
    spt_week_avg = (spt_week_WD + spt_week_WE) / 7

    sleep_week_WD = mean(sleep_day[names(sleep_day) %in% wkdays], na.rm = T)*5
    sleep_week_WE = mean(sleep_day[names(sleep_day) %in% wkends], na.rm = T)*2
    sleep_week_avg = (sleep_week_WD + sleep_week_WE) / 7

    waso_week_WD = mean(waso_day[names(waso_day) %in% wkdays], na.rm = T)*5
    waso_week_WE = mean(waso_day[names(waso_day) %in% wkends], na.rm = T)*2
    waso_week_avg = (waso_week_WD + waso_week_WE) / 7

    eff_week_WD = mean(eff_day[names(eff_day) %in% wkdays], na.rm = T)*5
    eff_week_WE = mean(eff_day[names(eff_day) %in% wkends], na.rm = T)*2
    eff_week_avg = (eff_week_WD + eff_week_WE) / 7

    # Estruct results in a list:
    resultados <- list(
      total_valid_days = total_valid_days,
      valid_weekdays = valid_weekdays,
      valid_weekends = valid_weekends,
      days_analysed = days_analysed,
      dates = dates,

      sb_unbt_week_hrs = sb_unbt_week_hrs,
      sb_bts_week_hrs = sb_bts_week_hrs,
      lig_week_min = lig_week_min,
      mod_week_min = mod_week_min,
      vig_week_min = vig_week_min,
      guidelines_min = guidelines_min,
      guidelines_perc = guidelines_perc,

      dur_day_IN_unbt_min = dur_day_IN_unbt_min,
      dur_day_IN_bts_60_min = dur_day_IN_bts_60_min,

      sb_unbt_week_avg = sb_unbt_week_avg,
      sb_bts_week_avg = sb_bts_week_avg,
      lig_week_avg = lig_week_avg,
      mod_week_avg = mod_week_avg,
      vig_week_avg = vig_week_avg,

      lig_day_min = lig_day_min,
      mod_day_min = mod_day_min,
      vig_day_min = vig_day_min,

      steps_day_total = steps_total,
      steps_day_1_39spm = steps_1_39spm,
      steps_day_40_99spm = steps_40_99spm,
      steps_day_100spm = steps_100spm,
      steps_total_week_avg = paweek$steps_total_wei,
      steps_1_39spm_week_avg = paweek$step_count_1_39spm_wei,
      steps_40_99spm_week_avg = paweek$step_count_40_99spm_wei,
      steps_100spm_week_avg = paweek$`step_count_100spm+_wei`,

      sleep_day = sleep_day,
      sleep_week_avg = sleep_week_avg,

      waso_day = waso_day,
      waso_week_avg = waso_week_avg,

      eff_day = eff_day,
      eff_week_avg = eff_week_avg
    )

    descripciones <- list(
      total_valid_days = "Número total de días válidos",
      valid_weekdays = "Número de días válidos entre semana",
      valid_weekends = "Número de días válidos en fin de semana",
      days_analysed = "Nombres de los días de la semana",
      dates = "Fechas durante las que se realiza la evaluación",

      sb_unbt_week_hrs = "Horas totales a la semana en comportamiento sedentario con interrupciones",
      sb_bts_week_hrs = "Horas totales a la semana en comportamiento sedentario en bloques de al menos 60 minutos",
      lig_week_min = "Minutos totales a la semana de actividad física ligera",
      mod_week_min = "Minutos totales a la semana de actividad física moderada",
      vig_week_min = "Minutos totales a la semana de actividad física vigorosa",
      guidelines_min = "Minutos totales de actividad física moderada a vigorosa a la semana",
      guidelines_perc = "Porcentaje del cumplimiento de la recomendación de 150 minutos de MVPA semanales",

      dur_day_IN_unbt_min = "Minutos totales diarios en comportamiento sedentario con interrupciones",
      dur_day_IN_bts_60_min = "Minutos totales diarios en comportamiento sedentario en bloques de al menos 60 minutos",

      sb_unbt_week_avg = "Promedio diario de horas en comportamiento sedentario con interrupciones",
      sb_bts_week_avg = "Promedio diario de horas en comportamiento sedentario en bloques de al menos 60 minutos",
      lig_week_avg = "Promedio diario de minutos en actividad física ligera",
      mod_week_avg = "Promedio diario de minutos en actividad física moderada",
      vig_week_avg = "Promedio diario de minutos en actividad física vigorosa",

      lig_day_min = "Minutos acumulados en actividad física ligera por día",
      mod_day_min = "Minutos acumulados en actividad física moderada por día",
      vig_day_min = "Minutos acumulados en actividad física vigorosa por día",

      steps_day_total = "Cantidad total de pasos por día",
      steps_day_1_39spm = "Cantidad de pasos por día realizados con una cadencia de 1-39 pasos/minuto",
      steps_day_40_99spm = "Cantidad de pasos por día realizados con una cadencia de 40-99 pasos/minuto",
      steps_day_100spm = "Cantidad de pasos por día realizados con una cadencia de 100 pasos/minuto o superior",
      steps_total_week_avg = "Promedio diario de pasos a lo largo de la semana",
      steps_1_39spm_week_avg = "Promedio diario de pasos a lo largo de la semana realizados con una cadencia de 1-39 pasos/minuto",
      steps_40_99spm_week_avg = "Promedio diario de pasos a lo largo de la semana realizados con una cadencia de 40-99 pasos/minuto",
      steps_100spm_week_avg = "Promedio diario de pasos a lo largo de la semana realizados con una cadencia de 100 pasos/minuto o superior",

      sleep_day = "Tiempo total de sueño efectivo por noche",
      sleep_week_avg = "Promedio diario de sueño efectivo a lo largo de la semana",

      waso_day = "Tiempo total despierto después del inicio del sueño (WASO) por noche",
      waso_week_avg = "Promedio diario de WASO a lo largo de la semana",

      eff_day = "Eficiencia del sueño durante los días laborables (porcentaje de tiempo dormido respecto al tiempo en cama) por noche",
      eff_week_avg = "Promedio diario de eficiencia del sueño a lo largo de la semana"
    )

    # Build JSON
    json_output <- lapply(names(resultados), function(var) {
      list(
        name = var,
        value = resultados[[var]],
        description = descripciones[[var]]
      )
    })

    json_file = file.path(output_dir, "output_00_bin", "results", "resultado_estructurado.json")
    write(jsonlite::toJSON(json_output, pretty = TRUE, auto_unbox = TRUE), json_file)
    print(paste("JSON generado en: ", json_file))
}

# Uncomment to run directly
if (sys.nframe() == 0) {
    args <- commandArgs(trailingOnly = TRUE)
    if (length(args) < 2) {
        stop("Use: Rscript analisis_movimiento.R <root_path> <bin_dir>")
    }
    process_data(args[1], args[2])
}
#process_data()

