import logging
import os
import sys
from datetime import datetime
import codecs
from utils.resource_handler import get_logs_dir

def setup_logger(log_level=logging.INFO):
    """Configura o logger com suporte aprimorado a Unicode/Emojis"""
    # Configura o logger
    logger = logging.getLogger('TelegramForwarderBot')
    
    # Define o nível de log
    logger.setLevel(log_level)
    
    # Remove handlers antigos para evitar duplicação
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Cria formatador para logs
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', 
                                  datefmt='%Y-%m-%d %H:%M:%S')
    
    # Adiciona handler para enviar logs para o console (com suporte a Unicode)
    console_handler = logging.StreamHandler(stream=sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Usa o diretório de logs definido pelo resource handler
    log_dir = get_logs_dir()
    
    # Adiciona handler para enviar logs para arquivo com encoding UTF-8
    log_file = os.path.join(log_dir, f'bot_{datetime.now().strftime("%Y%m%d")}.log')
    try:
        # Usa codecs.open para garantir suporte a UTF-8 com BOM
        file_handler = logging.FileHandler(log_file, encoding='utf-8-sig')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except Exception as e:
        print(f"Erro ao configurar log em arquivo: {e}")
        # Adiciona apenas log para console em caso de erro
    
    # Adiciona handler personalizado para mensagens sem problemas de encoding
    class EncodingSafeHandler(logging.Handler):
        def emit(self, record):
            try:
                msg = self.format(record)
                if isinstance(msg, bytes):
                    msg = msg.decode('utf-8', errors='replace')
            except Exception:
                pass
    
    # Adiciona o handler customizado
    encoding_handler = EncodingSafeHandler()
    encoding_handler.setFormatter(formatter)
    logger.addHandler(encoding_handler)
    
    return logger

# Configuração global do logger
logger = setup_logger()
