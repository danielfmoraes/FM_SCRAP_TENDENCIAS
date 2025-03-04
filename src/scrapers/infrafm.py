import requests
import logging
import time
from bs4 import BeautifulSoup
from datetime import datetime
from src.utils.helpers import clean_text, save_article, extract_date

logger = logging.getLogger(__name__)

class InfraFMScraper:
    def __init__(self):
        self.base_url = "https://www.infrafm.com.br"
        self.content_index_url = "https://www.infrafm.com.br/Indice-de-conteudos/0/ultimos-conteudos"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
    
    def get_article_links(self, page_url, max_pages=5):
        """Extrai links de artigos da página de índice de conteúdos"""
        article_links = []
        current_page = 1
        
        try:
            while current_page <= max_pages:
                # Adicionar parâmetro de paginação se não for a primeira página
                url = page_url
                if current_page > 1:
                    url = f"{page_url}?pagina={current_page}"
                
                logger.info(f"Coletando links da página {current_page}: {url}")
                response = requests.get(url, headers=self.headers)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Encontrar links de artigos na página
                article_elements = soup.select('a.busca_title')
                
                if not article_elements:
                    # Tentar outro seletor se o primeiro não funcionar
                    article_elements = soup.select('div.busca_item a')
                
                page_links = []
                for link in article_elements:
                    href = link.get('href')
                    if href:
                        # Converter URLs relativas para absolutas
                        if href.startswith('/'):
                            href = self.base_url + href
                        
                        if href not in article_links and '/Textos/' in href:
                            page_links.append(href)
                
                if not page_links:
                    logger.warning(f"Nenhum link encontrado na página {current_page}. Verificando HTML...")
                    # Imprimir alguns links da página para debug
                    all_links = soup.select('a')
                    for i, link in enumerate(all_links[:10]):
                        href = link.get('href')
                        text = link.text.strip()
                        logger.warning(f"Link {i+1}: {text} -> {href}")
                    break
                
                article_links.extend(page_links)
                logger.info(f"Encontrados {len(page_links)} links na página {current_page}")
                
                # Verificar se há mais páginas
                next_page = soup.select_one('a.next_page')
                if not next_page:
                    break
                
                current_page += 1
                time.sleep(1)  # Pausa para evitar sobrecarga no servidor
                
        except Exception as e:
            logger.error(f"Erro ao coletar links: {str(e)}")
        
        return article_links
    
    def scrape_article(self, article_url):
        """Extrai dados de um artigo específico"""
        try:
            response = requests.get(article_url, headers=self.headers)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extrair título
            title_tag = soup.select_one('h1.titulo_texto') or soup.select_one('h1')
            title = title_tag.text.strip() if title_tag else "Sem título"
            
            # Extrair data
            date_tag = soup.select_one('span.data_texto') or soup.select_one('div.data')
            date_str = date_tag.text.strip() if date_tag else None
            date = extract_date(date_str) if date_str else datetime.now()
            
            # Extrair autor
            author_tag = soup.select_one('span.autor_texto') or soup.select_one('div.autor')
            author = author_tag.text.strip() if author_tag else "InfraFM"
            
            # Extrair conteúdo
            content_tag = soup.select_one('div.texto_completo') or soup.select_one('div.conteudo_texto')
            
            if content_tag:
                # Remover elementos indesejados
                for unwanted in content_tag.select('script, style, iframe'):
                    unwanted.decompose()
                
                content = content_tag.text.strip()
            else:
                content = ""
            
            # Extrair categorias/tags
            categories = []
            category_tags = soup.select('div.tags a') or soup.select('div.categorias a')
            
            for cat in category_tags:
                categories.append(cat.text.strip())
            
            # Criar dicionário com os dados do artigo
            article_data = {
                'title': title,
                'url': article_url,
                'date': date.isoformat() if hasattr(date, 'isoformat') else str(date),
                'author': author,
                'content': content,
                'categories': categories,
                'source': 'InfraFM',
                'language': 'pt'
            }
            
            return article_data
            
        except Exception as e:
            logger.error(f"Erro ao extrair dados do artigo {article_url}: {str(e)}")
            return None
    
    def run(self, limit=None):
        """Executa o scraper completo"""
        all_articles = []
        
        # Coletar links de artigos
        article_links = self.get_article_links(self.content_index_url)
        
        # Limitar o número de artigos se necessário
        if limit and len(article_links) > limit:
            article_links = article_links[:limit]
        
        # Extrair dados de cada artigo
        for article_url in article_links:
            article_data = self.scrape_article(article_url)
            
            if article_data:
                # Salvar artigo em arquivo
                save_article(article_data)
                all_articles.append(article_data)
            
            # Pausa para evitar sobrecarga no servidor
            time.sleep(1)
            
            # Verificar se atingiu o limite
            if limit and len(all_articles) >= limit:
                break
        
        logger.info(f"Coletados {len(all_articles)} artigos da InfraFM")
        return all_articles