import jwt
from fastapi import HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
#from env_config import settings

# in production load this from os.getenv("JWT_SECRET_KEY") or a secure vault    
JWT_SECRET_KEY = "c820734a34c97336911250bd7ef342bfbb5194ca483e2f7afe8fb4d6985108e3"
ALGORITHM = "HS256"  # You can use other algorithms like HS512, RS256, etc.

security=HTTPBearer()  # This will be used to extract the token from the Authorization header

# function to verify token and return payload or raise HTTPException if invalid or expired
def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[ALGORITHM])
        return payload  # You can return the payload or any specific claims you need
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="JWT Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="JWT Invalid token")