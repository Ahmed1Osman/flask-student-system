import sqlite3
import os
from urllib.parse import urlparse

# Try to import psycopg (version 3)
try:
    import psycopg
    from psycopg.rows import dict_row
    PSYCOPG_AVAILABLE = True
except ImportError:
    PSYCOPG_AVAILABLE = False

def get_db_config():
    """Get database configuration from environment"""
    database_url = os.environ.get('DATABASE_URL')
    
    if database_url and PSYCOPG_AVAILABLE:
        # Parse PostgreSQL URL
        parsed = urlparse(database_url)
        return {
            'type': 'postgresql',
            'url': database_url
        }
    else:
        # Use SQLite for local development
        return {
            'type': 'sqlite',
            'path': os.path.join(os.path.dirname(os.path.abspath(__file__)), 'students.db')
        }

def get_connection():
    """Get database connection (SQLite or PostgreSQL)"""
    config = get_db_config()
    
    if config['type'] == 'postgresql':
        # PostgreSQL connection with psycopg3
        conn = psycopg.connect(config['url'], row_factory=dict_row)
        return conn
    else:
        # SQLite connection
        conn = sqlite3.connect(config['path'])
        conn.row_factory = sqlite3.Row
        return conn

def init_db():
    """Initialize database tables"""
    config = get_db_config()
    conn = None
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        if config['type'] == 'postgresql':
            # PostgreSQL schema
            print("Initializing PostgreSQL database...")
            
            # Create users table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    username VARCHAR(255) UNIQUE NOT NULL,
                    password VARCHAR(255) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create students table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS students (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    age INTEGER,
                    city VARCHAR(255),
                    image VARCHAR(255),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create indexes for better performance
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_students_name ON students(name)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_students_city ON students(city)
            """)
            
        else:
            # SQLite schema
            print("Initializing SQLite database...")
            
            # Enable foreign keys
            cursor.execute("PRAGMA foreign_keys = ON")
            
            # Create users table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create students table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS students (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    age INTEGER,
                    city TEXT,
                    image TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Check if image column exists, if not add it (for existing databases)
            cursor.execute("PRAGMA table_info(students)")
            columns = [column[1] for column in cursor.fetchall()]
            if 'image' not in columns:
                cursor.execute("ALTER TABLE students ADD COLUMN image TEXT")
                print("Added image column to students table")
        
        conn.commit()
        print(f"Database initialized successfully! Using: {config['type']}")
        
    except Exception as e:
        print(f"Database error: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()