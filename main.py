import argparse
import os
import pandas as pd
import logging
import matplotlib.pyplot as plt
os.environ['QT_QPA_PLATFORM'] = 'xcb'
from wordcloud import WordCloud
from src.scrapers import AbrafacScraper, InfraFMScraper, GoogleScholarScraper, IfmaScraper
from src.utils.helpers import ensure_dir
from src.processors.text_processor import TextProcessor
from src.processors.categorizer import categorize_article


# Configuração do logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuração dos argumentos
parser = argparse.ArgumentParser(description='Coletar e processar artigos sobre facilities.')
parser.add_argument('--sources', nargs='+', choices=['abrafac', 'infrafm', 'ifma', 'google_scholar', 'all'],
                    default=['all'], help='Fontes para coleta de dados')
parser.add_argument('--limit', type=int, default=None, help='Limite de artigos por fonte')
parser.add_argument('--report', action='store_true', help='Gerar relatório de tendências')
parser.add_argument('--translate', action='store_true', help='Traduzir conteúdo não português para português')
parser.add_argument('--output', type=str, default='data/processed/report.html', help='Caminho para o arquivo de saída do relatório')
parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                    default='INFO', help='Nível de logging')
args = parser.parse_args()

# Garantir que os diretórios existam
ensure_dir('data/raw')
ensure_dir('data/processed')

# Coletar artigos
all_articles = []
sources = args.sources
limit = args.limit
translate_non_pt = args.translate

if 'all' in sources or 'abrafac' in sources:
    logger.info("Coletando dados da ABRAFAC...")
    scraper = AbrafacScraper()
    all_articles.extend(scraper.run(limit=limit))

if 'all' in sources or 'infrafm' in sources:
    logger.info("Coletando dados da InfraFM...")
    scraper = InfraFMScraper()
    all_articles.extend(scraper.run(limit=limit))

if 'all' in sources or 'ifma' in sources:
    logger.info("Coletando dados do IFMA Blog...")
    scraper = IfmaScraper()
    all_articles.extend(scraper.run(limit=limit))

if 'all' in sources or 'google_scholar' in sources:
    logger.info("Coletando dados do Google Scholar...")
    scraper = GoogleScholarScraper(headless=True)
    all_articles.extend(scraper.run(limit=limit))

# Processamento de texto
text_processor = TextProcessor()
df = pd.DataFrame(all_articles)

if 'content' in df.columns:
    df['clean_content'] = df['content'].fillna('').apply(text_processor.clean_text)
if 'abstract' in df.columns:
    df['clean_abstract'] = df['abstract'].fillna('').apply(text_processor.clean_text)
df['clean_title'] = df['title'].fillna('').apply(text_processor.clean_text)

# Traduzir se necessário
if translate_non_pt:
    logger.info("Traduzindo conteúdo não português...")
    for idx, row in df[df['language'] != 'pt'].iterrows():
        try:
            if pd.notna(row['clean_title']):
                df.at[idx, 'translated_title'] = translate_text(row['clean_title'], target_lang='pt')
            if 'clean_abstract' in df.columns and pd.notna(row['clean_abstract']):
                df.at[idx, 'translated_abstract'] = translate_text(row['clean_abstract'], target_lang='pt')
            elif 'clean_content' in df.columns and pd.notna(row['clean_content']):
                df.at[idx, 'translated_content'] = translate_text(row['clean_content'][:1000], target_lang='pt')
        except Exception as e:
            logger.error(f"Erro ao traduzir artigo {idx}: {str(e)}")

# Extração de palavras-chave
df['keywords'] = df.apply(lambda row: text_processor.extract_keywords(
    row['clean_content'] if 'clean_content' in df.columns and pd.notna(row['clean_content'])
    else row['clean_abstract'] if 'clean_abstract' in df.columns and pd.notna(row['clean_abstract'])
    else row['clean_title']), axis=1)

# Categorização de artigos
fm_categories = {
    'tecnologia': ['iot', 'automação', 'digital', 'software', 'ai', 'inteligência artificial'],
    'sustentabilidade': ['sustentável', 'energia', 'eficiência energética', 'carbono', 'esg'],
    'gestão_espacial': ['espaço', 'layout', 'ocupação', 'coworking'],
    'manutenção': ['manutenção', 'preventiva', 'preditiva', 'falha', 'reparo'],
    'saúde_bem_estar': ['saúde', 'ergonomia', 'qualidade do ar', 'segurança'],
    'gestão_contratos': ['contrato', 'terceirização', 'fornecedor', 'kpi']
}
df['categories'] = df.apply(lambda row: categorize_article(
    row['clean_content'] if 'clean_content' in df.columns and pd.notna(row['clean_content'])
    else row['clean_abstract'] if 'clean_abstract' in df.columns and pd.notna(row['clean_abstract'])
    else row['clean_title'],
    row['keywords'], fm_categories), axis=1)

# Salvar dados
df.to_csv('data/processed/articles_processed.csv', index=False)
df.to_json('data/processed/articles_processed.json', orient='records', force_ascii=False, indent=4)

# Gerar nuvem de palavras-chave
html = """
        <div class="section">
            <h2>Palavras-chave Mais Frequentes</h2>
"""
all_keywords = []
for keywords in df['keywords']:
    all_keywords.extend(keywords)
keyword_text = ' '.join(all_keywords)
if keyword_text.strip():
    wordcloud = WordCloud(width=800, height=400, background_color='white').generate(keyword_text)
    plt.figure(figsize=(10, 5))
    plt.imshow(wordcloud, interpolation='bilinear')
    plt.axis('off')
    wordcloud_path = 'data/processed/wordcloud.png'
    plt.savefig(wordcloud_path)
    plt.close()
    html += f"""
                <div class="chart">
                    <img src="{os.path.relpath(wordcloud_path, os.path.dirname(args.output))}" alt="Nuvem de Palavras-chave" style="max-width: 100%;">
                </div>
            </div>
    """
else:
    html += """
                <div class="alert">
                    <p>Não foi possível gerar a nuvem de palavras-chave porque nenhuma palavra-chave foi encontrada.</p>
                </div>
            </div>
    """

logger.info("Processamento concluído!")
