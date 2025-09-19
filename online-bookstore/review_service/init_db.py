from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database import engine, SessionLocal
from models import Base, Review

def init_db():
    """Initialize the database and create tables"""
    try:
        # Create all tables
        Base.metadata.create_all(bind=engine)
        print("✅ Review Service database tables created successfully!")
        return True
    except Exception as e:
        print(f"❌ Error creating Review Service database tables: {str(e)}")
        return False

def create_sample_data():
    """Create sample data for testing"""
    db = SessionLocal()
    try:
        # Check if any reviews exist
        existing_review = db.query(Review).first()
        if not existing_review:
            print("✅ Review Service ready for reviews")
    except Exception as e:
        print(f"❌ Error checking sample data: {str(e)}")
    finally:
        db.close()

if __name__ == "__main__":
    init_db()
    create_sample_data()
