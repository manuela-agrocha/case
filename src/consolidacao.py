import pandas as pd
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def consolidar_datasets(diretorio_base: str, subpasta: str) -> pd.DataFrame:

    caminho_pasta = Path(diretorio_base) / subpasta
    arquivos_csv = list(caminho_pasta.glob('*.csv')) 
    
    if not arquivos_csv:
        logging.error(f"Nenhum arquivo CSV encontrado na pasta {caminho_pasta}")
        return pd.DataFrame()

    lista_de_dataframes = []
    
    for arquivo in arquivos_csv:
        logging.info(f"Lendo e consolidando: {arquivo.name}")
        
        df_mensal = pd.read_csv(
            arquivo,
            sep=';',              
            encoding='utf-8'      
        )
        
        df_mensal['din_instante'] = pd.to_datetime(df_mensal['din_instante'], format='mixed')
        
        lista_de_dataframes.append(df_mensal)
        
    df_unificado = pd.concat(lista_de_dataframes, ignore_index=True)
    
    logging.info(f"Consolidação de '{subpasta}' finalizada! Linhas brutas: {len(df_unificado)}\n")
    return df_unificado

def qualidade_de_dados(df: pd.DataFrame, tipo_dataset: str) -> tuple[pd.DataFrame, dict]:

    logging.info(f"--- Iniciando Qualidade de Dados: {tipo_dataset.upper()} ---")
    
    total_linhas_iniciais = len(df)
    
    df_limpo = df.drop_duplicates() # duplicatas
    linhas_removidas_duplicadas = total_linhas_iniciais - len(df_limpo)
    
    linhas_removidas_vento = 0
    if 'flg_dadoventoinvalido' in df_limpo.columns:
        linhas_antes_vento = len(df_limpo)
        df_limpo = df_limpo[df_limpo['flg_dadoventoinvalido'] == 0]
        linhas_removidas_vento = linhas_antes_vento - len(df_limpo)
          
    colunas_numericas = df_limpo.select_dtypes(include=['float64', 'int64']).columns
    df_limpo[colunas_numericas] = df_limpo[colunas_numericas].fillna(0.0)
       
    logging.info(f"Relatório {tipo_dataset}: {total_linhas_iniciais} linhas originais -> "
                 f"{linhas_removidas_duplicadas} duplicatas removidas -> "
                 f"{linhas_removidas_vento} ventos inválidos descartados -> "
                 f"{len(df_limpo)} linhas limpas finais.\n")
    
    # Calcula os nulos
    percentual_nulos = (df.isnull().sum() / len(df)) * 100
    nulos_formatados = percentual_nulos[percentual_nulos > 0].round(2)
    
    logging.info(f"\n--- RELATÓRIO DE NULOS ({tipo_dataset}) ---")
    if nulos_formatados.empty:
        logging.info("Nenhuma coluna possui valores nulos.")
    else:
        for coluna, valor in nulos_formatados.items():
            logging.info(f"Coluna '{coluna}': {valor}% de dados nulos originais")
    logging.info("-------------------------------------------\n")
    
    return df_limpo

if __name__ == "__main__":
    
    df_usinas_completo = consolidar_datasets("data/raw", "usinas")
    df_detalhamento_completo = consolidar_datasets("data/raw", "detalhamento")

    df_usinas_limpo = qualidade_de_dados(df_usinas_completo, "Usinas")
    df_detalhe_limpo = qualidade_de_dados(df_detalhamento_completo, "Detalhamento")

    logging.info("Salvando os dados limpos no disco...")
    pasta_processada = Path("data/processed")
    pasta_processada.mkdir(parents=True, exist_ok=True)
    
    df_usinas_limpo.to_parquet(pasta_processada / "usinas_consolidado.parquet", index=False)
    df_detalhe_limpo.to_parquet(pasta_processada / "detalhamento_consolidado.parquet", index=False)
    
    logging.info("Tudo pronto! Arquivos Parquet salvos com sucesso na pasta 'data/processed'!")