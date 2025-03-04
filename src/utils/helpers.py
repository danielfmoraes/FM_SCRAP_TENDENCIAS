import os
import json
import logging
import re
import string
from datetime import datetime
import hashlib

def setup_logging(log_level=logging.INFO):
    """
    Configura o sistema de logging para o projeto.
    
    Args:
        log_level: Nível de logging (padrão: INFO)
    """
    # Criar diretório de logs se não existir
    log_dir = 'logs'
    ensure_dir(log_dir)
    
    # Nome do arquivo de log com timestamp
    log_file = os.path.join(log_dir, f'fm_trends_{datetime.now().strftime("%Y%m%d")}.log')
    
    # Configurar formato de logging
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    
    # Reduzir verbosidade de logs de bibliotecas externas
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('selenium').setLevel(logging.WARNING)
    logging.getLogger('webdriver_manager').setLevel(logging.WARNING)

def ensure_dir(directory):
    """
    Garante que um diretório exista, criando-o se necessário.
    
    Args:
        directory: Caminho do diretório
    """
    if not os.path.exists(directory):
        os.makedirs(directory)

def clean_text(text):
    """
    Limpa e normaliza um texto.
    
    Args:
        text: Texto a ser limpo
        
    Returns:
        Texto limpo e normalizado
    """
    if not text or not isinstance(text, str):
        return ""
    
    # Remover caracteres especiais e pontuação
    text = re.sub(r'[^\w\s]', ' ', text)
    
    # Remover espaços extras
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text

def generate_article_id(article_data):
    """
    Gera um ID único para um artigo com base em seu URL e título.
    
    Args:
        article_data: Dicionário com dados do artigo
        
    Returns:
        ID único do artigo
    """
    # Usar URL como base para o ID, se disponível
    if 'url' in article_data and article_data['url']:
        base = article_data['url']
    # Caso contrário, usar título
    elif 'title' in article_data and article_data['title']:
        base = article_data['title']
    else:
        # Fallback para timestamp se nem URL nem título estiverem disponíveis
        base = str(datetime.now().timestamp())
    
    # Gerar hash MD5 do texto base
    return hashlib.md5(base.encode('utf-8')).hexdigest()

def save_article(article_data, directory='data/raw'):
    """
    Salva dados de um artigo em um arquivo JSON.
    
    Args:
        article_data: Dicionário com dados do artigo
        directory: Diretório onde salvar o arquivo
        
    Returns:
        Caminho do arquivo salvo
    """
    # Garantir que o diretório exista
    ensure_dir(directory)
    
    # Gerar ID para o artigo
    article_id = generate_article_id(article_data)
    
    # Adicionar ID e timestamp ao artigo
    article_data['id'] = article_id
    article_data['collected_at'] = datetime.now().isoformat()
    
    # Definir caminho do arquivo
    file_path = os.path.join(directory, f'article_{article_id}.json')
    
    # Salvar como JSON
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(article_data, f, ensure_ascii=False, indent=4)
    
    return file_path

def load_articles(directory='data/raw'):
    """
    Carrega todos os artigos salvos em um diretório.
    
    Args:
        directory: Diretório contendo os arquivos JSON dos artigos
        
    Returns:
        Lista de dicionários com dados dos artigos
    """
    articles = []
    
    # Verificar se o diretório existe
    if not os.path.exists(directory):
        return articles
    
    # Listar arquivos JSON no diretório
    for filename in os.listdir(directory):
        if filename.endswith('.json'):
            file_path = os.path.join(directory, filename)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    article_data = json.load(f)
                    articles.append(article_data)
            except Exception as e:
                logging.error(f"Erro ao carregar artigo {file_path}: {str(e)}")
    
    return articles

def extract_date(date_str):
    """
    Extrai uma data de uma string em vários formatos possíveis.
    
    Args:
        date_str: String contendo uma data
        
    Returns:
        Objeto datetime ou None se não for possível extrair
    """
    if not date_str:
        return None
    
    # Lista de formatos de data comuns
    date_formats = [
        '%Y-%m-%d',           # 2023-01-31
        '%d/%m/%Y',           # 31/01/2023
        '%d-%m-%Y',           # 31-01-2023
        '%d.%m.%Y',           # 31.01.2023
        '%d %b %Y',           # 31 Jan 2023
        '%d %B %Y',           # 31 January 2023
        '%b %d, %Y',          # Jan 31, 2023
        '%B %d, %Y',          # January 31, 2023
        '%Y%m%d'              # 20230131
    ]
    
    # Tentar cada formato
    for date_format in date_formats:
        try:
            return datetime.strptime(date_str.strip(), date_format)
        except ValueError:
            continue
    
    # Tentar extrair com regex se os formatos não funcionarem
    try:
        # Procurar padrão de data (dia/mês/ano)
        match = re.search(r'(\d{1,2})[/.-](\d{1,2})[/.-](\d{2,4})', date_str)
        if match:
            day, month, year = map(int, match.groups())
            # Ajustar ano de 2 dígitos
            if year < 100:
                year += 2000 if year < 50 else 1900
            return datetime(year, month, day)
    except:
        pass
    
    return None