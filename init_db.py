import os
import pymysql
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_USER = os.getenv('DB_USER', 'root')
DB_PASSWORD = os.getenv('DB_PASSWORD', '')
DB_NAME = os.getenv('DB_NAME', 'studentdb')

def init_database():
    """Initializes the MySQL database and the students table."""
    try:
        # Connect to MySQL server (without specifying DB_NAME in case it doesn't exist yet)
        connection = pymysql.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            autocommit=True
        )
        with connection.cursor() as cursor:
            # Create database if not exists
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{DB_NAME}`;")
            cursor.execute(f"USE `{DB_NAME}`;")
            
            # Create students table
            create_table_sql = """
            CREATE TABLE IF NOT EXISTS students (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                email VARCHAR(150) NOT NULL,
                course VARCHAR(100),
                photo_url VARCHAR(500)
            );
            """
            cursor.execute(create_table_sql)
            
        connection.close()
        print(f"Success: Database '{DB_NAME}' and table 'students' are verified/initialized.")
        return True
    except pymysql.MySQLError as e:
        # Ensure password is never included in error output
        print(f"Database Initialization Error: {type(e).__name__} - {e.args[-1] if e.args else 'Unknown error'}")
        return False

if __name__ == '__main__':
    init_database()
