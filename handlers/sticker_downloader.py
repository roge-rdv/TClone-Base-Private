from telethon import events
from utils.logger import logger
from utils.resource_handler import get_media_dir
import os
import asyncio
from telethon.tl.types import DocumentAttributeFilename, InputStickerSetID

# Diretório para armazenar as mídias de substituição
MEDIA_DIR = get_media_dir()

async def download_media(event):
    """
    Handler para download de stickers e imagens para substituição.
    Para usar: responda a um sticker/imagem com o comando "/save ID"
    onde ID é um identificador único que você escolhe para o sticker/imagem.
    """
    try:
        # Verifica se é uma resposta a uma mensagem com comando de salvamento
        if not event.is_reply or not event.raw_text:
            return
        
        # Verifica se o comando é "/save ID"
        command_parts = event.raw_text.split()
        if len(command_parts) != 2 or command_parts[0] != "/save":
            return
        
        # Obtém o ID personalizado para o sticker/imagem
        custom_id = command_parts[1]
        
        # Obtém a mensagem respondida
        replied_msg = await event.get_reply_message()
        
        # Verifica se a mensagem respondida contém mídia
        if not replied_msg.media:
            await event.respond("A mensagem respondida não contém mídia")
            return
        
        # Baixa o sticker/imagem
        if replied_msg.sticker:
            # É um sticker
            original_id = replied_msg.document.id
            
            # Determina a extensão correta com base no tipo
            mime_type = getattr(replied_msg.document, 'mime_type', 'image/webp')
            if mime_type == 'application/x-tgsticker':
                extension = '.tgs'  # Stickers animados
            elif mime_type == 'video/webm':
                extension = '.webm'  # Video stickers
            else:
                extension = '.webp'  # Stickers normais
            
            # Salva o sticker com a extensão correta
            file_path = await replied_msg.download_media(
                file=os.path.join(MEDIA_DIR, f"sticker_{custom_id}{extension}")
            )
            
            media_type = "Sticker"
            
            # Mensagem informativa
            await event.respond(f"✅ Sticker salvo com ID: {custom_id}\n"
                              f"📝 ID original: {original_id}\n"
                              f"🔖 Tipo: {mime_type}\n\n"
                              f"Para substituir, adicione ao config.json:\n"
                              f"```json\n\"sticker_replacements\": {{\n    \"{original_id}\": \"{custom_id}\"\n}}\n```")
            
        elif replied_msg.photo:
            # É uma imagem
            file_path = await replied_msg.download_media(os.path.join(MEDIA_DIR, f"image_{custom_id}.jpg"))
            media_type = "Imagem"
            original_id = replied_msg.photo.id
            
            # Mensagem informativa
            await event.respond(f"✅ Imagem salva com ID: {custom_id}\n"
                              f"📝 ID original: {original_id}\n\n"
                              f"Para substituir, adicione ao config.json:\n"
                              f"```json\n\"image_replacements\": {{\n    \"{original_id}\": \"{custom_id}\"\n}}\n```")
            
        else:
            await event.respond("Tipo de mídia não suportado para substituição")
            return
        
        logger.info(f"{media_type} salvo para substituição: ID={custom_id}, Original ID={original_id}, Path={file_path}")
    
    except Exception as e:
        logger.error(f"Erro ao salvar mídia: {e}", exc_info=True)
        await event.respond(f"❌ Erro ao salvar mídia: {str(e)}")
