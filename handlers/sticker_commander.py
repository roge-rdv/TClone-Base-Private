from telethon import events
from utils.logger import logger
import json
import os

# Diretório para armazenar as mídias de substituição
MEDIA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "media")
os.makedirs(MEDIA_DIR, exist_ok=True)

CONFIG_PATH = 'config.json'

async def handle_sticker_commands(event):
    """
    Handler para comandos relacionados a stickers e imagens.
    
    Comandos:
    /replace - Responda a um sticker original com este comando para substituí-lo por outro
    /replaceimg - Responda a uma imagem original com este comando para substituí-la por outra
    /list - Lista todas as substituições configuradas
    /remove ID - Remove uma substituição de sticker pelo ID original
    /removeimg ID - Remove uma substituição de imagem pelo ID original
    """
    try:
        if not event.raw_text:
            return
            
        command = event.raw_text.split()
        command_name = command[0].lower()
        
        # Comando para substituir sticker
        if command_name == "/replace" and event.is_reply:
            # Guarda o ID do usuário e mensagem para uso futuro
            user_id = event.sender_id
            
            # Obtém a mensagem original (sticker a ser substituído)
            original_msg = await event.get_reply_message()
            
            # Verifica se é um sticker
            if not original_msg.sticker:
                await event.respond("Você deve responder a um sticker com o comando /replace")
                return
                
            # Obtém o ID do sticker original
            original_id = str(original_msg.document.id)
            
            # Avisa o usuário para enviar o sticker substituto
            response = await event.respond("Agora envie o sticker que servirá como substituto")
            
            # Configura callback para receber o sticker substituto
            async def wait_for_replacement(ev):
                try:
                    # Verifica se é o mesmo usuário e se é um sticker
                    if ev.sender_id != user_id or not ev.sticker:
                        return
                        
                    # Obtém o ID do sticker substituto
                    replacement_id = f"{ev.document.id}"
                    custom_id = f"sticker_{replacement_id}"
                    
                    # Baixa o sticker substituto como .tgs
                    file_path = await ev.download_media(
                        file=os.path.join(MEDIA_DIR, f"{custom_id}.tgs")
                    )
                    
                    # Atualiza o config.json
                    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                        config = json.load(f)
                        
                    if 'sticker_replacements' not in config:
                        config['sticker_replacements'] = {}
                        
                    config['sticker_replacements'][original_id] = custom_id.replace("sticker_", "")
                    
                    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
                        json.dump(config, f, indent=4, ensure_ascii=False)
                        
                    # Confirma para o usuário
                    await event.client.send_message(
                        entity=ev.chat_id,
                        message=f"✅ Substituição de sticker configurada com sucesso!\n\n"
                               f"Sticker original ID: `{original_id}`\n"
                               f"Substituto ID: `{custom_id}`\n\n"
                               f"O sticker será substituído automaticamente a partir de agora."
                    )
                    
                    # Remove a espera por nova mensagem
                    event.client.remove_event_handler(wait_for_replacement)
                    
                except Exception as e:
                    logger.error(f"Erro ao configurar substituição de sticker: {e}", exc_info=True)
                    await event.client.send_message(
                        entity=ev.chat_id,
                        message=f"❌ Erro ao configurar substituição: {e}"
                    )
                    event.client.remove_event_handler(wait_for_replacement)
            
            # Registra o handler temporário
            event.client.add_event_handler(wait_for_replacement, events.NewMessage())
            
            return
            
        # Comando para substituir imagem
        elif command_name == "/replaceimg" and event.is_reply:
            # Guarda o ID do usuário
            user_id = event.sender_id
            
            # Obtém a mensagem original (imagem a ser substituída)
            original_msg = await event.get_reply_message()
            
            # Verifica se é uma imagem
            if not original_msg.photo:
                await event.respond("Você deve responder a uma imagem com o comando /replaceimg")
                return
                
            # Obtém o ID da imagem original
            original_id = str(original_msg.photo.id)
            
            # Avisa o usuário para enviar a imagem substituta
            response = await event.respond("Agora envie a imagem que servirá como substituta")
            
            # Configura callback para receber a imagem substituta
            async def wait_for_image_replacement(ev):
                try:
                    # Verifica se é o mesmo usuário e se é uma imagem
                    if ev.sender_id != user_id or not ev.photo:
                        return
                        
                    # Obtém o ID da imagem substituta
                    replacement_id = f"{ev.photo.id}"
                    custom_id = f"image_{replacement_id}"
                    
                    # Baixa a imagem substituta
                    file_path = await ev.download_media(
                        file=os.path.join(MEDIA_DIR, f"{custom_id}.jpg")
                    )
                    
                    # Atualiza o config.json
                    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                        config = json.load(f)
                        
                    if 'image_replacements' not in config:
                        config['image_replacements'] = {}
                        
                    config['image_replacements'][original_id] = custom_id.replace("image_", "")
                    
                    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
                        json.dump(config, f, indent=4, ensure_ascii=False)
                        
                    # Confirma para o usuário
                    await event.client.send_message(
                        entity=ev.chat_id,
                        message=f"✅ Substituição de imagem configurada com sucesso!\n\n"
                               f"Imagem original ID: `{original_id}`\n"
                               f"Substituto ID: `{custom_id}`\n\n"
                               f"A imagem será substituída automaticamente a partir de agora."
                    )
                    
                    # Remove a espera por nova mensagem
                    event.client.remove_event_handler(wait_for_image_replacement)
                    
                except Exception as e:
                    logger.error(f"Erro ao configurar substituição de imagem: {e}", exc_info=True)
                    await event.client.send_message(
                        entity=ev.chat_id,
                        message=f"❌ Erro ao configurar substituição: {e}"
                    )
                    event.client.remove_event_handler(wait_for_image_replacement)
            
            # Registra o handler temporário
            event.client.add_event_handler(wait_for_image_replacement, events.NewMessage())
            
            return
            
        # Comando para listar substituições
        elif command_name == "/list":
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                config = json.load(f)
                
            sticker_replacements = config.get('sticker_replacements', {})
            image_replacements = config.get('image_replacements', {})
            
            if not sticker_replacements and not image_replacements:
                await event.respond("Não há substituições configuradas.")
                return
                
            # Formata a lista de substituições
            replacements_text = "📋 **Substituições configuradas:**\n\n"
            
            if sticker_replacements:
                replacements_text += "🔄 **Stickers:**\n"
                for original, replacement in sticker_replacements.items():
                    replacements_text += f"Original: `{original}`\nSubstituto: `{replacement}`\n\n"
            
            if image_replacements:
                replacements_text += "🖼️ **Imagens:**\n"
                for original, replacement in image_replacements.items():
                    replacements_text += f"Original: `{original}`\nSubstituto: `{replacement}`\n\n"
                
            await event.respond(replacements_text)
            return
            
        # Comando para remover substituição de sticker
        elif command_name == "/remove" and len(command) > 1:
            original_id = command[1]
            
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                config = json.load(f)
                
            sticker_replacements = config.get('sticker_replacements', {})
            
            if original_id not in sticker_replacements:
                await event.respond(f"ID original `{original_id}` não encontrado nas substituições de stickers.")
                return
                
            # Remove a substituição
            replacement_id = sticker_replacements[original_id]
            del sticker_replacements[original_id]
            
            # Salva as alterações
            config['sticker_replacements'] = sticker_replacements
            with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
                
            await event.respond(f"✅ Substituição de sticker removida com sucesso!\n\nOriginal: `{original_id}`\nSubstituto: `{replacement_id}`")
            return
            
        # Comando para remover substituição de imagem
        elif command_name == "/removeimg" and len(command) > 1:
            original_id = command[1]
            
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                config = json.load(f)
                
            image_replacements = config.get('image_replacements', {})
            
            if original_id not in image_replacements:
                await event.respond(f"ID original `{original_id}` não encontrado nas substituições de imagens.")
                return
                
            # Remove a substituição
            replacement_id = image_replacements[original_id]
            del image_replacements[original_id]
            
            # Salva as alterações
            config['image_replacements'] = image_replacements
            with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
                
            await event.respond(f"✅ Substituição de imagem removida com sucesso!\n\nOriginal: `{original_id}`\nSubstituto: `{replacement_id}`")
            return
            
    except Exception as e:
        logger.error(f"Erro ao processar comando: {e}", exc_info=True)
        await event.respond(f"❌ Erro ao processar comando: {e}")
