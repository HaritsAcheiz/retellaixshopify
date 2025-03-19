import requests
from dataclasses import dataclass
from dotenv import load_dotenv
import os
from urllib.parse import urljoin
import logging
from requests.exceptions import RequestException, Timeout

load_dotenv()
logging.basicConfig(level=logging.INFO)


@dataclass
class ShopifyApi():
	store_name: str = None
	access_token: str = None
	version: str = None
	api_url: str = None
	session: requests.Session = None
	retries: int = 3
	timeout: float = 10.0

	# Support
	def send_request(self, query, variables=None):
		"""
		Sends an HTTP POST request to the Shopify API.

		Args:
		query (str): The GraphQL query string.
		variables (dict, optional): Variables for the GraphQL query.

		Returns:
		dict: The parsed JSON response from Shopify.

		Raises:
		ValueError: If the response contains an error.
		"""
		for attempt in range(1, self.retries + 1):
			try:
				response = self.session.post(
					self.api_url,
					json={"query": query, "variables": variables},
					timeout=self.timeout
				)

				# Raise an HTTP error for non-success status codes
				response.raise_for_status()

				# Parse the JSON response
				json_response = response.json()

				# Check for API-specific errors
				if 'errors' in json_response:
					print(json_response)
					raise ValueError(f"Shopify API Error: {json_response['errors']}")

				return json_response

			except Timeout:
				logging.warning(f"Timeout on attempt {attempt}/{self.retries}")
			except RequestException as e:
				logging.error(f"Request failed on attempt {attempt}/{self.retries}: {e}")
			except ValueError as ve:
				logging.error(f"Shopify API returned an error: {ve}")
				raise ve  # Reraise if it's an API error

		# If all retries fail, raise an exception
		raise RuntimeError("Failed to send request after multiple attempts.")

	# Create
	def create_session(self):
		print("Creating session...")
		headers = {
			'X-Shopify-Access-Token': self.access_token,
			'Content-Type': 'application/json'
		}
		self.session = requests.Session()
		self.session.headers.update(headers)
		self.api_url = f'https://{self.store_name}.myshopify.com/admin/api/{self.version}/graphql.json'

	def create_carrier_service(self, name, callbackUrl, discovery, active):
		print("Creating carrier service...")
		query = '''
			mutation CarrierServiceCreate($input: DeliveryCarrierServiceCreateInput!) {
				carrierServiceCreate(input: $input){
					carrierService {
						id
						name
						callbackUrl
						active
						supportsServiceDiscovery
					}
					userErrors {
						field
						message
					}
				}
			}
		'''

		variables = {
			"input": {
				"name": name,
				"callbackUrl": callbackUrl,
				"supportsServiceDiscovery": discovery,
				"active": active
			}
		}

		response = self.send_request(query, variables=variables)

		return response

	def create_webhook(self, topic, callbackUrl, _format=None, _filter=None):
		print('Creating Webhook...')
		query = """
			mutation webhookSubscriptionCreate($topic: WebhookSubscriptionTopic!, $webhookSubscription: WebhookSubscriptionInput!) {
				webhookSubscriptionCreate(topic: $topic, webhookSubscription: $webhookSubscription) {
					webhookSubscription {
						id
						topic
						filter
						format
						endpoint {
							__typename
							... on WebhookHttpEndpoint {
								callbackUrl
							}
						}
					}
					userErrors {
						field
						message
					}
				}
			}
		"""

		variables = {
			"topic": topic,
			"webhookSubscription": {
				"callbackUrl": callbackUrl,  # "https://example.org/endpoint"
				"format": _format,  # "JSON"
			}
		}

		# "filter": _filter  # "type:lookbook"

		response = self.send_request(query, variables=variables)

		return response

	# Read
	def products(self):
		print("Fetching Products...")
		query = '''
			{
				products(first:10){
					edges{
						node{
							handle
						}
					}
					pageInfo{
						endCursor
						hasNextPage
					}
				}
			}
		'''
		response = self.send_request(query)

		return response

	def get_webhooks(self):
		print("Fetching Webhooks...")
		query = '''
			query {
				webhookSubscriptions(first: 2) {
					edges {
						node {
							id
							topic
							endpoint {
								__typename
								... on WebhookHttpEndpoint {
									callbackUrl
								}
								... on WebhookEventBridgeEndpoint {
									arn
								}
								... on WebhookPubSubEndpoint {
									pubSubProject
									pubSubTopic
								}
							}
						}
					}
				}
			}
		'''

		response = self.send_request(query)

		return response

	def orders(self, cursor=None, order_name=None):
		print("Fetching Orders...")
		variables = {}
		if cursor and order_name:
			return None
		elif cursor and not order_name:
			query = """
				query getOrders($cursor: String) {
					orders(first: 10, after: $cursor, sortKey: CREATED_AT, reverse: true) {
						pageInfo {
							hasNextPage
							endCursor
						}
						edges {
							node {
								id
								name
								createdAt
								totalPriceSet{
									shopMoney{
										amount
									}
								}
								customer {
									firstName
									lastName
								}
								displayFinancialStatus
								displayFulfillmentStatus
								shippingAddress {
									address1
									city
									country
									zip
								}
								lineItems(first: 5) {
									edges {
										node {
											title
											quantity
										}
									}
								}
							}
						}
					}
				}
			"""
			variables["after"] = cursor
		
		elif not cursor and order_name:
			query = """
				query getOrders($query: String) {
					orders(first: 10, sortKey: CREATED_AT, reverse: true, query: $query) {
						pageInfo {
							hasNextPage
							endCursor
						}
						edges {
							node {
								id
								name
								createdAt
								totalPriceSet{
									shopMoney{
										amount
									}
								}
								customer {
									firstName
									lastName
								}
								displayFinancialStatus
								displayFulfillmentStatus
								shippingAddress {
									address1
									city
									country
									zip
								}
								lineItems(first: 5) {
									edges {
										node {
											title
											quantity
										}
									}
								}
							}
						}
					}
				}
			"""
			variables["query"] = f"name:{order_name}"
		
		elif not cursor and not order_name:
			query = """
				query {
					orders(first: 10, sortKey: CREATED_AT, reverse: true) {
						pageInfo {
							hasNextPage
							endCursor
						}
						edges {
							node {
								id
								name
								createdAt
								totalPriceSet{
									shopMoney{
										amount
									}
								}
								customer {
									firstName
									lastName
								}
								displayFinancialStatus
								displayFulfillmentStatus
								shippingAddress {
									address1
									city
									country
									zip
								}
								lineItems(first: 5) {
									edges {
										node {
											title
											quantity
										}
									}
								}
							}
						}
					}
				}
			"""
			variable = None

		response = self.send_request(query, variables=variables)

		return response

	def order(self, order_id, mode):
		print(f'Fetching Order {order_id}...')
		try:
			if mode == 'details':
				query = """
					query getOrder($id: ID!) {
						order(id: $id) {
							id
							name
							createdAt
							shippingAddress {
								address1
								address2
								city
								province
								provinceCode
								zip
								country
								countryCode
								phone
							}
							displayFinancialStatus
							displayFulfillmentStatus
							currentTotalAdditionalFeesSet{
								shopMoney{
									amount
								}
							}
							currentTotalDiscountsSet{
								shopMoney{
									amount
								}
							}
							currentShippingPriceSet{
								shopMoney{
									amount
								}
							}
							currentTotalDutiesSet{
								shopMoney{
									amount
								}
							}
							currentTotalTaxSet{
								shopMoney{
									amount
								}
							}
							currentSubtotalPriceSet{
								shopMoney{
									amount
								}
							}
							currentTotalPriceSet{
								shopMoney{
									amount
								}
							}
							totalReceivedSet{
								shopMoney{
									amount
								}
							}
							lineItems(first: 20) {
								edges {
									node {
										title
										name
										currentQuantity
										variant{
											price
										}
										product{
											variants(first: 1){
												edges{
													node{
														price
														inventoryItem{
															measurement{
																weight{
																	unit
																	value
																}
															}
														}
													}
												}
											}
										}
									}
								}
							}
							currentSubtotalLineItemsQuantity
							currentTotalWeight
							customer {
								firstName
								lastName
								email
								phone
							}
						}
					}
				"""
				variables = {"id": order_id}

				return self.send_request(query=query, variables=variables)

			elif mode == 'search':
				query = """
					query getOrder($id: ID!) {
						order(id: $id) {
							id
							name
							createdAt
							totalPriceSet{
								shopMoney{
									amount
								}
							}
							customer {
								firstName
								lastName
							}
							displayFinancialStatus
							displayFulfillmentStatus
							shippingAddress {
								address1
								address2
								city
								country
								zip
							}
							lineItems(first: 5) {
								edges {
									node {
										title
										currentQuantity
										variant{
											price
										}
									}
								}
							}
						}
					}
				"""
				variables = {"id": order_id}

				return self.send_request(query=query, variables=variables)
		except Exception as e:
			return None

	# Update

	# Delete
	def delete_webhook(self, _id):
		print('Creating Webhook...')
		query = """
			mutation webhookSubscriptionDelete($id: ID!) {
				webhookSubscriptionDelete(id: $id) {
					userErrors {
						field
						message
					}
					deletedWebhookSubscriptionId
				}
			}
		"""

		variables = {
			"id": _id
		}

		response = self.send_request(query, variables=variables)

		return response


if __name__ == '__main__':
	api = ShopifyApi(store_name=os.getenv('MC_STORE_NAME'), access_token=os.getenv('MC_ACCESS_TOKEN'), version='2024-10')
	api.create_session()
	response = api.products()
	# response = api.create_carrier_service(
	# 	name='Maersk',
	# 	callbackUrl='https://gasscooters.pythonanywhere.com/rates',
	# 	discovery=True,
	# 	active=True
	# )
	# response = api.get_webhooks()
	# response = api.create_webhook(topic='CARTS_CREATE', callbackUrl='https://0a98-120-188-37-151.ngrok-free.app/webhook', _format='JSON')
	# response = api.delete_webhook('')
	# response = api.orders()

	print(response)