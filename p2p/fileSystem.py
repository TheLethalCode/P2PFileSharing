import p2p.constants as constants
import sys
import os
import mysql.connector
from mysql.connector.errors import ProgrammingError


class fileSystem(object):

    """
        Initialises an FileSystem object
        If already present at set location, then loads from directory
        Else creates a new database with set columns
    """

    def __init__(self):
        super().__init__()

        self.fsLocation = constants.FILESYS_PATH
        try:
            self.fs_db = mysql.connector.connect(
                host=constants.DB_HOST,
                user=constants.DB_USERNAME,
                password=constants.DB_PASSWORD,
                database=constants.DB_NAME
            )
            self.fs_db_cursor = self.fs_db.cursor()
            print("DATABASE EXISTS")
            self.view_table(constants.DB_TABLE_FILE)
        except:
            print("DATABASE AND TABLE DNE")
            self.fs_db = mysql.connector.connect(
                host=constants.DB_HOST,
                user=constants.DB_USERNAME,
                password=constants.DB_PASSWORD,
            )
            self.fs_db_cursor = self.fs_db.cursor()
            self.fs_db_cursor.execute("CREATE DATABASE "+constants.DB_NAME)
            self.fs_db_cursor.execute("USE "+constants.DB_NAME)
            self.fs_db.commit()
            print("CREATING TABLE")
            query = "CREATE TABLE "+constants.DB_TABLE_FILE+" ( "\
                + "id INT AUTO_INCREMENT PRIMARY KEY,"\
                + constants.FT_NAME+" VARCHAR(100) NOT NULL, "\
                + constants.FT_PATH+" VARCHAR(255), "\
                + constants.FT_SIZE+" INT(255), "\
                + constants.FT_CHECKSUM + " VARCHAR(255), "\
                + constants.FT_PARENTID + " VARCHAR(255), "\
                + constants.FT_RANDOMID + " INT(255), "\
                + constants.FT_STATUS + " VARCHAR(255), "\
                + constants.FT_REPLICATED_TO + " VARCHAR(255)"\
                + ")"
            print(query)
            self.fs_db_cursor.execute(query)
            self.fs_db.commit()

    def add_entry(self, table_name, name, path, size, checksum, parentID, randomID, status, replication):
        query = "INSERT INTO "+table_name+"(" + constants.FT_NAME+"," + constants.FT_PATH+", "\
                + constants.FT_SIZE+", " + constants.FT_CHECKSUM + ", " + constants.FT_PARENTID + ", " \
                + constants.FT_RANDOMID + ", " + constants.FT_STATUS + ", " + constants.FT_REPLICATED_TO + ")"\
                + "VALUES ('%s','%s','%d','%s','%s','%s','%s','%s')" % (name,
                                                                        path, size, checksum, parentID, randomID, status, replication)

        print(query)
        try:
            self.fs_db_cursor.execute(query)
            self.fs_db.commit()
            print("Commit Successful")
            print(self.fs_db_cursor.rowcount, "record inserted")
        except Exception as Ex:
            # TODO ADD SOME LOGGING MECHANISM
            print(Ex)
            self.fs_db.rollback()

    def view_table(self, table_name):
        query = "SELECT * FROM "+table_name
        print(query)

        try:
            self.fs_db_cursor.execute(query)
            result = self.fs_db_cursor.fetchall()
            for r in result:
                print(r)
        except Exception as Ex:
            # TODO ADD SOME LOGGING MECHANISM
            print(Ex)
            self.fs_db.rollback()

    def search(self, word):
        query = 'SELECT %s,%s,%s FROM %s WHERE %s LIKE ' % (
            constants.FT_NAME, constants.FT_SIZE, constants.FT_CHECKSUM, constants.DB_TABLE_FILE, constants.FT_NAME)
        query += "'%"+word+"%' "
        query += " OR "+constants.FT_PATH+" LIKE '%"+word+"%'"
        print(query)
        response = []
        try:
            self.fs_db_cursor.execute(query)
            result = self.fs_db_cursor.fetchall()
            for r in result:
                response.append({
                    'name': r[0],
                    'size': r[1],
                    'checksum': r[2]
                })
                # print(r)
        except Exception as Ex:
            # TODO ADD SOME LOGGING MECHANISM
            print(Ex)
            self.fs_db.rollback()
        finally:
            return response

    def upload_file(self, filepath):
        pass

    def remove_table(self, table_name):
        query = "DROP TABLE "+table_name
        self.execute_query(query)

    def remove_database(self, database_name):
        query = "DROP DATABASE "+database_name
        self.execute_query(query)

    def execute_query(self, query, response=False):
        if response == True:
            try:
                self.fs_db_cursor.execute(query)
                result = self.fs_db_cursor.fetchall()
                return result
            except Exception as Ex:
                # TODO ADD SOME LOGGING MECHANISM
                print(Ex)
                self.fs_db.rollback()
        else:
            try:
                self.fs_db_cursor.execute(query)
                self.fs_db.commit()
                print("Commit Successful")
            except Exception as Ex:
                # TODO ADD SOME LOGGING MECHANISM
                print(Ex)
                self.fs_db.rollback()

        pass
    pass
