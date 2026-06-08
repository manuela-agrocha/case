# Desafio Técnico: Engenharia de Dados - Casa dos Ventos

Este repositório contém a solução ponta a ponta para o desafio de Engenharia de Dados. O projeto consiste em um pipeline ELT (Extract, Load, Transform) construído em Python que consome dados da API do Operador Nacional do Sistema (ONS), processa regras de negócio do setor elétrico, constrói um Data Warehouse local e serve os dados através de uma API REST.

---

## 🏗️ 1. Arquitetura da Solução (Ambiente Local)

O fluxo de dados foi desenhado para ser modular, idempotente e resiliente. Abaixo está o diagrama da arquitetura implementada:

```mermaid
graph TD
    A[API do ONS] -->|Extract| B(Camada Raw / CSV)
    B -->|Load & Consolidate| C(Camada Processed / Parquet)
    C -->|Transform & JOIN| D(Dataset Analítico Particionado)
    D -->|Dimensional Modeling| E[(Data Warehouse Local)]
    
    subgraph Modelagem Snowflake
        E1(dim_tempo) -.-> F[fato_geracao_spe]
        E2(dim_spe) -.-> F
        E3(dim_conjunto) -.-> E2
        E1 -.-> G[facto_restricao_conjunto]
        E3 -.-> G
    end
    
    E --> E1
    
    F -->|Consumo| H[FastAPI]
    G -->|Consumo| H
    H -->|JSON / REST| I(Usuário Final / BI)
    
    J[Data Observability / Validação] -.->|Monitora| E