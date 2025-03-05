import os
import sys
import argparse
import logging
import pandas as pd
import json
from datetime import datetime
from src.utils.helpers import ensure_dir, setup_logging
from src.processors import TextProcessor, translate_text, categorize_article

# Configurar variável de ambiente para evitar erros Qt
os.environ['QT_QPA_PLATFORM'] = 'xcb'

def parse_arguments():
    """Analisa os argumentos da linha de comando"""
    parser = argparse.ArgumentParser(description='Coleta de dados em Facility Management')
    
    parser.add_argument('--sources', nargs='+', choices=['abrafac', 'infrafm', 'ifma', 'google_scholar', 'all'],
                        default=['all'], help='Fontes para coleta de dados')

    parser.add_argument('--limit', type=int, default=None,
                        help='Limite de artigos por fonte')
    
    parser.add_argument('--translate', action='store_true',
                        help='Traduzir conteúdo não português para português')
    
    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                        default='INFO', help='Nível de logging')
    
    return parser.parse_args()

def collect_data(sources, limit=None):
    """Coleta dados das fontes especificadas"""
    logger = logging.getLogger(__name__)
    all_articles = []
    
    # Garantir que os diretórios de dados existam
    ensure_dir('data/raw')
    ensure_dir('data/processed')
    
    # Importar scrapers aqui para evitar importação circular
    from src.scrapers import AbrafacScraper, InfraFMScraper, IfmaScraper, GoogleScholarScraper
    
    # Coletar da ABRAFAC
    if 'all' in sources or 'abrafac' in sources:
        logger.info("Coletando dados da ABRAFAC...")
        scraper = AbrafacScraper()
        articles = scraper.run(limit=limit)
        logger.info(f"Coletados {len(articles)} artigos da ABRAFAC")
        all_articles.extend(articles)
    
    # Coletar da InfraFM
    if 'all' in sources or 'infrafm' in sources:
        logger.info("Coletando dados da InfraFM...")
        scraper = InfraFMScraper()
        articles = scraper.run(limit=limit)
        logger.info(f"Coletados {len(articles)} artigos da InfraFM")
        all_articles.extend(articles)
    
    # Coletar do IFMA
    if 'all' in sources or 'ifma' in sources:
        logger.info("Coletando dados do IFMA Blog...")
        scraper = IfmaScraper()
        articles = scraper.run(limit=limit)
        logger.info(f"Coletados {len(articles)} artigos do IFMA Blog")
        all_articles.extend(articles)
    
    # Coletar do Google Scholar
    if 'all' in sources or 'google_scholar' in sources:
        logger.info("Coletando dados do Google Scholar...")
        scraper = GoogleScholarScraper(headless=True)
        articles = scraper.run(limit=limit)
        logger.info(f"Coletados {len(articles)} artigos do Google Scholar")
        all_articles.extend(articles)
    
    return all_articles

def process_data(articles, translate_non_pt=False):
    """Processa os dados coletados"""
    logger = logging.getLogger(__name__)
    logger.info(f"Processando {len(articles)} artigos...")
    
    # Inicializar processador de texto
    text_processor = TextProcessor()
    
    # Converter para DataFrame para facilitar o processamento
    df = pd.DataFrame(articles)
    
    # Aplicar limpeza de texto
    if 'content' in df.columns:
        df['clean_content'] = df['content'].fillna('').apply(text_processor.clean_text)
    
    if 'abstract' in df.columns:
        df['clean_abstract'] = df['abstract'].fillna('').apply(text_processor.clean_text)
    
    df['clean_title'] = df['title'].fillna('').apply(text_processor.clean_text)
    
    # Traduzir conteúdo não português se solicitado
    if translate_non_pt:
        logger.info("Traduzindo conteúdo não português...")
        non_pt_count = 0
        
        for idx, row in df[df['language'] != 'pt'].iterrows():
            try:
                # Traduzir título
                if pd.notna(row['clean_title']):
                    translated_title = translate_text(row['clean_title'], target_lang='pt')
                    df.at[idx, 'translated_title'] = translated_title
                
                # Traduzir resumo ou conteúdo
                if 'clean_abstract' in df.columns and pd.notna(row['clean_abstract']):
                    translated_text = translate_text(row['clean_abstract'], target_lang='pt')
                    df.at[idx, 'translated_abstract'] = translated_text
                elif 'clean_content' in df.columns and pd.notna(row['clean_content']):
                    # Traduzir apenas os primeiros 1000 caracteres para economizar recursos
                    text_to_translate = row['clean_content'][:1000]
                    translated_text = translate_text(text_to_translate, target_lang='pt')
                    df.at[idx, 'translated_content'] = translated_text
                
                non_pt_count += 1
                if non_pt_count % 10 == 0:
                    logger.info(f"Traduzidos {non_pt_count} artigos não portugueses")
                    
            except Exception as e:
                logger.error(f"Erro ao traduzir artigo {idx}: {str(e)}")
    
    # Extrair palavras-chave
    logger.info("Extraindo palavras-chave...")
    df['keywords'] = df.apply(
        lambda row: text_processor.extract_keywords(
            row['clean_content'] if 'clean_content' in df.columns and pd.notna(row['clean_content']) 
            else row['clean_abstract'] if 'clean_abstract' in df.columns and pd.notna(row['clean_abstract'])
            else row['clean_title']
        ),
        axis=1
    )
    
    # Categorizar artigos
    logger.info("Categorizando artigos...")
    fm_categories = {
        'tecnologia': ['iot', 'internet das coisas', 'automação', 'digital', 'software', 'tecnologia', 'app', 'aplicativo', 'bim', 'inteligente', 'smart', 'ai', 'ia', 'inteligência artificial'],
        'sustentabilidade': ['sustentável', 'sustentabilidade', 'verde', 'ambiental', 'energia', 'eficiência energética', 'carbono', 'renovável', 'esg', 'leed'],
        'gestão_espacial': ['espaço', 'layout', 'ocupação', 'workplace', 'ambiente de trabalho', 'escritório', 'flexível', 'coworking'],
        'manutenção': ['manutenção', 'preventiva', 'preditiva', 'corretiva', 'equipamento', 'falha', 'reparo', 'vida útil'],
        'saúde_bem_estar': ['saúde', 'bem-estar', 'ergonomia', 'conforto', 'qualidade do ar', 'covid', 'pandemia', 'segurança'],
        'gestão_contratos': ['contrato', 'terceirização', 'outsourcing', 'fornecedor', 'sla', 'kpi', 'desempenho', 'indicador']
    }
    
    df['categories'] = df.apply(
        lambda row: categorize_article(
            text=row['clean_content'] if 'clean_content' in df.columns and pd.notna(row['clean_content']) 
            else row['clean_abstract'] if 'clean_abstract' in df.columns and pd.notna(row['clean_abstract'])
            else row['clean_title'],
            keywords=row['keywords'],
            category_dict=fm_categories
        ),
        axis=1
    )
    
    # Salvar dados processados
    processed_csv_path = 'data/processed/articles_processed.csv'
    df.to_csv(processed_csv_path, index=False)
    logger.info(f"Dados processados salvos em {processed_csv_path}")
    
    processed_json_path = 'data/processed/articles_processed.json'
    df.to_json(processed_json_path, orient='records', force_ascii=False, indent=4)
    logger.info(f"Dados processados salvos em {processed_json_path}")
    
    return df

def main():
    """Função principal do programa"""
    # Importações necessárias
    from src.utils.helpers import load_articles
    
    # Configurar argumentos e logging
    args = parse_arguments()
    setup_logging(getattr(logging, args.log_level))
    
    logger = logging.getLogger(__name__)
    logger.info("Iniciando coleta e processamento de dados em Facility Management")
    
    # Coletar dados
    if args.sources:
        logger.info(f"Coletando dados das fontes: {', '.join(args.sources)}")
        articles = collect_data(args.sources, args.limit)
        logger.info(f"Coletados {len(articles)} artigos no total")
        
        # Processar dados
        df = process_data(articles, args.translate)
    
    logger.info("Coleta e processamento concluídos com sucesso")
    print("Processamento concluído! Verifique a pasta 'data' para os resultados.")

if __name__ == "__main__":
    main()