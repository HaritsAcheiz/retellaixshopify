from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
import datetime
import logging
import json
import uvicorn
from shopifyapi import ShopifyApp
import os

app = FastAPI()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Mock database for orders, products, and shipments
orders_db = {
    "12345": {
        "orderNumber": "12345",
        "customerName": "Sam",
        "items": ["Red Sports Ride-On Car"],
        "status": "Shipped",
        "orderDate": "2024-01-10",
        "estimatedDelivery": "2024-01-14"
    },
    "67890": {
        "orderNumber": "67890",
        "customerName": "Alex",
        "items": ["Blue Police Ride-On Car"],
        "status": "Processing",
        "orderDate": "2024-01-12",
        "estimatedDelivery": "2024-01-18"
    }
}

products_db = {
    "Red Sports Ride-On Car": {
        "name": "Red Sports Ride-On Car",
        "description": "A sleek ride-on car for kids aged 3-7 with LED headlights and a top speed of 3 mph.",
        "price": 199.99,
        "stock": 10
    },
    "Blue Police Ride-On Car": {
        "name": "Blue Police Ride-On Car",
        "description": "A police-themed ride-on car with a working horn and parental remote control.",
        "price": 219.99,
        "stock": 5
    }
}

shipments_db = {
    "12345": {
        "orderNumber": "12345",
        "status": "In Transit",
        "shippingDate": "2024-01-10",
        "estimatedDelivery": "2024-01-14",
        "trackingLink": "https://tracking.magiccars.com/12345"
    },
    "67890": {
        "orderNumber": "67890",
        "status": "Processing",
        "shippingDate": None,
        "estimatedDelivery": "2024-01-18",
        "trackingLink": None
    }
}

# Custom function: Get order status
@app.post("/getorder")
async def get_order_status(request: Request):
    try:
        # Define Shopify App
        s = ShopifyApp(store_name=os.getenv('STORE_NAME'), access_token=os.getenv('SHOPIFY_ACCESS_TOKEN'), api_version=os.getenv('API_VERSION'))
        client = s.create_session()

        data = await request.json()
        orderNumber = data['args']['orderNumber']

        response = s.get_orders(client, orderNumber)

        print(response.json())
        
        # if orderNumber in orders_db:
        #     orderDetails = orders_db[orderNumber]
        #     responseMessage = f"Your order {orderNumber} is currently {orderDetails['status']}. It was placed on {orderDetails['orderDate']} and is estimated to arrive by {orderDetails['estimatedDelivery']}."
            
        #     return JSONResponse(status_code=200, content={"result": responseMessage})
        # else:
        #     raise HTTPException(status_code=404, detail="Order not found")
    except Exception as e:
        logger.error(f"Failed to parse request body: {e}")
        raise HTTPException(status_code=400, detail="Invalid request body")

# Custom function: Get product details
@app.post("/getproduct")
async def get_product_details(request: Request):
    try:
        # Define Shopify App
        s = ShopifyApp(store_name=os.getenv('STORE_NAME'), access_token=os.getenv('SHOPIFY_ACCESS_TOKEN'), api_version=os.getenv('API_VERSION'))
        client = s.create_session()
        
        data = await request.json()
        productName = data['args']['productName']
        if productName in products_db:
            productDetails = products_db['productName']
            responseMessage = f"Your order {orderNumber} is currently {productDetails['status']}. It was placed on {productDetails['orderDate']} and is estimated to arrive by {productDetails['estimatedDelivery']}."

            return JSONResponse(status_code=200, content={"result": responseMessage})
        else:
            raise HTTPException(status_code=404, detail="Product not found")
    except Exception as e:
        logger.error(f"Failed to parse request body: {e}")
        raise HTTPException(status_code=400, detail="Invalid request body")

# Custom function: Check shipment status
@app.post("/shipment")
async def check_shipment_status(request: Request):
    try:
        # Define Shopify App
        s = ShopifyApp(store_name=os.getenv('STORE_NAME'), access_token=os.getenv('SHOPIFY_ACCESS_TOKEN'), api_version=os.getenv('API_VERSION'))
        client = s.create_session()

        data = await request.json()
        airwayBill = request.airwayBill

        if airwayBill in shipments_db:
            shipmentDetails = shipments_db['airwayBill']
            responseMessage = f"Your order {airwayBill} is currently {shipmentDetails['status']}. It was placed on {shipmentDetails['orderDate']} and is estimated to arrive by {shipmentDetails['estimatedDelivery']}."

            return JSONResponse(status_code=200, content={"result": responseMessage})
        else:
            raise HTTPException(status_code=404, detail="Shipment not found")
    except Exception as e:
        logger.error(f"Failed to parse request body: {e}")
        raise HTTPException(status_code=400, detail="Invalid request body")

# Root endpoint
@app.get("/")
def read_root():
    return {"message": "Welcome to Magic Cars Backend API!"}

# Run the server
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=5000, reload=True)