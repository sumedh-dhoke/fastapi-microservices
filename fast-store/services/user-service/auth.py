from passlib.context import CryptContext
import jwt
from datetime import datetime, timedelta, timezone


# we use bcrypt for secure password hashing. bcrypt is a widely used and secure hashing algorithm that is designed to be slow, making it resistant to brute-force attacks. It also incorporates a salt to protect against rainbow table attacks.
pwd_context = CryptContext(schemes=["bcrypt"],deprecated="auto")


# Must match the shared secret in jwt-utils.py file.
JWT_SECRET_KEY = "c820734a34c97336911250bd7ef342bfbb5194ca483e2f7afe8fb4d6985108e3"
ALGORITHM = "HS256"  # You can use other algorithms like HS512, RS256, etc.

def hash_password(password: str):
    """Hash a password for storing."""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str):
    """Hash plain password and compare it with previously stored hashed password."""
    return pwd_context.verify(plain_password, hashed_password) # return true if the password is correct, otherwise false

def create_access_token(data: dict):
    """Create a JWT access token with an optional expiration time."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=5)  # Token expires in 5 minutes. You can adjust this duration as needed.
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=ALGORITHM) # create signed JWT token using the provided data, secret key, and algorithm. The resulting token is a string that can be sent to clients for authentication and authorization purposes.
    return encoded_jwt