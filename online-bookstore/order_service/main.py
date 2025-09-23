from fastapi import FastAPI, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel, validator
from datetime import datetime
import time
from database import SessionLocal, engine
from models import Order, OrderItem
import models
from shared_auth import require_auth
from shared_logging import MicroserviceLogger

# Create database tables
models.Base.metadata.create_all(bind=engine)
print("✅ Order Service database tables created successfully!")

app = FastAPI(title="Order Service", version="1.0.0")

# Initialize logger
logger = MicroserviceLogger("order_service")

# Dependency to get database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Pydantic models
class OrderItemCreate(BaseModel):
    book_id: int
    quantity: int
    price: float
    
    @validator('book_id')
    def book_id_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError('Book ID must be greater than 0')
        return v
    
    @validator('quantity')
    def quantity_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError('Quantity must be greater than 0')
        return v
    
    @validator('price')
    def price_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError('Price must be greater than 0')
        return v

class OrderCreate(BaseModel):
    user_id: int
    items: List[OrderItemCreate]
    
    @validator('user_id')
    def user_id_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError('User ID must be greater than 0')
        return v
    
    @validator('items')
    def items_must_not_be_empty(cls, v):
        if not v:
            raise ValueError('Order must contain at least one item')
        return v

class OrderItemResponse(BaseModel):
    id: int
    book_id: int
    quantity: int
    price: float

    class Config:
        from_attributes = True

class OrderResponse(BaseModel):
    id: int
    user_id: int
    order_date: datetime
    status: str
    total_amount: float
    items: List[OrderItemResponse]

    class Config:
        from_attributes = True

class OrderStatusUpdate(BaseModel):
    status: str

@app.post("/orders", response_model=OrderResponse)
def create_order(request: Request, order: OrderCreate, current_user: dict = Depends(require_auth), db: Session = Depends(get_db)):
    """Create a new order - requires authentication"""
    start_time = time.time()
    user_id = current_user.get('user_id')
    error_message = None
    response_data = None
    status_code = 200
    
    try:
        # Validate order data
        if not order.items:
            raise HTTPException(status_code=400, detail="Order must contain at least one item")
        
        if order.user_id <= 0:
            raise HTTPException(status_code=400, detail="Invalid user ID")
        
        # Validate all items
        for item in order.items:
            if item.quantity <= 0:
                raise HTTPException(status_code=400, detail="Item quantity must be greater than 0")
            if item.price <= 0:
                raise HTTPException(status_code=400, detail="Item price must be greater than 0")
            if item.book_id <= 0:
                raise HTTPException(status_code=400, detail="Invalid book ID")
        
        # Calculate total amount
        total_amount = sum(item.price * item.quantity for item in order.items)
        
        # Create order
        db_order = Order(
            user_id=order.user_id,
            order_date=datetime.utcnow(),
            status="pending",
            total_amount=total_amount
        )
        db.add(db_order)
        db.commit()
        db.refresh(db_order)
        
        # Create order items
        for item in order.items:
            db_item = OrderItem(
                order_id=db_order.id,
                book_id=item.book_id,
                quantity=item.quantity,
                price=item.price
            )
            db.add(db_item)
        
        db.commit()
        db.refresh(db_order)
        response_data = db_order
        
    except HTTPException as e:
        db.rollback()
        status_code = e.status_code
        error_message = e.detail
        raise e
    except Exception as e:
        db.rollback()
        status_code = 500
        error_message = "Error creating order"
        raise HTTPException(status_code=500, detail="Error creating order")
    finally:
        execution_time = (time.time() - start_time) * 1000
        logger.log_request(
            endpoint="/orders",
            method="POST",
            status_code=status_code,
            user_id=user_id,
            request_data=order,
            response_data=response_data,
            error_message=error_message,
            execution_time_ms=execution_time
        )
    
    return response_data

@app.get("/orders", response_model=List[OrderResponse])
def get_orders(request: Request, current_user: dict = Depends(require_auth), db: Session = Depends(get_db)):
    """Get all orders - requires authentication"""
    start_time = time.time()
    user_id = current_user.get('user_id')
    error_message = None
    response_data = None
    status_code = 200
    
    try:
        orders = db.query(Order).all()
        response_data = orders
        return orders
    except Exception as e:
        status_code = 500
        error_message = str(e)
        raise HTTPException(status_code=500, detail="Error fetching orders")
    finally:
        execution_time = (time.time() - start_time) * 1000
        logger.log_request(
            endpoint="/orders",
            method="GET",
            status_code=status_code,
            user_id=user_id,
            request_data=None,
            response_data=len(response_data) if response_data else 0,
            error_message=error_message,
            execution_time_ms=execution_time
        )

@app.get("/orders/{order_id}", response_model=OrderResponse)
def get_order(request: Request, order_id: int, current_user: dict = Depends(require_auth), db: Session = Depends(get_db)):
    """Get a specific order by ID - requires authentication"""
    start_time = time.time()
    user_id = current_user.get('user_id')
    error_message = None
    response_data = None
    status_code = 200
    
    try:
        if order_id <= 0:
            raise HTTPException(status_code=400, detail="Invalid order ID")
            
        order = db.query(Order).filter(Order.id == order_id).first()
        if order is None:
            raise HTTPException(status_code=404, detail="Order not found")
        
        response_data = order
        return order
    except HTTPException as e:
        status_code = e.status_code
        error_message = e.detail
        raise e
    except Exception as e:
        status_code = 500
        error_message = str(e)
        raise HTTPException(status_code=500, detail="Error fetching order")
    finally:
        execution_time = (time.time() - start_time) * 1000
        logger.log_request(
            endpoint=f"/orders/{order_id}",
            method="GET",
            status_code=status_code,
            user_id=user_id,
            request_data={"order_id": order_id},
            response_data=response_data,
            error_message=error_message,
            execution_time_ms=execution_time
        )

@app.get("/orders/user/{user_id}", response_model=List[OrderResponse])
def get_user_orders(request: Request, user_id: int, current_user: dict = Depends(require_auth), db: Session = Depends(get_db)):
    """Get all orders for a specific user - requires authentication"""
    start_time = time.time()
    current_user_id = current_user.get('user_id')
    error_message = None
    response_data = None
    status_code = 200
    
    try:
        orders = db.query(Order).filter(Order.user_id == user_id).all()
        response_data = orders
        return orders
    except Exception as e:
        status_code = 500
        error_message = str(e)
        raise HTTPException(status_code=500, detail="Error fetching user orders")
    finally:
        execution_time = (time.time() - start_time) * 1000
        logger.log_request(
            endpoint=f"/orders/user/{user_id}",
            method="GET",
            status_code=status_code,
            user_id=current_user_id,
            request_data={"user_id": user_id},
            response_data=len(response_data) if response_data else 0,
            error_message=error_message,
            execution_time_ms=execution_time
        )

@app.put("/orders/{order_id}/status", response_model=OrderResponse)
def update_order_status(request: Request, order_id: int, status_update: OrderStatusUpdate, current_user: dict = Depends(require_auth), db: Session = Depends(get_db)):
    """Update order status - requires authentication"""
    start_time = time.time()
    user_id = current_user.get('user_id')
    error_message = None
    response_data = None
    status_code = 200
    
    try:
        order = db.query(Order).filter(Order.id == order_id).first()
        if order is None:
            raise HTTPException(status_code=404, detail="Order not found")
        
        valid_statuses = ["pending", "confirmed", "shipped", "delivered", "cancelled"]
        if status_update.status not in valid_statuses:
            raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {valid_statuses}")
        
        order.status = status_update.status
        db.commit()
        db.refresh(order)
        response_data = order
        return order
    except HTTPException as e:
        status_code = e.status_code
        error_message = e.detail
        raise e
    except Exception as e:
        status_code = 500
        error_message = str(e)
        raise HTTPException(status_code=500, detail="Error updating order status")
    finally:
        execution_time = (time.time() - start_time) * 1000
        logger.log_request(
            endpoint=f"/orders/{order_id}/status",
            method="PUT",
            status_code=status_code,
            user_id=user_id,
            request_data=status_update,
            response_data=response_data,
            error_message=error_message,
            execution_time_ms=execution_time
        )

@app.get("/health")
def health_check(request: Request):
    """Health check endpoint - public"""
    start_time = time.time()
    status_code = 200
    response_data = {"status": "healthy", "service": "order_service"}
    
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
    uvicorn.run(app, host="0.0.0.0", port=8003)
