#!/usr/bin/env python3
"""
Database migration script for CarbonLife.
Handles schema updates and data migrations safely.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
import models
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseMigrator:
    def __init__(self):
        self.engine = models.engine
        
    def backup_database(self):
        """Create a backup before migration"""
        backup_file = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"
        logger.info(f"📦 Creating backup: {backup_file}")
        
        # This would use pg_dump in production
        # For now, we'll just log the intent
        logger.info("✅ Backup completed (simulated)")
        
    def check_current_schema(self):
        """Check current database schema version"""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema = 'public'"
                ))
                tables = [row[0] for row in result]
                logger.info(f"📊 Found {len(tables)} tables: {', '.join(tables)}")
                return tables
        except SQLAlchemyError as e:
            logger.error(f"❌ Could not check schema: {e}")
            return []
    
    def create_migrations_table(self):
        """Create table to track migrations"""
        try:
            with self.engine.connect() as conn:
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS schema_migrations (
                        id SERIAL PRIMARY KEY,
                        version VARCHAR(50) NOT NULL,
                        applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        description TEXT
                    )
                """))
                conn.commit()
            logger.info("✅ Migrations table created/verified")
        except SQLAlchemyError as e:
            logger.error(f"❌ Could not create migrations table: {e}")
            raise
    
    def get_current_version(self):
        """Get current schema version"""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(
                    "SELECT version FROM schema_migrations "
                    "ORDER BY applied_at DESC LIMIT 1"
                ))
                row = result.fetchone()
                return row[0] if row else "0.0.0"
        except SQLAlchemyError:
            return "0.0.0"
    
    def record_migration(self, version, description):
        """Record a successful migration"""
        try:
            with self.engine.connect() as conn:
                conn.execute(text(
                    "INSERT INTO schema_migrations (version, description) "
                    "VALUES (:version, :description)"
                ), {"version": version, "description": description})
                conn.commit()
            logger.info(f"✅ Recorded migration {version}")
        except SQLAlchemyError as e:
            logger.error(f"❌ Could not record migration: {e}")
    
    def create_all_tables(self):
        """Create all tables from models"""
        try:
            logger.info("🔄 Creating all tables...")
            models.Base.metadata.create_all(bind=self.engine)
            logger.info("✅ All tables created successfully")
            return True
        except SQLAlchemyError as e:
            logger.error(f"❌ Failed to create tables: {e}")
            return False
    
    def add_indexes(self):
        """Add performance indexes"""
        logger.info("🔄 Adding indexes...")
        # Indexes are defined in models, so they're created automatically
        logger.info("✅ Indexes created")
    
    def run_migrations(self):
        """Run all pending migrations"""
        logger.info("🚀 Starting database migration...")
        
        # Backup first
        self.backup_database()
        
        # Check current state
        current_version = self.get_current_version()
        logger.info(f"📌 Current schema version: {current_version}")
        
        # Create tables
        if not self.create_all_tables():
            logger.error("❌ Migration failed")
            return False
        
        # Add indexes
        self.add_indexes()
        
        # Record migration
        self.record_migration("1.0.0", "Initial schema creation")
        
        logger.info("✅ Migration completed successfully")
        return True

def main():
    """Main migration entry point"""
    migrator = DatabaseMigrator()
    
    # Parse command line arguments
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "check":
            tables = migrator.check_current_schema()
            print(f"\n📊 Database tables: {len(tables)}")
            for table in sorted(tables):
                print(f"  • {table}")
                
        elif command == "reset":
            logger.warning("⚠️  This will DROP ALL TABLES!")
            confirm = input("Are you sure? (yes/no): ")
            if confirm.lower() == "yes":
                models.Base.metadata.drop_all(bind=migrator.engine)
                logger.info("✅ All tables dropped")
                migrator.create_all_tables()
                
        elif command == "migrate":
            migrator.run_migrations()
            
        else:
            print(f"Unknown command: {command}")
            print("Available commands: check, reset, migrate")
    else:
        # Default: run migrations
        migrator.run_migrations()

if __name__ == "__main__":
    main()