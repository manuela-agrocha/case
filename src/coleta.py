import requests
import logging
import pandas as pd
import time
from pathlib import Path

logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def download_ons_coff_data(start_date: str, end_date: str, output_base_dir: str = "data/raw"):

    dir_usinas = Path(output_base_dir) / "usinas"
    dir_detalhamento = Path(output_base_dir) / "detalhamento"
    
    dir_usinas.mkdir(parents=True, exist_ok=True)
    dir_detalhamento.mkdir(parents=True, exist_ok=True)

    base_url_usinas = "https://ons-aws-prod-opendata.s3.amazonaws.com/dataset/restricao_coff_eolica_tm/RESTRICAO_COFF_EOLICA_{year}_{month}.csv"
    base_url_detalhamento = "https://ons-aws-prod-opendata.s3.amazonaws.com/dataset/restricao_coff_eolica_detail_tm/RESTRICAO_COFF_EOLICA_DETAIL_{year}_{month}.csv"

    months_to_download = pd.date_range(start=start_date, end=end_date, freq='MS')

    for dt in months_to_download:
        year_str = dt.strftime("%Y")
        month_str = dt.strftime("%m") # Garante o '0' à esquerda (ex: 03, 10)
        
        logging.info(f"Iniciando coleta para o período: {month_str}/{year_str}")

        url_usinas = base_url_usinas.format(year=year_str, month=month_str)
        file_path_usinas = dir_usinas / f"RESTRICAO_COFF_EOLICA_{year_str}_{month_str}.csv"
        _download_file(url_usinas, file_path_usinas)

        url_detalhamento = base_url_detalhamento.format(year=year_str, month=month_str)
        file_path_detalhamento = dir_detalhamento / f"RESTRICAO_COFF_EOLICA_DETAIL_{year_str}_{month_str}.csv"
        _download_file(url_detalhamento, file_path_detalhamento)

def _download_file(url: str, save_path: Path, max_retries: int = 3):
    if save_path.exists():
        logging.info(f"Idempotência ativada: Arquivo já existe. Ignorando download de {save_path.name}")
        return True

    for attempt in range(1, max_retries + 1):
        try:
            response = requests.get(url, stream=True, timeout=15)
            response.raise_for_status()
            
            with open(save_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            logging.info(f"Download concluído: {save_path.name}")
            return True
            
        except requests.exceptions.HTTPError as e:
            if response.status_code == 404:
                logging.error(f"Fallback: Mês indisponível no ONS (404) - {url}")
                return False
            logging.warning(f"Erro HTTP {response.status_code}. Tentativa {attempt}/{max_retries}...")
        except requests.exceptions.RequestException as e:
            logging.warning(f"Falha de conexão. Tentativa {attempt}/{max_retries} - Erro: {e}")
        
        time.sleep(2 ** attempt)
        
    logging.error(f"Falha definitiva ao baixar {save_path.name} após {max_retries} tentativas.")
    return False

if __name__ == "__main__":
    download_ons_coff_data(start_date="2025-10-01", end_date="2026-03-01")