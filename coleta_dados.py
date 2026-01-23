import pandas as pd
import requests
import os
from datetime import datetime, timedelta

# --- Configurações SFCR 54 kWp ---
LAT, LON = -21.967841992730392, -46.81400488524457
ARQUIVO_DIARIO = "1_dados_diarios_NASA.csv"
ARQUIVO_HORARIO = "1_irradiancia_horaria_NASA.csv"
DATA_INICIAL_ESTUDO = datetime(2022, 1, 1)

# 1. Definir data limite de segurança (Hoje - 30 dias)
data_limite_superior = datetime.now() - timedelta(days=30)

def coletar_dados_nasa(resolucao, parametros, data_inicio, data_fim):
    """Função auxiliar para requisitar dados à API"""
    start_str = data_inicio.strftime('%Y%m%d')
    end_str = data_fim.strftime('%Y%m%d')
    
    url = (
        f"https://power.larc.nasa.gov/api/temporal/{resolucao}/point?"
        f"parameters={parametros}&"
        f"community=RE&longitude={LON}&latitude={LAT}&"
        f"start={start_str}&end={end_str}&format=JSON"
    )
    
    try:
        response = requests.get(url, timeout=60)
        response.raise_for_status()
        return response.json()['properties']['parameter']
    except Exception as e:
        print(f"❌ Erro na requisição {resolucao}: {e}")
        return None

# ==========================================
# 1. PROCESSAMENTO DIÁRIO (GHI + TEMP MÍN/MÉD/MÁX)
# ==========================================
print("Iniciando coleta diária...")
params_d = "ALLSKY_SFC_SW_DWN,T2M,T2M_MIN,T2M_MAX"
# Dados diários permitem períodos longos, então buscamos tudo até a data limite
dados_d = coletar_dados_nasa("daily", params_d, DATA_INICIAL_ESTUDO, data_limite_superior)

if dados_d:
    df_diario = pd.DataFrame(dados_d)
    df_diario.index = pd.to_datetime(df_diario.index, format='%Y%m%d')
    df_diario.index.name = 'Data'
    df_diario.columns = ['GHI_kWh_m2_dia', 'Temp_Media_C', 'Temp_Min_C', 'Temp_Max_C']
    df_diario = df_diario[df_diario['GHI_kWh_m2_dia'] != -999]
    df_diario.to_csv(ARQUIVO_DIARIO, encoding='utf-8-sig')
    print(f"✅ Arquivo diário atualizado até {df_diario.index.max().date()}")

# ==========================================
# 2. PROCESSAMENTO HORÁRIO (APENAS GHI)
# ==========================================
print("\nIniciando coleta horária...")

# Verifica onde parou para não começar sempre em 2024
if os.path.exists(ARQUIVO_HORARIO):
    df_h_existente = pd.read_csv(ARQUIVO_HORARIO, index_col=0, parse_dates=True)
    data_inicio_h = df_h_existente.index.max() + timedelta(hours=1)
    print(f"Retomando horários de: {data_inicio_h}")
else:
    data_inicio_h = DATA_INICIAL_ESTUDO
    df_h_existente = pd.DataFrame()
    print("Iniciando base horária do zero (2022).")

if data_inicio_h < data_limite_superior:
    # A API limita a 1 ano (365 dias) por pedido horário
    data_fim_h = min(data_inicio_h + timedelta(days=364), data_limite_superior)
    
    params_h = "ALLSKY_SFC_SW_DWN"
    dados_h = coletar_dados_nasa("hourly", params_h, data_inicio_h, data_fim_h)

    if dados_h:
        df_novo_h = pd.DataFrame(dados_h)
        df_novo_h.index = pd.to_datetime(df_novo_h.index, format='%Y%m%d%H')
        df_novo_h.index.name = 'Data_Hora'
        df_novo_h.columns = ['GHI_W_m2']
        
        # Filtro de erro (-999), mantendo os zeros noturnos
        df_novo_h = df_novo_h[df_novo_h['GHI_W_m2'] != -999]
        
        df_final_h = pd.concat([df_h_existente, df_novo_h]).sort_index()
        df_final_h = df_final_h[~df_final_h.index.duplicated(keep='last')]
        df_final_h.to_csv(ARQUIVO_HORARIO, encoding='utf-8-sig')
        print(f"✅ Arquivo horário atualizado até {df_final_h.index.max()}")
else:
    print("✅ Base horária já está atualizada até o limite de 30 dias.")
