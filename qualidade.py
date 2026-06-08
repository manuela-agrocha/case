import pandas as pd
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')

def qualidade_de_dados(df: pd.DataFrame, tipo_dataset: str) -> tuple[pd.DataFrame, dict]:
    logging.info(f"\n--- Iniciando Qualidade de Dados: {tipo_dataset.upper()} ---")
    
    total_linhas_iniciais = len(df)
    
    df_limpo = df.drop_duplicates()
    linhas_removidas_duplicadas = total_linhas_iniciais - len(df_limpo)
    
    linhas_removidas_vento = 0
    if 'flg_dadoventoinvalido' in df_limpo.columns:
        linhas_antes_vento = len(df_limpo)
        df_limpo = df_limpo[df_limpo['flg_dadoventoinvalido'] == 0]
        linhas_removidas_vento = linhas_antes_vento - len(df_limpo)
        
    colunas_numericas = df_limpo.select_dtypes(include=['float64', 'int64']).columns
    df_limpo[colunas_numericas] = df_limpo[colunas_numericas].fillna(0.0)
    
    percentual_nulos = (df.isnull().sum() / len(df)) * 100
    dict_nulos = percentual_nulos[percentual_nulos > 0].round(2).to_dict()

    relatorio = {
        "Dataset": tipo_dataset,
        "Total_Linhas_Iniciais": total_linhas_iniciais,
        "Total_Linhas_Finais": len(df_limpo),
        "Duplicatas_Removidas": linhas_removidas_duplicadas,
        "Ventos_Invalidos_Removidos": linhas_removidas_vento,
        "Percentual_Nulos_Original": dict_nulos
    }
    
    logging.info(f"Linhas Iniciais: {total_linhas_iniciais}")
    logging.info(f"Duplicatas removidas: {linhas_removidas_duplicadas}")
    if linhas_removidas_vento > 0:
         logging.info(f"Ventos inválidos removidos: {linhas_removidas_vento}")
    logging.info(f"Linhas Finais (Limpas): {len(df_limpo)}")
    
    return df_limpo, relatorio