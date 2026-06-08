import pandas as pd
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

def construir_modelo_dimensional():
    pasta_projeto = Path(__file__).parent.parent
    pasta_processada = pasta_projeto / "data/processed"
    pasta_dw = pasta_projeto / "data/dw"  # DW = Data Warehouse
    pasta_dw.mkdir(parents=True, exist_ok=True)
    
    logging.info("A ler o Dataset Analítico consolidado da Parte 1...")
    df_base = pd.read_parquet(pasta_processada / "dataset_analitico_cdv")
    df_base['din_instante'] = pd.to_datetime(df_base['din_instante'])

    logging.info("A construir dim_tempo...")
    dim_tempo = pd.DataFrame({'data_hora': df_base['din_instante'].unique()})
    dim_tempo['id_tempo'] = dim_tempo['data_hora'].dt.strftime('%Y%m%d%H%M').astype(int)
    dim_tempo['ano'] = dim_tempo['data_hora'].dt.year
    dim_tempo['mes'] = dim_tempo['data_hora'].dt.month
    dim_tempo['dia'] = dim_tempo['data_hora'].dt.day
    dim_tempo['hora'] = dim_tempo['data_hora'].dt.hour
    dim_tempo['minuto'] = dim_tempo['data_hora'].dt.minute

    logging.info("A construir dim_conjunto...")
    cols_conjunto = ['nom_conjuntousina']
    if 'nom_estado' in df_base.columns: cols_conjunto.append('nom_estado')
    if 'id_subsistema' in df_base.columns: cols_conjunto.append('id_subsistema')
    
    dim_conjunto = df_base[cols_conjunto].drop_duplicates().reset_index(drop=True)
    dim_conjunto['id_conjunto'] = dim_conjunto.index + 1  # Surrogate Key (Chave Primária)

    logging.info("A construir dim_spe (com hierarquia Snowflake)...")
    cols_spe = ['ceg', 'projeto', 'nom_conjuntousina']
    dim_spe = df_base[cols_spe].drop_duplicates().reset_index(drop=True)
    dim_spe['id_spe'] = dim_spe.index + 1
    
    mapa_conjunto = dim_conjunto.set_index('nom_conjuntousina')['id_conjunto']
    dim_spe['fk_conjunto'] = dim_spe['nom_conjuntousina'].map(mapa_conjunto)
    dim_spe = dim_spe.drop(columns=['nom_conjuntousina']) # Removemos o texto para normalizar

    logging.info("A mapear as chaves estrangeiras (FKs)...")
    df_base['fk_tempo'] = df_base['din_instante'].dt.strftime('%Y%m%d%H%M').astype(int)
    
    mapa_spe = dim_spe.set_index('ceg')['id_spe']
    df_base['fk_spe'] = df_base['ceg'].map(mapa_spe)
    df_base['fk_conjunto'] = df_base['nom_conjuntousina'].map(mapa_conjunto)

    logging.info("A construir facto_geracao_spe...")
    fato_geracao = df_base[['fk_tempo', 'fk_spe', 
                            'val_ventoverificado', 'val_geracaoestimada', 'val_geracaoverificada']].copy()

    logging.info("A construir facto_restricao_conjunto...")
    fato_restricao = df_base[['fk_tempo', 'fk_conjunto', 
                              'val_geracaolimitada', 'val_geracaoreferencia', 'cod_razaorestricao']].drop_duplicates().copy()

    logging.info("A guardar o modelo dimensional em formato Parquet...")
    dim_tempo.to_parquet(pasta_dw / "dim_tempo.parquet", index=False)
    dim_conjunto.to_parquet(pasta_dw / "dim_conjunto.parquet", index=False)
    dim_spe.to_parquet(pasta_dw / "dim_spe.parquet", index=False)
    fato_geracao.to_parquet(pasta_dw / "fato_geracao_spe.parquet", index=False)
    fato_restricao.to_parquet(pasta_dw / "facto_restricao_conjunto.parquet", index=False)

    logging.info("\n=== SUCESSO! MODELO POPULADO ===")
    logging.info(f"dim_tempo: {len(dim_tempo)} registos")
    logging.info(f"dim_conjunto: {len(dim_conjunto)} registos")
    logging.info(f"dim_spe: {len(dim_spe)} registos")
    logging.info(f"facto_geracao_spe: {len(fato_geracao)} registos")
    logging.info(f"facto_restricao_conjunto: {len(fato_restricao)} registos")

if __name__ == "__main__":
    construir_modelo_dimensional()