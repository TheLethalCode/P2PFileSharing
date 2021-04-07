import p2p.constants as constants
import sys, os
import pandas as pd

class fileSystem(object):
    
    """
        Initialises an FileSystem object
        If already present at set location, then loads from directory
        Else creates a new pandas dataframe with set columns
    """
    def __init__(self):
        super().__init__()

        self.fsLocation = constants.FILESYS_PATH
        try:
            self.fs_df = pd.read_pickle(self.fsLocation)
        except:
            self.fs_df = pd.DataFrame(columns={"Name","Path","Size","CheckSum","ParentId","Status"})


    """
        Save the pandas dataframe to directory
    """
    def save_df(self):
        self.fs_df.to_pickle(self.fsLocation)

    """
        Make a new entry to the dataframe
        Can be called when making a new file available for upload or downloading a file
    
        Args:
            Name    : (str) Filename
            Path    : (str) File Path
            Size    : (int) File Size in bytes
            Checksum: (str) MD5-based checksum for complete file
            ParentId: (str) Id of source of the file
            Status  : (str) Status of file in fs
    """
    def new_entry(self, name, path, size, checksum, parentId, status):
        self.fs_df.append({"Name":name, "Path":path, "Size":size,"CheckSum":checksum, "ParentId":parentId, "Status":status}, ignore_index=True)

    """
        Make a new entry to the dataframe
        Makes a new file available for upload
    
        Args:
            Path    : (str) Path of file to be uploaded 
    """
    def upload_file(self,filepath):
        pass

    
    pass