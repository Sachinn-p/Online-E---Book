from fastapi import FastAPI, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
import time
from database import SessionLocal, engine
from models import Payment
import models
from shared_auth import require_auth
from shared_logging import MicroserviceLogger

# Create database tables
models.Base.metadata.create_all(bind=engine)
print("✅ Payment Service database tables created successfully!")

app = FastAPI(title="Payment Service", version="1.0.0")

# Initialize logger
logger = MicroserviceLogger("payment_service")

# Dependency to get database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Pydantic models
class PaymentCreate(BaseModel):
    order_id: int
    amount: float
    payment_method: str
    card_number: str

class PaymentResponse(BaseModel):
    id: int
    order_id: int
    amount: float
    payment_method: str
    payment_date: datetime
    status: str

    class Config:
        from_attributes = True

class RefundCreate(BaseModel):
    amount: float
    reason: str

@app.post("/payments", response_model=PaymentResponse)
def process_payment(request: Request, payment: PaymentCreate, current_user: dict = Depends(require_auth), db: Session = Depends(get_db)):
    """Process a payment - requires authentication"""
    start_time = time.time()
    user_id = current_user.get('user_id')
    error_message = None
    response_data = None
    status_code = 200
    
    try:
        # Validate payment data
        if payment.amount <= 0:
            raise HTTPException(status_code=400, detail="Payment amount must be greater than 0")
        if payment.order_id <= 0:
            raise HTTPException(status_code=400, detail="Invalid order ID")
        if len(payment.payment_method.strip()) == 0:
            raise HTTPException(status_code=400, detail="Payment method cannot be empty")
        if len(payment.card_number.strip()) == 0:
            raise HTTPException(status_code=400, detail="Card number cannot be empty")
        
        # Basic card number validation (length check)
        card_number = payment.card_number.replace(" ", "").replace("-", "")
        if not card_number.isdigit() or len(card_number) < 13 or len(card_number) > 19:
            raise HTTPException(status_code=400, detail="Invalid card number format")
        
        # Simulate payment processing
        import random
        success = random.choice([True, True, True, False])  # 75% success rate
        
        db_payment = Payment(
            order_id=payment.order_id,
            amount=payment.amount,
            payment_method=payment.payment_method.strip(),
            payment_date=datetime.utcnow(),
            status="completed" if success else "failed"
        )
        
        db.add(db_payment)
        db.commit()
        db.refresh(db_payment)
        
        if not success:
            raise HTTPException(status_code=400, detail="Payment processing failed")
        
        response_data = db_payment
        return db_payment
    except HTTPException as e:
        db.rollback()
        status_code = e.status_code
        error_message = e.detail
        raise e
    except Exception as e:
        db.rollback()
        status_code = 500
        error_message = "Error processing payment"
        raise HTTPException(status_code=500, detail="Error processing payment")
    finally:
        execution_time = (time.time() - start_time) * 1000
        logger.log_request(
            endpoint="/payments",
            method="POST",
            status_code=status_code,
            user_id=user_id,
            request_data=payment,
            response_data=response_data,
            error_message=error_message,
            execution_time_ms=execution_time
        )

@app.get("/payments/{payment_id}", response_model=PaymentResponse)
def get_payment(request: Request, payment_id: int, current_user: dict = Depends(require_auth), db: Session = Depends(get_db)):
    """Get payment by ID - requires authentication"""
    start_time = time.time()
    user_id = current_user.get('user_id')
    error_message = None
    response_data = None
    status_code = 200
    
    try:
        if payment_id <= 0:
            raise HTTPException(status_code=400, detail="Invalid payment ID")
            
        payment = db.query(Payment).filter(Payment.id == payment_id).first()
        if payment is None:
            raise HTTPException(status_code=404, detail="Payment not found")
        
        response_data = payment
        return payment
    except HTTPException as e:
        status_code = e.status_code
        error_message = e.detail
        raise e
    except Exception as e:
        status_code = 500
        error_message = str(e)
        raise HTTPException(status_code=500, detail="Error fetching payment")
    finally:
        execution_time = (time.time() - start_time) * 1000
        logger.log_request(
            endpoint=f"/payments/{payment_id}",
            method="GET",
            status_code=status_code,
            user_id=user_id,
            request_data={"payment_id": payment_id},
            response_data=response_data,
            error_message=error_message,
            execution_time_ms=execution_time
        )

@app.get("/payments/order/{order_id}", response_model=List[PaymentResponse])
def get_payments_by_order(request: Request, order_id: int, current_user: dict = Depends(require_auth), db: Session = Depends(get_db)):
    """Get all payments for an order - requires authentication"""
    start_time = time.time()
    user_id = current_user.get('user_id')
    error_message = None
    response_data = None
    status_code = 200
    
    try:
        payments = db.query(Payment).filter(Payment.order_id == order_id).all()
        response_data = payments
        return payments
    except Exception as e:
        status_code = 500
        error_message = str(e)
        raise HTTPException(status_code=500, detail="Error fetching payments")
    finally:
        execution_time = (time.time() - start_time) * 1000
        logger.log_request(
            endpoint=f"/payments/order/{order_id}",
            method="GET",
            status_code=status_code,
            user_id=user_id,
            request_data={"order_id": order_id},
            response_data=len(response_data) if response_data else 0,
            error_message=error_message,
            execution_time_ms=execution_time
        )

@app.post("/payments/{payment_id}/refund")
def process_refund(payment_id: int, refund: RefundCreate, current_user: dict = Depends(require_auth), db: Session = Depends(get_db)):
    """Process a refund - requires authentication"""
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if payment is None:
        raise HTTPException(status_code=404, detail="Payment not found")
    
    if payment.status != "completed":
        raise HTTPException(status_code=400, detail="Can only refund completed payments")
    
    if refund.amount > payment.amount:
        raise HTTPException(status_code=400, detail="Refund amount cannot exceed payment amount")
    
    # Create refund record (simplified - in real system this would be a separate table)
    refund_payment = Payment(
        order_id=payment.order_id,
        amount=-refund.amount,  # Negative amount for refund
        payment_method=payment.payment_method,
        payment_date=datetime.utcnow(),
        status="refunded"
    )
    
    db.add(refund_payment)
    db.commit()
    db.refresh(refund_payment)
    
    return {
        "message": "Refund processed successfully",
        "refund_id": refund_payment.id,
        "amount": refund.amount,
        "reason": refund.reason
    }

@app.get("/health")
def health_check(request: Request):
    """Health check endpoint - public"""
    start_time = time.time()
    status_code = 200
    response_data = {"status": "healthy", "service": "payment_service"}
    
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
    uvicorn.run(app, host="0.0.0.0", port=8005)
