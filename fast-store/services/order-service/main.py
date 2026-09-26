from fastapi import FastAPI, HTTPException
import json
from contextlib import asynccontextmanager
import aio_pika
import asyncio


# global variable to hold the connection and channel
rabbitmq_connection = None
rabbitmq_channel = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan handler: open RabbitMQ connection and channel, declare queue."""
    global rabbitmq_connection

    for i in range(5):  # Retry up to 5 times
        try:
            # Establish connection to RabbitMQ

            rabbitmq_connection = await aio_pika.connect_robust("amqp://admin:pass123@rabbitmq:5672/")
            break  # Exit the loop if connection is successful
        except Exception as e:
            print(f" ❌ Attempt {i + 1}/5: Failed to connect to RabbitMQ. Retrying in {2**i} seconds...")
            await asyncio.sleep(2 ** i)  # Exponential backoff  

    else:
        print(" ❌ Failed to connect to RabbitMQ after 5 attempts. Exiting.")
        raise ConnectionError("Failed to connect to RabbitMQ after 5 attempts.")
    print(" ✅ Connected to RabbitMQ successfully.")
    yield  # This is where the application runs

    # Cleanup: Close the channel and connection
    
    await rabbitmq_connection.close()


app = FastAPI(lifespan=lifespan)    

@app.post("/orders/")
async def place_order(product_id: int, user_id: int):
    # ensure we have a connection before publishing
    if rabbitmq_connection is None:
        raise HTTPException(status_code=503, detail="RabbitMQ not available")

    # 1. Create a order event payload
    order_event = {
        "event": "orderPlaced",
        "product_id": product_id,
        "user_id": user_id,
        "status": "pending"
    }
    # 2. Update the DB with the change synchronously, but the event is published asynchronously to RabbitMQ for other services to consume.


    # 3. Publish the order event to RabbitMQ asynchronously.
    async with rabbitmq_connection.channel() as channel:
        message = aio_pika.Message(body=json.dumps(order_event).encode())
        await channel.default_exchange.publish(message, routing_key="order_events1") # publish to existing Queue named order_events. Note let connsuming service create queue and dlq


    # 3. Return a response to the client   
    return {"message": "Order received and is being processed in background"} 