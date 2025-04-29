import json
import os
from utils.logger import logger
from utils.resource_handler import get_media_dir, load_config

# Diretório para armazenar as mídias de substituição
MEDIA_DIR = get_media_dir()

async def replace_media(event, config):
    try:
        # Verifica se a mensagem contém mídia
        if not event.media:
            return None

        # Identifica stickers para substituição
        if event.sticker:
            sticker_id = str(event.document.id)
            sticker_replacements = config.get('sticker_replacements', {})
            
            if sticker_id in sticker_replacements:
                # Obtém o ID personalizado
                custom_id = sticker_replacements[sticker_id]
                
                # Se o ID já começa com "sticker_", usa direto, senão adiciona o prefixo
                if not custom_id.startswith("sticker_"):
                    custom_id = f"sticker_{custom_id}"
                
                # Verifica extensões possíveis para stickers usando o caminho correto
                possible_paths = [
                    os.path.join(MEDIA_DIR, f"{custom_id}.webp"),  # Formato standard sticker
                    os.path.join(MEDIA_DIR, f"{custom_id}.webm"),  # Formato vídeo sticker
                    os.path.join(MEDIA_DIR, f"{custom_id}.tgs")    # Formato animado sticker
                ]
                
                # Procura o arquivo em todas as extensões possíveis
                for replacement_path in possible_paths:
                    if os.path.exists(replacement_path):
                        # Simplificando o log para conter apenas o ID e não o caminho completo
                        logger.info(f"Sticker substituído: {sticker_id} -> {os.path.basename(replacement_path)}")
                        return replacement_path
                
                logger.warning(f"Arquivo de substituição não encontrado para sticker {sticker_id}")
        
        # Identifica imagens para substituição
        elif event.photo:
            photo_id = str(event.photo.id)
            image_replacements = config.get('image_replacements', {})
            
            if photo_id in image_replacements:
                # Caminho do arquivo local de substituição
                replacement_path = os.path.join(MEDIA_DIR, f"image_{image_replacements[photo_id]}.jpg")
                
                # Verifica se o arquivo de substituição existe
                if os.path.exists(replacement_path):
                    logger.info(f"Imagem substituída: {photo_id} -> {replacement_path}")
                    return replacement_path
                else:
                    logger.warning(f"Arquivo de substituição não encontrado: {replacement_path}")
        
        return None

    except Exception as e:
        logger.error(f"Erro ao substituir mídia: {e}", exc_info=True)
        return None
