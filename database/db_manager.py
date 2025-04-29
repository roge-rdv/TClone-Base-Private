import sqlite3
import os
import logging
import time
from utils.resource_handler import get_database_path
from utils.logger import logger

class DatabaseManager:
    def __init__(self, db_path: str = None):
        # Usar o caminho do banco de dados do resource handler
        self.db_path = db_path or get_database_path()
        
        # Garantir que o diretório do banco de dados existe
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        self.conn = None
        self._connect()
        self._create_table()
        self._maintenance()

    def _connect(self):
        """Estabelece a conexão com o banco de dados."""
        try:
            # Fecha conexão anterior se estiver aberta
            if self.conn:
                self.conn.close()
            
            # Abre nova conexão
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False, isolation_level=None)
            # Configura para evitar bloqueios persistentes
            self.conn.execute("PRAGMA journal_mode=WAL")
            self.conn.execute("PRAGMA busy_timeout=5000")
        except sqlite3.Error as e:
            logger.error(f"Erro ao conectar ao banco de dados: {e}")

    def _create_table(self) -> None:
        """Cria a tabela para mapeamento de IDs."""
        try:
            self.conn.execute('''
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id INTEGER,
                    original_message_id INTEGER,
                    destination_message_id INTEGER,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(chat_id, original_message_id)
                )
            ''')
        except sqlite3.Error as e:
            logger.error(f"Erro ao criar tabela: {e}")
            self._reconnect()
    
    def _reconnect(self):
        """Reconecta ao banco de dados em caso de erro."""
        time.sleep(1)  # Pequeno delay antes de reconectar
        self._connect()
    
    def _execute_with_retry(self, sql, params=()):
        """Executa comando SQL com retry em caso de bloqueio."""
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                return self.conn.execute(sql, params)
            except sqlite3.OperationalError as e:
                if "database is locked" in str(e) and retry_count < max_retries - 1:
                    retry_count += 1
                    logger.warning(f"Banco de dados bloqueado, tentativa {retry_count}/{max_retries}")
                    time.sleep(retry_count * 0.5)  # Tempo crescente entre tentativas
                    self._reconnect()
                else:
                    raise
            except sqlite3.Error as e:
                logger.error(f"Erro ao executar SQL: {e}")
                raise
    
    def _maintenance(self) -> None:
        """Realiza manutenção periódica do banco de dados."""
        try:
            # Conta registros antes da limpeza
            cursor = self._execute_with_retry("SELECT COUNT(*) FROM messages")
            count_before = cursor.fetchone()[0]
            
            # Remove mapeamentos mais antigos que 30 dias
            self._execute_with_retry('''
                DELETE FROM messages
                WHERE timestamp < datetime('now', '-30 day')
            ''')
            
            # Conta registros após a limpeza
            cursor = self._execute_with_retry("SELECT COUNT(*) FROM messages")
            count_after = cursor.fetchone()[0]
            
            # Fecha conexão antes do VACUUM
            self.conn.close()
            
            # Reconecta e executa VACUUM em uma nova conexão
            temp_conn = sqlite3.connect(self.db_path)
            temp_conn.execute("VACUUM")
            temp_conn.close()
            
            # Reconecta ao banco de dados
            self._connect()
            
            removed = count_before - count_after
            if removed > 0:
                logger.info(f"Manutenção do DB: {removed} registros antigos removidos")
            
            logger.info(f"Banco de dados inicializado: {count_after} mapeamentos")
            
        except sqlite3.Error as e:
            logger.error(f"Erro na manutenção do banco de dados: {e}")
            # Tenta reconectar em caso de erro
            self._reconnect()

    def insert_message(self, chat_id: int, original_message_id: int, destination_message_id: int) -> None:
        """Insere um novo mapeamento de mensagem ou atualiza se já existir."""
        try:
            self._execute_with_retry('''
                INSERT OR REPLACE INTO messages 
                (chat_id, original_message_id, destination_message_id, timestamp)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ''', (chat_id, original_message_id, destination_message_id))
        except sqlite3.Error as e:
            logger.error(f"Erro ao inserir mensagem no banco de dados: {e}")
            self._reconnect()

    def get_mapped_message_id(self, chat_id: int, original_message_id: int) -> int:
        """Recupera o ID da mensagem no destino, com base no ID original."""
        try:
            cursor = self._execute_with_retry('''
                SELECT destination_message_id FROM messages
                WHERE chat_id = ? AND original_message_id = ?
            ''', (chat_id, original_message_id))
            
            result = cursor.fetchone()
            return result[0] if result else None
        except sqlite3.Error as e:
            logger.error(f"Erro ao recuperar ID mapeado: {e}")
            self._reconnect()
            return None

    def delete_mapping(self, chat_id: int, original_message_id: int) -> None:
        """Remove um mapeamento de mensagem."""
        try:
            self._execute_with_retry('''
                DELETE FROM messages
                WHERE chat_id = ? AND original_message_id = ?
            ''', (chat_id, original_message_id))
        except sqlite3.Error as e:
            logger.error(f"Erro ao remover mapeamento: {e}")
            self._reconnect()
    
    def close(self):
        """Fecha explicitamente a conexão com o banco de dados."""
        if self.conn:
            try:
                self.conn.close()
                logger.info("Conexão com o banco de dados fechada explicitamente.")
                self.conn = None
            except Exception as e:
                logger.error(f"Erro ao fechar conexão com o banco de dados: {e}")
    
    def __del__(self):
        """Garantir que a conexão seja fechada corretamente."""
        self.close()
