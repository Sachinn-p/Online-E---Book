from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database import engine, SessionLocal
from models import Base, User

def init_db():
    """Initialize the database and create tables"""
    try:
        # Create all tables
        Base.metadata.create_all(bind=engine)
        print("✅ User Service database tables created successfully!")
        return True
    except Exception as e:
        print(f"❌ Error creating User Service database tables: {str(e)}")
        return False

def create_sample_data():
    """Create sample data for testing"""
    db = SessionLocal()
    try:
        # Check if any users exist
        existing_user = db.query(User).first()
        if not existing_user:
            # Create a sample user
            from auth import get_password_hash
            sample_user = User(
                username="admin",
                email="admin@bookstore.com",
                password_hash=get_password_hash("admin123"),
                full_name="Admin User"
            )
            db.add(sample_user)
            db.commit()
            print("✅ Sample admin user created (admin/admin123)")
    except Exception as e:
        print(f"❌ Error creating sample data: {str(e)}")
    finally:
        db.close()

if __name__ == "__main__":
    init_db()
    create_sample_data()
