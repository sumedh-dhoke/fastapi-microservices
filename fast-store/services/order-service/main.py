from fastapi import FastAPI
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
    global rabbitmq_connection, rabbitmq_channel

    # Establish connection to RabbitMQ
    rabbitmq_connection = await aio_pika.connect_robust("amqp://admin:pass123@rabbitmq:5672/")
    
    # Create a channel and declare a queue named "order_events"
    async with rabbitmq_connection.channel() as rabbitmq_channel:
      await rabbitmq_channel.declare_queue("order_events", durable=True)  # create Queue named order_events
    
    yield  # This is where the application runs

    # Cleanup: Close the channel and connection
    await rabbitmq_channel.close()
    await rabbitmq_connection.close()


app = FastAPI(lifespan=lifespan)    

@app.post("/orders/")
async def place_order(product_id: int, user_id: int):
    global rabbitmq_channel

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
        await channel.default_exchange.publish(message, routing_key="order_events") # create Queue named order_events


    # 3. Return a response to the client   
    return {"message": "Order received and is being processed in background"} 