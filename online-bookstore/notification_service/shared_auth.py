import requests
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Dict, Optional

# User service URL for token verification
USER_SERVICE_URL = "http://localhost:8001"

# Security scheme for JWT
security = HTTPBearer()

class AuthService:
    """Authentication service to verify tokens with user service"""
    
    @staticmethod
    def verify_token_with_user_service(token: str) -> Dict:
        """Verify token with user service"""
        try:
            headers = {"Authorization": f"Bearer {token}"}
            response = requests.get(f"{USER_SERVICE_URL}/verify-token", headers=headers)
            
            if response.status_code == 200:
                return response.json()
            else:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid authentication credentials",
                    headers={"WWW-Authenticate": "Bearer"},
                )
        except requests.RequestException:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Authentication service unavailable"
            )

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict:
    """Get current user information from JWT token"""
    token = credentials.credentials
    user_info = AuthService.verify_token_with_user_service(token)
    return user_info

def require_auth(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict:
    """Dependency to require authentication"""
    return get_current_user(credentials)
