from telethon import events
from utils.logger import logger
from utils.scheduler import reload_scheduler
from utils.resource_handler import get_config_path, load_config, save_config
import json
import os
import re
from datetime import datetime

# Usa o caminho de configuração do resource handler
CONFIG_PATH = get_config_path()

# Lista de comandos administrativos que sempre funcionam
ADMIN_COMMANDS = ['/help', '/status', '/config', '/block', '/unblock', '/blocklist', 
                 '/replace', '/unreplace', '/replacelist', '/schedule', '/settime', 
                 '/showschedule', '/deletestatus', '/clearmappings', '/textoonly']

async def handle_config_commands(event):
    """
    Handler para comandos relacionados à configuração do bot.
    
    Comandos:
    /block [palavra] - Adiciona uma palavra à lista de bloqueadas
    /unblock [palavra] - Remove uma palavra da lista de bloqueadas
    /blocklist - Mostra a lista de palavras bloqueadas
    
    /replace [original]=[substituto] - Adiciona uma substituição de texto
    /unreplace [original] - Remove uma substituição de texto
    /replacelist - Mostra a lista de substituições de texto
    
    /schedule on/off - Ativa/desativa o agendamento
    /settime start [HH:MM] - Define horário de início
    /settime end [HH:MM] - Define horário de término
    /showschedule - Mostra as configurações de agendamento
    
    /textoonly on/off - Ativa/desativa replicação apenas de texto
    
    /config - Mostra todas as configurações
    """
    try:
        if not event.raw_text:
            return
            
        command_full = event.raw_text.strip()
        command_parts = command_full.split()
        command_name = command_parts[0].lower()
        
        # ----- COMANDOS PARA PALAVRAS BLOQUEADAS -----
        
        # Adicionar palavra bloqueada
        if command_name == "/block" and len(command_parts) > 1:
            # Extrai a palavra a ser bloqueada (pode conter espaços)
            word = " ".join(command_parts[1:]).lower()
            
            # Carrega a configuração atual usando o resource handler
            config = load_config()
            
            # Garante que a lista existe
            if 'blocked_words' not in config:
                config['blocked_words'] = []
                
            # Verifica se a palavra já está na lista
            if word in config['blocked_words']:
                await event.respond(f"⚠️ A palavra '{word}' já está na lista de bloqueadas.")
                return
                
            # Adiciona a palavra à lista
            config['blocked_words'].append(word)
            
            # Salva a configuração usando o resource handler
            save_config(config)
                
            await event.respond(f"✅ Palavra '{word}' adicionada à lista de bloqueadas.")
            return
            
        # Remover palavra bloqueada
        elif command_name == "/unblock" and len(command_parts) > 1:
            # Extrai a palavra a ser desbloqueada
            word = " ".join(command_parts[1:]).lower()
            
            # Carrega a configuração atual usando o resource handler
            config = load_config()
                
            # Verifica se a lista existe
            if 'blocked_words' not in config or word not in config['blocked_words']:
                await event.respond(f"⚠️ A palavra '{word}' não está na lista de bloqueadas.")
                return
                
            # Remove a palavra da lista
            config['blocked_words'].remove(word)
            
            # Salva a configuração usando o resource handler
            save_config(config)
                
            await event.respond(f"✅ Palavra '{word}' removida da lista de bloqueadas.")
            return
            
        # Listar palavras bloqueadas
        elif command_name == "/blocklist":
            # Carrega a configuração atual usando o resource handler
            config = load_config()
                
            # Verifica se há palavras bloqueadas
            blocked_words = config.get('blocked_words', [])
            
            if not blocked_words:
                await event.respond("📋 Não há palavras bloqueadas.")
                return
                
            # Formata a lista de palavras bloqueadas
            blocked_list = "📋 **Palavras bloqueadas:**\n\n"
            for i, word in enumerate(blocked_words, 1):
                blocked_list += f"{i}. `{word}`\n"
                
            await event.respond(blocked_list)
            return
            
        # ----- COMANDOS PARA SUBSTITUIÇÕES DE TEXTO -----
        
        # Adicionar substituição de texto
        elif command_name == "/replace" and len(command_parts) > 1:
            # Extrai o texto completo após o comando
            replace_text = " ".join(command_parts[1:])
            
            # Verifica se o formato é correto (original=substituto)
            if "=" not in replace_text:
                await event.respond("⚠️ Formato incorreto. Use: `/replace palavra=substituto` (sem espaços antes/depois do sinal =)")
                return
                
            # Divide em original e substituto
            original, substitute = replace_text.split("=", 1)
            original = original.strip()
            substitute = substitute.strip()
            
            # Verifica se os campos estão vazios
            if not original or not substitute:
                await event.respond("⚠️ Texto original e substituto não podem estar vazios")
                return
            
            # Garante que estamos usando UTF-8 para caracteres especiais
            if isinstance(original, bytes):
                original = original.decode('utf-8', errors='replace')
            if isinstance(substitute, bytes):
                substitute = substitute.decode('utf-8', errors='replace')
            
            # Carrega a configuração atual usando o resource handler
            config = load_config()
                
            # Garante que o dicionário existe
            if 'replacements' not in config:
                config['replacements'] = {}
                
            # Adiciona a substituição
            config['replacements'][original] = substitute
            
            # Salva a configuração usando o resource handler
            save_config(config)
                
            # Responder com emoji e cores para facilitar visualização
            await event.respond(f"✅ Substituição adicionada com sucesso!\n\n📝 Texto original: `{original}`\n📝 Substituído por: `{substitute}`\n\nExemplo: `{original}` → `{substitute}`")
            return
            
        # Remover substituição de texto
        elif command_name == "/unreplace" and len(command_parts) > 1:
            # Extrai o texto original
            original = " ".join(command_parts[1:])
            
            # Carrega a configuração atual usando o resource handler
            config = load_config()
                
            # Verifica se existe o dicionário e a chave
            if 'replacements' not in config or original not in config['replacements']:
                await event.respond(f"⚠️ Não há substituição configurada para '{original}'.")
                return
                
            # Remove a substituição
            substitute = config['replacements'][original]
            del config['replacements'][original]
            
            # Salva a configuração usando o resource handler
            save_config(config)
                
            await event.respond(f"✅ Substituição removida: '{original}' → '{substitute}'")
            return
            
        # Listar substituições de texto
        elif command_name == "/replacelist":
            # Carrega a configuração atual usando o resource handler
            config = load_config()
                
            # Verifica se há substituições
            replacements = config.get('replacements', {})
            
            if not replacements:
                await event.respond("📋 Não há substituições de texto configuradas.")
                return
                
            # Formata a lista de substituições
            replace_list = "📋 **Substituições de texto configuradas:**\n\n"
            for i, (original, substitute) in enumerate(replacements.items(), 1):
                replace_list += f"{i}. `{original}` → `{substitute}`\n"
                
            await event.respond(replace_list)
            return
            
        # ----- COMANDOS PARA AGENDAMENTO -----
        
        # Ativar/desativar agendamento
        elif command_name == "/schedule" and len(command_parts) > 1:
            # Verifica o parâmetro (on/off)
            param = command_parts[1].lower()
            
            if param not in ["on", "off"]:
                await event.respond("⚠️ Parâmetro inválido. Use 'on' ou 'off'.")
                return
                
            # Converte para booleano
            enable = param == "on"
            
            # Carrega a configuração atual usando o resource handler
            config = load_config()
                
            # Garante que o dicionário existe
            if 'schedule' not in config:
                config['schedule'] = {}
                
            # Atualiza a configuração
            config['schedule']['enable'] = enable
            
            # Salva a configuração usando o resource handler
            save_config(config)
            
            # Recarrega o agendador
            await reload_scheduler(event.client)
                
            await event.respond(f"✅ Agendamento {'ativado' if enable else 'desativado'}.")
            return
            
        # Definir horários
        elif command_name == "/settime" and len(command_parts) > 2:
            # Verifica o tipo (start/end)
            time_type = command_parts[1].lower()
            
            if time_type not in ["start", "end"]:
                await event.respond("⚠️ Tipo inválido. Use 'start' ou 'end'.")
                return
                
            # Verifica o formato da hora (HH:MM)
            time_str = command_parts[2]
            if not re.match(r"^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$", time_str):
                await event.respond("⚠️ Formato de hora inválido. Use o formato HH:MM (ex: 08:30).")
                return
                
            # Carrega a configuração atual usando o resource handler
            config = load_config()
                
            # Garante que o dicionário existe
            if 'schedule' not in config:
                config['schedule'] = {}
                
            # Atualiza a configuração
            config['schedule'][f'{time_type}_time'] = time_str
            
            # Salva a configuração usando o resource handler
            save_config(config)
            
            # Recarrega o agendador para aplicar as alterações
            await reload_scheduler(event.client)
                
            await event.respond(f"✅ Horário de {'início' if time_type == 'start' else 'término'} definido para {time_str}.")
            return
            
        # Mostrar configuração de agendamento
        elif command_name == "/showschedule":
            # Carrega a configuração atual usando o resource handler
            config = load_config()
                
            # Verifica se há configuração de agendamento
            schedule = config.get('schedule', {})
            
            # Formata a mensagem
            enable = schedule.get('enable', False)
            start_time = schedule.get('start_time', 'Não definido')
            end_time = schedule.get('end_time', 'Não definido')
            
            # Verifica se o bot está no período ativo
            now = datetime.now().time()
            is_active_period = False
            
            if start_time != 'Não definido' and end_time != 'Não definido':
                start_parts = start_time.split(':')
                end_parts = end_time.split(':')
                
                start_hour, start_minute = int(start_parts[0]), int(start_parts[1])
                end_hour, end_minute = int(end_parts[0]), int(end_parts[1])
                
                current_hour, current_minute = now.hour, now.minute
                
                if start_hour < end_hour:
                    # Período normal
                    is_active_period = (current_hour > start_hour or (current_hour == start_hour and current_minute >= start_minute)) and \
                                       (current_hour < end_hour or (current_hour == end_hour and current_minute < end_minute))
                else:
                    # Período que cruza a meia-noite
                    is_active_period = (current_hour > start_hour or (current_hour == start_hour and current_minute >= start_minute)) or \
                                       (current_hour < end_hour or (current_hour == end_hour and current_minute < end_minute))
            
            schedule_msg = f"""
⏰ **Configuração de Agendamento:**

• Status: {'✅ Ativado' if enable else '❌ Desativado'}
• Horário de início: {start_time}
• Horário de término: {end_time}

➡️ O bot {'processará' if enable else 'não processará'} mensagens entre {start_time} e {end_time}.
🔄 Estado atual: {'🟢 Ativo' if (enable and is_active_period) else '🔴 Inativo'}
            """
            
            await event.respond(schedule_msg)
            return
            
        # ----- COMANDO PARA REPLICAR APENAS TEXTO -----
        
        # Ativar/desativar replicação apenas de texto
        elif command_name == "/textoonly" and len(command_parts) > 1:
            # Verifica o parâmetro (on/off)
            param = command_parts[1].lower()
            
            if param not in ["on", "off"]:
                await event.respond("⚠️ Parâmetro inválido. Use 'on' ou 'off'.")
                return
                
            # Converte para booleano
            enable = param == "on"
            
            # Carrega a configuração atual usando o resource handler
            config = load_config()
                
            # Atualiza a configuração
            config['replicar_apenas_texto'] = enable
            
            # Salva a configuração usando o resource handler
            save_config(config)
                
            await event.respond(f"✅ Modo 'replicar apenas texto' {'ativado' if enable else 'desativado'}.\n\n" + 
                              f"{'🔤 O bot agora replicará APENAS mensagens de texto.' if enable else '🔤📷 O bot agora replicará mensagens de texto E mídia.'}")
            return
            
        # ----- COMANDOS GERAIS -----
        
        # Mostrar todas as configurações
        elif command_name == "/config":
            # Carrega a configuração atual usando o resource handler
            config = load_config()
                
            # Formata a mensagem
            blocked_count = len(config.get('blocked_words', []))
            replace_count = len(config.get('replacements', {}))
            source_count = len(config.get('source_chats', []))
            dest_count = len(config.get('destination_chats', []))
            sticker_count = len(config.get('sticker_replacements', {}))
            image_count = len(config.get('image_replacements', {}))
            schedule = config.get('schedule', {})
            
            config_msg = f"""
⚙️ **Configuração do Bot:**

• Chats de origem: {source_count}
• Chats de destino: {dest_count}
• Palavras bloqueadas: {blocked_count}
• Substituições de texto: {replace_count}
• Substituições de stickers: {sticker_count}
• Substituições de imagens: {image_count}

📅 **Agendamento:**
• Status: {'✅ Ativado' if schedule.get('enable', False) else '❌ Desativado'}
• Horário: {schedule.get('start_time', 'N/A')} - {schedule.get('end_time', 'N/A')}

🔧 **Outros:**
• Apenas texto: {'✅ Sim' if config.get('replicar_apenas_texto', False) else '❌ Não'}
• Nível de log: {config.get('log_level', 'INFO')}

📝 Use /help para ver todos os comandos disponíveis.
            """
            
            await event.respond(config_msg)
            return

        # ----- COMANDOS PARA GERENCIAMENTO DE MENSAGENS -----
        
        # Comando para verificar o status da sincronização de deleções
        elif command_name == "/deletestatus":
            try:
                # Obtém estatísticas do banco de dados
                from database.db_manager import DatabaseManager
                db = DatabaseManager()
                
                # Obtém contagem de mapeamentos
                cursor = db.conn.execute("SELECT COUNT(*) FROM messages")
                total_mappings = cursor.fetchone()[0]
                
                # Obtém contagem dos últimos dias
                cursor = db.conn.execute("SELECT COUNT(*) FROM messages WHERE timestamp > datetime('now', '-1 day')")
                recent_mappings = cursor.fetchone()[0]
                
                status_message = f"""
📊 **Status de Sincronização de Deleções:**

• Total de mapeamentos: {total_mappings}
• Mapeamentos recentes (24h): {recent_mappings}

ℹ️ **Como funciona:**
O sistema de deleção sincronizada depende do mapeamento entre mensagens originais e replicadas.
Quando uma mensagem é apagada no grupo de origem, o bot procura seu ID correspondente no banco 
de dados e tenta apagá-la no grupo de destino.

⚠️ **Se as deleções não estiverem funcionando:**
1. Certifique-se de que o bot tem permissões de admin para apagar mensagens
2. Verifique se há mapeamentos recentes no banco de dados
3. Use /clearmappings para limpar mapeamentos antigos se necessário

📝 As mensagens mais antigas que 30 dias são automaticamente removidas do banco.
                """
                
                await event.respond(status_message)
                
            except Exception as e:
                logger.error(f"Erro ao verificar status das deleções: {e}")
                await event.respond(f"❌ Erro ao verificar status: {e}")
            
            return
        
        # Comando para limpar mapeamentos
        elif command_name == "/clearmappings" and len(command_parts) > 1:
            try:
                days = int(command_parts[1])
                if days <= 0:
                    await event.respond("⚠️ O número de dias deve ser maior que zero.")
                    return
                
                # Limpa mapeamentos mais antigos que o número especificado de dias
                from database.db_manager import DatabaseManager
                db = DatabaseManager()
                
                # Obtém contagem antes da limpeza
                cursor = db.conn.execute("SELECT COUNT(*) FROM messages")
                before_count = cursor.fetchone()[0]
                
                # Executa a limpeza
                db.conn.execute(f"DELETE FROM messages WHERE timestamp < datetime('now', '-{days} day')")
                db.conn.commit()
                
                # Obtém contagem após a limpeza
                cursor = db.conn.execute("SELECT COUNT(*) FROM messages")
                after_count = cursor.fetchone()[0]
                
                # Otimiza o banco
                db.conn.execute("VACUUM")
                db.conn.commit()
                
                removed = before_count - after_count
                
                await event.respond(f"✅ Limpeza concluída:\n• Mapeamentos removidos: {removed}\n• Mapeamentos restantes: {after_count}")
                
            except ValueError:
                await event.respond("⚠️ Formato inválido. Use: /clearmappings [dias]")
            except Exception as e:
                logger.error(f"Erro ao limpar mapeamentos: {e}")
                await event.respond(f"❌ Erro ao limpar mapeamentos: {e}")
            
            return
            
    except Exception as e:
        logger.error(f"Erro ao processar comando de configuração: {e}", exc_info=True)
        await event.respond(f"❌ Erro ao processar comando: {e}")
