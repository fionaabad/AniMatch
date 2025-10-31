import mysql.connector

class Conexion:
    def __init__(self, user = "root", password = "root"):
        self.SetConn(mysql.connector.connect(
            host="localhost",
            user=user,
            password=password,
            database="animatch_db") )
        
        self.SetCursor(self.__conn.cursor()) 

    def GetConn(self):
        return self.__conn
    
    def SetConn(self, conn):
        self.__conn = conn
        
    def GetCursor(self):
        return self.__cursor
    
    def SetCursor(self, cursor):
        self.__cursor = cursor 
