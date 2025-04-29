import os
import sys
import shutil
import json
import subprocess
import time

print("Iniciando processo de build do TClone Bot...")

# Verifica e remove pacotes incompatíveis antes de iniciar
def check_incompatible_packages():
    incompatible_packages = [
        "pathlib",  # Obsoleto, já incluído na biblioteca padrão
    ]
    
    for package in incompatible_packages:
        try:
            # Verifica se o pacote está instalado
            result = subprocess.run(
                [sys.executable, "-m", "pip", "show", package],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:  # Pacote está instalado
                print(f"Removendo pacote incompatível: {package}")
                subprocess.run(
                    [sys.executable, "-m", "pip", "uninstall", "-y", package],
                    check=True
                )
                print(f"Pacote {package} removido com sucesso.")
            
        except Exception as e:
            print(f"Erro ao verificar/remover {package}: {e}")

# Executa verificação de pacotes incompatíveis
check_incompatible_packages()

# Verifica se PyInstaller está instalado
try:
    import PyInstaller.__main__
except ImportError:
    print("PyInstaller não encontrado. Instalando...")
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "pyinstaller>=6.10.0"],
            check=True
        )
        import PyInstaller.__main__
        print("PyInstaller instalado com sucesso.")
    except Exception as e:
        print(f"Erro ao instalar PyInstaller: {e}")
        sys.exit(1)

# Cria diretório para arquivos de build se não existir
os.makedirs('build', exist_ok=True)

# Define os argumentos comuns do PyInstaller
def get_pyinstaller_args(has_console=False, suffix=""):
    app_name = "TCloneBot" if not suffix else f"TCloneBot_{suffix}"
    
    args = [
        'main.py',                      # Script principal
        f'--name={app_name}',           # Nome do executável
        '--onefile',                    # Um único arquivo executável
        '--clean',                      # Limpa os caches antes de construir
    ]
    
    # Adiciona o parâmetro console/noconsole
    if not has_console:
        args.append('--noconsole')
    
    # Adiciona imports ocultos (dependências que o PyInstaller pode não detectar)
    hidden_imports = [
        'telethon',
        'sqlite3',
        'apscheduler',
        'apscheduler.triggers.cron',
        'apscheduler.schedulers.asyncio',
        'asyncio',
        'pytz',
        'cryptography',
        'compat'
    ]
    
    # Adiciona os imports ocultos
    for imp in hidden_imports:
        args.append(f'--hidden-import={imp}')
    
    # Adiciona o diretório compat
    args.append('--add-data=compat;compat')
        
    # Configura os diretórios de saída
    args.extend([
        '--distpath=./dist',            # Diretório de saída
        '--workpath=./build',           # Diretório de trabalho
    ])
    
    return args

# Cria hook para os módulos que precisam de tratamento especial
hook_path = "hook-telethon.py"
with open(hook_path, "w") as f:
    f.write("""
# PyInstaller hook for telethon
from PyInstaller.utils.hooks import collect_all

# Collect all modules, binaries and data files for telethon
datas, binaries, hiddenimports = collect_all('telethon')

# Add additional hidden imports if needed
hiddenimports.extend(['compat', 'compat.imghdr'])
""")

print("Construindo versão COM console (para visualizar logs em tempo real)...")
# Executa o build com console
PyInstaller.__main__.run(get_pyinstaller_args(has_console=True, suffix="console"))

print("Construindo versão SEM console (para uso normal)...")
# Executa o build sem console
PyInstaller.__main__.run(get_pyinstaller_args(has_console=False))

# Cria um config.json de exemplo se não existir
config_example = {
    "api_id": "<seu_api_id>",
    "api_hash": "<seu_api_hash>",
    "bot_token": "<token_do_bot>",
    "source_chats": [-100123456789],
    "destination_chats": [-100987654321],
    "chat_id": 123456789,
    "log_level": "INFO",
    "blocked_words": [],
    "replacements": {},
    "sticker_replacements": {},
    "image_replacements": {},
    "schedule": {
        "enable": False,
        "start_time": "00:00",
        "end_time": "00:00"
    },
    "replicar_apenas_texto": False
}

# Copia o config existente para uma pasta de backup
dist_dir = "dist"
if os.path.exists(os.path.join(dist_dir, "config.json")):
    try:
        os.makedirs(os.path.join(dist_dir, "backup"), exist_ok=True)
        shutil.copy2(
            os.path.join(dist_dir, "config.json"),
            os.path.join(dist_dir, "backup", f"config_backup_{int(time.time())}.json")
        )
        print("Backup do config.json existente criado.")
    except Exception as e:
        print(f"Erro ao criar backup do config.json: {e}")

# Cria diretórios necessários
for directory in ["media", "logs", "data"]:
    os.makedirs(os.path.join(dist_dir, directory), exist_ok=True)

# Copia o arquivo config.json se não existir
config_path = os.path.join(dist_dir, "config.json")
if not os.path.exists(config_path):
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config_example, f, indent=4, ensure_ascii=False)

# Cria README.txt com instruções
readme_path = os.path.join(dist_dir, "README.txt")
with open(readme_path, 'w', encoding='utf-8') as f:
    f.write("""
INSTRUÇÕES DE USO DO TCLONE BOT
===============================

Este pacote contém duas versões do executável:

1. TCloneBot.exe - Versão principal sem janela de console (para uso normal)
2. TCloneBot_console.exe - Versão com janela de console (para diagnóstico de problemas)

CONFIGURAÇÃO:
------------
1. Edite o arquivo config.json com suas informações:
   - api_id: Seu API ID do Telegram
   - api_hash: Seu API Hash do Telegram
   - bot_token: Token do seu bot no Telegram
   - source_chats: IDs dos chats de origem
   - destination_chats: IDs dos chats de destino
   - chat_id: ID para enviar notificações administrativas

PASTAS:
------
- media: Armazena stickers e imagens para substituição
- logs: Contém os arquivos de log do bot
- data: Armazena o banco de dados para sincronização de exclusões

INICIALIZAÇÃO:
-------------
1. Para iniciar normalmente: Execute TCloneBot.exe
2. Para diagnóstico: Execute TCloneBot_console.exe (mostra logs em tempo real)

IMPORTANTE:
----------
- Não mova os executáveis para fora desta pasta
- Mantenha a estrutura de diretórios para o funcionamento correto
- O bot deve ter permissões de administrador nos chats de destino para replicar exclusões

Para mais informações ou suporte, use o comando /help no chat com o bot.
""")

print(f"""
Build concluído com sucesso!

Arquivos gerados em: {os.path.abspath(dist_dir)}

INSTRUÇÕES:
1. Foram criados dois executáveis:
   - TCloneBot.exe (sem console, para uso normal)
   - TCloneBot_console.exe (com console, para diagnóstico)

2. Para verificar se está funcionando corretamente, execute a versão com console (TCloneBot_console.exe)
   que mostrará os logs em tempo real.

3. O arquivo config.json contém todas as configurações e pode ser editado
4. O diretório "media" armazenará stickers e imagens
5. Logs serão salvos no diretório "logs"

IMPORTANTE:
- Não mova os executáveis; mantenha-os junto com config.json
- Preencha as credenciais no config.json se ainda não estiverem preenchidas
""")
