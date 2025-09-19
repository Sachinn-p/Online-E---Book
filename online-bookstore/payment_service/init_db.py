from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database import engine, SessionLocal
from models import Base, Payment

def init_db():
    """Initialize the database and create tables"""
    try:
        # Create all tables
        Base.metadata.create_all(bind=engine)
        print("✅ Payment Service database tables created successfully!")
        return True
    except Exception as e:
        print(f"❌ Error creating Payment Service database tables: {str(e)}")
        return False

def create_sample_data():
    """Create sample data for testing"""
    db = SessionLocal()
    try:
        # Check if any payments exist
        existing_payment = db.query(Payment).first()
        if not existing_payment:
            print("✅ Payment Service ready for transactions")
    except Exception as e:
        print(f"❌ Error checking sample data: {str(e)}")
    finally:
        db.close()

if __name__ == "__main__":
    init_db()
    create_sample_data()
