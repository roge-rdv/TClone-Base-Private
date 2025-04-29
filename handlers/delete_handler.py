# handlers/delete_handler.py
from telethon import events
from database.db_manager import DatabaseManager
from utils.logger import logger
import json
import asyncio
import time

db = DatabaseManager()
# Adiciona semáforo para evitar processamento concorrente de exclusões
delete_semaphore = asyncio.Semaphore(1)

# Deleta imediatamente sem criar tarefa separada
async def handle_delete(event: events.MessageDeleted.Event):
    """Exclui mensagens no destino quando deletadas na origem."""
    # Captura o momento exato do evento
    event_time = time.time()
    logger.info(f"[{event_time:.6f}] Evento de exclusão detectado no chat {event.chat_id}")
    
    # Se não houver IDs para excluir, retornamos imediatamente
    if not event.deleted_ids:
        logger.warning("Nenhuma mensagem original encontrada para exclusão.")
        return
        
    # Logamos os IDs que serão excluídos
    logger.info(f"Detectadas {len(event.deleted_ids)} mensagens excluídas: {event.deleted_ids}")
    
    # Força o loop a processar esta tarefa imediatamente
    # Executa o código de exclusão com alta prioridade
    await asyncio.sleep(0)  # Força o evento loop a processar operações pendentes
    await force_instant_deletion(event.client, event.chat_id, event.deleted_ids)

# Força o processamento imediato do evento sem esperar pelo próximo ciclo
async def force_instant_deletion(client, chat_id, message_ids):
    # Usa o semáforo para garantir exclusividade
    async with delete_semaphore:
        try:
            start_time = time.time()
            logger.info(f"[INSTANT DELETE] Iniciando exclusão forçada: {message_ids} do chat {chat_id}")
            
            # Força sincronização
            await asyncio.sleep(0)
            
            # Carrega configurações
            with open('config.json', 'r') as f:
                config = json.load(f)
                
            # Mantém contagem das mensagens excluídas com sucesso
            success_count = 0
            not_found_count = 0
            error_count = 0
            
            # Processa as exclusões com prioridade absoluta
            for original_id in message_ids:
                # Pausa outras tarefas para maximizar prioridade
                await asyncio.sleep(0)
                
                # Busca o ID correspondente no destino
                destination_id = db.get_mapped_message_id(chat_id, original_id)
                    
                if not destination_id:
                    not_found_count += 1
                    logger.warning(f"[INSTANT DELETE] ID {original_id} não encontrado no banco de dados")
                    continue
                    
                logger.info(f"[INSTANT DELETE] ID {original_id} mapeado para ID {destination_id} no destino")
                
                # Força mais uma sincronização antes da exclusão
                await asyncio.sleep(0)
                
                # Exclui a mensagem em cada chat de destino
                for dest_chat in config['destination_chats']:
                    # Deleta a mensagem imediatamente (sem criar tasks)
                    start = time.time()
                    try:
                        await client.delete_messages(dest_chat, destination_id)
                        end = time.time()
                        logger.info(f"[INSTANT DELETE] Mensagem {destination_id} excluída no chat {dest_chat} em {end-start:.3f}s")
                        success_count += 1
                    except Exception as e:
                        error_count += 1
                        logger.error(f"[INSTANT DELETE] Erro ao excluir mensagem {original_id} no destino {dest_chat}: {e}")
                    
                    # Remove o mapeamento após exclusão bem-sucedida
                    db.delete_mapping(chat_id, original_id)
            
            # Garante que o evento foi concluído antes de liberar o lock
            await asyncio.sleep(0)
            
            # Log resumido da operação
            end_time = time.time()
            total_time = end_time - start_time
            logger.info(f"[INSTANT DELETE] Operação de exclusão concluída em {total_time:.3f}s")
            
            if success_count > 0:
                logger.info(f"[INSTANT DELETE] {success_count} mensagens excluídas com sucesso")
            if not_found_count > 0:
                logger.warning(f"[INSTANT DELETE] {not_found_count} mensagens não encontradas no banco")
            if error_count > 0:
                logger.error(f"[INSTANT DELETE] Falha ao excluir {error_count} mensagens")
                
        except Exception as e:
            logger.error(f"[INSTANT DELETE] Erro crítico durante exclusão instantânea: {e}", exc_info=True)
        
        # Espera processamento final antes de retornar
        await asyncio.sleep(0.05)