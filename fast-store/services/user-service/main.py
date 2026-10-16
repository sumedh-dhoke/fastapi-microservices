from fastapi import FastAPI,Depends,HTTPException,Response,status
from contextlib import asynccontextmanager
from fastapi.security import OAuth2PasswordRequestForm
from db import engine,get_session
from sqlmodel import SQLModel,Session,select,text
from models import User, UserPublic
import grpc
import product_pb2
import product_pb2_grpc
from fastapi.middleware.cors import CORSMiddleware   
from auth import hash_password,verify_password,create_access_token
from shared_utils.jwt_utils import verify_token
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor




# connect to DB
@asynccontextmanager
async def lifespan(app: FastAPI):
    SQLModel.metadata.create_all(engine)
    yield

app = FastAPI(lifespan=lifespan)

# 1. Set up OpenTelemetry tracing.Name the service for traceing purposes. This name will appear in the Jaeger UI and other tracing backends.

resource= Resource.create({"service.name":"user-service"})
provider = TracerProvider(resource=resource)


# 2. Tell it where to send the traces. In this case, we are sending them to the Jaeger instance running on the Docker network at port 4317.
# Jaeger all-in-one exposes OTLP over gRPC on 4317 when COLLECTOR_OTLP_ENABLED=true.
processor = BatchSpanProcessor(OTLPSpanExporter(endpoint="jaeger:4317", insecure=True))
provider.add_span_processor(processor)
trace.set_tracer_provider(provider)


# 3. Auto- Instrument FastAPI to automatically create spans for incoming HTTP requests.
# This will allow you to see traces for each request made to the FastAPI application in the Jaeger UI.

FastAPIInstrumentor.instrument_app(app, tracer_provider=provider)



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
def login(form_data: OAuth2PasswordRequestForm = Depends(),db:Session=Depends(get_session)):
    
    db_user = db.exec(select(User).where(User.email==form_data.username)).first()
    if not db_user or not verify_password(form_data.password, db_user.password):
        raise HTTPException(status_code=404,detail="Incorrect email or password")
    jwt_access_token = create_access_token(data={"sub":str(db_user.id),"email":db_user.email})
    return {"access_token":jwt_access_token,"token_type":"bearer"}


@app.get("/health/liveness",tags=["Health"]) # livesness probe checks if the service is alive and running. It can be used by Kubernetes or other orchestrators to determine if the service is still running and responsive.
def liveness_probe():
    return {"status": "alive"}  

@app.get("/health/readiness",tags=["Health"]) # readiness probe checks if the service is ready to handle requests. It can be used by Kubernetes or other orchestrators to determine if the service is ready to receive traffic.
def readiness_probe(response: Response, session: Session = Depends(get_session)):
    # Here you can add checks to see if the service is ready to handle requests, e.g., check database connection, external services, etc.
    # For simplicity, we will just return a static response.
    try:
        session.exec(text("SELECT 1"))  # Simple query to check DB connection
        return {"status": "ready"}
    except Exception as e:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "unavailable","detail" : str(e)}