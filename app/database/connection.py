"""
Модуль подключения к базам данных
Поддерживает: PostgreSQL, MySQL, SQLite
"""
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from contextlib import contextmanager
from typing import Optional, Generator
import pandas as pd


class DatabaseConnection:
    """Класс для подключения к различным типам БД"""
    
    def __init__(
        self,
        db_type: str = "sqlite",
        host: str = "localhost",
        port: int = 5432,
        database: str = "",
        user: str = "",
        password: str = "",
        sqlite_path: str = ""
    ):
        self.db_type = db_type
        self.engine: Optional[Engine] = None
        self._connection_params = {
            "host": host,
            "port": port,
            "database": database,
            "user": user,
            "password": password,
            "sqlite_path": sqlite_path
        }
    
    def connect(self) -> bool:
        """Создание подключения к БД"""
        try:
            if self.db_type == "sqlite":
                path = self._connection_params["sqlite_path"]
                self.engine = create_engine(f"sqlite:///{path}")
            
            elif self.db_type == "postgresql":
                self.engine = create_engine(
                    f"postgresql://{self._connection_params['user']}:{self._connection_params['password']}"
                    f"@{self._connection_params['host']}:{self._connection_params['port']}"
                    f"/{self._connection_params['database']}"
                )
            
            elif self.db_type == "mysql":
                self.engine = create_engine(
                    f"mysql+mysqlconnector://{self._connection_params['user']}:{self._connection_params['password']}"
                    f"@{self._connection_params['host']}:{self._connection_params['port']}"
                    f"/{self._connection_params['database']}"
                )
            
            else:
                raise ValueError(f"Неподдерживаемый тип БД: {self.db_type}")
            
            # Проверка подключения
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            
            return True
        
        except Exception as e:
            print(f"Ошибка подключения к БД: {e}")
            return False
    
    @contextmanager
    def get_connection(self) -> Generator:
        """Контекстный менеджер для работы с подключением"""
        if not self.engine:
            raise RuntimeError("Сначала выполните connect()")
        
        conn = self.engine.connect()
        try:
            yield conn
        finally:
            conn.close()
    
    def execute_query(self, query: str, params: Optional[dict] = None) -> pd.DataFrame:
        """Выполнение SQL запроса и возврат результата в DataFrame"""
        with self.get_connection() as conn:
            return pd.read_sql_query(text(query), conn, params=params)
    
    def test_connection(self) -> dict:
        """Тестирование подключения и возврат информации о БД"""
        try:
            with self.get_connection() as conn:
                if self.db_type == "postgresql":
                    result = conn.execute(text("SELECT version()")).scalar()
                elif self.db_type == "mysql":
                    result = conn.execute(text("SELECT version()")).scalar()
                elif self.db_type == "sqlite":
                    result = conn.execute(text("SELECT sqlite_version()")).scalar()
                else:
                    result = "Unknown"
            
            return {"status": "connected", "version": result}
        
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def get_tables(self) -> list:
        """Получение списка таблиц в БД"""
        with self.get_connection() as conn:
            if self.db_type == "postgresql":
                query = """
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public'
                """
            elif self.db_type == "mysql":
                query = """
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = DATABASE()
                """
            elif self.db_type == "sqlite":
                query = "SELECT name FROM sqlite_master WHERE type='table'"
            else:
                return []
            
            result = pd.read_sql_query(text(query), conn)
            return result.iloc[:, 0].tolist()
    
    def get_table_schema(self, table_name: str) -> pd.DataFrame:
        """Получение схемы таблицы"""
        with self.get_connection() as conn:
            if self.db_type == "postgresql":
                query = """
                    SELECT column_name, data_type, is_nullable
                    FROM information_schema.columns
                    WHERE table_name = :table
                    ORDER BY ordinal_position
                """
            elif self.db_type == "mysql":
                query = """
                    SELECT column_name, data_type, is_nullable
                    FROM information_schema.columns
                    WHERE table_name = :table
                    ORDER BY ordinal_position
                """
            elif self.db_type == "sqlite":
                query = f"PRAGMA table_info({table_name})"
                result = pd.read_sql_query(text(query), conn)
                result.columns = ["cid", "name", "type", "notnull", "default_value", "pk"]
                return result[["name", "type", "notnull"]]
            else:
                return pd.DataFrame()
            
            result = pd.read_sql_query(text(query), conn, params={"table": table_name})
            return result


def create_connection_from_config() -> DatabaseConnection:
    """Создание подключения на основе конфигурации"""
    from config import DB_TYPE, DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD, APP_DATABASE_PATH
    
    return DatabaseConnection(
        db_type=DB_TYPE,
        host=DB_HOST,
        port=int(DB_PORT) if DB_PORT else 5432,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        sqlite_path=str(APP_DATABASE_PATH)
    )
