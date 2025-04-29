from telethon import events, errors
from telethon.tl.functions.channels import JoinChannelRequest
from database.db_manager import DatabaseManager
from utils.scheduler import is_active
from filters.content_filter import filter_content, safe_text
from utils.bypass_tools import bypass_restriction
from filters.media_replacer import replace_media
from utils.logger import logger
from utils.resource_handler import is_limit_reached, increment_action_count
import json
import os

db = DatabaseManager()

async def handle_new_message(event):
    # Verifica se o limite de ações foi atingido
    if is_limit_reached():
        logger.error("Limite de ações atingido. Acesse https://global.tribopay.com.br/qpqbz5koox para adquirir a versão completa.")
        await event.respond("⚠️ Limite de ações atingido. Acesse https://global.tribopay.com.br/qpqbz5koox para adquirir a versão completa.")
        return

    # Incrementa o contador de ações
    if not increment_action_count():
        logger.error("Erro ao incrementar contador de ações. Acesso bloqueado.")
        await event.respond("⚠️ Acesso bloqueado. Acesse https://global.tribopay.com.br/qpqbz5koox para adquirir a versão completa.")
        return

    try:
        # Primeiro, verifica explicitamente se é um comando administrativo
        is_admin_command = False
        if event.raw_text and event.raw_text.startswith('/'):
            # Lista de comandos administrativos que sempre funcionam
            admin_commands = ['/help', '/status', '/config', '/block', '/unblock', '/blocklist', 
                             '/replace', '/unreplace', '/replacelist', '/schedule', '/settime', 
                             '/showschedule', '/deletestatus', '/clearmappings', '/textoonly']
            command = event.raw_text.split()[0].lower()
            is_admin_command = command in admin_commands
        
        # Verifica se o bot está ativo pelo agendador (exceto para comandos administrativos)
        if not is_active and not is_admin_command:
            # Log mais detalhado para debug
            logger.info(f"Bot inativo pelo agendador. Ignorando mensagem: '{event.raw_text if event.raw_text else '[Media]'}'")
            return
            
        # Identifica o tipo de mensagem para log mais informativo
        if event.raw_text:
            # Mensagem com texto
            logger.info(f"Nova mensagem recebida: {safe_text(event.raw_text)}")
        elif event.sticker:
            # É um sticker
            sticker_id = str(event.document.id)
            sticker_set = getattr(event.document, 'sticker_set', None)
            emoji = None
            for attr in getattr(event.document, 'attributes', []):
                if hasattr(attr, 'alt'):
                    emoji = attr.alt
                    break
            
            logger.info(f"Sticker recebido [ID: {sticker_id}]{f', Emoji: {emoji}' if emoji else ''}")
        elif event.photo:
            # É uma foto
            photo_id = str(event.photo.id)
            caption = event.raw_text or "[Sem legenda]"
            logger.info(f"Foto recebida [ID: {photo_id}], Legenda: {caption}")
        elif event.document:
            # É um documento/arquivo
            doc_id = str(event.document.id)
            mime_type = getattr(event.document, 'mime_type', 'desconhecido')
            filename = "desconhecido"
            for attr in getattr(event.document, 'attributes', []):
                if hasattr(attr, 'file_name'):
                    filename = attr.file_name
                    break
                    
            logger.info(f"Documento recebido [ID: {doc_id}], Tipo: {mime_type}, Nome: {filename}")
        elif event.video:
            # É um vídeo
            video_id = str(event.video.id)
            duration = "desconhecida"
            for attr in getattr(event.video, 'attributes', []):
                if hasattr(attr, 'duration'):
                    duration = f"{attr.duration} segundos"
                    break
                    
            logger.info(f"Vídeo recebido [ID: {video_id}], Duração: {duration}")
        else:
            # Outro tipo de mídia
            logger.info("Mídia recebida [Tipo desconhecido]")
            
        # Se é um comando administrativo, deixa passar para outros handlers
        if is_admin_command:
            logger.debug(f"Comando administrativo detectado: {event.raw_text}")
            return
        
        # Carrega configurações
        with open('config.json', 'r') as f:
            config = json.load(f)

        # Aplica filtros de conteúdo apenas para mensagens de texto
        if not event.media:
            filtered_message = await filter_content(event, config)
            if not filtered_message:
                logger.warning(f"Mensagem bloqueada: {safe_text(event.text)}")
                return
        else:
            filtered_message = event.raw_text or ""
            
        # Garante que filtered_message é uma string Unicode válida
        if filtered_message and isinstance(filtered_message, bytes):
            try:
                filtered_message = filtered_message.decode('utf-8')
            except UnicodeDecodeError:
                filtered_message = filtered_message.decode('utf-8', errors='replace')

        # Processa mídias restritas (prepara para substituição)
        media_data = await bypass_restriction(event)

        # Verifica se há uma substituição configurada
        replacement_path = await replace_media(event, config)
        
        # Realiza a substituição se necessário
        if replacement_path:
            # Simplificando o log para não mostrar o caminho completo
            logger.info(f"Mídia será substituída: {os.path.basename(replacement_path)}")
            
            # Verifica se é um sticker (baseado na extensão do arquivo)
            if replacement_path.endswith('.webp') or replacement_path.endswith('.webm') or replacement_path.endswith('.tgs'):
                # Para stickers, precisamos enviar com os atributos corretos
                media_data = {
                    "file": replacement_path, 
                    "attributes": None,
                    "is_sticker": True  # Marcamos como sticker para tratamento especial
                }
            else:
                # Para outros tipos de mídia
                media_data = {"file": replacement_path, "attributes": None}

        # Verifica se deve replicar apenas texto
        if config.get("replicar_apenas_texto", False) and event.media:
            logger.info("Mensagem ignorada por ser mídia e 'replicar_apenas_texto' está ativado.")
            return

        # Envia para todos os destinos configurados
        for dest in config['destination_chats']:
            # Verifica novamente se o bot ainda está ativo 
            # (em caso de ter sido desativado durante o processamento)
            if not is_active:
                logger.info("Bot desativado durante o processamento. Interrompendo envio.")
                return

            try:
                if media_data:
                    # Envia a mídia substituída ou original
                    if media_data.get("is_sticker", False) or (event.sticker and not replacement_path):
                        # Envia como sticker
                        try:
                            sent_msg = await event.client.send_file(
                                entity=dest,
                                file=media_data['file'],
                                force_document=False,     # Não enviar como documento
                                allow_cache=False,       # Não usar cache
                                supports_streaming=False, # Não é streaming
                                silent=False,             # Notificar o chat
                                attributes=media_data.get('attributes'),
                                mime_type="image/webp"    # Força o MIME type para stickers
                            )
                            # Log simplificado
                            logger.info(f"Sticker enviado para {dest}")
                        except Exception as sticker_error:
                            logger.error(f"Erro ao enviar sticker: {sticker_error}")
                            # Tenta enviar como documento em caso de falha
                            sent_msg = await event.client.send_file(
                                entity=dest,
                                file=media_data['file']
                            )
                    else:
                        # Envia mídia normal
                        sent_msg = await event.client.send_file(
                            entity=dest,
                            file=media_data['file'],
                            caption=filtered_message,
                            attributes=media_data.get('attributes', None)
                        )
                    
                    # Salva mapeamento no banco para TODAS as mensagens (incluindo mídia)
                    # para garantir que a deleção funcione corretamente
                    try:
                        db.insert_message(event.chat_id, event.id, sent_msg.id)
                        logger.debug(f"Mapeamento salvo: {event.id} -> {sent_msg.id}")
                    except Exception as e:
                        logger.error(f"Erro ao salvar mapeamento: {e}")
                else:
                    # Envia mensagem de texto - garante que está em formato Unicode
                    try:
                        sent_msg = await event.client.send_message(
                            entity=dest,
                            message=filtered_message,
                            parse_mode='md'  # Usa markdown para melhor suporte a caracteres especiais
                        )
                    except errors.ChatAdminRequiredError:
                        logger.warning(f"Permissão de admin necessária para enviar no chat {dest}. Tentando método alternativo...")
                        try:
                            # Tenta entrar no canal/grupo se possível
                            try:
                                await event.client(JoinChannelRequest(dest))
                                logger.info(f"Entrou automaticamente no chat {dest}")
                            except:
                                logger.warning(f"Não foi possível entrar no chat {dest}")
                            
                            # Tenta enviar como mensagem simples sem formatação
                            sent_msg = await event.client.send_message(
                                entity=dest,
                                message=filtered_message,
                                parse_mode=None,  # Desativa formatação para evitar problemas
                                link_preview=False  # Desativa preview para evitar problemas
                            )
                            logger.info(f"Mensagem enviada com bypass para {dest}")
                        except Exception as bypass_error:
                            logger.error(f"Falha no bypass para {dest}: {bypass_error}")
                            continue
                    
                    # Salva mapeamento no banco
                    try:
                        db.insert_message(event.chat_id, event.id, sent_msg.id)
                        logger.debug(f"Mapeamento salvo: {event.id} -> {sent_msg.id}")
                    except Exception as e:
                        logger.error(f"Erro ao salvar mapeamento: {e}")

            except errors.ChatWriteForbiddenError:
                logger.error(f"Sem permissão para escrever no chat {dest}. Verifique se o bot foi adicionado como membro.")
                continue
            except errors.UserBannedInChannelError:
                logger.error(f"Bot banido no chat {dest}. Não é possível enviar mensagens.")
                continue
            except errors.ChannelPrivateError:
                logger.error(f"O chat {dest} é privado e o bot não tem acesso. Adicione o bot no grupo/canal.")
                continue
            except Exception as e:
                logger.error(f"Erro ao enviar mensagem para {dest}: {e}")
                continue

    except Exception as e:
        logger.error(f"Erro ao processar mensagem: {e}", exc_info=True)
