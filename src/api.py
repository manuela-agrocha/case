from fastapi import FastAPI, HTTPException, Query
from typing import Optional
import pandas as pd
from pathlib import Path

app = FastAPI(
    title="API Casa dos Ventos",
    description="Serviço de fornecimento de dados do Data Warehouse Eólico",
    version="1.0.0"
)

pasta_dw = Path(__file__).parent.parent / "data/dw"

def carregar_tabela(nome_tabela: str):
    caminho = pasta_dw / f"{nome_tabela}.parquet"
    if not caminho.exists():
        raise HTTPException(status_code=500, detail=f"Erro interno: Tabela {nome_tabela} não encontrada.")
    return pd.read_parquet(caminho)


# ENDPOINT 1: HEALTH CHECK
@app.get("/health", tags=["Sistema"])
def health_check():
    return {"status": "ok", "mensagem": "API da Casa dos Ventos operante e pronta para receber pedidos!"}

# ENDPOINT 2: LISTAR PROJETOS
@app.get("/projects", tags=["Projetos"])
def listar_projetos():
    dim_spe = carregar_tabela("dim_spe")
    dim_conjunto = carregar_tabela("dim_conjunto")
    
    df_projetos = pd.merge(dim_spe, dim_conjunto, left_on='fk_conjunto', right_on='id_conjunto')
    
    resumo = df_projetos.groupby('projeto').agg({
        'nom_estado': 'first',
        'id_subsistema': 'first'
    }).reset_index()
    
    return resumo.to_dict(orient="records")

# ENDPOINT 3: GERAÇÃO POR PROJETO
@app.get("/generation/{project_id}", tags=["Geração"])
def obter_geracao(
    project_id: str, 
    start_date: Optional[str] = Query(None, description="Data início (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="Data fim (YYYY-MM-DD)"),
    agregacao: str = Query("mensal", description="Escolha: 'diario' ou 'mensal'")
):
    fato_geracao = carregar_tabela("fato_geracao_spe")
    dim_spe = carregar_tabela("dim_spe")
    dim_tempo = carregar_tabela("dim_tempo")
    
    spes_do_projeto = dim_spe[dim_spe['projeto'] == project_id.upper()]
    if spes_do_projeto.empty:
        raise HTTPException(status_code=404, detail=f"Projeto '{project_id}' não encontrado.")
        
    geracao_filtrada = fato_geracao[fato_geracao['fk_spe'].isin(spes_do_projeto['id_spe'])]
    
    df_final = pd.merge(geracao_filtrada, dim_tempo, left_on='fk_tempo', right_on='id_tempo')
    
    df_final['data_hora'] = pd.to_datetime(df_final['data_hora'])
    if start_date:
        df_final = df_final[df_final['data_hora'] >= pd.to_datetime(start_date)]
    if end_date:
        df_final = df_final[df_final['data_hora'] <= pd.to_datetime(end_date)]
        
    colunas_agrupamento = ['ano', 'mes', 'dia'] if agregacao == 'diario' else ['ano', 'mes']
    
    resultado = df_final.groupby(colunas_agrupamento)['val_geracaoverificada'].sum().reset_index()
    resultado = resultado.rename(columns={'val_geracaoverificada': 'geracao_total_mw'})
    
    return resultado.to_dict(orient="records")


# ENDPOINT 4: RESUMO DE RESTRIÇÕES (Cortes do ONS)
@app.get("/restrictions/summary", tags=["Restrições"])
def resumo_restricoes(
    project_id: Optional[str] = Query(None, description="Filtrar por sigla do Projeto (Ex: BBS)"),
    start_date: Optional[str] = Query(None, description="Data início (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="Data fim (YYYY-MM-DD)")
):
    fato_restricao = carregar_tabela("facto_restricao_conjunto")
    dim_tempo = carregar_tabela("dim_tempo")
    dim_conjunto = carregar_tabela("dim_conjunto")
    
    df_rest = pd.merge(fato_restricao, dim_tempo, left_on='fk_tempo', right_on='id_tempo')
    
    if project_id:
        dim_spe = carregar_tabela("dim_spe")
        spes_projeto = dim_spe[dim_spe['projeto'] == project_id.upper()]
        conjuntos_do_projeto = spes_projeto['fk_conjunto'].unique()
        df_rest = df_rest[df_rest['fk_conjunto'].isin(conjuntos_do_projeto)]
        
        if df_rest.empty:
            raise HTTPException(status_code=404, detail="Nenhuma restrição encontrada para este projeto.")

    df_rest['data_hora'] = pd.to_datetime(df_rest['data_hora'])
    if start_date:
        df_rest = df_rest[df_rest['data_hora'] >= pd.to_datetime(start_date)]
    if end_date:
        df_rest = df_rest[df_rest['data_hora'] <= pd.to_datetime(end_date)]

    df_rest['horas_restricao'] = 0.5
    df_rest['energia_mwh_perdida'] = df_rest['val_geracaolimitada'] * 0.5
    
    resumo = df_rest.groupby('cod_razaorestricao').agg({
        'horas_restricao': 'sum',
        'energia_mwh_perdida': 'sum'
    }).reset_index()
    
    return resumo.to_dict(orient="records")