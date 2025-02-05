from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.exc import OperationalError, SQLAlchemyError
import logging


# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SessionManager:
    """
    Класс для управления сессиями базы данных для разных пользователей.
    """

    def __init__(self):
        """
        Инициализация менеджера сессий.
        """
        self.sessions = {}
        self.user_uris = {}
        logger.info("SessionManager инициализирован.")

    def __del__(self):
        """
        Закрытие всех активных сессий при удалении объекта.
        """
        self.close_all_sessions()

    def create_session(self, user_id, db_uri):
        """
        Создает сессию для пользователя.
        :param user_id: ID пользователя.
        :param db_uri: Строка подключения к базе данных.
        """
        if not db_uri:
            logger.error("Не указан URI базы данных для пользователя %s.", user_id)
            raise ValueError("URI базы данных не может быть пустым.")

        try:
            engine = create_engine(db_uri)
            session_factory = sessionmaker(bind=engine)
            Session = scoped_session(session_factory)
            self.sessions[user_id] = Session
            self.user_uris[user_id] = db_uri
            logger.info("Сессия создана для пользователя %s.", user_id)
        except SQLAlchemyError as e:
            logger.error("Ошибка при создании сессии для пользователя %s: %s", user_id, e)
            raise

    def get_session(self, user_id):
        """
        Возвращает существующую сессию или создает новую.
        :param user_id: ID пользователя.
        :return: Сессия пользователя.
        """
        # if user_id not in self.user_uris:
        #     logger.error("URI для пользователя %s отсутствует.", user_id)
        #     raise KeyError(f"URI для пользователя {user_id} отсутствует.")
        #
        # if user_id not in self.sessions:
        #     logger.warning("Сессия для пользователя %s отсутствует, создается новая.", user_id)
        #     self.create_session(user_id, self.user_uris[user_id])
        #
        # return self.sessions[user_id]
        return self.sessions.get(user_id)

    def execute_query(self, user_id, query, params=None):
        """
        Выполняет SQL-запрос для указанного пользователя.
        :param user_id: ID пользователя.
        :param query: SQL-запрос в виде строки.
        :param params: Параметры для запроса (словарь или список).
        :return: Результаты выполнения запроса.
        """
        session_find = self.get_session(user_id)
        if not session_find:
            logger.error("Не удалось найти сессию для пользователя %s.", user_id)
            return None

        try:
            with session_find.connection() as connect:
                query = text(query)
                result = connect.execute(query, params) if params else connect.execute(query)
                connect.commit()
                logger.info("Запрос выполнен для пользователя %s.", user_id)
                return result.fetchall() if result.returns_rows else None
        except OperationalError as e:
            logger.error("Ошибка выполнения запроса для пользователя %s: %s", user_id, e)
            return None
        except SQLAlchemyError as e:
            logger.error("Неизвестная ошибка при выполнении запроса для пользователя %s: %s", user_id, e)
            return None

    def close_session(self, user_id):
        """
        Закрывает сессию для указанного пользователя.
        :param user_id: ID пользователя.
        """
        session1 = self.sessions.pop(user_id, None)
        if not session1:
            logger.warning("Сессия для пользователя %s уже закрыта или не существовала.", user_id)
            return

        try:
            session1.close()
            session1.bind.dispose()
            logger.info("Сессия для пользователя %s успешно закрыта.", user_id)
        except SQLAlchemyError as e:
            logger.error("Ошибка при закрытии сессии пользователя %s: %s", user_id, e)

        self.user_uris.pop(user_id, None)

    def close_all_sessions(self):
        """
        Закрывает все активные сессии.
        """
        user_ids = list(self.sessions.keys())
        for user_id in user_ids:
            self.close_session(user_id)
        logger.info("Все сессии успешно закрыты.")