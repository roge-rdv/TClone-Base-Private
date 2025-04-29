from telethon import errors
from telethon.tl.types import DocumentAttributeFilename, MessageMediaDocument, MessageMediaPhoto
from telethon.tl.functions.channels import JoinChannelRequest
from utils.logger import logger
import io
import asyncio

async def bypass_restriction(event):
    try:
        # Verifica se a mensagem contém mídia
        if not event.media:
            return None

        # Estratégia 1: Usa a mídia original diretamente
        try:
            if event.sticker:
                # Se for um sticker, marca explicitamente
                return {
                    "file": event.document,
                    "attributes": getattr(event.document, "attributes", None),
                    "is_sticker": True,
                    "mime_type": getattr(event.document, "mime_type", "image/webp")
                }
            return {
                "file": event.document or event.photo,
                "attributes": getattr(event.document, "attributes", None) if event.document else None
            }
        except:
            # Se falhar, tenta métodos alternativos
            pass
            
        # Estratégia 2: Baixa e re-envia a mídia
        try:
            # Baixa o arquivo para a memória
            media_bytes = io.BytesIO()
            await event.download_media(file=media_bytes)
            media_bytes.seek(0)  # Retorna ao início do arquivo
            
            # Obtém o tipo correto de mídia
            mime_type = None
            filename = None
            
            if event.document:
                for attr in event.document.attributes:
                    if isinstance(attr, DocumentAttributeFilename):
                        filename = attr.file_name
                        break
                mime_type = getattr(event.document, 'mime_type', None)
            
            return {
                "file": media_bytes, 
                "attributes": getattr(event.document, "attributes", None) if event.document else None,
                "mime_type": mime_type,
                "filename": filename,
                "is_sticker": event.sticker,
                "is_photo": event.photo is not None,
                "is_video": event.video is not None,
                "is_voice": event.voice is not None,
                "is_audio": event.audio is not None,
                "is_gif": event.gif is not None
            }
            
        except Exception as e:
            logger.error(f"Erro no bypass de mídia (método 2): {e}")
            pass
            
        # Se todas as estratégias falharem, retorna None
        logger.warning("Todas as estratégias de bypass de mídia falharam")
        return None

    except Exception as e:
        logger.error(f"Erro ao processar mídia para compartilhamento: {e}", exc_info=True)
        return None

async def attempt_group_join(client, chat_id):
    """Tenta entrar em um grupo/canal para obter acesso."""
    try:
        await client(JoinChannelRequest(chat_id))
        logger.info(f"Entrou no chat {chat_id} automaticamente")
        return True
    except errors.UserAlreadyParticipantError:
        logger.info(f"Já é participante do chat {chat_id}")
        return True
    except Exception as e:
        logger.error(f"Não foi possível entrar no chat {chat_id}: {e}")
        return False
