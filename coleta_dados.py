import pandas as pd
import requests
import os
from datetime import datetime, timedelta

# --- Configurações ---
LAT, LON = -21.967841992730392, -46.81400488524457
ARQUIVO_HORARIO = "1_irradiancia_horaria_NASA.csv"
ARQUIVO_DIARIO = "1_dados_diarios_NASA.csv"
DATA_INICIAL = datetime(2022, 1, 1)
data_limite = datetime.now() - timedelta(days=30)

def atualizar_csv(df_novo, nome_arquivo):
    if os.path.exists(nome_arquivo):
        df_antigo = pd.read_csv(nome_arquivo, index_col=0, parse_dates=True)
        df_final = pd.concat([df_antigo, df_novo]).sort_index()
        df_final = df_final[~df_final.index.duplicated(keep='last')]
    else:
        df_final = df_novo
    df_final.to_csv(nome_arquivo, encoding='utf-8-sig')

# --- 1. Coleta Diária (Irradiância + Temperatura) ---
print("Coletando dados diários...")
url_diaria = f"https://power.larc.nasa.gov/api/temporal/daily/point?parameters=ALLSKY_SFC_SW_DWN,T2M&community=RE&longitude={LON}&latitude={LAT}&start={DATA_INICIAL.strftime('%Y%m%d')}&end={data_limite.strftime('%Y%m%d')}&format=JSON"
res_d = requests.get(url_diaria).json()
df_d = pd.DataFrame(res_d['properties']['parameter'])
df_d.index = pd.to_datetime(df_d.index, format='%Y%m%d')
df_d = df_d[df_d['T2M'] != -999]
atualizar_csv(df_d, ARQUIVO_DIARIO)

# --- 2. Coleta Horária (Apenas Irradiância) ---
# (Mantendo a lógica de fatias de 365 dias para evitar erro de limite da API)
print("Coletando dados horários...")
# Aqui você pode manter a lógica de verificação de última data para economizar tempo
url_horaria = f"https://power.larc.nasa.gov/api/temporal/hourly/point?parameters=ALLSKY_SFC_SW_DWN&community=RE&longitude={LON}&latitude={LAT}&start={DATA_INICIAL.strftime('%Y%m%d')}&end={data_limite.strftime('%Y%m%d')}&format=JSON"
# Nota: Para períodos longos (>1 ano), a API horária pode exigir múltiplas chamadas.
