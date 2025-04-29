from telethon import events
from database.db_manager import DatabaseManager
from utils.logger import logger
import json

db = DatabaseManager()

async def handle_edit(event):
    try:
        # Carrega configurações para obter chats de destino
        with open('config.json', 'r') as f:
            config = json.load(f)
        
        # Obtém o mapeamento de IDs da mensagem
        original_id = event.id
        if not original_id:
            logger.warning("Nenhuma mensagem original encontrada para edição.")
            return

        # Obtém ID da mensagem no chat de destino
        mapped_id = db.get_mapped_message_id(event.chat_id, original_id)

        if not mapped_id:
            logger.warning(f"Mensagem editada não encontrada no banco: {original_id}")
            return

        # Obtém o texto atualizado
        new_text = event.raw_text

        # Para cada chat de destino, atualiza a mensagem usando o ID mapeado
        success_count = 0
        for dest_chat in config['destination_chats']:
            try:
                # Edita a mensagem no chat de destino (não no chat original)
                await event.client.edit_message(
                    entity=dest_chat,  # Corrige para usar o chat de destino
                    message=mapped_id,
                    text=new_text
                )
                success_count += 1
                logger.info(f"Mensagem {original_id} editada no destino {dest_chat} (ID: {mapped_id})")
            except Exception as e:
                logger.error(f"Erro ao editar mensagem {mapped_id} no chat {dest_chat}: {e}")
        
        if success_count > 0:
            logger.info(f"Mensagem editada com sucesso em {success_count} chat(s) de destino")

    except Exception as e:
        logger.error(f"Erro ao sincronizar edição: {e}", exc_info=True)
