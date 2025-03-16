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

        order_data = response.json()
        order = order_data['data']['orders']['edges'][0]['node']
        order_number = order['name']

        if orderNumber == order_number:
            line_items = order['lineItems']['edges']
            subtotal_quantity = order['currentSubtotalLineItemsQuantity']
            subtotal_price = order['currentSubtotalPriceSet']['shopMoney']['amount']
            currency = order['lineItems']['edges'][0]['node']['originalUnitPriceSet']['shopMoney']['currencyCode']
            total_weight = order['currentTotalWeight']
            payment_gateway = order['paymentGatewayNames'][0]
            shipping_method = order['shippingLines']['edges'][0]['node']['title']
            shipping_cost = order['shippingLines']['edges'][0]['node']['currentDiscountedPriceSet']['shopMoney']['amount']
            financial_status = order['displayFinancialStatus']
            fulfillment_status = order['displayFulfillmentStatus']
            return_status = order['returnStatus']
            cancellation = order['cancellation']
            cancel_reason = order['cancelReason']
            cancelled_at = order['cancelledAt']
            created_at = order['createdAt']
            closed_at = order['closedAt']

            # Format the list of items
            items_list = []
            for item in line_items:
                item_name = item['node']['name']
                item_quantity = item['node']['currentQuantity']
                item_price = item['node']['originalUnitPriceSet']['shopMoney']['amount']
                items_list.append(f"{item_quantity} {item_name} for {currency}{item_price}")

            # Join the items into a natural-sounding sentence
            if len(items_list) == 1:
                items_description = items_list[0]
            elif len(items_list) == 2:
                items_description = f"{items_list[0]} and {items_list[1]}"
            else:
                items_description = ", ".join(items_list[:-1]) + f", and {items_list[-1]}"

            # Format the response using f-string with natural language
            responseMessage = (
                f"Your order #{order_number} includes {items_description}. "
                f"The subtotal for {subtotal_quantity} item(s) is {currency}{subtotal_price}, and the total weight is {total_weight} lbs. "
                f"It was paid via {payment_gateway} and {fulfillment_status.lower()} via {shipping_method} for {currency}{shipping_cost}. "
                f"The financial status is {financial_status.lower()}, and the return status is {return_status.lower().replace('_', ' ')}. "
                f"The order was created on {created_at.split('T')[0]} and completed on {closed_at.split('T')[0]}. "
                f"{'The order was not cancelled.' if cancellation is None else 'The order was cancelled.'} "
                f"{'No cancellation reason was provided.' if cancel_reason is None else f'The cancellation reason was: {cancel_reason}.'} "
                f"{'No cancellation date was recorded.' if cancelled_at is None else f'The order was cancelled on {cancelled_at.split("T")[0]}.'}"
            )

            # Add confirmation question
            responseMessage += "\n\nDoes this answer your question, or would you like additional information?"

            return JSONResponse(status_code=200, content={"result": responseMessage})
        else:
            raise HTTPException(status_code=404, detail="Order not found")
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