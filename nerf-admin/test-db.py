import mysql.connector
from mysql.connector import Error

def test_mysql_connection():
    try:
        connection = mysql.connector.connect(
            host='localhost',        # Change this to your Docker container's IP if needed
            port=3306,               # Specify the port if it's not the default
            database='nerfbot_db',   # Your database name
            user='root',     # Your MySQL username
            password='rootpass'  # Your MySQL password
        )

        if connection.is_connected():
            db_info = connection.get_server_info()
            print(f"Connected to MySQL Server version {db_info}")
            
            cursor = connection.cursor()
            cursor.execute("SELECT DATABASE();")
            record = cursor.fetchone()
            print(f"You're connected to database: {record[0]}")

            # Test query
            cursor.execute("SHOW TABLES;")
            tables = cursor.fetchall()
            print("Tables in the database:")
            for table in tables:
                print(table[0])

    except Error as e:
        print(f"Error while connecting to MySQL: {e}")
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()
            print("MySQL connection is closed")

if __name__ == "__main__":
    test_mysql_connection()