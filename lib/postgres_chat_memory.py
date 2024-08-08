""" This is an edit of langchains postgres.py 
It comes from: from langchain.memory import PostgresChatMessageHistory
It's modified to add a new column called user_id to the table, so that
messages can be added according to a particular user id

"""

import json
import logging
from typing import List

from langchain.schema import (
    BaseChatMessageHistory,
)
from langchain.schema.messages import BaseMessage, _message_to_dict, messages_from_dict

logger = logging.getLogger(__name__)

DEFAULT_CONNECTION_STRING = "postgresql://postgres:mypassword@localhost/chat_history"


class PostgresChatMessageHistory(BaseChatMessageHistory):
    """Chat message history stored in a Postgres database."""

    def __init__(
        self,
        conversation_uuid: str,
        user_id: int,
        connection_string: str = DEFAULT_CONNECTION_STRING,
        table_name: str = "message_store",
    ):
        import psycopg
        from psycopg.rows import dict_row

        try:
            self.connection = psycopg.connect(connection_string)
            self.cursor = self.connection.cursor(row_factory=dict_row)
        except psycopg.OperationalError as error:
            logger.error(error)

        self.conversation_uuid = conversation_uuid
        self.user_id = user_id
        self.table_name = table_name

        self._create_table_if_not_exists()

    def _create_table_if_not_exists(self) -> None:
        create_table_query = f"""CREATE TABLE IF NOT EXISTS {self.table_name} (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL,
            conversation_uuid TEXT NOT NULL,
            message JSONB NOT NULL
        );"""
        self.cursor.execute(create_table_query)
        self.connection.commit()

    @property
    def messages(self) -> List[BaseMessage]:  # type: ignore
        """Retrieve the messages from PostgreSQL"""

        query = (
            f"SELECT message FROM {self.table_name} WHERE conversation_uuid = %s AND user_id = %s ORDER BY id;"
        )

        self.cursor.execute(query, (self.conversation_uuid, self.user_id,))

        items = [record["message"] for record in self.cursor.fetchall()]
        messages = messages_from_dict(items)
        return messages

    def add_message(self, message: BaseMessage) -> None:
        """Append the message to the record in PostgreSQL"""
        from psycopg import sql

        query = sql.SQL("INSERT INTO {} (user_id, conversation_uuid, message) VALUES (%s, %s, %s);").format(
            sql.Identifier(self.table_name)
        )
        self.cursor.execute(
            query, (self.user_id, self.conversation_uuid, json.dumps(_message_to_dict(message)))
        )
        self.connection.commit()

    def clear(self) -> None:
        """Clear session memory from PostgreSQL"""
        query = f"DELETE FROM {self.table_name} WHERE conversation_uuid = %s AND user_id = %s;"
        self.cursor.execute(query, (self.conversation_uuid,self.user_id,))
        self.connection.commit()

    def __del__(self) -> None:
        if self.cursor:
            self.cursor.close()
        if self.connection:
            self.connection.close()
