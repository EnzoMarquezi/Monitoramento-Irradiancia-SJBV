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

def coletar_dados_nasa(resolucao, parametros, data_inicio):
    """Função auxiliar para requisitar dados à API"""
    start_str = data_inicio.strftime('%Y%m%d')
    end_str = data_limite_superior.strftime('%Y%m%d')
    
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
print("Iniciando coleta diária (Irradiância + Temperaturas)...")
# Parâmetros: Irradiância (ALLSKY_SFC_SW_DWN), Temp Média (T2M), Temp Mín (T2M_MIN), Temp Máx (T2M_MAX)
params_d = "ALLSKY_SFC_SW_DWN,T2M,T2M_MIN,T2M_MAX"
dados_d = coletar_dados_nasa("daily", params_d, DATA_INICIAL_ESTUDO)

if dados_d:
    df_diario = pd.DataFrame(dados_d)
    df_diario.index = pd.to_datetime(df_diario.index, format='%Y%m%d')
    df_diario.index.name = 'Data'
    df_diario.columns = ['GHI_kWh_m2_dia', 'Temp_Media_C', 'Temp_Min_C', 'Temp_Max_C']
    
    # Filtro de erro (-999)
    df_diario = df_diario[df_diario['GHI_kWh_m2_dia'] != -999]
    df_diario.to_csv(ARQUIVO_DIARIO, encoding='utf-8-sig')
    print(f"✅ Arquivo diário atualizado: {ARQUIVO_DIARIO}")

# ==========================================
# 2. PROCESSAMENTO HORÁRIO (APENAS GHI)
# ==========================================
print("\nIniciando coleta horária (Apenas Irradiância)...")
# Para dados horários, a NASA limita a 1 ano por pedido. 
# Vamos buscar o último ano disponível dentro do limite de 30 dias.
data_inicio_h = max(DATA_INICIAL_ESTUDO, data_limite_superior - timedelta(days=364))
params_h = "ALLSKY_SFC_SW_DWN"
dados_h = coletar_dados_nasa("hourly", params_h, data_inicio_h)

if dados_h:
    df_horario = pd.DataFrame(dados_h)
    df_horario.index = pd.to_datetime(df_horario.index, format='%Y%m%d%H')
    df_horario.index.name = 'Data_Hora'
    df_horario.columns = ['GHI_W_m2']
    
    # Filtro de erro (-999) e manutenção de zeros (noite)
    df_horario = df_horario[df_horario['GHI_W_m2'] != -999]
    df_horario.to_csv(ARQUIVO_HORARIO, encoding='utf-8-sig')
    print(f"✅ Arquivo horário atualizado: {ARQUIVO_HORARIO}")
