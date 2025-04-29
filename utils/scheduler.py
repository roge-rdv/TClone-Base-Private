from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime, time
import json
import logging
import os
from utils.resource_handler import load_config, get_config_path

logger = logging.getLogger('TelegramForwarderBot')

# Variável global para controle do estado do bot
is_active = True  # Começa como ativo por padrão
# Cliente Telegram para enviar notificações
telegram_client = None
# Armazena a instância do agendador para controle global
current_scheduler = None

async def notify_status_change(status: bool):
    """Notifica mudança de status para o chat configurado."""
    try:
        if telegram_client is None:
            return
            
        # Carrega configurações usando o resource handler para garantir consistência
        config = load_config()
            
        # Obtém o chat_id para enviar notificações
        notification_chat = config.get('chat_id')
        if not notification_chat:
            return
            
        # Prepara a mensagem com base no status
        now = datetime.now().strftime("%H:%M:%S")
        if status:
            message = f"⚡ **Bot Ativado** ⚡\n\nO bot foi ativado pelo agendamento às {now} e agora está replicando mensagens."
        else:
            message = f"⏸️ **Bot Pausado** ⏸️\n\nO bot foi pausado pelo agendamento às {now} e não está mais replicando mensagens."
            
        # Envia a notificação
        await telegram_client.send_message(entity=notification_chat, message=message)
        logger.info(f"Notificação de {'ativação' if status else 'pausa'} enviada para {notification_chat}")
    except Exception as e:
        logger.error(f"Erro ao enviar notificação de status: {e}")

async def toggle_active_status(status: bool):
    """Ativa/desativa o processamento de mensagens."""
    global is_active
    
    # Garantir que a variável tenha visibilidade global
    current_status = is_active
    
    # Registra a solicitação de alteração de status
    logger.info(f"Solicitação para {'ativar' if status else 'desativar'} o bot. Status atual: {'ativo' if current_status else 'inativo'}")
    
    # Somente prossegue se houver mudança de status
    if current_status != status:
        # Importante: modifica a variável global
        is_active = status
        
        # Log mais descritivo para debug
        logger.info(f"Bot {'ativado' if status else 'desativado'} pelo agendador. Status anterior: {'ativo' if current_status else 'inativo'}")
        
        # Força a atualização imediata via variável global
        # Isso garante que outras partes do código vejam o novo valor
        globals()['is_active'] = status
        
        # Envia notificação sobre a mudança de status
        await notify_status_change(status)
    else:
        logger.info(f"Estado do bot já está como {'ativo' if status else 'inativo'}, sem mudanças")

def _is_time_between(start_time_str, end_time_str, current_time=None):
    """Verifica se o horário atual está entre start_time e end_time."""
    # Se não for informado o horário atual, usa o horário atual do sistema
    if current_time is None:
        current_time = datetime.now().time()
    elif isinstance(current_time, datetime):
        current_time = current_time.time()
        
    # Converte as strings de hora para objetos time
    def parse_time(time_str):
        parts = time_str.split(':')
        hour = int(parts[0])
        minute = int(parts[1] if len(parts) > 1 else 0)
        return time(hour, minute)
        
    start_time = parse_time(start_time_str)
    end_time = parse_time(end_time_str)
    
    # Se o período não atravessa a meia-noite
    if start_time <= end_time:
        return start_time <= current_time <= end_time
    # Se o período atravessa a meia-noite
    else:
        return current_time >= start_time or current_time <= end_time

def setup_scheduler(client=None):
    """Configura o agendador com base no config.json."""
    global telegram_client
    global is_active
    global current_scheduler
    
    # Armazena o cliente para uso nas notificações
    telegram_client = client
    
    # Shutdown a previous scheduler if exists with better error handling
    if current_scheduler is not None:
        try:
            # Check if the scheduler is running before attempting to shut it down
            if hasattr(current_scheduler, 'running') and current_scheduler.running:
                current_scheduler.shutdown(wait=False)
                logger.info("Agendador anterior desligado")
            else:
                logger.debug("Agendador anterior não estava em execução")
        except Exception as e:
            logger.debug(f"Aviso ao desligar agendador anterior: {str(e)}")
    
    # Create a new scheduler
    scheduler = AsyncIOScheduler()
    current_scheduler = scheduler
    
    try:
        # Usa resource_handler para garantir consistência
        config_path = get_config_path()
        config = load_config()
        
        schedule_config = config.get('schedule', {})
        
        if schedule_config.get('enable', False):
            # Extrai horários de início e fim
            start_time = schedule_config.get('start_time', '00:00')
            end_time = schedule_config.get('end_time', '00:00')
            
            # Verifica horários inválidos
            if start_time == end_time:
                logger.warning("Horários de início e fim são idênticos. Agendamento pode não funcionar corretamente.")
            
            # Verifica se o horário atual está dentro do período ativo
            current_is_active = _is_time_between(start_time, end_time)
            
            # Define o estado inicial do bot
            is_active = current_is_active
            logger.info(f"Estado inicial do bot definido como: {'ativo' if is_active else 'inativo'}")
            
            # Extrai as horas e minutos para configurar os triggers
            start_hour, start_minute = map(int, start_time.split(':'))
            end_hour, end_minute = map(int, end_time.split(':'))

            logger.info(f"Agendamento: {start_time} - {end_time}, estado atual: {'ativo' if is_active else 'inativo'}")

            # Configura jobs do agendador
            # Job para ativar o bot
            scheduler.add_job(
                toggle_active_status,
                trigger=CronTrigger(hour=start_hour, minute=start_minute),
                args=[True],  # Ativar no start_time
                id='activate_bot',
                max_instances=1,
                replace_existing=True
            )
            
            # Job para desativar o bot
            scheduler.add_job(
                toggle_active_status,
                trigger=CronTrigger(hour=end_hour, minute=end_minute),
                args=[False],  # Desativar no end_time
                id='deactivate_bot',
                max_instances=1,
                replace_existing=True
            )
            
            # Add a job that logs next scheduled activations/deactivations
            scheduler.add_job(
                log_next_schedule_events,
                'interval',
                minutes=15,
                id='log_schedule',
                max_instances=1,
                replace_existing=True
            )
            
            # Log first schedule info immediately
            log_next_schedule_events()
            
            logger.info(f"Agendador configurado: ativo de {start_time} até {end_time}")
            logger.info(f"Próxima ativação: {start_hour:02d}:{start_minute:02d}, próxima desativação: {end_hour:02d}:{end_minute:02d}")
        else:
            logger.info("Agendamento desabilitado no config.json.")
            is_active = True  # Se o agendamento estiver desabilitado, o bot estará sempre ativo
        
    except Exception as e:
        logger.error(f"Erro ao configurar agendador: {e}", exc_info=True)
        is_active = True  # Em caso de erro, o bot deve ficar ativo por padrão
    
    # Start the scheduler
    try:
        scheduler.start()
        logger.info("Agendador iniciado com sucesso")
    except Exception as e:
        logger.error(f"Erro ao iniciar o agendador: {e}")
    
    return scheduler

def log_next_schedule_events():
    """Logs the next scheduled activation and deactivation times."""
    try:
        if current_scheduler is None:
            logger.debug("Não é possível registrar próximos eventos - scheduler não inicializado")
            return
            
        # Get all jobs
        jobs = current_scheduler.get_jobs()
        
        # Find activation and deactivation jobs
        activation_job = None
        deactivation_job = None
        
        for job in jobs:
            if job.id == 'activate_bot':
                activation_job = job
            elif job.id == 'deactivate_bot':
                deactivation_job = job
        
        # Check if jobs are properly scheduled and have next_run_time
        if activation_job:
            try:
                if hasattr(activation_job, 'next_run_time') and activation_job.next_run_time:
                    logger.info(f"Próxima ativação do bot: {activation_job.next_run_time.strftime('%Y-%m-%d %H:%M:%S')}")
                else:
                    # If next_run_time isn't available, log with the trigger's hour/minute
                    if hasattr(activation_job, 'trigger') and hasattr(activation_job.trigger, 'fields'):
                        fields = activation_job.trigger.fields
                        hour = fields[5].get_value(datetime.now())
                        minute = fields[6].get_value(datetime.now())
                        logger.info(f"Próxima ativação do bot agendada para: {hour:02d}:{minute:02d}")
            except Exception as e:
                logger.debug(f"Não foi possível determinar próxima ativação: {e}")
                
        if deactivation_job:
            try:
                if hasattr(deactivation_job, 'next_run_time') and deactivation_job.next_run_time:
                    logger.info(f"Próxima desativação do bot: {deactivation_job.next_run_time.strftime('%Y-%m-%d %H:%M:%S')}")
                else:
                    # If next_run_time isn't available, log with the trigger's hour/minute
                    if hasattr(deactivation_job, 'trigger') and hasattr(deactivation_job.trigger, 'fields'):
                        fields = deactivation_job.trigger.fields
                        hour = fields[5].get_value(datetime.now())
                        minute = fields[6].get_value(datetime.now())
                        logger.info(f"Próxima desativação do bot agendada para: {hour:02d}:{minute:02d}")
            except Exception as e:
                logger.debug(f"Não foi possível determinar próxima desativação: {e}")
    except Exception as e:
        logger.error(f"Erro ao registrar próximos eventos de agendamento: {e}")

def check_schedule_status():
    """Verifica periodicamente se o estado atual corresponde ao esperado com base no horário."""
    global is_active
    
    try:
        # Load current configuration
        config = load_config()
        schedule_config = config.get('schedule', {})
        
        # Only check if scheduling is enabled
        if schedule_config.get('enable', False):
            start_time = schedule_config.get('start_time', '00:00')
            end_time = schedule_config.get('end_time', '00:00')
            
            # Check if we're in the active time window
            should_be_active = _is_time_between(start_time, end_time)
            
            # If there's a mismatch, fix it
            if should_be_active != is_active:
                logger.warning(f"Detectada inconsistência no estado do bot: deveria estar {'ativo' if should_be_active else 'inativo'}, mas está {'ativo' if is_active else 'inativo'}")
                is_active = should_be_active
                # Force global update
                globals()['is_active'] = should_be_active
                logger.info(f"Estado corrigido para: {'ativo' if should_be_active else 'inativo'}")
                
                # Notify about the change asynchronously
                if telegram_client:
                    import asyncio
                    asyncio.create_task(notify_status_change(should_be_active))
    
    except Exception as e:
        logger.error(f"Erro ao verificar status do agendamento: {e}")

# Função para recarregar o agendador quando as configurações são alteradas
async def reload_scheduler(client=None):
    """Recarrega o agendador depois que as configurações forem alteradas."""
    global telegram_client
    global current_scheduler
    
    if client:
        telegram_client = client
    
    # Stoppa o agendador atual se existir with improved error handling
    if current_scheduler is not None:
        try:
            # Only attempt to shut down if the scheduler exists and is running
            if hasattr(current_scheduler, 'running'):
                if current_scheduler.running:
                    try:
                        # Use a more defensive approach to shutdown
                        current_scheduler.shutdown(wait=False)
                        logger.info("Agendador anterior desligado para recarga")
                    except Exception as e:
                        logger.debug(f"Aviso ao tentar desligar agendador: {str(e)}")
                else:
                    logger.debug("Agendador não estava em execução, nenhum desligamento necessário")
        except Exception as e:
            logger.debug(f"Erro ao acessar o estado do agendador: {str(e)}")
            # Continue anyway, we'll create a new scheduler
    
    # Configura um novo agendador
    logger.info("Reconfigurando agendador após alteração de configurações")
    new_scheduler = setup_scheduler(telegram_client)
    current_scheduler = new_scheduler
    return new_scheduler

def get_is_active_status():
    """Função auxiliar para recuperar o status atual."""
    global is_active
    return is_active
