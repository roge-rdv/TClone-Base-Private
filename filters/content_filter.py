import json
import re
from telethon import events
from utils.logger import logger

def safe_text(text):
    """Sanitiza o texto para logging seguro, removendo caracteres problemáticos se necessário."""
    if not text:
        return "[Vazio]"
    try:
        # Primeiro, garantimos que estamos trabalhando com um objeto str
        if isinstance(text, bytes):
            text = text.decode('utf-8')
        
        # Verifica se o texto é válido em UTF-8
        text.encode('utf-8')
        return text
    except UnicodeError:
        # Em caso de erro, tenta uma abordagem mais robusta
        try:
            # Tenta decodificar com erros ignorados
            if isinstance(text, bytes):
                return text.decode('utf-8', errors='replace')
            else:
                # Converte para bytes e de volta para garantir validade
                return text.encode('utf-8', errors='replace').decode('utf-8')
        except:
            return "[Texto com caracteres não suportados]"

async def filter_content(event, config):
    """
    Filtra o conteúdo da mensagem com base nas regras definidas em config.json.
    Retorna o texto filtrado ou None se a mensagem deve ser bloqueada.
    """
    # Obtém o texto da mensagem, garantindo que é uma string Unicode válida
    text = event.raw_text or ""
    
    # Garante que o texto esteja em formato Unicode válido
    if text and isinstance(text, bytes):
        try:
            text = text.decode('utf-8')
        except UnicodeDecodeError:
            text = text.decode('utf-8', errors='replace')
    
    # Log do texto recebido (sanitizado para evitar problemas de codificação)
    logger.info(f"Texto recebido para filtragem: {safe_text(text)}")
    
    # Se o texto estiver vazio, retorna como está
    if not text:
        return text
    
    # Verifica palavras bloqueadas
    blocked_words = config.get('blocked_words', [])
    for word in blocked_words:
        # Garante que a palavra bloqueada está em formato Unicode
        if isinstance(word, bytes):
            word = word.decode('utf-8', errors='replace')
            
        if word.lower() in text.lower():
            return None  # Bloqueia a mensagem
    
    # Aplica substituições
    replacements = config.get('replacements', {})
    # Cria uma cópia do texto original para trabalhar
    filtered_text = text
    
    for original, replacement in replacements.items():
        # Garante que as strings de substituição estão em formato Unicode
        if isinstance(original, bytes):
            original = original.decode('utf-8', errors='replace')
        if isinstance(replacement, bytes):
            replacement = replacement.decode('utf-8', errors='replace')
        
        # Usa regex para substituição case-insensitive
        pattern = re.compile(re.escape(original), re.IGNORECASE)
        filtered_text = pattern.sub(replacement, filtered_text)
    
    # Log do texto após as substituições
    logger.info(f"Texto após substituições: {safe_text(filtered_text)}")
    
    return filtered_text
