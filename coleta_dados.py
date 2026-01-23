import pandas as pd
import requests
import os
from datetime import datetime, timedelta

# --- Configurações SFCR 54 kWp ---
LAT, LON = -21.967841992730392, -46.81400488524457
ARQUIVO_SAIDA = "1_dados_NASA_SJBV_Completo.csv"
DATA_INICIAL_ESTUDO = datetime(2022, 1, 1)

# 1. Definir data limite (Hoje - 30 dias para garantir dados consolidados)
data_limite_superior = datetime.now() - timedelta(days=30)

# 2. Verificar ponto de partida
if os.path.exists(ARQUIVO_SAIDA):
    df_existente = pd.read_csv(ARQUIVO_SAIDA, index_col='Data', parse_dates=True)
    data_inicio_request = df_existente.index.max() + timedelta(days=1)
    print(f"Retomando coleta de temperatura e irradiância de: {data_inicio_request.date()}")
else:
    data_inicio_request = DATA_INICIAL_ESTUDO
    df_existente = pd.DataFrame()
    print("Iniciando nova base de dados do zero (2022).")

# 3. Execução da Requisição (Resolução Diária)
if data_inicio_request < data_limite_superior:
    # A NASA permite períodos maiores para dados diários, mas manteremos 1 ano por segurança
    data_fim_request = min(data_inicio_request + timedelta(days=364), data_limite_superior)
    
    start_str = data_inicio_request.strftime('%Y%m%d')
    end_str = data_fim_request.strftime('%Y%m%d')
    
    # Parâmetros: ALLSKY_SFC_SW_DWN (Irradiância GHI) e T2M (Temperatura a 2m)
    url = (
        f"https://power.larc.nasa.gov/api/temporal/daily/point?"
        f"parameters=ALLSKY_SFC_SW_DWN,T2M&"
        f"community=RE&longitude={LON}&latitude={LAT}&"
        f"start={start_str}&end={end_str}&format=JSON"
    )

    try:
        response = requests.get(url, timeout=60)
        response.raise_for_status()
        json_data = response.json()

        params = json_data['properties']['parameter']
        df_novo = pd.DataFrame(params)
        df_novo.index = pd.to_datetime(df_novo.index, format='%Y%m%d')
        df_novo.index.name = 'Data'
        df_novo.columns = ['GHI_kWh_m2_dia', 'Temp_Media_C']

        # Filtro de erro (-999)
        df_novo = df_novo[df_novo['GHI_kWh_m2_dia'] != -999]

        if not df_novo.empty:
            df_final = pd.concat([df_existente, df_novo]).sort_index()
            df_final = df_final[~df_final.index.duplicated(keep='last')]
            df_final.to_csv(ARQUIVO_SAIDA, encoding='utf-8-sig')
            print(f"✅ Sucesso! Dados de Irradiância e Temperatura salvos até {df_novo.index.max().date()}.")
        else:
            print("⚠️ Apenas valores inválidos encontrados para este período.")
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        exit(1)
else:
    print("✅ Base de dados de 2022-2024 já está totalmente atualizada.")
