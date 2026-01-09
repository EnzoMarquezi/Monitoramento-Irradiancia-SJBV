import pandas as pd
import requests
import os
from datetime import datetime, timedelta

# --- Configurações SFCR 54 kWp ---
LAT, LON = -21.967841992730392, -46.81400488524457
ARQUIVO_SAIDA = "1_irradiancia_NASA_SJBV_FromAPI.csv"
DATA_INICIAL_ESTUDO = datetime(2022, 1, 1)

# 1. Definir data limite (Hoje - 30 dias)
data_limite_superior = datetime.now() - timedelta(days=30)

# 2. Verificar onde a coleta parou
if os.path.exists(ARQUIVO_SAIDA):
    df_existente = pd.read_csv(ARQUIVO_SAIDA, index_col='Data_Hora', parse_dates=True)
    # Começa exatamente no minuto após o último registro
    data_inicio_request = df_existente.index.max() + timedelta(hours=1)
    print(f"Retomando coleta de: {data_inicio_request}")
else:
    data_inicio_request = DATA_INICIAL_ESTUDO
    df_existente = pd.DataFrame()
    print("Iniciando nova base de dados do zero (2022).")

# 3. Execução da Requisição
if data_inicio_request < data_limite_superior:
    # A NASA limita dados horários a períodos de no máximo 1 ano (365 dias)
    # Calculamos o fim desta fatia de coleta
    data_fim_request = min(data_inicio_request + timedelta(days=364), data_limite_superior)
    
    start_str = data_inicio_request.strftime('%Y%m%d')
    end_str = data_fim_request.strftime('%Y%m%d')
    
    url = (
        f"https://power.larc.nasa.gov/api/temporal/hourly/point?"
        f"parameters=ALLSKY_SFC_SW_DWN,ALLSKY_SFC_SW_DNI,ALLSKY_SFC_SW_DIFF&"
        f"community=RE&longitude={LON}&latitude={LAT}&"
        f"start={start_str}&end={end_str}&format=JSON"
    )

    try:
        response = requests.get(url, timeout=60)
        response.raise_for_status()
        json_data = response.json()

        # Extração direta para garantir que zeros não sejam descartados
        params = json_data['properties']['parameter']
        df_novo = pd.DataFrame(params)
        df_novo.index = pd.to_datetime(df_novo.index, format='%Y%m%d%H')
        df_novo.index.name = 'Data_Hora'
        df_novo.columns = ['GHI_W_m2', 'DNI_W_m2', 'DHI_W_m2']

        # Concatenar mantendo a ordem cronológica
        df_final = pd.concat([df_existente, df_novo]).sort_index()
        
        # Remover duplicatas apenas se houver sobreposição exata de data/hora
        df_final = df_final[~df_final.index.duplicated(keep='last')]

        # Salvar o arquivo
        df_final.to_csv(ARQUIVO_SAIDA, encoding='utf-8-sig')
        print(f"✅ Sucesso! Dados adicionados de {start_str} até {end_str}.")
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        exit(1)
else:
    print("✅ Base de dados já está atualizada.")
