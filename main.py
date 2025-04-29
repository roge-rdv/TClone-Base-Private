import sys
if sys.version_info >= (3, 13):
    import compat  # This will set up the imghdr module compatibility

import json
import asyncio
import signal
import os
from telethon import TelegramClient, events
from database.db_manager import DatabaseManager
from handlers.message_handler import handle_new_message
from handlers.edit_handler import handle_edit
from handlers.delete_handler import handle_delete
from utils.scheduler import setup_scheduler
from utils.logger import setup_logger
from handlers.id_extractor import extract_ids
from handlers.sticker_downloader import download_media
from handlers.sticker_commander import handle_sticker_commands
import os
from handlers.welcome_handler import send_welcome_message
from handlers.help_handler import handle_help_command
from handlers.status_handler import handle_status_command
from handlers.config_commander import handle_config_commands
import logging
from utils.permissions_checker import verify_permissions
import time
from utils.resource_handler import get_config_path, get_app_root, load_config, is_bundled
from utils.scheduler import is_active as scheduler_is_active
from utils.resource_handler import increment_action_count, is_limit_reached

# Configuração inicial
logger = setup_logger()  # Inicializa logs com nível padrão

# Semáforo global para controlar operações
GLOBAL_OP_LOCK = asyncio.Lock()

# Flag para indicar quando uma exclusão está em andamento
delete_in_progress = False

# Flag para controlar o encerramento do programa
shutdown_event = asyncio.Event()

# Tenta importar win32api de maneira mais robusta
HAS_WIN32API = True
try:
    if os.name == 'nt':  # Apenas tenta importar no Windows
        import pywin32  # Verifica se pywin32 está instalado
        from win32 import api as win32api  # Importa corretamente o módulo
        HAS_WIN32API = True
except ImportError:
    # O módulo pywin32/win32api não está disponível
    print("Aviso: win32api/pywin32 não encontrado. O tratamento de CTRL+C será através do mecanismo padrão.")
    HAS_WIN32API = False

# Define as funções wrapper ANTES de usá-las no main()
async def handle_delete_with_lock(event):
    """Função wrapper para handle_delete que usa o lock global"""
    # Verifica se o limite de ações foi atingido
    if is_limit_reached():
        logger.error("Limite de ações atingido. Acesse https://global.tribopay.com.br/qpqbz5koox ou entre em contato pelo perfil t.me/roge_rdv para adquirir a versão completa.")
        return

    # Incrementa o contador de ações
    if not increment_action_count():
        logger.error("Erro ao incrementar contador de ações. Acesso bloqueado.")
        return

    global delete_in_progress
    delete_in_progress = True
    
    try:
        # As deleções devem ocorrer mesmo quando o bot está inativo
        # Adquire o lock com prioridade máxima
        async with GLOBAL_OP_LOCK:
            # Processa a exclusão com prioridade
            await handle_delete(event)
    finally:
        # Sempre define como False, mesmo se houver erro
        delete_in_progress = False

async def handle_message_with_lock(event):
    """Função wrapper para handle_new_message que espera exclusões terminarem"""
    # Verifica se o limite de ações foi atingido
    if is_limit_reached():
        logger.error("Limite de ações atingido. Acesse https://global.tribopay.com.br/qpqbz5koox ou entre em contato pelo perfil t.me/roge_rdv para adquirir a versão completa.")
        await event.respond("⚠️ Limite de ações atingido. Acesse https://global.tribopay.com.br/qpqbz5koox ou entre em contato pelo perfil t.me/roge_rdv para adquirir a versão completa.")
        return

    # Incrementa o contador de ações
    if not increment_action_count():
        logger.error("Erro ao incrementar contador de ações. Acesso bloqueado.")
        await event.respond("⚠️ Acesso bloqueado. Acesse https://global.tribopay.com.br/qpqbz5koox ou entre em contato pelo perfil t.me/roge_rdv para adquirir a versão completa.")
        return

    # Verificação imediata do status ativo - retorna se inativo
    from utils.scheduler import is_active
    if not is_active:
        # Verifica se é um comando administrativo antes de ignorar
        if event.raw_text and event.raw_text.startswith('/'):
            # Comandos administrativos específicos sempre passam
            admin_commands = ['/help', '/status', '/config', '/schedule', '/settime', '/showschedule']
            command = event.raw_text.split()[0].lower()
            if command in admin_commands:
                # Log específico para comandos que passam mesmo quando inativo
                logger.debug(f"Permitindo comando administrativo durante inatividade: {command}")
                await handle_new_message(event)
                return
        
        # Log mais descritivo para entender o fluxo
        logger.info(f"Bot inativo: mensagem ignorada no wrapper (tipo: {'texto' if event.raw_text else 'mídia'}")
        return
    
    # Se uma exclusão estiver em andamento, aguarda um pouco
    if delete_in_progress:
        await asyncio.sleep(0.5)  # Espera 500ms para permitir que a exclusão termine
    
    # Adquire o lock apenas quando não houver exclusões em andamento
    async with GLOBAL_OP_LOCK:
        await handle_new_message(event)

# Handler para sinais (CTRL+C)
def signal_handler():
    logger.info("Sinal de interrupção recebido (CTRL+C). Finalizando...")
    shutdown_event.set()

# Configura a política do asyncio para melhor responsividade
try:
    # Define a política de evento com limite mais alto de tarefas pendentes
    asyncio.get_event_loop().set_task_factory(lambda loop, coro: asyncio.Task(coro, loop=loop))
    # Configura o event loop para processar mais tarefas por ciclo
    asyncio.get_event_loop().slow_callback_duration = 0.1  # Reduz o limite para logging de callbacks lentos
except Exception as e:
    logger.warning(f"Não foi possível otimizar a configuração do event loop: {e}")

async def shutdown(client):
    """Função para encerramento limpo do bot."""
    try:
        logger.info("Iniciando encerramento limpo...")
        
        # Desconecta o cliente Telegram
        if client and client.is_connected():
            logger.info("Desconectando cliente Telegram...")
            await client.disconnect()
            
        # Fecha quaisquer recursos abertos
        logger.info("Fechando recursos...")
        
        # Exemplo: Fechar conexão com o banco de dados
        from database.db_manager import DatabaseManager
        db = DatabaseManager()
        if hasattr(db, 'conn') and db.conn:
            db.close()
            logger.info("Conexão com o banco de dados fechada.")
            
        logger.info("Encerramento concluído. Saindo...")
        
    except Exception as e:
        logger.error(f"Erro durante o encerramento: {e}", exc_info=True)
    finally:
        # Garante que o programa será finalizado
        sys.exit(0)

async def main():
    client = None  # Define fora do try para estar disponível no finally
    
    try:
        logger.info(f"TClone Bot iniciando...(executável: {is_bundled()})")
        logger.info(f"Diretório base: {get_app_root()}")
        
        # Verifica se o arquivo config.json existe
        config_path = get_config_path()
        if not os.path.exists(config_path):
            logger.error(f"Arquivo config.json não encontrado em {config_path}!")
            return
        
        # Carrega configurações usando o resource handler
        config = load_config()
        
        # Configura o handler para CTRL+C e outros sinais de término
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, lambda: asyncio.create_task(shutdown(client)))
            except NotImplementedError:
                # Windows não suporta add_signal_handler
                pass
        
        logger.info("Handlers de sinal configurados (CTRL+C habilitado para parar o bot)")
        
        # Configura o nível de log conforme definido no config.json
        log_level = config.get('log_level', 'INFO').upper()
        numeric_level = getattr(logging, log_level, logging.INFO)
        logger.setLevel(numeric_level)
        logger.info(f"Nível de log configurado para: {log_level}")
        
        # Verifica API ID, que é sempre necessário
        api_id = config.get('api_id')
        if not api_id:
            logger.error("API ID é obrigatório e não pode estar vazio!")
            return
            
        # Verifica se o limite de ações foi atingido
        if is_limit_reached():
            logger.error("Limite de ações atingido. Acesse https://global.tribopay.com.br/qpqbz5koox ou entre em contato pelo perfil t.me/roge_rdv para adquirir a versão completa.")
            print("⚠️ Limite de ações atingido. Acesse https://global.tribopay.com.br/qpqbz5koox ou entre em contato pelo perfil t.me/roge_rdv para adquirir a versão completa.")
            
            # Mantém o programa em execução, mas bloqueia todas as funcionalidades
            while True:
                await asyncio.sleep(60)  # Aguarda indefinidamente até que o programa seja encerrado manualmente
        
        # Incrementa o contador de ações
        if not increment_action_count():
            logger.error("Erro ao incrementar contador de ações. Acesso bloqueado.")
            print("⚠️ Acesso bloqueado. Acesse https://global.tribopay.com.br/qpqbz5koox ou entre em contato pelo perfil t.me/roge_rdv para adquirir a versão completa.")
            return

        # Verifica se há token de bot ou credenciais de API
        bot_token = config.get('bot_token')
        if bot_token and bot_token.strip():
            # Modo bot: usa api_hash do config ou valor padrão
            api_hash = config.get('api_hash')
            if not api_hash or api_hash.strip() == "":
                logger.error("API Hash é obrigatório mesmo usando token de bot!")
                return
            
            # Cria uma sessão específica para o bot para evitar conflitos
            session_name = 'bot_token_session'
            
            # Inicializa o cliente Telegram como bot
            client = TelegramClient(
                session=session_name,
                api_id=api_id,
                api_hash=api_hash
            )
            
            logger.info("Iniciando com token de bot...")
            auth_mode = "bot"
        else:
            # Modo usuário: verifica todas as credenciais necessárias
            api_hash = config.get('api_hash')
            if not api_hash or api_hash.strip() == "":
                logger.error("API Hash é obrigatório para autenticação de usuário!")
                return
                    
            # Inicializa o cliente Telegram com credenciais de usuário
            client = TelegramClient(
                session='bot_session',
                api_id=api_id,
                api_hash=api_hash
            )
            logger.info("Iniciando com credenciais de usuário...")
            
            # Define o modo de autenticação
            auth_mode = "user"
        
        # Inicializa o banco de dados
        db = DatabaseManager()
        logger.info("Banco de dados inicializado")
        
        # Registra os handlers administrativos primeiro (que funcionam mesmo quando inativo)
        client.add_event_handler(
            handle_help_command, 
            events.NewMessage()
        )
        client.add_event_handler(
            handle_status_command, 
            events.NewMessage()
        )
        # Registra o handler para comandos de configuração
        client.add_event_handler(
            handle_config_commands, 
            events.NewMessage()
        )
        
        # Registra o handler para comandos de stickers (que também podem ser administrativos)
        client.add_event_handler(
            handle_sticker_commands, 
            events.NewMessage()
        )
        
        # Para garantir que o processamento de exclusão seja realmente instantâneo,
        # registra o handler de exclusão PRIMEIRO para garantir processamento prioritário
        client.add_event_handler(
            handle_delete_with_lock,  # Modificado para não precisar de client como parâmetro
            events.MessageDeleted(chats=config['source_chats'])
        )
        
        # Pequeno delay para garantir prioridade de exclusão
        await asyncio.sleep(0.1)
        
        # Outros handlers com prioridade normal - registra depois para menor prioridade
        client.add_event_handler(
            handle_message_with_lock,  # Modificado para não precisar de client como parâmetro
            events.NewMessage(chats=config['source_chats'])
        )
        
        client.add_event_handler(
            handle_edit, 
            events.MessageEdited(chats=config['source_chats'])
        )
        
        # Registra handlers auxiliares
        client.add_event_handler(
            extract_ids, 
            events.NewMessage(chats=config['source_chats'])
        )
        client.add_event_handler(
            download_media, 
            events.NewMessage(chats=config['source_chats'])
        )
        
        logger.info("Handlers registrados com sucesso.")
        
        # Configura o agendador
        setup_scheduler(client)
        logger.info("Agendador ativado")
        
        if is_limit_reached():
            logger.error("Limite de ações atingido. Acesse https://global.tribopay.com.br/qpqbz5koox ou entre em contato pelo perfil t.me/roge_rdv para adquirir a versão completa.")
            print("⚠️ Limite de ações atingido. Acesse https://global.tribopay.com.br/qpqbz5koox ou entre em contato pelo perfil t.me/roge_rdv para adquirir a versão completa.")
            return

        # Incrementa o contador de ações
        if not increment_action_count():
            logger.error("Erro ao incrementar contador de ações. Acesso bloqueado.")
            print("⚠️ Acesso bloqueado. Acesse https://global.tribopay.com.br/qpqbz5koox ou entre em contato pelo perfil t.me/roge_rdv para adquirir a versão completa.")
            return

        # Inicia o cliente com o método correto de autenticação
        try:
            if (auth_mode == "bot"):
                # Autenticação via token de bot (com tratamento de erro específico)
                logger.info(f"Tentando conexão com token do bot...")
                await client.start(bot_token=bot_token)
                
                # Verifica se o login foi bem-sucedido
                me = await client.get_me()
                if me is None:
                    logger.error("Falha ao conectar com o token do bot!")
                    return
                    
                if not me.bot:
                    logger.warning("Conectado, mas a conta não é um bot! Verifique o token.")
                
                logger.info(f"Bot conectado como @{me.username} (ID: {me.id})")
            else:
                # Autenticação via número de telefone (conta de usuário)
                await client.start(phone=lambda: input("Digite seu número de telefone: "))
                logger.info("Bot conectado ao Telegram usando conta de usuário!")
            
            # Verifica permissões nos chats configurados
            logger.info("Verificando permissões nos chats configurados...")
            permissions = await verify_permissions(client, config)
            
            if not permissions or not permissions.get('all_accessible'):
                logger.warning("⚠️ Alguns chats não estão acessíveis. O bot pode funcionar com limitações.")
                
                # Notifica o usuário sobre problemas de permissão
                notify_chat = config.get('chat_id')
                if notify_chat:
                    problematic_chats = []
                    
                    for chat_id, status in permissions.get('source_chats', {}).items():
                        if not status['is_member']:
                            problematic_chats.append(f"- Chat origem: {status['title']} ({chat_id}): {status['error']}")
                    
                    for chat_id, status in permissions.get('destination_chats', {}).items():
                        if not status['is_member']:
                            problematic_chats.append(f"- Chat destino: {status['title']} ({chat_id}): {status['error']}")
                    
                    if problematic_chats:
                        warning_msg = "⚠️ **Atenção: Problemas de permissão detectados**\n\n"
                        warning_msg += "Os seguintes chats não estão acessíveis:\n\n"
                        warning_msg += "\n".join(problematic_chats)
                        warning_msg += "\n\nAdicione o bot a esses chats ou verifique as permissões."
                        
                        await client.send_message(entity=notify_chat, message=warning_msg)
            else:
                logger.info("✅ Todos os chats configurados estão acessíveis!")
                
        except Exception as auth_error:
            logger.error(f"Erro de autenticação: {auth_error}")
            if auth_mode == "bot":
                logger.error("Falha na autenticação com token de bot. Verifique se o token é válido.")
            else:
                logger.error("Falha na autenticação de usuário.")
            return
        
        # Envia mensagem de boas-vindas após a conexão
        await send_welcome_message(client)
        
        # Substitui a linha original client.run_until_disconnected() 
        # por uma implementação mais robusta que responde ao CTRL+C
        try:
            logger.info("Bot em execução. Pressione CTRL+C para parar.")
            while not shutdown_event.is_set():
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            pass
        
    except Exception as e:
        logger.error(f"Erro crítico: {e}", exc_info=True)
    finally:
        # Garante que o shutdown seja chamado mesmo se ocorrer algum erro
        if client and client.is_connected():
            await shutdown(client)

if __name__ == "__main__":
    # Configura um manipulador de exceções global
    def handle_global_exception(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            print("\nPrograma terminado por KeyboardInterrupt (CTRL+C)")
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        logger.error("Exceção não tratada:", exc_info=(exc_type, exc_value, exc_traceback))
    
    # Instala o manipulador de exceções global
    sys.excepthook = handle_global_exception
    
    try:
        # No Windows, tenta configurar o handler para CTRL+C usando win32api se disponível
        if os.name == 'nt' and HAS_WIN32API:
            try:
                def handle_ctrl_c(ctrl_type):
                    if ctrl_type == 0:  # CTRL_C_EVENT
                        print("CTRL+C detectado, finalizando...")
                        asyncio.create_task(shutdown(None))
                        return True  # Sinaliza que o evento foi tratado
                    return False
                win32api.SetConsoleCtrlHandler(handle_ctrl_c, True)
                print("Handler de CTRL+C instalado via win32api")
            except Exception as e:
                print(f"Erro ao configurar handler de CTRL+C via win32api: {e}")
        
        # Executa o programa principal com tratamento de KeyboardInterrupt
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nPrograma terminado por KeyboardInterrupt (CTRL+C)")
    except Exception as e:
        logger.error(f"Erro fatal na execução principal: {e}", exc_info=True)
        sys.exit(1)
