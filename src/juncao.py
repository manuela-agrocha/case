import pandas as pd
import logging
import shutil
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

def realizar_juncao_datasets():
    pasta_projeto = Path(__file__).parent.parent
    pasta_processada = pasta_projeto / "data/processed"
    
    logging.info("Lendo arquivos filtrados da Casa dos Ventos...")
    df_det = pd.read_parquet(pasta_processada / "detalhamento_cdv_final.parquet")
    df_usi = pd.read_parquet(pasta_processada / "usinas_cdv_final.parquet")
    
    logging.info("Criando chaves textuais normalizadas...")
    df_det['chave_join'] = (df_det['nom_conjuntousina'].str.upper()
                            .str.normalize('NFKD').str.encode('ascii', errors='ignore')
                            .str.decode('utf-8').str.replace(r'[^A-Z0-9]', '', regex=True))
    
    df_usi['chave_join'] = (df_usi['nom_usina'].str.upper()
                            .str.normalize('NFKD').str.encode('ascii', errors='ignore')
                            .str.decode('utf-8').str.replace(r'[^A-Z0-9]', '', regex=True))

    logging.info("Realizando o LEFT JOIN temporal...")
    linhas_antes = len(df_det)
    
    df_merged = pd.merge(
        df_det, 
        df_usi[['chave_join', 'din_instante', 'val_geracaolimitada', 'val_geracaoreferencia', 'cod_razaorestricao', 'nom_estado']], 
        on=['chave_join', 'din_instante'], 
        how='left'
    )
    
    linhas_depois = len(df_merged)
    if linhas_antes != linhas_depois:
        logging.warning(f"Atenção: Houve explosão de linhas no merge! De {linhas_antes} para {linhas_depois}")
        
    nulos_apos_merge = df_merged['val_geracaolimitada'].isnull().sum()
    percentual_perda = (nulos_apos_merge / linhas_depois) * 100

    logging.info("\n=== RESULTADO DO MERGE ===")
    logging.info(f"Linhas preservadas na granularidade SPE: {linhas_depois}")
    logging.info(f"Instantes sem correspondência no Conjunto (Perdas): {nulos_apos_merge} ({percentual_perda:.2f}%)")
    
    df_merged = df_merged.drop(columns=['chave_join'])
    
    logging.info("Preparando particionamento dos dados...")
    df_merged['ano_mes'] = df_merged['din_instante'].dt.strftime('%Y-%m')
    
    caminho_saida = pasta_processada / "dataset_analitico_cdv"
    
    if caminho_saida.exists():
        logging.info("Limpando partições antigas para evitar duplicação...")
        shutil.rmtree(caminho_saida)  # Apaga a pasta inteira e tudo dentro dela

    logging.info("Salvando Dataset Analítico particionado em Parquet...")
    df_merged.to_parquet(
        caminho_saida,
        index=False,
        partition_cols=['projeto', 'ano_mes']
    )
    logging.info("Merge Finalizado.")

if __name__ == "__main__":
    realizar_juncao_datasets()