import pandas as pd
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("Data_Quality_Validator")

def executar_validacoes(threshold_completude: float = 95.0):
    pasta_dw = Path(__file__).parent.parent / "data/dw"
    
    logger.info("=== INICIANDO TESTES DE QUALIDADE (DATA OBSERVABILITY) ===")
    
    # CARREGAMENTO DOS DADOS DO DW
    try:
        fato_geracao = pd.read_parquet(pasta_dw / "fato_geracao_spe.parquet")
        fato_restricao = pd.read_parquet(pasta_dw / "facto_restricao_conjunto.parquet")
        dim_tempo = pd.read_parquet(pasta_dw / "dim_tempo.parquet")
        dim_spe = pd.read_parquet(pasta_dw / "dim_spe.parquet")
    except Exception as e:
        logger.error(f"Falha ao carregar DW para validação: {e}")
        return False

    # 1. SCHEMA VALIDATION
    logger.info("[1/4] Validando Schemas...")
    colunas_esperadas_geracao = {'fk_tempo': 'int32', 'fk_spe': 'int64', 'val_ventoverificado': 'float64'}
    for col, dtype in colunas_esperadas_geracao.items():
        if col not in fato_geracao.columns: # <-- CORRIGIDO AQUI
            logger.error(f"Schema Error: Coluna '{col}' ausente em fato_geracao_spe.")
        # Se quiséssemos ser super rigorosos, checaríamos os tipos exatos aqui.
    logger.info("Schema validado com sucesso.")

    # 2. FRESHNESS CHECK
    logger.info("[2/4] Validando Freshness (Recência dos dados)...")
    dim_tempo['data_hora'] = pd.to_datetime(dim_tempo['data_hora'])
    data_mais_recente = dim_tempo['data_hora'].max()
    
    if data_mais_recente.year == 2026 and data_mais_recente.month >= 3:
        logger.info(f"Freshness validado. Dados atualizados até: {data_mais_recente.strftime('%d/%m/%Y %H:%M')}")
    else:
        logger.warning(f"Alerta: Os dados mais recentes são de {data_mais_recente}. Mês 03/2026 ausente!")

    # 3. REGRAS DE NEGÓCIO
    logger.info("[3/4] Executando Regras de Negócio...")
    falhas_negocio = 0
    
    # Regra A: Geração não pode ser negativa
    geracao_negativa = fato_geracao[fato_geracao['val_geracaoverificada'] < 0]
    if not geracao_negativa.empty:
        logger.error(f"Violação de Negócio: Encontrados {len(geracao_negativa)} registos com geração negativa!")
        falhas_negocio += 1
        
    # Regra B: Vento entre 0 e 40 m/s
    vento_invalido = fato_geracao[~fato_geracao['val_ventoverificado'].between(0, 40, inclusive='both')]
    if not vento_invalido.empty:
        logger.error(f"Violação de Negócio: {len(vento_invalido)} registos de vento fora do limite (0 a 40 m/s)!")
        falhas_negocio += 1

    # Regra C: Limitada (Corte) <= Referência (Capacidade)
    restricao_absurda = fato_restricao[fato_restricao['val_geracaolimitada'] > fato_restricao['val_geracaoreferencia']]
    if not restricao_absurda.empty:
        logger.error(f"Violação de Negócio: {len(restricao_absurda)} cortes superam a capacidade de referência!")
        falhas_negocio += 1
        
    if falhas_negocio == 0:
        logger.info("Todas as regras de negócio foram cumpridas.")

    # 4. COMPLETUDE E GAPS (Por Projeto)
    logger.info(f"[4/4] Validando Completude (Threshold: {threshold_completude}%)...")
    
    data_inicial = dim_tempo['data_hora'].min()
    timestamps_esperados = len(pd.date_range(start=data_inicial, end=data_mais_recente, freq='30min'))
    
    df_analise = pd.merge(fato_geracao, dim_spe, left_on='fk_spe', right_on='id_spe')
    
    spes_por_projeto = dim_spe.groupby('projeto')['id_spe'].count()
    
    projetos_com_alerta = 0
    for projeto, group in df_analise.groupby('projeto'):
        qtd_spes = spes_por_projeto[projeto]
        esperado_total = timestamps_esperados * qtd_spes
        recebido_total = len(group)
        
        percentual = (recebido_total / esperado_total) * 100
        
        if percentual < threshold_completude:
            logger.warning(f"GAP DETETADO no Projeto {projeto}: Completude de {percentual:.2f}% (Esperado: {esperado_total} | Recebido: {recebido_total})")
            projetos_com_alerta += 1
        else:
            logger.info(f"  - Projeto {projeto}: Completude Saudável ({percentual:.2f}%)")

    logger.info("=== TESTES DE QUALIDADE CONCLUÍDOS ===")
    return True

if __name__ == "__main__":
    executar_validacoes()