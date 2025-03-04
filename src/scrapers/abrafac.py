import requests
import logging
import time
from bs4 import BeautifulSoup
from datetime import datetime
from src.utils.helpers import clean_text, save_article, extract_date

logger = logging.getLogger(__name__)

class AbrafacScraper:
    def __init__(self):
        self.base_url = "https://abrafac.org.br/publicacoes"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
    
    def get_publication_pages(self, max_pages=15):
        """Obtém as URLs de todas as páginas de publicações"""
        page_urls = []
        
        for page_num in range(1, max_pages + 1):
            if page_num == 1:
                page_url = self.base_url
            else:
                page_url = f"{self.base_url}/page/{page_num}/"
            
            page_urls.append(page_url)
        
        return page_urls
    
    def get_article_links(self, page_url):
        """Extrai links de artigos de uma página de publicações"""
        article_links = []
        
        try:
            response = requests.get(page_url, headers=self.headers)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Focar especificamente nos elementos de artigo com a estrutura correta
            article_elements = soup.select('article.tstk-ele-blog, article.tstk-ele')
            
            for article in article_elements:
                # Procurar o link dentro do título do post
                link_tag = article.select_one('h3.tstk-post-title a, div.post-item a[data-wpel-link="internal"]')
                
                if link_tag and link_tag.get('href'):
                    href = link_tag.get('href')
                    if 'abrafac.org.br' in href and href not in article_links:
                        article_links.append(href)
            
            # Se não encontrar com o seletor específico, tentar uma abordagem mais direta
            if not article_links:
                # Procurar links com o atributo data-wpel-link="internal"
                internal_links = soup.select('a[data-wpel-link="internal"]')
                
                for link in internal_links:
                    href = link.get('href')
                    if href and 'abrafac.org.br' in href and href not in article_links:
                        # Filtrar apenas URLs que parecem ser artigos
                        if '/page/' not in href and '/tag/' not in href and '/category/' not in href:
                            article_links.append(href)
            
            logger.info(f"Encontrados {len(article_links)} links de artigos na página {page_url}")
            
            # Se ainda não encontrou links, imprimir parte do HTML para debug
            if not article_links:
                logger.warning(f"Nenhum link encontrado na página {page_url}. Verificando HTML...")
                # Imprimir alguns links da página para debug
                all_links = soup.select('a[data-wpel-link="internal"]')
                for i, link in enumerate(all_links[:10]):
                    href = link.get('href')
                    text = link.text.strip()
                    logger.warning(f"Link {i+1}: {text} -> {href}")
            
        except Exception as e:
            logger.error(f"Erro ao coletar links da página {page_url}: {str(e)}")
        
        return article_links
    
    def scrape_article(self, article_url):
        """Extrai dados de um artigo específico"""
        try:
            response = requests.get(article_url, headers=self.headers)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extrair título
            title_tag = soup.select_one('h1.entry-title') or soup.select_one('h1') or soup.select_one('h2.entry-title')
            title = title_tag.text.strip() if title_tag else "Sem título"
            
            # Extrair data
            date_tag = soup.select_one('time.entry-date') or soup.select_one('span.posted-on time') or soup.select_one('span.posted-on')
            date_str = date_tag.text.strip() if date_tag else None
            date = extract_date(date_str) if date_str else datetime.now()
            
            # Extrair autor
            author_tag = soup.select_one('span.author') or soup.select_one('a.url.fn.n')
            author = author_tag.text.strip() if author_tag else "ABRAFAC"
            
            # Extrair conteúdo
            content_tag = soup.select_one('div.entry-content') or soup.select_one('div.post-content')
            
            if content_tag:
                # Remover elementos indesejados
                for unwanted in content_tag.select('script, style, iframe, .sharedaddy, .jp-relatedposts'):
                    unwanted.decompose()
                
                content = content_tag.text.strip()
            else:
                content = ""
            
            # Extrair categorias/tags
            categories = []
            category_tags = soup.select('span.cat-links a') or soup.select('footer.entry-footer a[rel="category tag"]')
            
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
                'source': 'ABRAFAC',
                'language': 'pt'
            }
            
            return article_data
            
        except Exception as e:
            logger.error(f"Erro ao extrair dados do artigo {article_url}: {str(e)}")
            return None
    
    def run(self, limit=None):
        """Executa o scraper completo"""
        all_articles = []
        
        # Obter URLs das páginas de publicações
        page_urls = self.get_publication_pages()
        
        # Limitar o número de páginas se necessário
        if limit:
            page_urls = page_urls[:min(limit, len(page_urls))]
        
        # Coletar links de artigos de cada página
        all_article_links = []
        for page_url in page_urls:
            article_links = self.get_article_links(page_url)
            all_article_links.extend(article_links)
            
            # Pausa para evitar sobrecarga no servidor
            time.sleep(1)
            
            # Verificar se atingiu o limite
            if limit and len(all_article_links) >= limit:
                all_article_links = all_article_links[:limit]
                break
        
        # Extrair dados de cada artigo
        for article_url in all_article_links:
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
        
        logger.info(f"Coletados {len(all_articles)} artigos da ABRAFAC")
        return all_articles