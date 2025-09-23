from fastapi import FastAPI, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel, validator
from decimal import Decimal
import time
from database import SessionLocal, engine
from models import Book
import models
from shared_auth import require_auth
from shared_logging import MicroserviceLogger

# Create database tables
models.Base.metadata.create_all(bind=engine)
print("✅ Catalog Service database tables created successfully!")

app = FastAPI(title="Catalog Service", version="1.0.0")

# Initialize logger
logger = MicroserviceLogger("catalog_service")

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
def create_book(request: Request, book: BookCreate, current_user: dict = Depends(require_auth), db: Session = Depends(get_db)):
    """Create a new book - requires authentication"""
    start_time = time.time()
    user_id = current_user.get('user_id')
    error_message = None
    response_data = None
    status_code = 200
    
    try:
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
        response_data = db_book
        return db_book
    except HTTPException as e:
        db.rollback()
        status_code = e.status_code
        error_message = e.detail
        raise e
    except Exception as e:
        db.rollback()
        status_code = 500
        error_message = "Error creating book"
        raise HTTPException(status_code=500, detail="Error creating book")
    finally:
        execution_time = (time.time() - start_time) * 1000
        logger.log_request(
            endpoint="/books",
            method="POST",
            status_code=status_code,
            user_id=user_id,
            request_data=book,
            response_data=response_data,
            error_message=error_message,
            execution_time_ms=execution_time
        )

@app.get("/books", response_model=List[BookResponse])
def get_books(request: Request, current_user: dict = Depends(require_auth), db: Session = Depends(get_db)):
    """Get all books - requires authentication"""
    start_time = time.time()
    user_id = current_user.get('user_id')
    error_message = None
    response_data = None
    status_code = 200
    
    try:
        books = db.query(Book).all()
        response_data = books
        return books
    except Exception as e:
        status_code = 500
        error_message = str(e)
        raise HTTPException(status_code=500, detail="Error fetching books")
    finally:
        execution_time = (time.time() - start_time) * 1000
        logger.log_request(
            endpoint="/books",
            method="GET",
            status_code=status_code,
            user_id=user_id,
            request_data=None,
            response_data=len(response_data) if response_data else 0,
            error_message=error_message,
            execution_time_ms=execution_time
        )

@app.get("/books/{book_id}", response_model=BookResponse)
def get_book(request: Request, book_id: int, current_user: dict = Depends(require_auth), db: Session = Depends(get_db)):
    """Get a specific book by ID - requires authentication"""
    start_time = time.time()
    user_id = current_user.get('user_id')
    error_message = None
    response_data = None
    status_code = 200
    
    try:
        if book_id <= 0:
            raise HTTPException(status_code=400, detail="Invalid book ID")
            
        book = db.query(Book).filter(Book.id == book_id).first()
        if book is None:
            raise HTTPException(status_code=404, detail="Book not found")
        
        response_data = book
        return book
    except HTTPException as e:
        status_code = e.status_code
        error_message = e.detail
        raise e
    except Exception as e:
        status_code = 500
        error_message = str(e)
        raise HTTPException(status_code=500, detail="Error fetching book")
    finally:
        execution_time = (time.time() - start_time) * 1000
        logger.log_request(
            endpoint=f"/books/{book_id}",
            method="GET",
            status_code=status_code,
            user_id=user_id,
            request_data={"book_id": book_id},
            response_data=response_data,
            error_message=error_message,
            execution_time_ms=execution_time
        )

@app.put("/books/{book_id}", response_model=BookResponse)
def update_book(request: Request, book_id: int, book_update: BookUpdate, current_user: dict = Depends(require_auth), db: Session = Depends(get_db)):
    """Update a book - requires authentication"""
    start_time = time.time()
    user_id = current_user.get('user_id')
    error_message = None
    response_data = None
    status_code = 200
    
    try:
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
        
        for field, value in update_data.items():
            if isinstance(value, str):
                value = value.strip()
            setattr(book, field, value)
        
        db.commit()
        db.refresh(book)
        response_data = book
        return book
    except HTTPException as e:
        db.rollback()
        status_code = e.status_code
        error_message = e.detail
        raise e
    except Exception as e:
        db.rollback()
        status_code = 500
        error_message = "Error updating book"
        raise HTTPException(status_code=500, detail="Error updating book")
    finally:
        execution_time = (time.time() - start_time) * 1000
        logger.log_request(
            endpoint=f"/books/{book_id}",
            method="PUT",
            status_code=status_code,
            user_id=user_id,
            request_data=book_update,
            response_data=response_data,
            error_message=error_message,
            execution_time_ms=execution_time
        )

@app.delete("/books/{book_id}")
def delete_book(request: Request, book_id: int, current_user: dict = Depends(require_auth), db: Session = Depends(get_db)):
    """Delete a book - requires authentication"""
    start_time = time.time()
    user_id = current_user.get('user_id')
    error_message = None
    response_data = None
    status_code = 200
    
    try:
        book = db.query(Book).filter(Book.id == book_id).first()
        if book is None:
            raise HTTPException(status_code=404, detail="Book not found")
        
        db.delete(book)
        db.commit()
        response_data = {"message": "Book deleted successfully"}
        return response_data
    except HTTPException as e:
        status_code = e.status_code
        error_message = e.detail
        raise e
    except Exception as e:
        status_code = 500
        error_message = "Error deleting book"
        raise HTTPException(status_code=500, detail="Error deleting book")
    finally:
        execution_time = (time.time() - start_time) * 1000
        logger.log_request(
            endpoint=f"/books/{book_id}",
            method="DELETE",
            status_code=status_code,
            user_id=user_id,
            request_data={"book_id": book_id},
            response_data=response_data,
            error_message=error_message,
            execution_time_ms=execution_time
        )

@app.get("/books/search/", response_model=List[BookResponse])
def search_books(request: Request, query: str, current_user: dict = Depends(require_auth), db: Session = Depends(get_db)):
    """Search books by title or author - requires authentication"""
    start_time = time.time()
    user_id = current_user.get('user_id')
    error_message = None
    response_data = None
    status_code = 200
    
    try:
        if len(query.strip()) < 2:
            raise HTTPException(status_code=400, detail="Search query must be at least 2 characters long")
        
        search_query = f"%{query.strip()}%"
        books = db.query(Book).filter(
            (Book.title.ilike(search_query)) | (Book.author.ilike(search_query))
        ).all()
        response_data = books
        return books
    except HTTPException as e:
        status_code = e.status_code
        error_message = e.detail
        raise e
    except Exception as e:
        status_code = 500
        error_message = str(e)
        raise HTTPException(status_code=500, detail="Error searching books")
    finally:
        execution_time = (time.time() - start_time) * 1000
        logger.log_request(
            endpoint="/books/search/",
            method="GET",
            status_code=status_code,
            user_id=user_id,
            request_data={"query": query},
            response_data=len(response_data) if response_data else 0,
            error_message=error_message,
            execution_time_ms=execution_time
        )

@app.get("/health")
def health_check(request: Request):
    """Health check endpoint - public"""
    start_time = time.time()
    status_code = 200
    response_data = {"status": "healthy", "service": "catalog_service"}
    
    execution_time = (time.time() - start_time) * 1000
    logger.log_request(
        endpoint="/health",
        method="GET",
        status_code=status_code,
        user_id=None,
        request_data=None,
        response_data=response_data,
        error_message=None,
        execution_time_ms=execution_time
    )
    
    return response_data

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
