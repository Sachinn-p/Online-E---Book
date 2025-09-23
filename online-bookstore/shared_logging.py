import httpx
import json
from datetime import datetime
from typing import Optional, Any
import asyncio
import threading

class MicroserviceLogger:
    def __init__(self, service_name: str, logging_service_url: str = "http://localhost:8004"):
        self.service_name = service_name
        self.logging_service_url = logging_service_url
    
    def _send_log_async(self, log_data: dict):
        """Send log asynchronously to avoid blocking the main thread"""
        def send_log():
            try:
                with httpx.Client(timeout=5.0) as client:
                    response = client.post(f"{self.logging_service_url}/logs", json=log_data)
                    if response.status_code != 200:
                        print(f"Failed to send log to logging service: {response.status_code}")
            except Exception as e:
                print(f"Error sending log to logging service: {str(e)}")
        
        # Run in a separate thread to avoid blocking
        thread = threading.Thread(target=send_log)
        thread.daemon = True
        thread.start()
    
    def log_request(
        self,
        endpoint: str,
        method: str,
        status_code: int,
        user_id: Optional[int] = None,
        request_data: Optional[Any] = None,
        response_data: Optional[Any] = None,
        error_message: Optional[str] = None,
        execution_time_ms: Optional[float] = None
    ):
        """Log a request to the logging service"""
        
        # Safely serialize request and response data
        def safe_serialize(data):
            if data is None:
                return None
            try:
                # Convert to dict if it's a Pydantic model
                if hasattr(data, 'dict'):
                    return data.dict()
                # Handle other serializable types
                json.dumps(data)  # Test if it's serializable
                return data
            except (TypeError, ValueError):
                return str(data)  # Fallback to string representation
        
        log_data = {
            "service_name": self.service_name,
            "endpoint": endpoint,
            "method": method,
            "status_code": status_code,
            "user_id": user_id,
            "request_data": safe_serialize(request_data),
            "response_data": safe_serialize(response_data),
            "error_message": error_message,
            "execution_time_ms": execution_time_ms,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Send log asynchronously
        self._send_log_async(log_data)
