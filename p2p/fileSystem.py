import shutil
import sqlite3
import math
import hashlib
from binaryornot.check import is_binary
import base64
import os
import re
import sys
import logging
import constants
# import p2p.constants as constants
import threading

# TODO: REPLICATION
# TODO: --> Set ParentID and RequestId properly
# TODO: --> request removal of replication when removing content
# TODO: saving states of dicts
# TODO: load states using
# TODO: clean code
# TODO: return None at proper places instead of false

logger = logging.getLogger('fileSystem')
logger.setLevel(logging.INFO)

fh = logging.FileHandler(os.path.join(constants.LOG_PATH, constants.LOG_FILE))
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(threadName)s - %(levelname)s - %(message)s'
)
fh.setFormatter(formatter)
logger.addHandler(fh)

class fileSystem(object):

    """
        Initialises an FileSystem object
        If already present at set location, then loads from directory
        Else creates a new database with set columns
    """

    def __init__(self):
        super().__init__()
        self.reqIdDict = {}
        self.downloadComplete = {}
        self.fileIdcache = {}
        self.databaseLock = threading.RLock()
        self.fsLocation = constants.FILESYS_PATH
        if not os.path.exists(constants.DOWNLOAD_FOLDER):
            os.makedirs(constants.DOWNLOAD_FOLDER)
        if not os.path.exists(constants.INCOMPLETE_FOLDER):
            os.makedirs(constants.INCOMPLETE_FOLDER)
        try:
            self.fs_db = sqlite3.connect(
                constants.DB_NAME, check_same_thread=False)
            self.fs_db_cursor = self.fs_db.cursor()
            print("DATABASE EXISTS")
            print("CREATING TABLE")
            query = "CREATE TABLE IF NOT EXISTS "+constants.DB_TABLE_FILE+" ( "\
                + constants.FT_ID + " INTEGER PRIMARY KEY AUTOINCREMENT,"\
                + constants.FT_NAME+" VARCHAR(100) NOT NULL, "\
                + constants.FT_PATH+" VARCHAR(255) UNIQUE, "\
                + constants.FT_SIZE+" INT(255), "\
                + constants.FT_CHECKSUM + " VARCHAR(255), "\
                + constants.FT_PARENTID + " VARCHAR(255), "\
                + constants.FT_REQUESTID + " INT(255), "\
                + constants.FT_STATUS + " VARCHAR(255), "\
                + constants.FT_REPLICATED_TO + " VARCHAR(255)"\
                + ")"
            print(query)
            with self.databaseLock:
                self.fs_db_cursor.execute(query)
                self.fs_db.commit()
            print(*self.view_table(constants.DB_TABLE_FILE), sep='\n')
        except Exception as ex:
            print(ex)
            pass

    def load_state(self):
        self.load_state_reqIdDict()
        self.load_state_downloadComplete_dict()
        self.load_state_fileIdCache()
        return True

    def load_state_reqIdDict(self):
        pass

    def load_state_downloadComplete_dict(self):
        pass

    def load_state_fileIdCache(self):
        pass

    def add_entry(self, table_name, name, path, size, checksum, parentID, randomID, status, replication):
        query = "INSERT INTO "+table_name+"(" + constants.FT_NAME+"," + constants.FT_PATH+", "\
                + constants.FT_SIZE+", " + constants.FT_CHECKSUM + ", " + constants.FT_PARENTID + ", " \
                + constants.FT_REQUESTID + ", " + constants.FT_STATUS + ", " + constants.FT_REPLICATED_TO + ")"\
                + "VALUES ('%s','%s','%d','%s','%s','%s','%s','%s')" % (name,
                                                                        path, size, checksum, parentID, randomID, status, replication)

        print(query)
        try:
            with self.databaseLock:
                self.fs_db_cursor.execute(query)
                self.fs_db.commit()
            print("Commit Successful")
            print(self.fs_db_cursor.rowcount, "record inserted")
        except Exception as Ex:
            # TODO ADD SOME LOGGING MECHANISM
            print(Ex)
            self.fs_db.rollback()

    def remove_entry(self, table_name, what, what_value):
        query = "DELETE from "+table_name+" where "+what+" = '"+what_value+"'"
        print(query)
        self.execute_query(query)
        return True

    def view_table(self, table_name):
        query = "SELECT * FROM "+table_name
        print(query)
        response = []
        try:
            with self.databaseLock:
                self.fs_db_cursor.execute(query)
                result = self.fs_db_cursor.fetchall()
            for r in result:
                response.append(self.get_list_item_to_fileSys_item(r))
            return response
        except Exception as Ex:
            # TODO ADD SOME LOGGING MECHANISM
            print(Ex)
            return None

    def search(self, word):
        query = 'SELECT %s,%s,%s,%s FROM %s WHERE (%s LIKE ' % (
            constants.FT_ID, constants.FT_NAME, constants.FT_SIZE, constants.FT_CHECKSUM, constants.DB_TABLE_FILE, constants.FT_NAME)
        query += "'%"+word+"%' "
        query += " OR "+constants.FT_PATH+" LIKE '%"+word+"%')"
        response = []
        try:
            with self.databaseLock:
                self.fs_db_cursor.execute(query)
                result = self.fs_db_cursor.fetchall()
            for r in result:
                response.append({
                    constants.FILE_ID: r[0],
                    constants.FT_NAME: r[1],
                    constants.NUM_CHUNKS: int(math.ceil(r[2]/constants.CHUNK_SIZE)),
                    constants.FT_CHECKSUM: r[3],
                    constants.FT_SIZE: r[2]
                })
        except Exception as Ex:
            print(Ex)
            self.fs_db.rollback()
        finally:
            return response

    def getContent(self, fileId, chunkNumber):
        """
            Returns as chunk of predefined ChunkSize from file using input FileID

            Inputs:
                fileId
                chunkNumber
            Returns:
                Chunk, if accessible
                False, if File DNE or File is not Binary
        """
        if fileId not in self.fileIdcache.keys():
            self.fileIdcache[fileId] = self.get_fileDetails_from_fileID(fileId)
        fileDetails = self.fileIdcache[fileId]
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
                        constants.CNT_CHECKSUM: self.checksum(readChunk),
                        constants.CNT_FILEPATH: fileDetails[constants.FT_PATH],
                        constants.CNT_SIZE: fileDetails[constants.FT_SIZE]
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
            constants.FT_REQUESTID: a[6],
            constants.FT_STATUS: a[7],
            constants.FT_REPLICATED_TO: a[8]
        }
        return a_dict

    def get_fileDetails_from_fileID(self, fileId):
        query = "SELECT * from "+constants.DB_TABLE_FILE + \
            " where "+constants.FT_ID+" = "+str(fileId)
        result = self.execute_query(query, True)[0]
        return self.get_list_item_to_fileSys_item(result)

    def get_fileDetails_from_reqID(self, reqId):
        query = "SELECT * from "+constants.DB_TABLE_FILE + \
            " where "+constants.FT_REQUESTID+" = "+str(reqId)
        result = self.execute_query(query, True)[0]
        return self.get_list_item_to_fileSys_item(result)

    def remove_table(self, table_name):
        query = "DROP TABLE "+table_name
        self.execute_query(query)

    def remove_database(self, database_name):
        query = "DROP DATABASE "+database_name
        self.execute_query(query)

    def execute_query(self, query, response=False):
        if response == True:
            try:
                with self.databaseLock:
                    self.fs_db_cursor.execute(query)
                    result = self.fs_db_cursor.fetchall()
                return result
            except Exception as Ex:
                # TODO ADD SOME LOGGING MECHANISM
                print(Ex)
                self.fs_db.rollback()
        else:
            try:
                with self.databaseLock:
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

    def checksum_large(self, path):
        md5_obj = hashlib.md5()
        blockSize = constants.CHUNK_SIZE
        with open(path, "rb") as a:
            chunk = a.read(constants.CHUNK_SIZE)
            while chunk:
                md5_obj.update(chunk)
                chunk = a.read(constants.CHUNK_SIZE)
            cSum = md5_obj.hexdigest()
        return cSum

    def writeChunk(self, mssg):
        content = mssg[constants.CONTENT]
        fileName = str(mssg[constants.REQUEST_ID])+"_" + \
            content[constants.CNT_FILENAME]
        chunk = content[constants.CNT_CHUNK]
        filepath = content[constants.CNT_FILEPATH]
        checkSum_rec = content[constants.CNT_CHECKSUM]
        print(self.checksum(chunk), checkSum_rec,
              self.checksum(chunk) == checkSum_rec)
        if self.checksum(chunk) != checkSum_rec:
            return False
        else:
            if mssg[constants.REQUEST_ID] not in self.reqIdDict.keys():
                self.reqIdDict[mssg[constants.REQUEST_ID]
                               ] = filepath.split("/")[-1]
            if os.path.isdir(constants.INCOMPLETE_FOLDER + fileName) == False:
                os.makedirs(constants.INCOMPLETE_FOLDER+fileName)
            with open(constants.INCOMPLETE_FOLDER+fileName+"/"+str(mssg[constants.CHUNK_NO]), "wb") as f:
                f.write(chunk)
            print("Writing Chunk Number %s to %s is Successful" % (
                  str(mssg[constants.CHUNK_NO]), fileName))
            return True

    def done(self, reqId):
        folderName = constants.INCOMPLETE_FOLDER + \
            str(self.get_foldername_using_reqId(reqId))
        print("FolderName", folderName)
        filename = self.reqIdDict[reqId]
        # filename = self.reqIdDict[reqId]
        print(folderName, filename)
        self.join_chunks(folderName, constants.DOWNLOAD_FOLDER + filename)
        filepath = constants.DOWNLOAD_FOLDER + filename
        self.add_entry(constants.DB_TABLE_FILE, filename.split(".")[0], filepath, os.stat(
            filepath).st_size, self.checksum_large(filepath), 0, 0, constants.FS_DOWNLOAD_COMPLETE, None)
        # TODO insert into table
        # Use this downloadComplete to point to the fileId
        self.downloadComplete[reqId] = filename
        print(type(self.reqIdDict))
        self.reqIdDict.pop(reqId)
        shutil.rmtree(folderName)
        return True

    def get_foldername_using_reqId(self, request_id):
        print("Requestid", request_id)
        for x in os.listdir(constants.INCOMPLETE_FOLDER):
            print(x, os.path.isdir(constants.INCOMPLETE_FOLDER+x),
                  x.startswith(str(request_id)+"_"))
            if os.path.isdir(constants.INCOMPLETE_FOLDER+x) and x.startswith(str(request_id)+"_"):
                return x
        pass

    def join_chunks(self, fromdir, toFile):
        with open(toFile, 'wb+') as output:
            parts = os.listdir(fromdir)
            parts.sort(key=lambda f: int(re.sub('\D', '', f)))
            for filename in parts:
                filepath = os.path.join(fromdir, filename)
                with open(filepath, 'rb') as input:
                    output.write(input.read())

    def update_status_using_reqId(self, table_name, reqId, newStatus):
        if reqId > 0:
            query = "UPDATE "+table_name+"SET "+constants.FT_STATUS+" = " + \
                newStatus+" WHERE "+constants.FT_REQUESTID+"="+str(reqId)
            print(query)
            self.execute_query(query)
        pass

    def isFinished(self, reqId):
        if reqId not in self.downloadComplete.keys():
            return False
        else:
            return True

    def add(self, path):
        """
            Make content available for download
            Add entry to table with Status as UPLOAD

            Returns
                TRUE on success
                FALSE on failure
        """
        if (not os.path.exists(path)) or (os.path.isfile(path) and not is_binary(path)):
            return False
        elif (os.path.isdir(path)):
            for file in os.listdir(path):
                file = path+"/"+file
                if os.path.isfile(file):
                    print(file)
                    self.add(file)
            return True
        else:
            filename = os.path.splitext(path)[0].split("/")[-1]
            file_stat = os.stat(path)
            size = file_stat.st_size
            cSum = self.checksum_large(path)
            parentId = "0"
            randId = 0
            status = constants.FS_UPLOADED
            replication = None
            self.add_entry(constants.DB_TABLE_FILE, filename, path,
                           size, cSum, parentId, randId, status, replication)
            return True

    def abort_download(self, reqId):
        folderName = self.get_foldername_using_reqId(reqId)
        self.reqIdDict.pop(reqId)
        shutil.rmtree(folderName)
        return True

    def removeShare(self, path):
        if (not os.path.exists(path)):
            return False
        elif (os.path.isdir(path)):
            for file in os.listdir(path):
                file = path+"/"+file
                if os.path.isfile(file):
                    print(file)
                    self.removeShare(file)
        else:
            self.remove_entry(constants.DB_TABLE_FILE, constants.FT_PATH, path)
            return True

    def reqId_to_name(self, reqId):
        if reqId in self.reqIdDict.keys():
            return self.reqIdDict[reqId]
        else:
            return None

    def test_done(self):
        for i in range(math.ceil(422898/constants.CHUNK_SIZE)):
            chunk = self.getContent(2, i)
            mssg = {
                'Data': chunk,
                'Chunk number': i,
                'Request ID': 124
            }
            self.writeChunk(mssg)
        print(self.done(124))
        pass
