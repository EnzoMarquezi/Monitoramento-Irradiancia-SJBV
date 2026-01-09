import pandas as pd
import requests
import os
from datetime import datetime, timedelta

# ==========================================
# CONFIGURAÇÕES TÉCNICAS (SFCR 54 kWp - IFSP)
# ==========================================
LAT, LON = -21.967841992730392, -46.81400488524457
ARQUIVO_SAIDA = "1_irradiancia_NASA_SJBV_FromAPI.csv"

# ==========================================
# LÓGICA DE DATAS AUTOMÁTICA
# ==========================================
# O robô sempre buscará dados de 14 dias atrás (atraso de 2 semanas)
data_alvo = datetime.now() - timedelta(days=14)
DATA_STR = data_alvo.strftime('%Y%m%d')

print(f"Iniciando coleta automatizada para o dia: {DATA_STR}")

# Parâmetros: GHI (Global), DNI (Direta), DHI (Difusa)
# Note que usamos a mesma data para INICIO e FIM para pegar apenas o dia específico
url_nasa = (
    f"https://power.larc.nasa.gov/api/temporal/hourly/point?"
    f"parameters=ALLSKY_SFC_SW_DWN,ALLSKY_SFC_SW_DNI,ALLSKY_SFC_SW_DIFF&"
    f"community=RE&longitude={LON}&latitude={LAT}&"
    f"start={DATA_STR}&end={DATA_STR}&format=JSON"
)

# ==========================================
# COLETA E PROCESSAMENTO
# ==========================================
try:
    response = requests.get(url_nasa, timeout=60)
    response.raise_for_status()
    data = response.json()

    # Criando o DataFrame do dia
    df_novo = pd.DataFrame(data['properties']['parameter'])
    df_novo.index = pd.to_datetime(df_novo.index, format='%Y%m%d%H')
    df_novo.index.name = 'Data_Hora'
    df_novo.columns = ['GHI_W_m2', 'DNI_W_m2', 'DHI_W_m2']

    # ==========================================
    # ATUALIZAÇÃO DO ARQUIVO CSV
    # ==========================================
    # Se o arquivo já existir, ele adiciona os novos dados sem apagar os antigos
    if os.path.exists(ARQUIVO_SAIDA):
        df_antigo = pd.read_csv(ARQUIVO_SAIDA, index_col='Data_Hora', parse_dates=True)
        # Combina os dados e remove duplicatas (caso o robô rode duas vezes no mesmo dia)
        df_final = pd.concat([df_antigo, df_novo]).drop_duplicates()
        df_final.to_csv(ARQUIVO_SAIDA, encoding='utf-8-sig')
        print(f"✅ Dados de {DATA_STR} adicionados ao arquivo existente.")
    else:
        # Se for a primeira vez, cria o arquivo
        df_novo.to_csv(ARQUIVO_SAIDA, encoding='utf-8-sig')
        print(f"✅ Arquivo novo criado com os dados de {DATA_STR}.")

except Exception as e:
    print(f"❌ Erro na automação: {e}")
    exit(1) # Informa ao GitHub que houve um erro
