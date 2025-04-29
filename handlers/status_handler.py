from telethon import events
from utils.logger import logger
from utils.scheduler import is_active
import json
import os
import datetime

CONFIG_PATH = 'config.json'

async def handle_status_command(event):
    """Envia mensagem com o status atual do bot."""
    try:
        if event.raw_text.strip() == "/status":
            # Carrega configurações
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # Verifica o tamanho do diretório de mídia
            media_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "media")
            media_files = len([f for f in os.listdir(media_dir) if os.path.isfile(os.path.join(media_dir, f))])
            
            # Conta o número de substituições configuradas
            sticker_replacements = len(config.get('sticker_replacements', {}))
            image_replacements = len(config.get('image_replacements', {}))
            
            # Verifica o status do agendador
            scheduler_enabled = config.get('schedule', {}).get('enable', False)
            
            # Formata a mensagem de status
            status_message = f"""
📊 **TClone Bot - Status Atual** 📊

⏰ **Data e Hora:** {datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')}

🔄 **Estado Geral:**
• Bot ativo: {'✅' if True else '❌'}
• Agendador ativo: {'✅' if scheduler_enabled else '❌'}
• Bot em operação: {'✅' if is_active else '❌'}

📈 **Estatísticas:**
• Chats de origem: {len(config.get('source_chats', []))}
• Chats de destino: {len(config.get('destination_chats', []))}
• Substituições de stickers: {sticker_replacements}
• Substituições de imagens: {image_replacements}
• Arquivos de mídia salvos: {media_files}

⚙️ **Configurações:**
• Palavras bloqueadas: {len(config.get('blocked_words', []))}
• Substituições de texto: {len(config.get('replacements', {}))}
• Apenas texto: {'✅' if config.get('replicar_apenas_texto', False) else '❌'}

🕒 **Agendamento:**
• Horário de início: {config.get('schedule', {}).get('start_time', 'N/A')}
• Horário de término: {config.get('schedule', {}).get('end_time', 'N/A')}
            """
            
            await event.respond(status_message)
            logger.info(f"Mensagem de status enviada para o chat {event.chat_id}")
            
    except Exception as e:
        logger.error(f"Erro ao enviar mensagem de status: {e}", exc_info=True)
