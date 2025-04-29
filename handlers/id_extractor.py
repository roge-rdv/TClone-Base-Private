from telethon import events
from utils.logger import logger

async def extract_ids(event):
    """Captura os IDs de stickers e imagens."""
    try:
        # Apenas registra o ID do sticker para depuração, sem mensagens extras
        if event.sticker:
            logger.debug(f"Sticker ID: {event.document.id}")
        elif event.photo:
            logger.debug(f"Image ID: {event.photo.id}")
    except Exception as e:
        logger.error(f"Erro ao capturar IDs: {e}", exc_info=True)
