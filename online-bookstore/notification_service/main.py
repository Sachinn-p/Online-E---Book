from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel
from datetime import datetime
from database import SessionLocal, engine
from models import Notification
import models
from shared_auth import require_auth

# Create database tables
models.Base.metadata.create_all(bind=engine)
print("✅ Notification Service database tables created successfully!")

app = FastAPI(title="Notification Service", version="1.0.0")

# Dependency to get database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Pydantic models
class NotificationCreate(BaseModel):
    user_id: int
    message: str
    type: str

class NotificationResponse(BaseModel):
    id: int
    user_id: int
    message: str
    type: str
    created_at: datetime
    is_read: bool

    class Config:
        from_attributes = True

@app.post("/notifications", response_model=NotificationResponse)
def send_notification(notification: NotificationCreate, current_user: dict = Depends(require_auth), db: Session = Depends(get_db)):
    """Send a notification - requires authentication"""
    # Validate input data
    if notification.user_id <= 0:
        raise HTTPException(status_code=400, detail="Invalid user ID")
    if len(notification.message.strip()) == 0:
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    if len(notification.type.strip()) == 0:
        raise HTTPException(status_code=400, detail="Notification type cannot be empty")
    
    # Validate notification type
    valid_types = ["order", "payment", "general", "system", "alert"]
    if notification.type.lower() not in valid_types:
        raise HTTPException(status_code=400, detail=f"Invalid notification type. Must be one of: {valid_types}")
    
    try:
        db_notification = Notification(
            user_id=notification.user_id,
            message=notification.message.strip(),
            type=notification.type.lower().strip(),
            created_at=datetime.utcnow(),
            is_read=False
        )
        
        db.add(db_notification)
        db.commit()
        db.refresh(db_notification)
        return db_notification
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Error creating notification")

@app.get("/notifications/user/{user_id}", response_model=List[NotificationResponse])
def get_user_notifications(user_id: int, current_user: dict = Depends(require_auth), db: Session = Depends(get_db)):
    """Get all notifications for a user - requires authentication"""
    notifications = db.query(Notification).filter(Notification.user_id == user_id).order_by(Notification.created_at.desc()).all()
    return notifications

@app.put("/notifications/{notification_id}/read")
def mark_notification_as_read(notification_id: int, current_user: dict = Depends(require_auth), db: Session = Depends(get_db)):
    """Mark a notification as read - requires authentication"""
    notification = db.query(Notification).filter(Notification.id == notification_id).first()
    if notification is None:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    notification.is_read = True
    db.commit()
    return {"message": "Notification marked as read"}

@app.delete("/notifications/{notification_id}")
def delete_notification(notification_id: int, current_user: dict = Depends(require_auth), db: Session = Depends(get_db)):
    """Delete a notification - requires authentication"""
    notification = db.query(Notification).filter(Notification.id == notification_id).first()
    if notification is None:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    db.delete(notification)
    db.commit()
    return {"message": "Notification deleted successfully"}

@app.get("/health")
def health_check():
    """Health check endpoint - public"""
    return {"status": "healthy", "service": "notification_service"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8005)
