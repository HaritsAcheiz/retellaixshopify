from flask import Flask, request, redirect, session, render_template, jsonify, send_from_directory, Response, abort
import os
import logging
import requests
from dotenv import load_dotenv
from shopify import ShopifyApi
from shopifyapi import ShopifyApp
from maersk import MaerskApi
from barcode import Code128
from barcode.writer import SVGWriter
import io
import json
from flask_cors import CORS

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.urandom(24)
# Allow all domains (or restrict to Shopify)
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True, allow_headers=["Authorization", "Content-Type"])

SHOPIFY_CLIENT_ID = os.getenv('P_API_KEY')
SHOPIFY_CLIENT_SECRET = os.getenv('P_API_SECRET')
SHOPIFY_SCOPE = "read_orders,read_products,read_customers"
REDIRECT_URI = os.getenv('P_REDIRECT_URI')
api = None
maerskapi = MaerskApi()


def get_order_id(order_name):
    global api
    response = api.orders(order_name=order_name)

    return response['data']['orders']['edges'][0]['node']['id']


@app.after_request
def add_headers(response):
    response.headers['X-Frame-Options'] = 'ALLOWALL'
    response.headers['Content-Security-Policy'] = (
        "frame-ancestors 'self' https://*.myshopify.com https://admin.shopify.com"
    )
    response.headers['Access-Control-Allow-Origin'] = '*'  # For development, restrict in production

    return response


# Shopify embedded app
@app.route('/')
def install():
    shop = request.args.get('shop')
    if not shop:

        return "Missing shop parameter", 400
    install_url = f"https://{shop}/admin/oauth/authorize"

    return redirect(
        f"{install_url}?client_id={SHOPIFY_CLIENT_ID}&scope={SHOPIFY_SCOPE}&redirect_uri={REDIRECT_URI}&embedded_app=true"
    )


@app.route('/api/init', methods=['GET'])
def init_app():
    shop_origin = request.args.get('shop')
    if not shop_origin:
        return jsonify({'error': 'Shop parameter is missing!'}), 400

    return jsonify({'apiKey': SHOPIFY_CLIENT_ID, 'shopOrigin': shop_origin})


@app.route('/callback')
def callback():
    shop = request.args.get('shop')
    code = request.args.get('code')
    if not shop or not code:

        return "Missing shop or code parameter", 400

    token_url = f"https://{shop}/admin/oauth/access_token"
    payload = {
        "client_id": SHOPIFY_CLIENT_ID,
        "client_secret": SHOPIFY_CLIENT_SECRET,
        "code": code,
    }
    response = requests.post(token_url, json=payload)
    if response.status_code == 200:
        access_token = response.json().get('access_token')
        logger.info(f"Access token retrieved for {shop}")
        token_file_path = "shopify_tokens.json"

        if os.path.exists(token_file_path):
            with open(token_file_path, "r") as token_file:
                all_tokens = json.load(token_file)
        else:
            all_tokens = {}

        all_tokens[shop] = access_token
        with open(token_file_path, "w") as token_file:
            json.dump(all_tokens, token_file, indent=4)

        session['shop'] = shop
        session['access_token'] = access_token

        return redirect(f"/index?shop={shop}")

    return "Failed to get access token", 400


@app.route('/index')
def index():
    global api

    shop = session.get('shop')
    access_token = session.get('access_token')

    if not shop or not access_token:
        token_file_path = "shopify_tokens.json"
        if os.path.exists(token_file_path):
            with open(token_file_path, "r") as token_file:
                all_tokens = json.load(token_file)
                shop = request.args.get('shop')
                access_token = all_tokens.get(shop)

    if not shop or not access_token:
        return "Unauthorized", 401

    # Fetch orders from Shopify
    api = ShopifyApi(store_name=shop.split('.')[0], access_token=access_token, version='2025-01')
    api.create_session()
    orders_data = api.orders()

    orders = []
    for edge in orders_data['data']['orders']['edges']:
        node = edge['node']
        orders.append({
            "no": node['name'],
            "date": node['createdAt'],
            "customer": f"{node['customer']['firstName']} {node['customer']['lastName']}" if node['customer'] else "Guest",
            "totalPrice": f"${node['totalPriceSet']['shopMoney']['amount']}",
            "paymentStatus": node['displayFinancialStatus'],
            "fulfillmentStatus": node['displayFulfillmentStatus'],
            "shippingAddress": (
                f"{node['shippingAddress']['address1']}, {node['shippingAddress']['city']}, {node['shippingAddress']['country']}, {node['shippingAddress']['zip']}"
                if node['shippingAddress'] else "No Address"
            ),
            "actions": "View"
        })

    return render_template('index.html', shop=shop, orders=orders, )


@app.route('/search_order')
def search_order():
    global api

    token_file_path = "shopify_tokens.json"
    if os.path.exists(token_file_path):
        with open(token_file_path, "r") as token_file:
            data = json.load(token_file)
            for key, value in data.items():
                shop = key
                access_token = value

    order_name = request.args.get('orderid')

    if not order_name:
        return jsonify({"error": "Order ID is required"}), 400

    try:
        order_id = get_order_id(order_name)
        response = api.order(order_id, mode='search')  # Assuming you have a method to get a specific order

        order_data = response['data']['order']
        if not order_data:
            return jsonify({"error": "Order not found"}), 404

        # Prepare the order data for rendering
        order = {
            "no": order_data['name'],
            "date": order_data['createdAt'],
            "customer": f"{order_data['customer']['firstName']} {order_data['customer']['lastName']}" if order_data['customer'] else "Guest",
            "totalPrice": f"${order_data['totalPriceSet']['shopMoney']['amount']}",
            "paymentStatus": order_data['displayFinancialStatus'],
            "fulfillmentStatus": order_data['displayFulfillmentStatus'],
            "shippingAddress": (
                f"{order_data['shippingAddress']['address1']}, {order_data['shippingAddress']['city']}, {order_data['shippingAddress']['country']}, {order_data['shippingAddress']['zip']}"
                if order_data['shippingAddress'] else "No Address"
            ),
            "detailAddress": {
                "address1": order_data['shippingAddress']['address1'],
                "address2": order_data['shippingAddress']['address2'],
                "city": order_data['shippingAddress']['city'],
                "country": order_data['shippingAddress']['country'],
                "zip": order_data['shippingAddress']['zip'],
            },
            "actions": "View"
        }

        # Render the index.html with the specific order data
        return render_template('index.html', shop=shop, orders=[order])  # Pass the order as a list

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/order-details')
def order_details():
    order_name = request.args.get('ordername')
    if not order_name:
        return jsonify({'error': 'Order ID is required'}), 400

    order_id = get_order_id(order_name)
    json_data = api.order(order_id, mode='details')
    order_data = json_data['data']['order']

    _items = []
    products = order_data['lineItems']['edges']
    for product in products:
        _items.append(product['node'])

    # tax_lines = []
    # if len(order_data['taxLines']) > 0:
    #     taxes = order_data['taxLines']['edges']
    #     for tax in taxes:
    #         tax_lines.append(tax['node'])

    order = {
        "no": order_data['name'],
        "date": order_data['createdAt'],
        "fulfillmentStatus": order_data['displayFulfillmentStatus'],
        "_items": _items,
        "subtotal": order_data['currentSubtotalPriceSet']['shopMoney']['amount'],
        "additional": order_data['currentTotalAdditionalFeesSet']['shopMoney']['amount'] if order_data['currentTotalAdditionalFeesSet'] else "0.0",
        # "tax": tax_lines,
        "tax": order_data['currentTotalTaxSet']['shopMoney']['amount'],
        "shipping": order_data['currentShippingPriceSet']['shopMoney']['amount'],
        "duties": order_data['currentTotalDutiesSet']['shopMoney']['amount'] if order_data['currentTotalDutiesSet'] else "0.0",
        "discount": order_data['currentTotalDiscountsSet']['shopMoney']['amount'],
        "total": order_data['currentTotalPriceSet']['shopMoney']['amount'],
        "paid": order_data['totalReceivedSet']['shopMoney']['amount'],
        "customer": {
            "name": f"{order_data['customer']['firstName']} {order_data['customer']['lastName']}" if order_data['customer'] else "Guest",
            "email": order_data['customer']['email'] if order_data['customer'] else "None",
            "phone": order_data['customer']['phone'] if order_data['customer'] else "None"
        },
        "shippingAddress": (
            f"{order_data['shippingAddress']['address1']}, {order_data['shippingAddress']['city']}, {order_data['shippingAddress']['country']}, {order_data['shippingAddress']['zip']}"
            if order_data['shippingAddress'] else "No Address"
        ),
        "detailAddress": {
            "address1": order_data['shippingAddress']['address1'],
            "address2": order_data['shippingAddress']['address2'],
            "city": order_data['shippingAddress']['city'],
            "country": order_data['shippingAddress']['country'],
            "zip": order_data['shippingAddress']['zip'],
        },
        "paymentStatus": order_data['displayFinancialStatus']
    }

    # Render the order details page or return JSON data
    return render_template('order-details.html', order_data=order)


@app.route('/get-shipping-options')
def get_shipping_options():
    global maerskapi
    global api

    zipcode = request.args.get('zipcode', '91710')  # Default ZIP code if not provided
    ordername = request.args.get('ordername', '')

    order_id = get_order_id(ordername)
    # order_id = ordername
    json_data = api.order(order_id, mode='details')
    order_data = json_data['data']['order']

    quote = maerskapi.get_new_quote_rest()
    ratingRootObject = maerskapi.quote_to_dict(quote.text)

    # Sample Data
    order_items = order_data['lineItems']['edges']
    LineItems = []
    for i in order_items:
        current_item = {}
        current_item["Pieces"] = f"{i['node']['currentQuantity']}"
        # variants = i['node']['product']['variants']['edges']
        # for variant in variants:
        #     current_item["Weight"]: variant['node']['inventoryItem']['measurement']['weight']['value']
        current_item["Weight"] = f"{int(i['node']['product']['variants']['edges'][0]['node']['inventoryItem']['measurement']['weight']['value'])}"
        current_item["Description"] = i['node']['title']
        current_item["Length"] = "61"
        current_item["Width"] = "40"
        current_item["Height"] = "24"
        LineItems.append(current_item.copy())

    data = {
        "Rating": {
            "LocationID": os.getenv('LOCATIONID'),
            "Shipper": {
                "Zipcode": zipcode
            },
            "Consignee": {
                "Zipcode": order_data['shippingAddress']['zip']
            },
            "LineItems": LineItems,
            "TariffHeaderID": os.getenv('TARIFFHEADERID')
        }
    }

    shipping_services = maerskapi.get_rating_rest(ratingRootObject, data)
    available_services = shipping_services["dsQuote"]["Quote"]

    return jsonify(available_services)

@app.route('/get-shipping-options-ext', methods=['POST'])
def get_shipping_options_ext():
    global maerskapi
    order_data = request.get_json()

    quote = maerskapi.get_new_quote_rest()
    ratingRootObject = maerskapi.quote_to_dict(quote.text)

    # Sample Data
    order_items = order_data['lineItems']['edges']
    LineItems = []
    for i in order_items:
        current_item = {}
        current_item["Pieces"] = f"{i['node']['currentQuantity']}"
        # variants = i['node']['product']['variants']['edges']
        # for variant in variants:
        #     current_item["Weight"]: variant['node']['inventoryItem']['measurement']['weight']['value']
        current_item["Weight"] = f"{int(i['node']['product']['variants']['edges'][0]['node']['inventoryItem']['measurement']['weight']['value'])}"
        current_item["Description"] = i['node']['title']
        current_item["Length"] = "61"
        current_item["Width"] = "40"
        current_item["Height"] = "24"
        LineItems.append(current_item.copy())

    data = {
        "Rating": {
            "LocationID": os.getenv('LOCATIONID'),
            "Shipper": {
                "Zipcode": zipcode
            },
            "Consignee": {
                "Zipcode": order_data['shippingAddress']['zip']
            },
            "LineItems": LineItems,
            "TariffHeaderID": os.getenv('TARIFFHEADERID')
        }
    }

    shipping_services = maerskapi.get_rating_rest(ratingRootObject, data)
    available_services = shipping_services["dsQuote"]["Quote"]

    return jsonify(available_services)


@app.route('/get-label', methods=['POST'])
def get_label():
    # try:
    payload = request.get_json()
    payload['Rating']["LocationID"] = os.getenv('LOCATIONID')
    payload['Rating']["TariffHeaderID"] = os.getenv('TARIFFHEADERID')

    data = payload

    response = maerskapi.get_new_quote_rest()
    ratingRootObject = maerskapi.quote_to_dict(response.text)

    response = maerskapi.get_rating_rest(ratingRootObject, data)
    rating_data = response

    response = maerskapi.get_new_shipment_rest()
    rootShipmentObject = maerskapi.shipment_to_dict(response.content)

    response = maerskapi.save_shipment_rest(rootShipmentObject, rating_data, data)

    # with open('save_shipment_output.json', 'r') as file:
    #     response = json.load(file)

    # ProNumber = 400615691
    ProNumber = response['dsResult']['Shipment'][0]['ProNumber']
    labelType = 'Label4x6'
    # Zipcode = 91710
    Zipcode = int(response['dsResult']['Shipper'][0]['Zipcode'].strip())

    response = maerskapi.get_label(ProNumber=ProNumber, labelType=labelType, Zipcode=Zipcode)

    if response.status_code == 200:
        return Response(
            response.text,
            mimetype='application/xml',
            status=200
        )
    else:
        return jsonify({
            'error': 'Failed to generate label',
            'status_code': response.status_code
        }), response.status_code

    # except Exception as e:
    #     return jsonify({
    #         'error': str(e)
    #     }), 500

# RetellAI
## Get Order Details
@app.route("/getorder", methods=['POST'])
def get_order_status():
    try:
        # Define Shopify App
        s = ShopifyApp(store_name=os.getenv('TRENDTIME_STORE_NAME'), access_token=os.getenv('TRENDTIME_ACCESS_TOKEN'), api_version=os.getenv('API_VERSION'))
        client = s.create_session()

        data = request.get_json()
        orderNumber = data['args']['orderNumber']

        response = s.get_orders(client, orderNumber)

        order_data = response.json()
        print(order_data)
        order = order_data['data']['orders']['edges'][0]['node']
        order_number = order['name']

        if orderNumber == order_number:
            # Extract all relevant information
            line_items = order['lineItems']['edges']
            subtotal_quantity = order['currentSubtotalLineItemsQuantity']
            subtotal_price = order['currentSubtotalPriceSet']['shopMoney']['amount']
            currency = order['lineItems']['edges'][0]['node']['originalUnitPriceSet']['shopMoney']['currencyCode']
            total_weight = order['currentTotalWeight']
            payment_gateway = order['paymentGatewayNames'][0]
            shipping_method = order['shippingLines']['edges'][0]['node']['title']
            shipping_cost = order['shippingLines']['edges'][0]['node']['currentDiscountedPriceSet']['shopMoney']['amount']
            financial_status = order['displayFinancialStatus']
            fulfillment_status = order['fulfillments'][0]['displayStatus']
            return_status = order['returnStatus']
            cancellation = order['cancellation']
            cancel_reason = order['cancelReason']
            cancelled_at = order['cancelledAt']
            created_at = order['createdAt']
            closed_at = order['closedAt']
            fulfillment = order['fulfillments'][0]
            tracking_company = fulfillment['trackingInfo'][0]['company'] if fulfillment['trackingInfo'] else None
            tracking_number = fulfillment['trackingInfo'][0]['number'] if fulfillment['trackingInfo'] else None

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

            responseMessage = (
                f"Your order #{order_number} includes {items_description}. "
                f"The subtotal for {subtotal_quantity} item(s) is {currency}{subtotal_price}, and the total weight is {total_weight} lbs. "
                f"It was paid via {payment_gateway} and {fulfillment_status.lower()} via {shipping_method} for {currency}{shipping_cost}. "
                f"The financial status is {financial_status.lower()}, and the return status is {return_status.lower().replace('_', ' ')}. "
                f"The order was created on {created_at.split('T')[0]} and completed on {closed_at.split('T')[0]}. "
                f"{'The order was not cancelled.' if cancellation is None else 'The order was cancelled.'} "
                f"{'No cancellation reason was provided.' if cancel_reason is None else f'The cancellation reason was: {cancel_reason}.'} "
                f'''{'No cancellation date was recorded.' if cancelled_at is None else f'The order was cancelled on {cancelled_at.split("T")[0]}.'} '''
                f"The fulfillment status is {fulfillment_status.lower()}, and the tracking company is {tracking_company if tracking_company else 'not available'}, with tracking number {tracking_number if tracking_number else 'not available'}."
                f"{'The order was delivered on ' + fulfillment['deliveredAt'].split('T')[0] + '.' if fulfillment_status == 'DELIVERED' else 'The estimated delivery date is ' + fulfillment['estimatedDeliveryAt'].split('T')[0] + '.'}"
            )

            return jsonify({"result": responseMessage}), 200
        else:
            abort(404, description="Order not found")
    except Exception as e:
        logger.error(f"Failed to parse request body: {e}")
        abort(400, description="Invalid request body")

## Get Product Details
@app.route("/getproduct", methods=['POST'])
def get_product_details():
    try:
        # Define Shopify App
        s = ShopifyApp(store_name=os.getenv('STORE_NAME'), access_token=os.getenv('SHOPIFY_ACCESS_TOKEN'), api_version=os.getenv('API_VERSION'))
        client = s.create_session()

        data = request.get_json()
        productName = data['args']['productName']
        # if productName in products_db:
        if True:
        #     productDetails = products_db['productName']
        #     responseMessage = f"Your order {productName} is currently {productDetails['status']}. It was placed on {productDetails['orderDate']} and is estimated to arrive by {productDetails['estimatedDelivery']}."

            return Response({"result": "under-construction"}, mimetype='application/json', status=200)
        else:
            abort(404, description="Order not found")
    except Exception as e:
        logger.error(f"Failed to parse request body: {e}")
        abort(400, description="Invalid request body")

## Sending details email
@app.route("/email", methods=['POST'])
def send_details_email():
    try:
        data = request.get_json()
        customerName = data['args']['customer_name']
        customerEmail = data['args']['customer_email']
        orderNumber = data['args']['order_number']
        itemsDescription = data['args']["items_description"]
        subtotal = data['args']["subtotal"]
        weight = data['args']["weight"]
        paymentGateway = data['args']["payment_gateway"]
        fulfillment = data['args']["fulfillment"]
        shipping = data['args']["shipping"]
        financialStatus = data['args']["financial_status"]
        returnStatus = data['args']["return_status"]
        cancellation = data['args']["cancellation"]
        tracking = data['args']["tracking"]
        cancelReason = data['args']["cancel_reason"]
        cancelledAt = data['args']["cancelled_at"]
        createdAt = data['args']["created_at"]
        closedAt = data['args']["closed_at"]
        currency = data['args']["currency"]

        # Define Shopify App
        s = ShopifyApp(store_name=os.getenv('TRENDTIME_STORE_NAME'), access_token=os.getenv('TRENDTIME_ACCESS_TOKEN'), api_version=os.getenv('API_VERSION'))
        client = s.create_session()

        response = s.get_orders(client, orderNumber)

        order_data = response.json()
        order = order_data['data']['orders']['edges'][0]['node']
        tracking_link = order['fulfillments']['trackingInfo'][0]['url']

        if customerEmail:
            responseMessage = f'Tracking Link {tracking_link} was sent'
            return jsonify({"result": "responseMessage"}), 200
        else:
            abort(404, description="Order not found")
    except Exception as e:
        logger.error(f"Failed to parse request body: {e}")
        abort(400, description="Invalid request body")


@app.errorhandler(404)
def not_found_error(error):
    """
    Handles 404 errors.
    """
    return render_template('error.html', error="Page not found"), 404


@app.errorhandler(500)
def internal_error(error):
    """
    Handles 500 errors.
    """
    return render_template('error.html', error="Internal server error"), 500


@app.route('/favicon.ico')
def favicon():
    """
    Handles favicon requests.
    """
    return '', 204


@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory('static', filename)


if __name__ == "__main__":
    # Ensure app is running in HTTPS using ngrok or other tunneling tools for local development
    app.run(host="0.0.0.0", port=5000, debug=True)