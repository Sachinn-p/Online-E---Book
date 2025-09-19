from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database import engine, SessionLocal
from models import Base, Book

def init_db():
    """Initialize the database and create tables"""
    try:
        # Create all tables
        Base.metadata.create_all(bind=engine)
        print("✅ Catalog Service database tables created successfully!")
        return True
    except Exception as e:
        print(f"❌ Error creating Catalog Service database tables: {str(e)}")
        return False

def create_sample_data():
    """Create sample data for testing"""
    db = SessionLocal()
    try:
        # Check if any books exist
        existing_book = db.query(Book).first()
        if not existing_book:
            # Create sample books
            sample_books = [
                Book(
                    title="The Great Gatsby",
                    author="F. Scott Fitzgerald",
                    isbn="9780743273565",
                    price=12.99,
                    stock_quantity=50
                ),
                Book(
                    title="To Kill a Mockingbird",
                    author="Harper Lee",
                    isbn="9780061120084",
                    price=14.99,
                    stock_quantity=30
                ),
                Book(
                    title="1984",
                    author="George Orwell",
                    isbn="9780451524935",
                    price=13.99,
                    stock_quantity=25
                )
            ]
            
            for book in sample_books:
                db.add(book)
            
            db.commit()
            print("✅ Sample books created in catalog")
    except Exception as e:
        print(f"❌ Error creating sample data: {str(e)}")
    finally:
        db.close()

if __name__ == "__main__":
    init_db()
    create_sample_data()
