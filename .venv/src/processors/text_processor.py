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
    tokens = self.token