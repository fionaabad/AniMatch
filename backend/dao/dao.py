# backend/dao/dao.py
import mysql.connector

class AnimatchDAO:

    @staticmethod
    def add_user(username, password, conn, role='user'):
        sql = "INSERT INTO users (`user`, `password`, `role`) VALUES (%s, %s, %s)"
        cur = conn.GetConn().cursor()
        try:
            cur.execute(sql, (username, password, role))
            conn.GetConn().commit()
            return True
        except mysql.connector.IntegrityError:
            # duplicado (si hay UNIQUE en `user`)
            return False
        except mysql.connector.Error as err:
            print("Error add_user:", err)
            return False
        finally:
            try:
                cur.close()
            except:
                pass

    @staticmethod
    def get_user_by_username(username, conn):
        sql = """
            SELECT 
                id_users       AS id,
                `user`         AS username,
                `password`     AS password,
                `role`         AS role
            FROM users
            WHERE `user` = %s
            LIMIT 1
        """
        cur = conn.GetConn().cursor(dictionary=True)
        try:
            cur.execute(sql, (username,))
            row = cur.fetchone()  # dict o None
            return row
        except mysql.connector.Error as err:
            print("Error get_user_by_username:", err)
            return None
        finally:
            try:
                cur.close()
            except:
                pass

    @staticmethod
    def list_users(conn):
        sql = """
            SELECT 
                id_users AS id,
                `user`   AS username,
                `role`   AS role
            FROM users
            ORDER BY id_users
        """
        cur = conn.GetConn().cursor(dictionary=True)
        try:
            cur.execute(sql)
            return cur.fetchall()
        except mysql.connector.Error as err:
            print("Error list_users:", err)
            return []
        finally:
            try:
                cur.close()
            except:
                pass
