import grpc
from concurrent import futures
import product_pb2
import product_pb2_grpc


# Implement the ProductServiceServicer for grpc connections.
class ProductService(product_pb2_grpc.ProductServiceServicer):
    def GetProduct(self, request, context):
        # Implement your logic to retrieve product information based on the request
        
        # For demonstration purposes, let's return a dummy product response
        response = product_pb2.ProductResponse(
            id=request.id,
            name="Sample Product",
            price=9.99
        )
        return response

# this code is for running the grpc server for product-service. It will listen on port 50051 and handle incoming requests for the ProductService.
def server():
    server= grpc.server(futures.ThreadPoolExecutor(max_workers=10))  # max_workers=10 allows handling multiple requests concurrently.
    product_pb2_grpc.add_ProductServiceServicer_to_server(ProductService(), server) # This line registers the ProductService implementation with the gRPC server, allowing it to handle incoming requests for the ProductService.
    server.add_insecure_port('[::]:50051') # The server will listen on all available network interfaces (IPv4 and IPv6) on port 50051.
    server.start() 
    server.wait_for_termination()  # This line keeps the server running indefinitely until it is manually stopped or terminated.

if __name__ == '__main__':
    server()