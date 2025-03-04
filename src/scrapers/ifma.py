import requests
import logging
import time
from bs4 import BeautifulSoup
from datetime import datetime
from src.utils.helpers import clean_text, save_article, extract_date

logger = logging.getLogger(__name__)

class IfmaScraper:
    def __init__(self):
        self.base_url = "https://blog.ifma.org/all"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
    
    def get_blog_pages(self, max_pages=5):
        """Obtém as URLs de todas as páginas do blog"""
        page_urls = [self.base_url]
        
        # O IFMA blog usa paginação com parâmetro page
        for page_num in range(2, max_pages + 1):
            page_url = f"{self.base_url}?page={page_num}"
            page_urls.append(page_url)
        
        return page_urls
    
    def get_article_links(self, page_url):
        """Extrai links de artigos de uma página do blog"""
        article_links = []
        
        try:
            response = requests.get(page_url, headers=self.headers)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Os artigos do blog IFMA geralmente estão em elementos com classe 'post-item'
            # ou dentro de elementos <article>
            article_elements = soup.select('.post-item, article, .blog-post')
            
            if not article_elements:
                # Se não encontrar com os seletores específicos, procurar links que parecem ser de artigos
                all_links = soup.select('a[href*="/blog/"]')
                for link in all_links:
                    href = link.get('href')
                    if href and '/blog/' in href and href not in article_links:
                        if not href.endswith('/all') and not 'page=' in href:
                            article_links.append(href)
            else:
                # Extrair links dos elementos de artigo encontrados
                for article in article_elements:
                    link_tag = article.select_one('a')
                    if link_tag and link_tag.get('href'):
                        href = link_tag.get('href')
                        # Garantir que o URL seja absoluto
                        if href.startswith('/'):
                            href = 'https://blog.ifma.org' + href
                        article_links.append(href)
            
            logger.info(f"Encontrados {len(article_links)} links de artigos na página {page_url}")
            
            # Se ainda não encontrou links, imprimir parte do HTML para debug
            if not article_links:
                logger.warning(f"Nenhum link encontrado na página {page_url}. Verificando HTML...")
                # Imprimir alguns links da página para debug
                all_links = soup.select('a')
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
            title_tag = soup.select_one('h1.post-title, h1.entry-title, h1')
            title = title_tag.text.strip() if title_tag else "Sem título"
            
            # Extrair data
            date_tag = soup.select_one('.post-date, .published, time')
            date_str = date_tag.text.strip() if date_tag else None
            date = extract_date(date_str) if date_str else datetime.now()
            
            # Extrair autor
            author_tag = soup.select_one('.post-author, .author, .byline')
            author = author_tag.text.strip() if author_tag else "IFMA"
            
            # Extrair conteúdo
            content_tag = soup.select_one('.post-body, .entry-content, article')
            
            if content_tag:
                # Remover elementos indesejados
                for unwanted in content_tag.select('script, style, iframe'):
                    unwanted.decompose()
                
                content = content_tag.text.strip()
            else:
                content = ""
            
            # Extrair categorias/tags
            categories = []
            category_tags = soup.select('.post-tags a, .tags a, .categories a')
            
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
                'source': 'IFMA Blog',
                'language': 'en'  # O blog da IFMA é em inglês
            }
            
            return article_data
            
        except Exception as e:
            logger.error(f"Erro ao extrair dados do artigo {article_url}: {str(e)}")
            return None
    
    def run(self, limit=None):
        """Executa o scraper completo"""
        all_articles = []
        
        # Obter URLs das páginas do blog
        page_urls = self.get_blog_pages()
        
        # Limitar o número de páginas se necessário
        if limit and limit < len(page_urls):
            page_urls = page_urls[:limit]
        
        # Coletar links de artigos de cada página
        all_article_links = []
        for page_url in page_urls:
            article_links = self.get_article_links(page_url)
            all_article_links.extend(article_links)
            
            # Pausa para evitar sobrecarga no servidor
            time.sleep(2)
            
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
            time.sleep(2)
            
            # Verificar se atingiu o limite
            if limit and len(all_articles) >= limit:
                break
        
        logger.info(f"Coletados {len(all_articles)} artigos do IFMA Blog")
        return all_articles