from telethon import events
from utils.logger import logger

async def handle_help_command(event):
    """Envia mensagem com a lista de comandos disponíveis."""
    try:
        if event.raw_text.strip().lower() == "/help":
            help_message = """
🤖 **TClone Bot - Comandos Disponíveis** 🤖

📋 **Comandos de Stickers e Imagens:**
• `/replace` - Responda a um sticker com este comando para substituí-lo por outro
• `/replaceimg` - Responda a uma imagem com este comando para substituí-la por outra
• `/list` - Lista todas as substituições de stickers e imagens configuradas
• `/remove ID` - Remove uma substituição de sticker pelo ID original
• `/removeimg ID` - Remove uma substituição de imagem pelo ID original

🔄 **Comandos de Texto:**
• `/block [palavra]` - Adiciona uma palavra à lista de bloqueadas
• `/unblock [palavra]` - Remove uma palavra da lista de bloqueadas
• `/blocklist` - Mostra a lista de palavras bloqueadas
• `/replace [original]=[substituto]` - Adiciona uma substituição de texto
• `/unreplace [original]` - Remove uma substituição de texto
• `/replacelist` - Mostra a lista de substituições de texto
• `/textoonly on/off` - Ativa/desativa replicação apenas de texto

🔄 **Comandos de Sincronização:**
• `/deletestatus` - Verifica o status da sincronização de deleções
• `/clearmappings [dias]` - Limpa mapeamentos mais antigos que o número de dias especificado

⏰ **Comandos de Agendamento:**
• `/schedule on/off` - Ativa/desativa o agendamento
• `/settime start [HH:MM]` - Define horário de início
• `/settime end [HH:MM]` - Define horário de término
• `/showschedule` - Mostra as configurações de agendamento

📊 **Informações:**
• `/status` - Mostra o status atual do bot
• `/config` - Mostra todas as configurações
• `/help` - Exibe esta mensagem de ajuda

🔧 **Configuração:**
• `/save ID` - Responda a um sticker/imagem para salvá-lo com um ID personalizado

Desenvolvido com 💙
            """
            
            await event.respond(help_message)
            logger.info(f"Mensagem de ajuda enviada para o chat {event.chat_id}")
            
    except Exception as e:
        logger.error(f"Erro ao enviar mensagem de ajuda: {e}", exc_info=True)
