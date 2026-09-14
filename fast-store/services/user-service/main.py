from fastapi import FastAPI,Depends,HTTPException
from contextlib import asynccontextmanager
from db import engine,get_session
from sqlmodel import SQLModel,Session,select
from models import User, UserPublic
import grpc
import product_pb2
import product_pb2_grpc
from fastapi.middleware.cors import CORSMiddleware   
from auth import hash_password,verify_password,create_access_token
from shared_utils.jwt_utils import verify_token




# connect to DB
@asynccontextmanager
async def lifespan(app: FastAPI):
    SQLModel.metadata.create_all(engine)
    yield

app = FastAPI(lifespan=lifespan)

# Health check endpoint
@app.get("/health")
def health_check():
    return {"status":"ok","service":"user-service"}

# CORS middleware configuration for allowing requests from any origin/domain/website. This is useful for development and testing purposes, but in production, you should restrict the allowed origins to trusted domains.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods (GET, POST, etc.)
    allow_headers=["*"],  # Allow all headers
)


# apis of user-service
@app.post("/users/", response_model=UserPublic)
def create_user(user: User, db: Session=Depends(get_session)):
    user.password = hash_password(user.password)  # Hash the password before storing it in the database 
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@app.get("/users/")
def read_users(db: Session = Depends(get_session)):
    users = db.exec(select(User)).all()
    return users

@app.get("/users/{user_id}/purchases/{product_id}")
def get_user_purchase(user_id:int, product_id:int, token_data: dict = Depends(verify_token)):

    if str(user_id) != token_data.get("sub"):
        raise HTTPException(status_code=403, detail="Forbidden: Not authorised to access this resource")

    # Create a gRPC channel to the product service
    with grpc.insecure_channel('product-service:50051') as channel: # This line establishes a gRPC channel to the product service running on the host 'product-service' and port 50051. The 'insecure_channel' method is used here, which means that the communication is not encrypted. In a production environment, you would typically use a secure channel with SSL/TLS for secure communication between services.
        # Create a stub (client) for the ProductService
        stub = product_pb2_grpc.ProductServiceStub(channel)
        
        # Create a request message for the GetProduct method
        request = product_pb2.ProductRequest(id=product_id)
        
        # Call the GetProduct method on the stub
        response = stub.GetProduct(request)
        
        # Return the product information along with user ID
        return {
            "user_id": user_id,
            "product": {
                "id": response.id,
                "name": response.name,
                "price": response.price
            },
            "source": "grpc"
        }


@app.post("/login")
def login(user_data:User,db:Session=Depends(get_session)):
    db_user = db.exec(select(User).where(User.email==user_data.email)).first()
    if not db_user or not verify_password(user_data.password, db_user.password):
        raise HTTPException(status_code=404,detail="Incorrect email or password")
    jwt_access_token = create_access_token(data={"sub":str(db_user.id),"email":db_user.email})
    return {"access_token":jwt_access_token,"token_type":"bearer"}