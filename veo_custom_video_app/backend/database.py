from sqlalchemy import create_engine
import os # Added import for os
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Attempt to import DATABASE_URL from user-created settings.py
# If settings.py is not found, fall back to environment variable then placeholder.
try:
    from veo_custom_video_app.config.settings import DATABASE_URL
    print(f"INFO: Successfully imported DATABASE_URL from config.settings: {DATABASE_URL}")
except ModuleNotFoundError:
    print("INFO: veo_custom_video_app.config.settings.py not found or DATABASE_URL not defined there.")
    # Diagnostic print:
    env_db_url = os.getenv('DATABASE_URL')
    print(f"DIAGNOSTIC: os.getenv('DATABASE_URL') returned: {env_db_url}")
    if env_db_url:
        DATABASE_URL = env_db_url
        print(f"INFO: Using DATABASE_URL from environment variable: {DATABASE_URL}")
    else:
        DATABASE_URL = "postgresql://user:password@localhost:5432/veoapp_test_db" # Placeholder
        print(f"INFO: Using placeholder DATABASE_URL as environment variable not set: {DATABASE_URL}")
    print("INFO: For production, ensure DATABASE_URL is correctly set in .env or config/settings.py.")

# Create SQLAlchemy engine
# For production, consider connection pooling options, e.g., pool_size, max_overflow.
# For async operations with asyncpg, you would use create_async_engine from sqlalchemy.ext.asyncio
engine = create_engine(DATABASE_URL)

# Create a configured "Session" class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create a Base for declarative class definitions
Base = declarative_base()

def get_db():
    """
    FastAPI dependency to get a database session.
    Ensures the database session is always closed after the request.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """
    Initializes the database by creating all tables defined by models
    that are registered with the `Base` metadata.
    """
    # Import all modules here that define models so that
    # they are registered with `Base.metadata`.
    # This ensures that `Base.metadata.create_all(engine)` knows about them.
    from veo_custom_video_app.backend.app import models as app_models

    print(f"INFO: Initializing database with URL: {DATABASE_URL}")
    print(f"INFO: Attempting to create tables for models found in: {app_models.__file__}")

    # IMPORTANT WORKAROUND:
    # The models in app_models.py currently define their own Base.
    # To make init_db work without immediately modifying models.py,
    # we temporarily assign the Base from this database.py module
    # to the models module. This allows Base.metadata.create_all
    # to see the tables defined in app_models.
    # A proper fix involves models.py directly importing Base from this file.
    original_models_base = getattr(app_models, 'Base', None)
    app_models.Base = Base 
    
    try:
        print(f"INFO: Tables to be created: {Base.metadata.tables.keys()}")
        Base.metadata.create_all(bind=engine)
        print("INFO: Database tables created successfully (if they didn't exist).")
    except Exception as e:
        print(f"ERROR: An error occurred during table creation: {e}")
        # Depending on the error, you might want to handle it more gracefully
        # or re-raise it.
    finally:
        # Restore the original Base in models module if it existed,
        # though this has limited effect as class definitions are already processed.
        # The proper fix is to have models.py import Base from database.py.
        if original_models_base:
            app_models.Base = original_models_base

# Example of how to run init_db (e.g., in a CLI script or main.py on startup)
# if __name__ == "__main__":
#     print("Initializing database...")
#     init_db()
#     print("Database initialization process completed.")
