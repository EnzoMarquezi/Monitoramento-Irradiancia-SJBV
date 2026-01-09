import pandas as pd
import requests
import os
from datetime import datetime, timedelta

# ==========================================
# CONFIGURAÇÕES TÉCNICAS (SFCR 54 kWp - IFSP)
# ==========================================
LAT, LON = -21.967841992730392, -46.81400488524457
ARQUIVO_SAIDA = "1_irradiancia_NASA_SJBV_FromAPI.csv"
DATA_INICIAL_ESTUDO = datetime(2022, 1, 1) # Início conforme o artigo

# 1. Definir a data alvo (hoje com 30 dias de atraso)
data_limite_superior = datetime.now() - timedelta(days=30)

# 2. Verificar o ponto de partida
if os.path.exists(ARQUIVO_SAIDA):
    df_existente = pd.read_csv(ARQUIVO_SAIDA, index_col='Data_Hora', parse_dates=True)
    # A próxima busca começa na hora seguinte ao último dado salvo
    data_inicio_request = df_existente.index.max() + timedelta(hours=1)
    print(f"Retomando coleta a partir de: {data_inicio_request}")
else:
    data_inicio_request = DATA_INICIAL_ESTUDO
    df_existente = pd.DataFrame()
    print("Iniciando nova base de dados do zero (2022).")

# 3. Lógica de Requisição (NASA limita horários a 1 ano por pedido)
if data_inicio_request < data_limite_superior:
    # Definimos o fim desta requisição (máximo 1 ano à frente ou o limite de 30 dias)
    data_fim_request = min(data_inicio_request + timedelta(days=365), data_limite_superior)
    
    start_str = data_inicio_request.strftime('%Y%m%d')
    end_str = data_fim_request.strftime('%Y%m%d')
    
    print(f"Solicitando dados de {start_str} até {end_str}...")
    
    url = (
        f"https://power.larc.nasa.gov/api/temporal/hourly/point?"
        f"parameters=ALLSKY_SFC_SW_DWN,ALLSKY_SFC_SW_DNI,ALLSKY_SFC_SW_DIFF&"
        f"community=RE&longitude={LON}&latitude={LAT}&"
        f"start={start_str}&end={end_str}&format=JSON"
    )

    try:
        response = requests.get(url, timeout=60)
        response.raise_for_status()
        data = response.json()

        # Processamento dos novos dados
        df_novo = pd.DataFrame(data['properties']['parameter'])
        df_novo.index = pd.to_datetime(df_novo.index, format='%Y%m%d%H')
        df_novo.index.name = 'Data_Hora'
        df_novo.columns = ['GHI_W_m2', 'DNI_W_m2', 'DHI_W_m2']

        # Concatenar e salvar
        df_final = pd.concat([df_existente, df_novo]).drop_duplicates().sort_index()
        df_final.to_csv(ARQUIVO_SAIDA, encoding='utf-8-sig')
        
        print(f"✅ Sucesso! Dados atualizados até {end_str}.")
        
    except Exception as e:
        print(f"❌ Erro na requisição: {e}")
        exit(1)
else:
    print("✅ A base de dados já está atualizada até o limite de 30 dias atrás.")
