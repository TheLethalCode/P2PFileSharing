import p2p.constants as constants
import sys
import os
import mysql.connector
from mysql.connector.errors import ProgrammingError
from binaryornot.check import is_binary
import hashlib


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
                + constants.FT_ID + " INT AUTO_INCREMENT PRIMARY KEY,"\
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
        query = 'SELECT %s,%s,%s,%s FROM %s WHERE %s LIKE ' % (
            constants.FT_ID, constants.FT_NAME, constants.FT_SIZE, constants.FT_CHECKSUM, constants.DB_TABLE_FILE, constants.FT_NAME)
        query += "'%"+word+"%' "
        query += " OR "+constants.FT_PATH+" LIKE '%"+word+"%'"
        print(query)
        response = []
        try:
            self.fs_db_cursor.execute(query)
            result = self.fs_db_cursor.fetchall()
            for r in result:
                response.append({
                    'id': r[0],
                    'name': r[1],
                    'size': r[2],
                    'checksum': r[3]
                })
                # print(r)
        except Exception as Ex:
            # TODO ADD SOME LOGGING MECHANISM
            print(Ex)
            self.fs_db.rollback()
        finally:
            return response

    """
        Returns as chunk of predefined ChunkSize from file using input FileID

        Inputs: 
            fileId
            chunkNumber
        Returns:
            Chunk, if accessible
            False, if File DNE or File is not Binary
    """

    def get_content(self, fileId, chunkNumber):
        fileDetails = self.get_fileDetails_from_fileID(fileId)
        file_path = fileDetails[constants.FT_PATH]
        if is_binary(file_path) == False:
            return False
        else:
            try:
                with open(file_path, "rb") as f:
                    f.seek(constants.CHUNK_SIZE * chunkNumber, 0)
                    readChunk = f.read(constants.CHUNK_SIZE)
                    return {
                        constants.CNT_CHUNK: readChunk,
                        constants.CNT_FILENAME: fileDetails[constants.FT_NAME],
                        constants.CNT_CHECKSUM: self.checksum(readChunk)
                    }
            except Exception as Ex:
                print(Ex)
                return False

    def get_list_item_to_fileSys_item(self, a):
        a_dict = {
            constants.FT_ID: a[0],
            constants.FT_NAME: a[1],
            constants.FT_PATH: a[2],
            constants.FT_SIZE: a[3],
            constants.FT_CHECKSUM: a[4],
            constants.FT_PARENTID: a[5],
            constants.FT_RANDOMID: a[6],
            constants.FT_STATUS: a[7],
            constants.FT_REPLICATED_TO: a[8]
        }
        return a_dict
        pass

    def get_fileDetails_from_fileID(self, fileId):
        query = "SELECT * from "+constants.DB_TABLE_FILE + \
            " where "+constants.FT_ID+" = "+str(fileId)
        result = self.execute_query(query, True)[0]
        return self.get_list_item_to_fileSys_item(result)

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

    def checksum(self, chunk):
        md5_hash = hashlib.md5()
        md5_hash.update(chunk)
        return md5_hash.hexdigest()

    def writeChunk(self, mssg):
        content = mssg[constants.CONTENT]
        fileName = str(mssg[constants.REQUEST_ID])+"_" + \
            content[constants.CNT_FILENAME]
        chunk = content[constants.CNT_CHUNK]
        checkSum_rec = content[constants.CNT_CHECKSUM]
        if self.checksum(chunk) != checkSum_rec:
            return False
        else:
            if os.path.isdir(fileName) == False:
                os.mkdir(fileName)
            with open(fileName+"/"+str(mssg[constants.CHUNK_NO]), "wb") as f:
                f.write(chunk)
            print("Writing Chunk Number %s to %s is Successful" % (
                  str(mssg[constants.CHUNK_NO]), fileName))
            return True

    def done(self):
        pass
