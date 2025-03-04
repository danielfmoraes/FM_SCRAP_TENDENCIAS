import re
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from nltk.stem import RSLPStemmer
import string
import unidecode

class TextProcessor:
    def __init__(self):
        # Baixar recursos do NLTK se necessário
        try:
            nltk.data.find('tokenizers/punkt')
            nltk.data.find('corpora/stopwords')
        except LookupError:
            nltk.download('punkt')
            nltk.download('stopwords')
            nltk.download('rslp')
        
        self.stop_words = set(stopwords.words('portuguese'))
        self.stemmer = RSLPStemmer()
    
    def clean_text(self, text):
        """Limpa e normaliza o texto"""
        if not text or not isinstance(text, str):
            return ""
        
        # Converter para minúsculas
        text = text.lower()
        
        # Remover URLs
        text = re.sub(r'https?://\S+|www\.\S+', '', text)
        
        # Remover emails
        text = re.sub(r'\S+@\S+', '', text)
        
        # Remover números
        text = re.sub(r'\d+', '', text)
        
        # Remover pontuação
        text = text.translate(str.maketrans('', '', string.punctuation))
        
        # Remover espaços extras
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Remover acentos
        text = unidecode.unidecode(text)
        
        return text
    
    def tokenize(self, text):
        """Tokeniza o texto em palavras"""
        return word_tokenize(text, language='portuguese')
    
    def remove_stopwords(self, tokens):
        """Remove stopwords dos tokens"""
        return [token for token in tokens if token not in self.stop_words]
    
    def stem_tokens(self, tokens):
        """Aplica stemming aos tokens"""
        return [self.stemmer.stem(token) for token in tokens]
    
    def preprocess_text(self, text):
        """Aplica todo o pipeline de pré-processamento"""
        clean = self.clean_text(text)
        tokens = self.tokenize(clean)
        tokens = self.remove_stopwords(tokens)
        tokens = self.stem_tokens(tokens)
        return tokens
    
    def extract_keywords(self, text, top_n=10):
        """Extrai as palavras-chave mais relevantes do texto"""
        if not text or not isinstance(text, str):
            return []
        
        # Pré-processar o texto
        tokens = self.preprocess_text(text)
        
        # Contar frequência das palavras
        word_freq = {}
        for token in tokens:
            if len(token) > 2:  # Ignorar palavras muito curtas
                if token in word_freq:
                    word_freq[token] += 1
                else:
                    word_freq[token] = 1
        
        # Ordenar por frequência
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        
        # Retornar as top_n palavras mais frequentes
        return [word for word, freq in sorted_words[:top_n]]