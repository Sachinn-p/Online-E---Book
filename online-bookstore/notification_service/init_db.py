from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database import engine, SessionLocal
from models import Base, Notification

def init_db():
    """Initialize the database and create tables"""
    try:
        # Create all tables
        Base.metadata.create_all(bind=engine)
        print("✅ Notification Service database tables created successfully!")
        return True
    except Exception as e:
        print(f"❌ Error creating Notification Service database tables: {str(e)}")
        return False

def create_sample_data():
    """Create sample data for testing"""
    db = SessionLocal()
    try:
        # Check if any notifications exist
        existing_notification = db.query(Notification).first()
        if not existing_notification:
            print("✅ Notification Service ready for notifications")
    except Exception as e:
        print(f"❌ Error checking sample data: {str(e)}")
    finally:
        db.close()

if __name__ == "__main__":
    init_db()
    create_sample_data()
