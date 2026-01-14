"""Database setup script - Initialize PostgreSQL with pgvector."""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config_loader import get_config_loader
from src.memory.db_manager import DatabaseManager


def setup_database():
    """Initialize database with schema."""
    print("Setting up database...")

    # Load configuration
    try:
        config_loader = get_config_loader()
        configs = config_loader.load_all_configs()
    except Exception as e:
        print(f"Error loading configuration: {e}")
        return False

    # Create database manager
    try:
        db_manager = DatabaseManager(configs)
        print("✓ Connected to database")

        # Read and execute init script
        init_script_path = Path(__file__).parent / 'init_db.sql'

        if not init_script_path.exists():
            print(f"Error: init_db.sql not found at {init_script_path}")
            return False

        with open(init_script_path, 'r') as f:
            sql_script = f.read()

        # Execute schema creation
        # Note: This is a simple version - in production, split by statements
        conn = db_manager.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute(sql_script)
            conn.commit()
            print("✓ Database schema created successfully")

            # Verify tables
            cursor.execute("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                ORDER BY table_name
            """)

            tables = cursor.fetchall()
            print(f"\n✓ Created {len(tables)} tables:")
            for table in tables:
                print(f"  - {table[0]}")

            return True

        except Exception as e:
            conn.rollback()
            print(f"Error creating schema: {e}")
            return False

        finally:
            cursor.close()
            db_manager.return_connection(conn)
            db_manager.close()

    except Exception as e:
        print(f"Error connecting to database: {e}")
        return False


if __name__ == '__main__':
    print("=" * 60)
    print("AUTONOMOUS CODING AGENT - Database Setup")
    print("=" * 60)

    success = setup_database()

    if success:
        print("\n✅ Database setup completed successfully!")
        print("\nNext steps:")
        print("1. Set your OPENAI_API_KEY in .env")
        print("2. Run: python -m src.main run")
    else:
        print("\n❌ Database setup failed")
        sys.exit(1)
