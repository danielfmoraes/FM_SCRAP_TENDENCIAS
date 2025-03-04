import re
import logging
from collections import Counter

logger = logging.getLogger(__name__)

def categorize_article(text, keywords=None, category_dict=None):
    """
    Categoriza um artigo com base em seu conteúdo e palavras-chave.
    
    Args:
        text (str): Texto do artigo
        keywords (list): Lista de palavras-chave extraídas do artigo
        category_dict (dict): Dicionário de categorias e termos relacionados
        
    Returns:
        list: Lista de categorias atribuídas ao artigo
    """
    if not text:
        return []
    
    # Categorias padrão se nenhuma for fornecida
    if category_dict is None:
        category_dict = {
            'tecnologia': ['iot', 'internet das coisas', 'automação', 'digital', 'software', 'tecnologia', 'app', 'aplicativo', 'bim', 'inteligente', 'smart', 'ai', 'ia', 'inteligência artificial'],
            'sustentabilidade': ['sustentável', 'sustentabilidade', 'verde', 'ambiental', 'energia', 'eficiência energética', 'carbono', 'renovável', 'esg', 'leed'],
            'gestão_espacial': ['espaço', 'layout', 'ocupação', 'workplace', 'ambiente de trabalho', 'escritório', 'flexível', 'coworking'],
            'manutenção': ['manutenção', 'preventiva', 'preditiva', 'corretiva', 'equipamento', 'falha', 'reparo', 'vida útil'],
            'saúde_bem_estar': ['saúde', 'bem-estar', 'ergonomia', 'conforto', 'qualidade do ar', 'covid', 'pandemia', 'segurança'],
            'gestão_contratos': ['contrato', 'terceirização', 'outsourcing', 'fornecedor', 'sla', 'kpi', 'desempenho', 'indicador']
        }
    
    # Normalizar texto para busca
    text_lower = text.lower()
    
    # Contagem de ocorrências de termos por categoria
    category_scores = Counter()
    
    # Verificar ocorrências de termos no texto
    for category, terms in category_dict.items():
        for term in terms:
            # Contar ocorrências do termo no texto
            count = len(re.findall(r'\b' + re.escape(term) + r'\b', text_lower))
            if count > 0:
                category_scores[category] += count
    
    # Adicionar pontuação com base nas palavras-chave
    if keywords:
        for keyword in keywords:
            keyword_lower = keyword.lower()
            for category, terms in category_dict.items():
                if any(term in keyword_lower for term in terms):
                    category_scores[category] += 2  # Peso maior para palavras-chave
    
    # Selecionar categorias com pontuação acima do limiar
    threshold = 1  # Pelo menos uma ocorrência
    categories = [category for category, score in category_scores.items() if score >= threshold]
    
    # Se nenhuma categoria for atribuída, usar 'outros'
    if not categories:
        categories = ['outros']
    
    return categories