import os
import logging
from dotenv import load_dotenv

# Importando os módulos da nossa pasta 'src'
from src.coleta import download_ons_coff_data
from src.consolidacao import consolidar_datasets, qualidade_de_dados
from src.filtragem import filtrar_escopo_casa_dos_ventos
from src.juncao import realizar_juncao_datasets
from src.modelagem import construir_modelo_dimensional
from src.validacao import executar_validacoes

def setup_logging():
    log_level_str = os.getenv("LOG_LEVEL", "INFO").upper()
    log_level = getattr(logging, log_level_str, logging.INFO)
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

def run_pipeline():
    # Carrega os parâmetros do arquivo .env
    load_dotenv()
    setup_logging()
    logger = logging.getLogger("Pipeline_Orchestrator")
    
    start_date = os.getenv("START_DATE", "2025-10-01")
    end_date = os.getenv("END_DATE", "2026-03-01")
    base_dir = os.getenv("BASE_DIR", "data")
    
    logger.info("=== INICIANDO PIPELINE ELT (CASA DOS VENTOS) ===")
    
    # ---------------------------------------------------------
    # FASE 1: EXTRACT (Coleta)
    # ---------------------------------------------------------
    logger.info("[FASE 1: EXTRACT] - Iniciando extração do ONS...")
    # (No coleta.py, certifique-se de que a função aceite o diretório base)
    download_ons_coff_data(start_date, end_date, output_base_dir=f"{base_dir}/raw")
    
    # ---------------------------------------------------------
    # FASE 2: LOAD (Consolidação no Data Lake)
    # ---------------------------------------------------------
    logger.info("[FASE 2: LOAD] - Carregando dados no Data Lake local...")
    df_usinas = consolidar_datasets(f"{base_dir}/raw", "usinas")
    df_detalhe = consolidar_datasets(f"{base_dir}/raw", "detalhamento")
    
    # Aplicação de Qualidade de Dados durante o Load
    df_usinas_limpo = qualidade_de_dados(df_usinas, "Usinas")
    df_detalhe_limpo = qualidade_de_dados(df_detalhe, "Detalhamento")
    
    df_usinas_limpo.to_parquet(f"{base_dir}/processed/usinas_consolidado.parquet", index=False)
    df_detalhe_limpo.to_parquet(f"{base_dir}/processed/detalhamento_consolidado.parquet", index=False)
    
    # ---------------------------------------------------------
    # FASE 3: TRANSFORM (Transformações de Negócio e Modelagem)
    # ---------------------------------------------------------
    logger.info("[FASE 3: TRANSFORM] - Aplicando regras de negócio...")
    filtrar_escopo_casa_dos_ventos()
    realizar_juncao_datasets()
    construir_modelo_dimensional()

    # ---------------------------------------------------------
    # FASE 4: DATA QUALITY (Validação e Observabilidade)
    # ---------------------------------------------------------
    logger.info("[FASE 4: DATA QUALITY] - Iniciando validações...")
    executar_validacoes(threshold_completude=95.0)
    
    logger.info("=== PIPELINE E TESTES CONCLUÍDOS COM SUCESSO ===")
    
if __name__ == "__main__":
    run_pipeline()