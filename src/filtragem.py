import pandas as pd
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

def filtrar_escopo_casa_dos_ventos():
    pasta_projeto = Path(__file__).parent.parent
    pasta_processada = pasta_projeto / "data/processed"
    
    logging.info("Lendo arquivos Parquet e o CSV...")
    df_det = pd.read_parquet(pasta_processada / "detalhamento_consolidado.parquet")
    df_usi = pd.read_parquet(pasta_processada / "usinas_consolidado.parquet")
    df_spes_cdv = pd.read_csv(pasta_projeto / "spes_casa_dos_ventos.csv", sep=';')
    
    logging.info("REQUISITO 1: Extraindo núcleo e filtrando SPEs...")
    
    df_det['nucleo_ceg'] = df_det['ceg'].str.extract(r'([0-9]{6}-[0-9])')
    nucleos_validos = df_spes_cdv['ceg'].tolist()     
    df_det_filtrado = df_det[df_det['nucleo_ceg'].isin(nucleos_validos)].copy()

    logging.info("REQUISITO 2: Filtrando Conjuntos vinculados...")
    
    df_det_filtrado['chave_temporaria'] = (df_det_filtrado['nom_conjuntousina']
                                           .str.upper()
                                           .str.normalize('NFKD')
                                           .str.encode('ascii', errors='ignore')
                                           .str.decode('utf-8')
                                           .str.replace(r'[^A-Z0-9]', '', regex=True))
    conjuntos_cdv = df_det_filtrado['chave_temporaria'].unique()    
    df_usi['chave_temporaria'] = (df_usi['nom_usina']
                                  .str.upper()
                                  .str.normalize('NFKD')
                                  .str.encode('ascii', errors='ignore')
                                  .str.decode('utf-8')
                                  .str.replace(r'[^A-Z0-9]', '', regex=True))    
    df_usi_filtrado = df_usi[df_usi['chave_temporaria'].isin(conjuntos_cdv)].copy()    
    df_det_filtrado = df_det_filtrado.drop(columns=['chave_temporaria'])

    logging.info("REQUISITO 3: Adicionando a coluna 'projeto'")
    
    mapa_projetos = df_spes_cdv.set_index('ceg')['projeto']    
    
    df_det_filtrado['projeto'] = df_det_filtrado['nucleo_ceg'].map(mapa_projetos)
    df_det_final = df_det_filtrado.drop(columns=['nucleo_ceg'])
    df_usi_final = df_usi_filtrado.drop(columns=['chave_temporaria'])

    logging.info("\n=== RESULTADO FINAL DA FILTRAGEM ===")
    logging.info(f"Detalhamento (SPEs): Reduzido para {len(df_det_final)} linhas.")
    logging.info(f"Usinas (Conjuntos): Reduzido para {len(df_usi_final)} linhas.")
    
    logging.info("Salvando os arquivos particionados/finais...")
    df_det_final.to_parquet(pasta_processada / "detalhamento_cdv_final.parquet", index=False)
    df_usi_final.to_parquet(pasta_processada / "usinas_cdv_final.parquet", index=False)
    logging.info("SUCESSO! Etapa concluída.")

if __name__ == "__main__":
    filtrar_escopo_casa_dos_ventos()