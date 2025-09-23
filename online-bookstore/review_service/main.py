from fastapi import FastAPI, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
import time
from database import SessionLocal, engine
from models import Review
import models
from shared_auth import require_auth
from shared_logging import MicroserviceLogger

# Create database tables
models.Base.metadata.create_all(bind=engine)
print("✅ Review Service database tables created successfully!")

app = FastAPI(title="Review Service", version="1.0.0")

# Initialize logger
logger = MicroserviceLogger("review_service")

# Dependency to get database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Pydantic models
class ReviewCreate(BaseModel):
    book_id: int
    user_id: int
    rating: int
    comment: str

class ReviewResponse(BaseModel):
    id: int
    book_id: int
    user_id: int
    rating: int
    comment: str
    created_at: datetime

    class Config:
        from_attributes = True

class BookRatingStats(BaseModel):
    book_id: int
    average_rating: float
    total_reviews: int

@app.post("/reviews", response_model=ReviewResponse)
def add_review(review: ReviewCreate, current_user: dict = Depends(require_auth), db: Session = Depends(get_db)):
    """Add a review for a book - requires authentication"""
    # Validate input data
    if review.rating < 1 or review.rating > 5:
        raise HTTPException(status_code=400, detail="Rating must be between 1 and 5")
    if review.book_id <= 0:
        raise HTTPException(status_code=400, detail="Invalid book ID")
    if review.user_id <= 0:
        raise HTTPException(status_code=400, detail="Invalid user ID")
    if len(review.comment.strip()) == 0:
        raise HTTPException(status_code=400, detail="Comment cannot be empty")
    
    # Check if user already reviewed this book
    existing_review = db.query(Review).filter(
        Review.book_id == review.book_id,
        Review.user_id == review.user_id
    ).first()
    
    if existing_review:
        raise HTTPException(status_code=400, detail="User has already reviewed this book")
    
    try:
        # Create new review
        db_review = Review(
            book_id=review.book_id,
            user_id=review.user_id,
            rating=review.rating,
            comment=review.comment.strip(),
            created_at=datetime.utcnow()
        )
        
        db.add(db_review)
        db.commit()
        db.refresh(db_review)
        
        return db_review
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Error creating review")

@app.get("/reviews/{review_id}", response_model=ReviewResponse)
def get_review(review_id: int, current_user: dict = Depends(require_auth), db: Session = Depends(get_db)):
    """Get a specific review by ID - requires authentication"""
    if review_id <= 0:
        raise HTTPException(status_code=400, detail="Invalid review ID")
        
    review = db.query(Review).filter(Review.id == review_id).first()
    if review is None:
        raise HTTPException(status_code=404, detail="Review not found")
    return review

@app.get("/reviews/book/{book_id}", response_model=List[ReviewResponse])
def get_book_reviews(book_id: int, current_user: dict = Depends(require_auth), db: Session = Depends(get_db)):
    """Get all reviews for a specific book - requires authentication"""
    reviews = db.query(Review).filter(Review.book_id == book_id).all()
    return reviews

@app.get("/reviews/user/{user_id}", response_model=List[ReviewResponse])
def get_user_reviews(user_id: int, current_user: dict = Depends(require_auth), db: Session = Depends(get_db)):
    """Get all reviews by a specific user - requires authentication"""
    reviews = db.query(Review).filter(Review.user_id == user_id).all()
    return reviews

@app.get("/reviews/book/{book_id}/stats", response_model=BookRatingStats)
def get_book_rating_stats(book_id: int, db: Session = Depends(get_db)):
    """Get rating statistics for a book - public endpoint"""
    result = db.query(
        func.avg(Review.rating).label('average_rating'),
        func.count(Review.id).label('total_reviews')
    ).filter(Review.book_id == book_id).first()
    
    if result.total_reviews == 0:
        raise HTTPException(status_code=404, detail="No reviews found for this book")
    
    return BookRatingStats(
        book_id=book_id,
        average_rating=round(float(result.average_rating), 2),
        total_reviews=int(result.total_reviews)
    )

@app.put("/reviews/{review_id}")
def update_review(
    review_id: int,
    rating: Optional[int] = None,
    comment: Optional[str] = None,
    current_user: dict = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """Update an existing review - requires authentication"""
    db_review = db.query(Review).filter(Review.id == review_id).first()
    if db_review is None:
        raise HTTPException(status_code=404, detail="Review not found")
    
    if rating is not None:
        if rating < 1 or rating > 5:
            raise HTTPException(status_code=400, detail="Rating must be between 1 and 5")
        db_review.rating = rating
    
    if comment is not None:
        db_review.comment = comment
    
    db.commit()
    db.refresh(db_review)
    
    return {"message": "Review updated successfully", "review_id": review_id}

@app.delete("/reviews/{review_id}")
def delete_review(review_id: int, current_user: dict = Depends(require_auth), db: Session = Depends(get_db)):
    """Delete a review - requires authentication"""
    db_review = db.query(Review).filter(Review.id == review_id).first()
    if db_review is None:
        raise HTTPException(status_code=404, detail="Review not found")
    
    db.delete(db_review)
    db.commit()
    
    return {"message": "Review deleted successfully", "review_id": review_id}

@app.get("/health")
def health_check(request: Request):
    """Health check endpoint - public"""
    start_time = time.time()
    status_code = 200
    response_data = {"status": "healthy", "service": "review_service"}
    
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
    uvicorn.run(app, host="0.0.0.0", port=8007)
