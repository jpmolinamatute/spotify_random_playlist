from os import path
import sqlite3
import logging
import uuid
from .common import isWritable, DEFAULT_DB


def row_to_marks(column: tuple) -> str:
    marks = ""
    size = len(column)
    for i in range(size):
        if (i + 1) < size:
            marks += "?, "
        else:
            marks += "?"
    return marks


def row_to_values(row: dict) -> tuple:
    val = tuple(row.values())
    if len(val) == 1:
        val = (val[0],)

    return val


def row_to_set_values(row: dict) -> str:
    values = ""
    for item in row.keys():
        values += f"{item} = excluded.{item}, "
    return values[:-2]


class DB:
    def __init__(self, logtag: str, table: str, filepath: str, row_id: str = ""):
        if isWritable(filepath):
            db_file_name = path.join(filepath, DEFAULT_DB)
        else:
            msg = f"Settings path '{filepath}' is not writable "
            msg += "or doesn't exists. "
            msg += "Please change it and try again"
            raise Exception(msg)
        self.logger = logging.getLogger(logtag)
        self.table = table
        self.row_id = row_id if row_id else str(uuid.uuid4())
        self.logger.debug(f"Opening connection to {DEFAULT_DB}")
        self.conn = sqlite3.connect(
            db_file_name, detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES
        )
        self.execute("PRAGMA foreign_keys = ON;")

    def insert(self, row: dict, upsert: str = "") -> int:
        columns = tuple(row.keys())
        marks = row_to_marks(columns)
        values = row_to_values(row)
        cursor = self.conn.cursor()
        sql_str = f"""
            INSERT INTO {self.table} {columns}
            VALUES({marks})
        """
        if upsert:
            set_values = row_to_set_values(row)
            sql_str += f"""
                ON CONFLICT({upsert}) DO UPDATE SET {set_values};
            """
        else:
            sql_str += ";"
        self.logger.debug(f"Executing {sql_str}")
        cursor.execute(sql_str, values)
        self.conn.commit()
        lastrowid = cursor.lastrowid
        cursor.close()
        return lastrowid

    def insert_many(self, content: list, columns: tuple) -> None:
        marks = row_to_marks(columns)
        sql_str = f"""
            INSERT INTO {self.table} {columns}
            VALUES ({marks});
        """
        cursor = self.conn.cursor()
        self.logger.debug(f"Executing {sql_str}")
        cursor.executemany(sql_str, content)
        self.conn.commit()
        cursor.close()

    def execute(self, sql_str: str, values: tuple = ()) -> None:
        cursor = self.conn.cursor()
        self.logger.debug(f"Executing\n{sql_str}")
        cursor.execute(sql_str, values)
        self.conn.commit()
        cursor.close()

    def query(self, sql_str: str, values: tuple = ()) -> list:
        cursor = self.conn.cursor()
        self.logger.debug(f"Executing {sql_str}")
        cursor.execute(sql_str, values)
        self.conn.commit()
        rows = cursor.fetchall()
        cursor.close()
        return rows

    def close(self) -> None:
        self.logger.debug(f"Closing connection to {DEFAULT_DB}")
        self.conn.close()

    def get_id(self) -> str:
        return self.row_id

    def set_id(self, oauth_id: str) -> bool:
        sql = f"""
            SELECT *
            FROM {self.table}
            WHERE id = ?;
        """
        valid = False

        row = self.query(sql, (oauth_id,))

        if row:
            self.row_id = oauth_id
            valid = True
        return valid

    def create_table(self):
        raise NotImplementedError

    def reset_table(self) -> None:
        self.logger.debug(f"Reseting table {self.table}")
        sql = f"DROP TABLE IF EXISTS {self.table};"
        self.execute(sql)
        self.create_table()
