import logging
from typing import Optional
from fastapi import HTTPException, Security, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from config.config import settings

logger = logging.getLogger(__name__)

# Initialize HTTP Bearer security scheme
security = HTTPBearer()

class AuthenticationService:
    """Service for handling API authentication"""

    def __init__(self):
        self.valid_token = settings.HACKRX_API_TOKEN

    async def verify_token(self, credentials: HTTPAuthorizationCredentials = Security(security)) -> str:
        """Verify the provided token"""

        if not credentials:
            raise HTTPException(
                status_code=401,
                detail="Authorization credentials required",
                headers={"WWW-Authenticate": "Bearer"},
            )

        token = credentials.credentials

        if not self._is_valid_token(token):
            logger.warning(f"Invalid token provided: {token[:10]}...")
            raise HTTPException(
                status_code=401,
                detail="Invalid authentication token",
                headers={"WWW-Authenticate": "Bearer"},
            )

        logger.debug("Token verified successfully")
        return token

    def _is_valid_token(self, token: str) -> bool:
        """Check if the token is valid"""
        return token == self.valid_token

# Create global auth service instance
auth_service = AuthenticationService()

# Dependency for protecting routes
async def get_current_token(token: str = Depends(auth_service.verify_token)) -> str:
    """Dependency to get current valid token"""
    return token

# Security middleware
class SecurityMiddleware:
    """Security middleware for additional protection"""

    @staticmethod
    def validate_request_size(content_length: Optional[int] = None) -> bool:
        """Validate request size"""
        if content_length and content_length > settings.MAX_FILE_SIZE:
            return False
        return True

    @staticmethod
    def sanitize_input(text: str) -> str:
        """Basic input sanitization"""
        if not text:
            return ""

        # Remove potentially dangerous characters
        dangerous_chars = ['<', '>', '"', "'", '&', 'javascript:', 'data:']

        for char in dangerous_chars:
            text = text.replace(char, '')

        return text.strip()
