parser.add_argument('--sources', nargs='+', choices=['abrafac', 'infrafm', 'google_scholar', 'all'],
                    default=['all'], help='Fontes para coleta de dados')

parser.add_argument('--limit', type=int, default=None,
                    help='Limite de artigos por fonte')

parser.add_argument('--report', action='store_true',
                    help='Gerar relatório de tendências')

parser.add_argument('--translate', action='store_true',
                    help='Traduzir conteúdo não português para português')

parser.add_argument('--output', type=str, default='data/processed/report.html',
                    help='Caminho para o arquivo de saída do relatório')

parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                    default='INFO', help='Nível de logging')

return parser.parse_args()

# Garantir que os diretórios de dados existam
ensure_dir('data/raw')
ensure_dir('data/processed')

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

# Coletar do Google Scholar
if 'all' in sources or 'google_scholar' in sources:
    logger.info("Coletando dados do Google Scholar...")
    scraper = GoogleScholarScraper(headless=True)
    articles = scraper.run(limit=limit)
    logger.info(f"Coletados {len(articles)} artigos do Google Scholar")
    all_articles.extend(articles)

return all_articles

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

# Garantir que o diretório de saída exista
output_dir = os.path.dirname(output_path)
ensure_dir(output_dir)

# Importar bibliotecas para visualização
import matplotlib.pyplot as plt
import seaborn as sns
from wordcloud import WordCloud
from collections import Counter

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
                `<img src="{os.path.relpath(source_chart_path, os.path.dirname(output_path))}" alt="Artigos por Fonte" style="max-width: 100%;">`
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
                `<img src="{os.path.relpath(category_chart_path, os.path.dirname(output_path))}" alt="Distribuição de Categorias" style="max-width: 100%;">`
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
                `<img src="{os.path.relpath(wordcloud_path, os.path.dirname(output_path))}" alt="Nuvem de Palavras-chave" style="max-width: 100%;">`
            </div>
        </div>
"""

# Artigos mais recentes por categoria
html += """
        <div class="section">
            <h2>Artigos Recentes por Categoria</h2>
"""

# Converter categorias de lista para string para facilitar filtragem
df['categories_str'] = df['categories'].apply(lambda x: ', '.join(x))

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
                    <td><a href="{url}" target="_blank">{title}