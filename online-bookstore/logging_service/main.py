from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from datetime import datetime
import logging
import os
from typing import Optional

app = FastAPI(title="Logging Service", version="1.0.0")

# Create logs directory if it doesn't exist
logs_dir = "/home/sachinn-p/Codes/Microservices/logs"
os.makedirs(logs_dir, exist_ok=True)

# Configure logging
log_file = os.path.join(logs_dir, "micro_services.log")
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class LogEntry(BaseModel):
    service_name: str
    endpoint: str
    method: str
    status_code: int
    user_id: Optional[int] = None
    request_data: Optional[dict] = None
    response_data: Optional[dict] = None
    error_message: Optional[str] = None
    execution_time_ms: Optional[float] = None
    timestamp: Optional[datetime] = None

@app.post("/logs")
def create_log(log_entry: LogEntry):
    """Store log entry"""
    try:
        # Set timestamp if not provided
        if not log_entry.timestamp:
            log_entry.timestamp = datetime.utcnow()
        
        # Format log message
        log_message = f"[{log_entry.service_name}] {log_entry.method} {log_entry.endpoint} - Status: {log_entry.status_code}"
        
        if log_entry.user_id:
            log_message += f" - User: {log_entry.user_id}"
        
        if log_entry.execution_time_ms:
            log_message += f" - Time: {log_entry.execution_time_ms:.2f}ms"
        
        if log_entry.error_message:
            log_message += f" - Error: {log_entry.error_message}"
        
        # Log the message
        if log_entry.status_code >= 400:
            logger.error(log_message)
        else:
            logger.info(log_message)
        
        return {"status": "success", "message": "Log stored successfully"}
    
    except Exception as e:
        logger.error(f"Failed to store log: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to store log")

@app.get("/logs")
def get_logs():
    """Get recent logs"""
    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            # Return last 100 lines
            return {"logs": lines[-100:]}
    except FileNotFoundError:
        return {"logs": []}
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to read logs")

@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "logging_service"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8004)
