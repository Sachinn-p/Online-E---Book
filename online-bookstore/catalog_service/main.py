from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel, validator
from decimal import Decimal
from database import SessionLocal, engine
from models import Book
import models
from shared_auth import require_auth

# Create database tables
models.Base.metadata.create_all(bind=engine)
print("✅ Catalog Service database tables created successfully!")

app = FastAPI(title="Catalog Service", version="1.0.0")

# Dependency to get database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Pydantic models
class BookCreate(BaseModel):
    title: str
    author: str
    isbn: str
    price: float
    stock_quantity: int
    
    class Config:
        str_strip_whitespace = True
    
    @validator('price')
    def price_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError('Price must be greater than 0')
        return v
    
    @validator('stock_quantity')
    def stock_must_be_non_negative(cls, v):
        if v < 0:
            raise ValueError('Stock quantity cannot be negative')
        return v

class BookUpdate(BaseModel):
    title: Optional[str] = None
    author: Optional[str] = None
    isbn: Optional[str] = None
    price: Optional[float] = None
    stock_quantity: Optional[int] = None

class BookResponse(BaseModel):
    id: int
    title: str
    author: str
    isbn: str
    price: float
    stock_quantity: int

    class Config:
        from_attributes = True

@app.post("/books", response_model=BookResponse)
def create_book(book: BookCreate, current_user: dict = Depends(require_auth), db: Session = Depends(get_db)):
    """Create a new book - requires authentication"""
    # Validate input data
    if book.price <= 0:
        raise HTTPException(status_code=400, detail="Price must be greater than 0")
    if book.stock_quantity < 0:
        raise HTTPException(status_code=400, detail="Stock quantity cannot be negative")
    if len(book.title.strip()) == 0:
        raise HTTPException(status_code=400, detail="Title cannot be empty")
    if len(book.author.strip()) == 0:
        raise HTTPException(status_code=400, detail="Author cannot be empty")
    if len(book.isbn.strip()) == 0:
        raise HTTPException(status_code=400, detail="ISBN cannot be empty")
    
    # Check if book with ISBN already exists
    existing_book = db.query(Book).filter(Book.isbn == book.isbn).first()
    if existing_book:
        raise HTTPException(status_code=400, detail="Book with this ISBN already exists")
    
    try:
        db_book = Book(
            title=book.title.strip(),
            author=book.author.strip(),
            isbn=book.isbn.strip(),
            price=book.price,
            stock_quantity=book.stock_quantity
        )
        db.add(db_book)
        db.commit()
        db.refresh(db_book)
        return db_book
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Error creating book")

@app.get("/books", response_model=List[BookResponse])
def get_books(current_user: dict = Depends(require_auth), db: Session = Depends(get_db)):
    """Get all books - requires authentication"""
    books = db.query(Book).all()
    return books

@app.get("/books/{book_id}", response_model=BookResponse)
def get_book(book_id: int, current_user: dict = Depends(require_auth), db: Session = Depends(get_db)):
    """Get a specific book by ID - requires authentication"""
    if book_id <= 0:
        raise HTTPException(status_code=400, detail="Invalid book ID")
        
    book = db.query(Book).filter(Book.id == book_id).first()
    if book is None:
        raise HTTPException(status_code=404, detail="Book not found")
    return book

@app.put("/books/{book_id}", response_model=BookResponse)
def update_book(book_id: int, book_update: BookUpdate, current_user: dict = Depends(require_auth), db: Session = Depends(get_db)):
    """Update a book - requires authentication"""
    if book_id <= 0:
        raise HTTPException(status_code=400, detail="Invalid book ID")
        
    book = db.query(Book).filter(Book.id == book_id).first()
    if book is None:
        raise HTTPException(status_code=404, detail="Book not found")
    
    # Validate update data
    update_data = book_update.dict(exclude_unset=True)
    if 'price' in update_data and update_data['price'] <= 0:
        raise HTTPException(status_code=400, detail="Price must be greater than 0")
    if 'stock_quantity' in update_data and update_data['stock_quantity'] < 0:
        raise HTTPException(status_code=400, detail="Stock quantity cannot be negative")
    if 'title' in update_data and len(update_data['title'].strip()) == 0:
        raise HTTPException(status_code=400, detail="Title cannot be empty")
    if 'author' in update_data and len(update_data['author'].strip()) == 0:
        raise HTTPException(status_code=400, detail="Author cannot be empty")
    if 'isbn' in update_data and len(update_data['isbn'].strip()) == 0:
        raise HTTPException(status_code=400, detail="ISBN cannot be empty")
    
    try:
        for field, value in update_data.items():
            if isinstance(value, str):
                value = value.strip()
            setattr(book, field, value)
        
        db.commit()
        db.refresh(book)
        return book
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Error updating book")

@app.delete("/books/{book_id}")
def delete_book(book_id: int, current_user: dict = Depends(require_auth), db: Session = Depends(get_db)):
    """Delete a book - requires authentication"""
    book = db.query(Book).filter(Book.id == book_id).first()
    if book is None:
        raise HTTPException(status_code=404, detail="Book not found")
    
    db.delete(book)
    db.commit()
    return {"message": "Book deleted successfully"}

@app.get("/books/search/", response_model=List[BookResponse])
def search_books(query: str, current_user: dict = Depends(require_auth), db: Session = Depends(get_db)):
    """Search books by title or author - requires authentication"""
    if len(query.strip()) < 2:
        raise HTTPException(status_code=400, detail="Search query must be at least 2 characters long")
    
    search_query = f"%{query.strip()}%"
    books = db.query(Book).filter(
        (Book.title.ilike(search_query)) | (Book.author.ilike(search_query))
    ).all()
    return books

@app.get("/health")
def health_check():
    """Health check endpoint - public"""
    return {"status": "healthy", "service": "catalog_service"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
