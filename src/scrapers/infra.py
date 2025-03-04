import requests
from bs4 import BeautifulSoup
import logging
from datetime import datetime
from src.utils.helpers import clean_text, save_article

logger = logging.getLogger(__name__)

class InfraFMScraper:
    def __init__(self):
        self.base_url = "https://www.infrafm.com.br/Textos/"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
    
    def get_article_links(self, categories=None):
        """Coleta links de artigos das categorias especificadas"""
        if categories is None:
            # Categorias relacionadas a FM
            categories = [3, 23992]  # Exemplo: 3 = Artigos, 23992 = IoT
        
        all_links = []
        
        for category in categories:
            url = f"{self.base_url}{category}/"
            try:
                response = requests.get(url, headers=self.headers)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.text, 'html.parser')
                articles = soup.select('div.noticia')
                
                for article in articles:
                    link_tag = article.select_one('a')
                    if link_tag and link_tag.get('href'):
                        title_tag = article.select_one('h2')
                        title = title_tag.text.strip() if title_tag else "Sem título"
                        
                        all_links.append({
                            'url': link_tag['href'] if link_tag['href'].startswith('http') else f"https://www.infrafm.com.br{link_tag['href']}",
                            'title': title
                        })
                
                logger.info(f"Coletados {len(articles)} artigos da categoria {category}")
            except Exception as e:
                logger.error(f"Erro ao coletar links da categoria {category}: {str(e)}")
        
        return all_links
    
    def scrape_article(self, article_info):
        """Extrai o conteúdo de um artigo específico"""
        try:
            response = requests.get(article_info['url'], headers=self.headers)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extrair data
            date_tag = soup.select_one('span.data')
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
            content_div = soup.select_one('div.texto')
            content = ""
            if content_div:
                content = content_div.get_text(separator='\n').strip()
                content = clean_text(content)
            
            # Extrair autor
            author_tag = soup.select_one('span.autor')
            author = author_tag.text.strip() if author_tag else "Desconhecido"
            
            # Extrair categorias/tags
            categories = []
            for cat_tag in soup.select('div.categorias a'):
                categories.append(cat_tag.text.strip())
            
            article_data = {
                'title': article_info['title'],
                'url': article_info['url'],
                'date': date,
                'author': author,
                'content': content,
                'categories': categories,
                'source': 'InfraFM',
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
