from telethon import events
from utils.logger import logger
from utils.resource_handler import MAX_ACTIONS, load_usage_data
import json
import os
import datetime

CONFIG_PATH = 'config.json'
FIRST_RUN_FILE = 'data/first_run.txt'

async def send_welcome_message(client):
    """
    Envia mensagem de boas-vindas com comandos disponíveis para o chat configurado.
    A mensagem só é enviada na primeira inicialização.
    """
    try:
        # Verifica se é a primeira execução
        os.makedirs(os.path.dirname(FIRST_RUN_FILE), exist_ok=True)
        
        if os.path.exists(FIRST_RUN_FILE):
            logger.info("Não é a primeira inicialização. Pulando mensagem de boas-vindas.")
            return
            
        # Carrega configurações
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # Verifica se há um chat_id configurado para receber a mensagem de boas-vindas
        welcome_chat = config.get('chat_id')
        if not welcome_chat:
            logger.info("Chat de boas-vindas não configurado. Pulando mensagem inicial.")
            return
        
        # Compõe a mensagem de boas-vindas com os comandos disponíveis
        usage_data = load_usage_data()
        remaining_actions = MAX_ACTIONS - usage_data["actions"]
        welcome_message = f"""
🤖 **TClone Bot - Bem-vindo!** 🤖

O bot está conectado e pronto para clonar mensagens.

⚠️ **Limite de ações:** {remaining_actions}/{MAX_ACTIONS}
Para remover o limite, adquira a versão completa: https://global.tribopay.com.br/qpqbz5koox ou chame @roge_rdv

**Principais comandos:**
• `/help` - Mostra todos os comandos disponíveis
• `/status` - Mostra o status atual do bot
• `/config` - Mostra todas as configurações

Desenvolvido por @roge_rdv
        """
        
        # Envia a mensagem para o chat configurado
        await client.send_message(entity=welcome_chat, message=welcome_message)
        logger.info(f"Mensagem de boas-vindas enviada para o chat {welcome_chat}")
        
        # Marca como não sendo mais a primeira inicialização
        with open(FIRST_RUN_FILE, 'w') as f:
            f.write(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        
    except Exception as e:
        logger.error(f"Erro ao enviar mensagem de boas-vindas: {e}", exc_info=True)
