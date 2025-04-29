# TClone Bot - Sincronização Avançada no Telegram

## Sumário
1. [Introdução](#introdução)
2. [Recursos Principais](#recursos-principais)
3. [Como Usar](#como-usar)
4. [Solução de Problemas](#solução-de-problemas)
5. [Licença](#licença)

---

## Introdução

O **TClone Bot** é uma ferramenta poderosa para sincronizar mensagens, edições e exclusões entre múltiplos grupos e canais do Telegram. Este repositório contém apenas o executável do bot, pronto para uso.

---

## Recursos Principais

- **Sincronização Completa**:
  - Replica mensagens, edições e exclusões entre grupos e canais.
- **Filtragem e Substituição**:
  - Bloqueia palavras específicas.
  - Substitui texto, stickers e imagens automaticamente.
- **Agendamento**:
  - Define horários específicos para ativar/desativar o bot.
- **Logs Detalhados**:
  - Registra todas as atividades para facilitar o diagnóstico.

---

## Como Usar

1. **Baixe o Executável**:
   - Faça o download do arquivo `TCloneBot.exe` ou `TCloneBot_console.exe` do repositório.

2. **Configuração Inicial**:
   - Edite o arquivo `config.json` que acompanha o executável.
   - Preencha os campos obrigatórios:
     ```json
     {
         "api_id": "SEU_API_ID",
         "api_hash": "SEU_API_HASH",
         "bot_token": "",  // Opcional, se usar um bot do BotFather
         "source_chats": [-100123456789],  // IDs dos chats de origem
         "destination_chats": [-100987654321],  // IDs dos chats de destino
         "chat_id": 123456789,  // Seu ID pessoal para notificações
         "log_level": "INFO"
     }
     ```

3. **Execute o Bot**:
   - Para uso normal: Execute `TCloneBot.exe`.
   - Para diagnóstico: Execute `TCloneBot_console.exe` (mostra logs em tempo real).

---

## Estrutura do Diretório

Após extrair o pacote, você verá os seguintes arquivos e pastas:

```
TCloneBot/
├── TCloneBot.exe               # Executável principal (sem console)
├── TCloneBot_console.exe       # Executável com console (para diagnóstico)
├── config.json                 # Arquivo de configuração
├── media/                      # Armazena stickers e imagens
├── logs/                       # Contém os arquivos de log
├── data/                       # Dados persistentes (ex: limites de uso)
└── README.txt                  # Instruções de uso
```

---

## Solução de Problemas

### O bot não está respondendo
- Certifique-se de que o arquivo `config.json` foi preenchido corretamente.
- Verifique se o bot tem permissões de administrador nos grupos/canais configurados.
- Consulte os logs no diretório `logs/` para mais detalhes.

### Limite de ações atingido
- O bot possui um limite de ações configurado. Para desbloquear, entre em contato pelo perfil [t.me/roge_rdv](https://t.me/roge_rdv).

---

## Licença

Este projeto está licenciado sob a [MIT License](LICENSE). O executável pode ser usado e distribuído livremente, mas o código-fonte não está incluído neste repositório.

---

© 2025 TClone Bot - Todos os direitos reservados.