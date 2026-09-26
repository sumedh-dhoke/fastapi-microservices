import json
from fastapi import FastAPI
from contextlib import asynccontextmanager
import aio_pika
import asyncio  

# global variable to hold the connection and channel
rabbitmq_connection = None
rabbitmq_channel = None         


# mock the inventory database as a dictionary. In actual implementation, this would be a real database like PostgreSQL, MySQL, etc. For simplicity, we are using an in-memory dictionary to simulate the inventory data.
inventory_db = {
    1: {"product_id": 1, "name": "Product A", "stock": 10},
    2: {"product_id": 2, "name": "Product B", "stock": 5}
    }


async def process_order_event(message: aio_pika.abc.AbstractIncomingMessage):
    try:
        event_data = json.loads(message.body.decode())
        print(f"📦 Received order event: {event_data}")

        product_id = event_data.get("product_id")

        # simulate fatal error for product_id 2 to test dead letter queue
        if product_id == 000:
            print("💥 Simulating fatal error for product_id 000 to test dead letter queue." )

            # reject the message and do not requeue it, so it goes to the dead letter queue
            await message.reject(requeue=False)
            return

        # normal bussiness logic for processing the order event
        if product_id in inventory_db and inventory_db[product_id]["stock"] > 0:
            inventory_db[product_id]["stock"] -= 1
            print(f"✅ Inventory reduced for product {product_id}. Remaining stock: {inventory_db[product_id]['stock']}")
        else:
            print(f"⚠️ Product {product_id} is out of stock or does not exist.")

        # Manually acknowledge the message after processing
        await message.ack() # this does not mean the message is removed from the queue, it just means we have successfully processed it and RabbitMQ can remove it from the queue. If we don't ack, RabbitMQ will requeue the message for another consumer to process.
    except Exception as e:
        print(f"❌ Error processing order event: {e}")
        # Reject the message and do not requeue it, so it goes to the dead letter queue
        await message.reject(requeue=False) 
        
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan handler: open RabbitMQ connection and channel, verify  existing queue and consume the messages from queue"""
    # 1. connect rabbitmq with retry mechanism

    for i in range(5):  # Retry up to 5 times
        try:
            rabbitmq_connection = await aio_pika.connect_robust("amqp://admin:pass123@rabbitmq:5672/")
            rabbitmq_channel = await rabbitmq_connection.channel()
            break  # Exit the loop if connection is successful
        except Exception as e:
            print(f" ❌ Attempt {i + 1}/5: Failed to connect to RabbitMQ. Retrying in {2**i} seconds...")
            # Implement exponential backoff for retries. This will wait for 2^i seconds before retrying, where i is the current attempt number (0 to 4).
            await asyncio.sleep(2 ** i)  # Wait for 2^i seconds before retrying
    else:
        print(" ❌ Could not connect to RabbitMQ after 5 attempts. Exiting.")
        raise ConnectionError("Could not connect to RabbitMQ after 5 attempts.")            


# 2. Implement dead letter exchange and dead letter queue for failed messages. This will help in handling messages that cannot be processed successfully.
    # Declare a dead letter exchange and queue
    dlx = await rabbitmq_channel.declare_exchange("dlx", aio_pika.ExchangeType.DIRECT)
    dlq_order_events1 = await rabbitmq_channel.declare_queue("dlq_order_events1", durable=True)
    
    # Bind the dead letter queue to the dead letter exchange
    await dlq_order_events1.bind(dlx, routing_key="order_events1") 

    # 3. Declare the main queue and tell it to route failed messages to the dead letter exchange    

    arguments = {
        "x-dead-letter-exchange": "dlx",  # Route failed messages to the dead letter exchange
        "x-dead-letter-routing-key": "order_events1"  # Route failed messages to the dead letter queue
    }
    queue = await rabbitmq_channel.declare_queue("order_events1", durable=True, arguments=arguments)  # declare Queue named order_events

    # 4. Consume messages from the queue and process them asynchronously
    await queue.consume(process_order_event)  # no_ack=False means we will manually acknowledge messages after processing
    print("🎧 Inventory Service is now listening for order events...")

    yield  # This is where the application runs

    await rabbitmq_channel.close()
    await rabbitmq_connection.close() 


app = FastAPI(lifespan=lifespan)




# Define an endpoint to get inventory details for a specific product
@app.get("/inventory/{product_id}")
async def get_inventory(product_id: int):
    return inventory_db.get(product_id, {"error": "Product not found"})