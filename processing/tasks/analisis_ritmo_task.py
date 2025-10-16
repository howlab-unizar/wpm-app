import os
import pandas as pd
import numpy as np

def rhythm_analysis(dir_path):
    global bio_status
    get_rhythm(dir_path)
    bio_status = "OK"

def get_rhythm(dir_path):
    results = pd.DataFrame()
    lista_res = []
    if os.path.exists(dir_path):

        #for f in os.listdir(dir_path):
        if os.path.isdir(dir_path):
            #print(f)

            #idx = f.find('_')
            #date = f[idx+1:]
            #id = f[:idx]
            #print(date)

            dirname = os.path.join(dir_path, "02_seg")

            for day in os.listdir(dirname):
                dir_day = os.path.join(dirname,day)
                if os.path.isdir(dir_day):
                    d2 = os.listdir(dir_day)

                    for hour in d2:
                        dir_hour = os.path.join(dir_day, hour)

                        d3 = os.listdir(dir_hour)

                        for seg in d3:
                            if seg[0:2] == "hr":
                                # if seg[-6:-4] == "_":
                                #     seg = seg[:-6] + "0" + seg[-6:]
                                dir_seg = os.path.join(dir_hour, seg)
                                print(dir_seg)

                                Media, STD, Maximo, Minimo = mata_processing(dir_seg)

                                res = [day+""+hour+""+seg[:-4],day, f'{hour}:{seg[3:]}', Media, STD, Maximo, Minimo]
                                lista_res.append(res)

        try:
            os.mkdir(os.path.join(dir_path, "03_bio"))
            with open(os.path.join(os.mkdir(os.path.join(dir_path, "03_bio")), 'bio_status.txt'), 'w') as bioStatusFile:
                            bioStatusFile.write("Started") # Actualiza el estado en el archivo de seguimiento de estado
        except:
            print("Carpeta existente")
         
        
        results = pd.DataFrame(lista_res, columns=['Segmento', "Fecha",  'Hora','Media', 'STD', 'Maximo', 'Minimo'])
        results.index = results.Segmento
        results = results.drop('Segmento', axis =1)
        results.to_csv(os.path.join(dir_path, "03_bio","HR_seg.csv"))

        results2 = pd.DataFrame()
        for dia in results.Fecha.unique():
            df_aux = results[results.Fecha == dia]
            d_aux = {'Fecha':[dia], 'Media': [np.round(np.nanmean(df_aux.Media),2)], 'STD': [np.round(np.nanstd(df_aux.STD),3)], 'Maximo': [np.nanmax(df_aux.Maximo)], 'Minimo': [np.nanmin(df_aux.Minimo)]}
            results2 = pd.concat([results2, pd.DataFrame(d_aux)])

        results2.to_csv(os.path.join(dir_path, "03_bio","HR_day.csv"))

    else:
        print("DIR DOES NOT EXIST")

def mata_processing(dir_seg):
    data = pd.read_csv(dir_seg)
    heart_rate = data.hr[data.hr>0]

    if heart_rate.empty:
        Media = -1
        STD = -1
        Maximo = -1
        Minimo = -1
    else:
        Media = np.nanmean(heart_rate)
        STD = np.nanstd(heart_rate)
        Maximo = np.nanmax(heart_rate)
        Minimo = np.nanmin(heart_rate)

    return [np.round(Media,2), np.round(STD,3), Maximo, Minimo]