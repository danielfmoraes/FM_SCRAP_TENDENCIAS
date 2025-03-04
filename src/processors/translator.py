import requests
import os
import logging
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

logger = logging.getLogger(__name__)

def translate_text(text, source_lang='auto', target_lang='pt'):
    """
    Traduz texto usando a API do Google Translate.
    
    Args:
        text (str): Texto a ser traduzido
        source_lang (str): Idioma de origem (padrão: auto-detecção)
        target_lang (str): Idioma de destino (padrão: português)
        
    Returns:
        str: Texto traduzido
    """
    if not text:
        return ""
    
    # Verificar se há uma chave de API configurada
    api_key = os.getenv('GOOGLE_TRANSLATE_API_KEY')
    
    if api_key:
        # Usar a API oficial do Google Translate (requer chave)
        try:
            url = "https://translation.googleapis.com/language/translate/v2"
            params = {
                'q': text,
                'target': target_lang,
                'key': api_key
            }
            
            if source_lang != 'auto':
                params['source'] = source_lang
                
            response = requests.post(url, params=params)
            response.raise_for_status()
            
            result = response.json()
            translated_text = result['data']['translations'][0]['translatedText']
            return translated_text
            
        except Exception as e:
            logger.error(f"Erro ao traduzir texto usando API oficial: {str(e)}")
            # Fallback para método alternativo
    
    # Método alternativo (sem API key) - menos confiável e com limites de uso
    try:
        # URL para API não oficial
        url = "https://translate.googleapis.com/translate_a/single"
        params = {
            'client': 'gtx',
            'sl': source_lang,
            'tl': target_lang,
            'dt': 't',
            'q': text
        }
        
        response = requests.get(url, params=params)
        response.raise_for_status()
        
        # Extrair texto traduzido da resposta
        result = response.json()
        translated_text = ''.join([sentence[0] for sentence in result[0] if sentence[0]])
        return translated_text
        
    except Exception as e:
        logger.error(f"Erro ao traduzir texto usando método alternativo: {str(e)}")
        return text  # Retornar texto original em caso de erro