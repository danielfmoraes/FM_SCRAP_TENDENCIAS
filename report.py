import os
import sys
import argparse
import logging
import pandas as pd
import json
from datetime import datetime
import matplotlib.pyplot as plt
import seaborn as sns
from wordcloud import WordCloud
from collections import Counter
from src.utils.helpers import ensure_dir, setup_logging

# Configurar variável de ambiente para evitar erros Qt
os.environ['QT_QPA_PLATFORM'] = 'xcb'

def parse_arguments():
    """Analisa os argumentos da linha de comando"""
    parser = argparse.ArgumentParser(description='Geração de relatórios de tendências em Facility Management')
    
    parser.add_argument('--input', type=str, default='data/processed/articles_processed.csv',
                        help='Caminho para o arquivo CSV de dados processados')
    
    parser.add_argument('--output', type=str, default='data/processed/report.html',
                        help='Caminho para o arquivo de saída do relatório')
    
    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                        default='INFO', help='Nível de logging')
    
    return parser.parse_args()

def generate_report(df, output_path):
    """Gera um relatório HTML com as tendências identificadas"""
    logger = logging.getLogger(__name__)
    logger.info("Gerando relatório de tendências...")
    
    # Garantir que o diretório de saída exista
    output_dir = os.path.dirname(output_path)
    ensure_dir(output_dir)
    
    # Configurar estilo das visualizações
    plt.style.use('ggplot')
    
    # Criar HTML básico
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Tendências em Facility Management</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; }}
            h1, h2, h3 {{ color: #2c3e50; }}
            .container {{ max-width: 1200px; margin: 0 auto; }}
            .section {{ margin-bottom: 40px; }}
            .chart {{ margin: 20px 0; }}
            table {{ border-collapse: collapse; width: 100%; }}
            th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
            th {{ background-color: #f2f2f2; }}
            tr:nth-child(even) {{ background-color: #f9f9f9; }}
            .alert {{ background-color: #f8d7da; color: #721c24; padding: 10px; border-radius: 5px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Tendências em Facility Management</h1>
            <p>Relatório gerado em {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>
            
            <div class="section">
                <h2>Visão Geral</h2>
                <p>Total de artigos analisados: {len(df)}</p>
    """
    
    # Adicionar resumo por fonte
    source_counts = df['source'].value_counts()
    html += """
                <h3>Artigos por Fonte</h3>
                <table>
                    <tr>
                        <th>Fonte</th>
                        <th>Número de Artigos</th>
                    </tr>
    """
    
    for source, count in source_counts.items():
        html += f"""
                    <tr>
                        <td>{source}</td>
                        <td>{count}</td>
                    </tr>
        """
    
    html += """
                </table>
    """
    
    # Gráfico de distribuição por fonte
    plt.figure(figsize=(10, 6))
    source_counts.plot(kind='bar')
    plt.title('Número de Artigos por Fonte')
    plt.xlabel('Fonte')
    plt.ylabel('Número de Artigos')
    plt.tight_layout()
    
    # Salvar gráfico como imagem
    source_chart_path = 'data/processed/source_chart.png'
    plt.savefig(source_chart_path)
    plt.close()
    
    html += f"""
                <div class="chart">
                    <img src="{os.path.relpath(source_chart_path, os.path.dirname(output_path))}" alt="Artigos por Fonte" style="max-width: 100%;">
                </div>
            </div>
    """
    
    # Análise de categorias
    html += """
            <div class="section">
                <h2>Categorias Identificadas</h2>
    """
    
    # Contar ocorrências de cada categoria
    category_counts = Counter()
    for cats in df['categories']:
        for cat in cats:
            category_counts[cat] += 1
    
    # Tabela de categorias
    html += """
                <table>
                    <tr>
                        <th>Categoria</th>
                        <th>Número de Artigos</th>
                    </tr>
    """
    
    for category, count in category_counts.most_common():
        html += f"""
                    <tr>
                        <td>{category}</td>
                        <td>{count}</td>
                    </tr>
        """
    
    html += """
                </table>
    """
    
    # Gráfico de distribuição por categoria
    plt.figure(figsize=(12, 6))
    category_df = pd.DataFrame(list(category_counts.items()), columns=['Categoria', 'Contagem'])
    category_df = category_df.sort_values('Contagem', ascending=False)
    
    plt.bar(category_df['Categoria'], category_df['Contagem'])
    plt.title('Distribuição de Categorias nos Artigos')
    plt.xlabel('Categoria')
    plt.ylabel('Número de Artigos')
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    
    # Salvar gráfico como imagem
    category_chart_path = 'data/processed/category_chart.png'
    plt.savefig(category_chart_path)
    plt.close()
    
    html += f"""
                <div class="chart">
                    <img src="{os.path.relpath(category_chart_path, os.path.dirname(output_path))}" alt="Distribuição de Categorias" style="max-width: 100%;">
                </div>
            </div>
    """
    
    # Nuvem de palavras
    html += """
            <div class="section">
                <h2>Palavras-chave Mais Frequentes</h2>
    """
    
    # Extrair todas as palavras-chave
    all_keywords = []
    for keywords in df['keywords']:
        all_keywords.extend(keywords)
    
    # Criar texto para nuvem de palavras
    keyword_text = ' '.join(all_keywords)
    
    # Verificar se há palavras-chave antes de gerar a nuvem
    if keyword_text.strip():
        # Gerar nuvem de palavras
        wordcloud = WordCloud(width=800, height=400, background_color='white').generate(keyword_text)
        
        plt.figure(figsize=(10, 5))
        plt.imshow(wordcloud, interpolation='bilinear')
        plt.axis('off')
        
        # Salvar nuvem de palavras como imagem
        wordcloud_path = 'data/processed/wordcloud.png'
        plt.savefig(wordcloud_path)
        plt.close()
        
        html += f"""
                    <div class="chart">
                        <img src="{os.path.relpath(wordcloud_path, os.path.dirname(output_path))}" alt="Nuvem de Palavras-chave" style="max-width: 100%;">
                    </div>
                </div>
        """
    else:
        # Se não houver palavras-chave, exibir uma mensagem
        html += """
                    <div class="alert">
                        <p>Não foi possível gerar a nuvem de palavras-chave porque nenhuma palavra-chave foi encontrada nos artigos.</p>
                    </div>
                </div>
        """
    
    # Artigos mais recentes por categoria
    html += """
            <div class="section">
                <h2>Artigos Recentes por Categoria</h2>
    """
    
    # Converter categorias de lista para string para facilitar filtragem
    df['categories_str'] = df['categories'].apply(lambda x: ', '.join(x) if isinstance(x, list) else '')
    
    for category in category_counts.keys():
        category_articles = df[df['categories_str'].str.contains(category)].sort_values('date', ascending=False).head(5)
        
        if len(category_articles) > 0:
            html += f"""
                <h3>{category.capitalize()}</h3>
                <table>
                    <tr>
                        <th>Título</th>
                        <th>Fonte</th>
                        <th>Data</th>
                    </tr>
            """
            
            for _, article in category_articles.iterrows():
                title = article['title']
                source = article['source']
                date = article['date'] if pd.notna(article['date']) else 'N/A'
                url = article['url'] if pd.notna(article['url']) else '#'
                
                html += f"""
                    <tr>
                        <td><a href="{url}" target="_blank">{title}</a></td>
                        <td>{source}</td>
                        <td>{date}</td>
                    </tr>
                """
            
            html += """
                </table>
            """
    
    html += """
            </div>
        </div>
    </body>
    </html>
    """
    
    # Salvar HTML
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    
    logger.info(f"Relatório salvo em {output_path}")
    return output_path

def main():
    """Função principal do programa"""
    # Configurar argumentos e logging
    args = parse_arguments()
    setup_logging(getattr(logging, args.log_level))
    
    logger = logging.getLogger(__name__)
    logger.info("Iniciando geração de relatório de tendências em Facility Management")
    
    # Carregar dados processados
    input_path = args.input
    if not os.path.exists(input_path):
        logger.error(f"Arquivo de entrada não encontrado: {input_path}")
        print(f"Erro: Arquivo de entrada não encontrado: {input_path}")
        sys.exit(1)
    
    logger.info(f"Carregando dados de {input_path}")
    
    # Determinar o formato do arquivo de entrada
    if input_path.endswith('.csv'):
        df = pd.read_csv(input_path)
    elif input_path.endswith('.json'):
        df = pd.read_json(input_path)
    else:
        logger.error(f"Formato de arquivo não suportado: {input_path}")
        print(f"Erro: Formato de arquivo não suportado: {input_path}")
        sys.exit(1)
    
    # Converter strings de lista para listas reais
    if 'categories' in df.columns and isinstance(df['categories'].iloc[0], str):
        df['categories'] = df['categories'].apply(lambda x: eval(x) if isinstance(x, str) else x)
    
    if 'keywords' in df.columns and isinstance(df['keywords'].iloc[0], str):
        df['keywords'] = df['keywords'].apply(lambda x: eval(x) if isinstance(x, str) else x)
    
    logger.info(f"Dados carregados: {len(df)} artigos")
    
    # Gerar relatório
    output_path = generate_report(df, args.output)
    
    logger.info("Geração de relatório concluída com sucesso")
    print(f"Relatório gerado com sucesso em: {output_path}")

if __name__ == "__main__":
    main()