
import requests
from bs4 import BeautifulSoup
import logging
from datetime import datetime
from src.utils.helpers import clean_text, save_article

logger = logging.getLogger(__name__)

class AbrafacScraper:
    def __init__(self):
        self.base_url = "https://abrafac.org.br/artigos-publicados/"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
    
    def get_article_links(self, pages=5):
        """Coleta links de artigos das primeiras 'pages' páginas"""
        all_links = []
        
        for page in range(1, pages + 1):
            url = f"{self.base_url}page/{page}/" if page > 1 else self.base_url
            try:
                response = requests.get(url, headers=self.headers)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.text, 'html.parser')
                articles = soup.select('article.post')
                
                for article in articles:
                    link_tag = article.select_one('h2.entry-title a')
                    if link_tag and link_tag.get('href'):
                        all_links.append({
                            'url': link_tag['href'],
                            'title': link_tag.text.strip()
                        })
                
                logger.info(f"Coletados {len(articles)} artigos da página {page}")
            except Exception as e:
                logger.error(f"Erro ao coletar links da página {page}: {str(e)}")
        
        return all_links
    
    def scrape_article(self, article_info):
        """Extrai o conteúdo de um artigo específico"""
        try:
            response = requests.get(article_info['url'], headers=self.headers)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extrair data
            date_tag = soup.select_one('time.entry-date')
            date = datetime.now().strftime("%Y-%m-%d")
            if date_tag:
                date_str = date_tag.text.strip()
                try:
                    # Converter formato de data brasileiro para ISO
                    date_parts = date_str.split('/')
                    if len(date_parts) == 3:
                        date = f"{date_parts[2]}-{date_parts[1]}-{date_parts[0]}"
                except:
                    pass
            
            # Extrair conteúdo
            content_div = soup.select_one('div.entry-content')
            content = ""
            if content_div:
                # Remover elementos indesejados
                for unwanted in content_div.select('div.sharedaddy, div.jp-relatedposts'):
                    unwanted.decompose()
                
                content = content_div.get_text(separator='\n').strip()
                content = clean_text(content)
            
            # Extrair autor
            author_tag = soup.select_one('span.author a')
            author = author_tag.text.strip() if author_tag else "Desconhecido"
            
            # Extrair categorias/tags
            categories = []
            for cat_tag in soup.select('span.cat-links a'):
                categories.append(cat_tag.text.strip())
            
            article_data = {
                'title': article_info['title'],
                'url': article_info['url'],
                'date': date,
                'author': author,
                'content': content,
                'categories': categories,
                'source': 'ABRAFAC',
                'language': 'pt'
            }
            
            return article_data
            
        except Exception as e:
            logger.error(f"Erro ao extrair artigo {article_info['url']}: {str(e)}")
            return None
    
    def run(self, limit=None):
        """Executa o scraper completo"""
        articles_links = self.get_article_links()
        
        if limit:
            articles_links = articles_links[:limit]
        
        results = []
        for article_info in articles_links:
            article_data = self.scrape_article(article_info)
            if article_data:
                save_article(article_data)
                results.append(article_data)
        
        return results