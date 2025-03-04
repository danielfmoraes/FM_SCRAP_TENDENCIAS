import os
import time
import logging
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options as ChromeOptions
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from webdriver_manager.firefox import GeckoDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from src.utils.helpers import clean_text, save_article

logger = logging.getLogger(__name__)

class GoogleScholarScraper:
    def __init__(self, headless=True):
        self.base_url = "https://scholar.google.com/scholar"
        self.headless = headless
        self.driver = self._setup_driver()
    
    def _setup_driver(self):
        """Configura o driver do Selenium com fallback de Chrome para Firefox"""
        logger.info("Tentando configurar Chrome WebDriver...")
        
        # Tentar usar Chrome primeiro
        try:
            options = ChromeOptions()
            if self.headless:
                options.add_argument("--headless")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-gpu")
            options.add_argument("--window-size=1920,1080")
            options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
            
            # Tentar encontrar o binário do Chrome em locais comuns
            chrome_paths = [
                "/usr/bin/google-chrome",
                "/usr/bin/google-chrome-stable",
                "/usr/bin/chromium",
                "/usr/bin/chromium-browser",
                "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",  # macOS
                "C:\Program Files\Google\Chrome\Application\chrome.exe",    # Windows
                "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
            ]
            
            for path in chrome_paths:
                if os.path.exists(path):
                    logger.info(f"Chrome encontrado em: {path}")
                    options.binary_location = path
                    break
            
            service = ChromeService(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options)
            logger.info("Chrome WebDriver configurado com sucesso")
            return driver
        
        except Exception as e:
            logger.warning(f"Falha ao configurar Chrome WebDriver: {str(e)}")
            logger.info("Tentando usar Firefox como alternativa...")
            
            # Fallback para Firefox
            try:
                options = FirefoxOptions()
                if self.headless:
                    options.add_argument("--headless")
                
                service = FirefoxService(GeckoDriverManager().install())
                driver = webdriver.Firefox(service=service, options=options)
                logger.info("Firefox WebDriver configurado com sucesso")
                return driver
                
            except Exception as e:
                logger.error(f"Falha ao configurar Firefox WebDriver: {str(e)}")
                raise Exception("Não foi possível configurar nenhum navegador. Instale Chrome ou Firefox e tente novamente.")
    
    def search_articles(self, query, language="pt", start_year=2020, pages=3):
        """Busca artigos no Google Scholar"""
        all_articles = []
        
        # Adicionar termos de busca específicos para FM
        fm_query = f"{query} \"facility management\" OR \"gestão de facilidades\" OR \"gestão predial\""
        
        # Adicionar filtro de data
        if start_year:
            fm_query += f" after:{start_year}"
        
        # Adicionar filtro de idioma
        lang_param = ""
        if language == "pt":
            lang_param = "&hl=pt-BR&lr=lang_pt"
        elif language == "en":
            lang_param = "&hl=en&lr=lang_en"
        
        for page in range(pages):
            start_index = page * 10
            search_url = f"{self.base_url}?q={fm_query}&start={start_index}{lang_param}"
            
            try:
                self.driver.get(search_url)
                time.sleep(3)  # Esperar carregamento para evitar detecção de bot
                
                # Esperar pelos resultados
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div.gs_ri"))
                )
                
                soup = BeautifulSoup(self.driver.page_source, 'html.parser')
                articles = soup.select('div.gs_ri')
                
                for article in articles:
                    title_tag = article.select_one('h3 a')
                    if not title_tag:
                        continue
                    
                    title = title_tag.text.strip()
                    url = title_tag.get('href', '')
                    
                    # Extrair autores e publicação
                    authors_tag = article.select_one('div.gs_a')
                    authors_text = authors_tag.text.strip() if authors_tag else ""
                    
                    # Extrair resumo
                    abstract_tag = article.select_one('div.gs_rs')
                    abstract = abstract_tag.text.strip() if abstract_tag else ""
                    
                    # Extrair ano
                    year = None
                    if authors_text:
                        # Tentar extrair o ano do texto de autores
                        import re
                        year_match = re.search(r'\b(19|20)\d{2}\b', authors_text)
                        if year_match:
                            year = year_match.group(0)
                    
                    article_data = {
                        'title': title,
                        'url': url,
                        'authors': authors_text,
                        'abstract': abstract,
                        'year': year,
                        'source': 'Google Scholar',
                        'language': language
                    }
                    
                    all_articles.append(article_data)
                
                logger.info(f"Coletados {len(articles)} artigos da página {page+1}")
                time.sleep(2)  # Pausa entre páginas para evitar bloqueio
                
            except Exception as e:
                logger.error(f"Erro ao buscar artigos na página {page+1}: {str(e)}")
        
        return all_articles
    
    def run(self, queries=None, limit=None):
        """Executa o scraper completo"""
        if queries is None:
            queries = [
                "tendências facility management",
                "inovação gestão predial",
                "tecnologia facility management",
                "sustentabilidade gestão facilidades",
                "IoT facility management"
            ]
        
        results = []
        try:
            for query in queries:
                articles = self.search_articles(query)
                
                if limit:
                    articles = articles[:limit]
                
                for article in articles:
                    save_article(article)
                    results.append(article)
                
                time.sleep(5)  # Pausa entre consultas
        finally:
            self.driver.quit()
        
        return results