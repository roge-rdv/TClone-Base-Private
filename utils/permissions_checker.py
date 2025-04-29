from telethon import TelegramClient, errors
from telethon.tl.functions.channels import GetParticipantRequest
from telethon.tl.types import ChannelParticipantAdmin, ChannelParticipantCreator
from utils.logger import logger
import asyncio

async def check_bot_permissions(client, chat_ids):
    """
    Verifica as permissões do bot nos chats configurados.
    Retorna um dicionário com o status de cada chat.
    """
    results = {}
    me = await client.get_me()
    
    for chat_id in chat_ids:
        try:
            # Tenta obter informações do chat
            chat = await client.get_entity(chat_id)
            chat_title = getattr(chat, 'title', str(chat_id))
            
            # Verifica se é membro do chat
            try:
                participant = await client(GetParticipantRequest(
                    channel=chat_id,
                    participant=me.id
                ))
                
                # Verifica se é administrador
                is_admin = isinstance(
                    participant.participant,
                    (ChannelParticipantAdmin, ChannelParticipantCreator)
                )
                
                results[chat_id] = {
                    "title": chat_title,
                    "is_member": True,
                    "is_admin": is_admin,
                    "error": None
                }
                
                if not is_admin:
                    logger.warning(f"Bot não é administrador em {chat_title} ({chat_id}). Algumas funções podem estar limitadas.")
                
            except errors.UserNotParticipantError:
                results[chat_id] = {
                    "title": chat_title,
                    "is_member": False,
                    "is_admin": False,
                    "error": "Não é membro deste chat"
                }
                logger.error(f"Bot não é membro do chat {chat_title} ({chat_id})")
                
        except errors.ChannelPrivateError:
            results[chat_id] = {
                "title": str(chat_id),
                "is_member": False,
                "is_admin": False,
                "error": "Chat privado, sem acesso"
            }
            logger.error(f"Chat {chat_id} é privado e o bot não tem acesso")
            
        except Exception as e:
            results[chat_id] = {
                "title": str(chat_id),
                "is_member": False,
                "is_admin": False,
                "error": str(e)
            }
            logger.error(f"Erro ao verificar permissões para {chat_id}: {e}")
    
    return results

async def verify_permissions(client, config):
    """Verifica e exibe o status de permissões para todos os chats configurados."""
    try:
        # Verifica permissões nos chats de origem
        logger.info("Verificando permissões nos chats de origem...")
        source_status = await check_bot_permissions(client, config['source_chats'])
        
        # Verifica permissões nos chats de destino
        logger.info("Verificando permissões nos chats de destino...")
        dest_status = await check_bot_permissions(client, config['destination_chats'])
        
        # Exibe resumo
        source_ok = sum(1 for status in source_status.values() if status['is_member'])
        source_admin = sum(1 for status in source_status.values() if status['is_admin'])
        dest_ok = sum(1 for status in dest_status.values() if status['is_member'])
        dest_admin = sum(1 for status in dest_status.values() if status['is_admin'])
        
        logger.info(f"Resumo de permissões:")
        logger.info(f"- Chats de origem: {source_ok}/{len(source_status)} acessíveis, {source_admin}/{len(source_status)} como admin")
        logger.info(f"- Chats de destino: {dest_ok}/{len(dest_status)} acessíveis, {dest_admin}/{len(dest_status)} como admin")
        
        # Retorna detalhes para uso pelo aplicativo
        return {
            "source_chats": source_status,
            "destination_chats": dest_status,
            "all_accessible": (source_ok == len(source_status) and dest_ok == len(dest_status))
        }
        
    except Exception as e:
        logger.error(f"Erro ao verificar permissões: {e}")
        return None
