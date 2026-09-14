from fastapi import FastAPI,Depends
from contextlib import asynccontextmanager
from db import engine,get_session
from sqlmodel import SQLModel,Session,select
from models import User
import grpc
import product_pb2
import product_pb2_grpc



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

# apis of user-service
@app.post("/users/")
def create_user(user: User, session: Session=Depends(get_session)):
    session.add(user)
    session.commit()
    session.refresh(user)
    return user

@app.get("/users/")
def read_users(session:Session =Depends(get_session)):
    users= session.exec(select(User)).all()
    return users

@app.get("/users/{user_id}/purchases/{product_id}")
def get_user_purchase(user_id:int, product_id:int):
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
