import os
import sys
import json
import logging
import hashlib
import platform
import hmac
import uuid

# Configuração de logger local para evitar dependência circular
_local_logger = logging.getLogger('ResourceHandler')
if not _local_logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    _local_logger.addHandler(handler)
    _local_logger.setLevel(logging.INFO)

# Detecta se o app está rodando em modo executável (PyInstaller)
def is_bundled():
    return getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')

def get_app_root():
    """Retorna o diretório raiz da aplicação, seja em dev ou executável."""
    if is_bundled():
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def get_config_path():
    """Retorna o caminho para o arquivo config.json.
    No modo executável, fica junto ao .exe
    No modo desenvolvimento, fica na raiz do projeto."""
    return os.path.join(get_app_root(), 'config.json')

def get_data_dir():
    """Retorna o diretório para dados persistentes.
    No modo executável, cria um diretório 'data' junto ao .exe
    No modo desenvolvimento, usa o diretório 'data' na raiz do projeto."""
    data_path = os.path.join(get_app_root(), 'data')
    os.makedirs(data_path, exist_ok=True)
    return data_path

def get_media_dir():
    """Retorna o diretório para arquivos de mídia.
    No modo executável, cria um diretório 'media' junto ao .exe
    No modo desenvolvimento, usa o diretório 'media' na raiz."""
    media_path = os.path.join(get_app_root(), 'media')
    os.makedirs(media_path, exist_ok=True)
    return media_path

def get_logs_dir():
    """Retorna o diretório para logs.
    No modo executável, cria um diretório 'logs' junto ao .exe
    No modo desenvolvimento, usa o diretório 'logs' na raiz."""
    logs_path = os.path.join(get_app_root(), 'logs')
    os.makedirs(logs_path, exist_ok=True)
    return logs_path

def get_database_path():
    """Retorna o caminho para o banco de dados.
    No modo executável, fica em data/messages.db
    No modo desenvolvimento, mantém o caminho original."""
    data_dir = get_data_dir()
    return os.path.join(data_dir, 'messages.db')

def load_config():
    """Carrega o arquivo de configuração, criando um padrão se não existir."""
    config_path = get_config_path()
    
    # Cria um arquivo de configuração padrão se não existir
    if not os.path.exists(config_path):
        default_config = {
            "api_id": "",
            "api_hash": "",
            "bot_token": "",
            "source_chats": [],
            "destination_chats": [],
            "chat_id": 0,
            "log_level": "INFO",
            "blocked_words": [],
            "replacements": {},
            "sticker_replacements": {},
            "image_replacements": {},
            "schedule": {
                "enable": False,
                "start_time": "00:00",
                "end_time": "00:00"
            },
            "replicar_apenas_texto": False
        }
        
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(default_config, f, indent=4, ensure_ascii=False)
        
        _local_logger.info(f"Arquivo de configuração padrão criado em: {config_path}")
    
    # Carrega e retorna a configuração
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        _local_logger.error(f"Erro ao carregar configurações: {e}")
        return {}

def save_config(config):
    """Salva o arquivo de configuração."""
    config_path = get_config_path()
    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        _local_logger.error(f"Erro ao salvar configurações: {e}")
        return False

SECRET_KEY = "super_secret_key"  # Chave secreta para gerar/verificar o hash

def get_hidden_data_dir():
    """Retorna o diretório oculto para armazenar o arquivo usage_limits.json."""
    if os.name == 'nt':  # Windows
        return os.path.join(os.getenv('LOCALAPPDATA'), 'TCloneBot')
    else:  # Linux/Mac
        return os.path.join(os.path.expanduser('~/.local/share'), 'TCloneBot')

def ensure_hidden_data_dir():
    """Garante que o diretório oculto exista."""
    hidden_dir = get_hidden_data_dir()
    os.makedirs(hidden_dir, exist_ok=True)
    return hidden_dir

LIMIT_FILE = os.path.join(ensure_hidden_data_dir(), 'usage_limits.json')
MAX_ACTIONS = 50

def calculate_hash(data):
    """Calcula o hash assinado do conteúdo."""
    serialized_data = json.dumps(data, sort_keys=True).encode('utf-8')
    return hmac.new(SECRET_KEY.encode('utf-8'), serialized_data, hashlib.sha256).hexdigest()

def get_machine_id():
    """Gera um ID único baseado em múltiplos identificadores do sistema."""
    try:
        # Identificadores do sistema
        node = platform.node()  # Nome do host
        system = platform.system()  # Sistema operacional
        processor = platform.processor()  # Processador
        mac_address = ':'.join(['{:02x}'.format((uuid.getnode() >> ele) & 0xff) for ele in range(0, 8 * 6, 8)][::-1])  # Endereço MAC
        disk_serial = get_disk_serial()  # Número de série do disco (implementado abaixo)

        # Combina todos os identificadores
        raw_id = f"{node}-{system}-{processor}-{mac_address}-{disk_serial}"
        return hashlib.sha256(raw_id.encode('utf-8')).hexdigest()
    except Exception as e:
        _local_logger.error(f"Erro ao gerar machine_id: {e}")
        return "unknown_machine_id"

def get_disk_serial():
    """Obtém o número de série do disco (funciona no Windows e Linux)."""
    try:
        if os.name == 'nt':  # Windows
            import subprocess
            result = subprocess.check_output("wmic diskdrive get SerialNumber", shell=True)
            serial = result.decode().split("\n")[1].strip()
            return serial
        else:  # Linux/Mac
            import subprocess
            result = subprocess.check_output("lsblk -o SERIAL", shell=True)
            serial = result.decode().split("\n")[1].strip()
            return serial
    except Exception as e:
        _local_logger.error(f"Erro ao obter número de série do disco: {e}")
        return "unknown_serial"

def load_usage_data():
    """Carrega os dados de uso (contador de ações e ID da máquina) com verificação de hash."""
    if not os.path.exists(LIMIT_FILE):
        return {"machine_id": get_machine_id(), "actions": 0, "hash": ""}

    try:
        with open(LIMIT_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Verifica o hash
        expected_hash = data.pop("hash", None)
        if expected_hash != calculate_hash(data):
            _local_logger.error("Arquivo usage_limits.json foi alterado. Bloqueando acesso.")
            return {"machine_id": get_machine_id(), "actions": MAX_ACTIONS}  # Bloqueia o acesso

        return data
    except Exception as e:
        _local_logger.error(f"Erro ao carregar dados de uso: {e}")
        return {"machine_id": get_machine_id(), "actions": MAX_ACTIONS}  # Bloqueia o acesso

def save_usage_data(data):
    """Salva os dados de uso no arquivo com hash assinado."""
    try:
        data_to_save = data.copy()
        data_to_save["hash"] = calculate_hash(data)
        with open(LIMIT_FILE, 'w', encoding='utf-8') as f:
            json.dump(data_to_save, f, indent=4, ensure_ascii=False)
    except Exception as e:
        _local_logger.error(f"Erro ao salvar dados de uso: {e}")

def increment_action_count():
    """Incrementa o contador de ações e verifica o limite."""
    data = load_usage_data()
    if data.get("machine_id") != get_machine_id():
        _local_logger.error("ID da máquina não corresponde. Bloqueando acesso.")
        return False  # Bloqueia se o ID da máquina não corresponder
    if data["actions"] >= MAX_ACTIONS:
        return False  # Limite atingido
    data["actions"] += 1
    save_usage_data(data)
    return True

def is_limit_reached():
    """Verifica se o limite de ações foi atingido."""
    data = load_usage_data()
    return data["actions"] >= MAX_ACTIONS
