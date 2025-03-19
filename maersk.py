from dataclasses import dataclass, field
from urllib.parse import urljoin, urlencode
from dotenv import load_dotenv
import zeep
from zeep.transports import Transport
import ssl
import requests
import xml.etree.ElementTree as ET
import os
import json
import logging
from datetime import datetime
import base64

# logging.basicConfig(level=logging.DEBUG)
load_dotenv()


@dataclass
class MaerskApi():
	base_api_url: str = 'https://pilotws.pilotdelivers.com'
	session: requests.Session = field(default_factory=requests.Session)

	def save_pdf_from_xml(self, xml_string, output_filename):
		# Parse the XML string
		root = ET.fromstring(xml_string)

		# Find the DataStream_Byte element
		data_stream_byte = root.find(".//{*}DataStream_Byte")  # Wildcard namespace
		print(data_stream_byte)

		if data_stream_byte is not None and data_stream_byte.text:
			# Decode the base64 string
			pdf_data = base64.b64decode(data_stream_byte.text)

		# Write the PDF data to a file
			with open(output_filename, 'wb') as pdf_file:
				pdf_file.write(pdf_data)

			print(f"PDF saved as {output_filename}")
		else:
			print("DataStream_Byte not found or empty.")

	def get_new_quote(self):
		settings = zeep.Settings(strict=False)

		self.session.headers.update({
			"Content-Type": "application/soap+xml; charset=utf-8"
		})

		# self.session.verify = 'certificates/server.pem'
		self.session.verify = False

		wsdl_url = "https://ws.pilotair.com/tms2.1/tms/PilotServiceRequest.asmx?WSDL"

		transport = Transport(session=self.session)
		zeep_client = zeep.Client(wsdl=wsdl_url, transport=transport, settings=settings)

		try:
			response = zeep_client.service.GetNewQuote()
			return response
		except Exception as e:
			print("Error:", e)
			return None

	def get_new_quote_rest(self):
		endpoint = 'https://ws.pilotair.com/tms2.1/tms/PilotServiceRequest.asmx/GetNewQuote'

		try:
			with requests.Session() as client:
				response = client.get(endpoint, verify=False)
			response.raise_for_status()
			return response
		except Exception as e:
			print(f"Error occurred: {e}")
			return None

	def get_new_shipment(self):
		# Disable SSL warnings if you're setting verify=False
		requests.packages.urllib3.disable_warnings()

		# Create a session
		session = requests.Session()
		session.headers.update({
			"Content-Type": "application/soap+xml; charset=utf-8"
		})
		session.verify = False  # Disable SSL verification if needed

		# Set up Zeep client
		wsdl_url = "https://ws3.pilotdelivers.com/webservice/wsshipments/Shipment.asmx?WSDL"
		settings = zeep.Settings(strict=False)
		transport = Transport(session=session)
		client = zeep.Client(wsdl=wsdl_url, transport=transport, settings=settings)

		# Call GetNewShipment
		try:
			response = client.service.GetNewShipment()
			# Check the full response
			print(response)

			# Extract the actual data from _value_1 if it exists
			if hasattr(response, 'GetNewShipmentResult'):
				shipment_result = response.GetNewShipmentResult
				if hasattr(shipment_result, '_value_1'):
					print(shipment_result._value_1)
				else:
					print("No _value_1 in GetNewShipmentResult")
			else:
				print("No GetNewShipmentResult in response")

		except Exception as e:
			print("Error:", e)

	def get_new_shipment_rest(self):
		# url = "https://ws3.pilotdelivers.com/webservice/wsshipments/Shipment.asmx"
		url = "https://ws3.pilotdelivers.com/webservice/wsshipmentsdev/Shipment.asmx"
		headers = {
			"Content-Type": "application/soap+xml; charset=utf-8",
			"SOAPAction": "http://tempuri.org/GetNewShipment"
		}

		# SOAP envelope as per documentation
		soap_envelope = """<?xml version="1.0" encoding="utf-8"?>
			<soap12:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
			xmlns:xsd="http://www.w3.org/2001/XMLSchema"
			xmlns:soap12="http://www.w3.org/2003/05/soap-envelope">
				<soap12:Body>
					<GetNewShipment xmlns="http://tempuri.org/" />
				</soap12:Body>
			</soap12:Envelope>
		"""

		response = requests.post(url, data=soap_envelope, headers=headers, verify=False)

		return response

	def find_origin_by_zip_rest(self, sZip):
		endpoint = urljoin(self.base_api_url, '/copilotforms/wsCoPilotSG.asmx/FindOriginByZip')

		payload = {'sZip': sZip}
		encoded_payload = urlencode(payload)
		content_length = str(len(encoded_payload))

		headers = {
			'Content-Type': 'application/x-www-form-urlencoded',
			'Content-Length': content_length
		}

		self.client.headers.update(headers)
		try:
			response = self.client.post(endpoint, data=encoded_payload)
			response.raise_for_status()
			return response
		except Exception as e:
			print(f"Error occurred: {e}")
			return None

	def find_origin_by_zip(self, sZip):
		self.session.headers.update({
			"Content-Type": "application/soap+xml; charset=utf-8",
		})

		wsdl_url = "https://pilotws.pilotdelivers.com/copilotforms/wsCoPilotSG.asmx?WSDL"

		transport = Transport(session=self.session)
		zeep_client = zeep.Client(wsdl=wsdl_url, transport=transport)

		try:
			return zeep_client.service.FindOriginByZip(sZip=sZip)
		except Exception as e:
			print("Error:", e)

	def service_info_rest(self, sOriginZip, sDestZip):
		endpoint = urljoin(self.base_api_url, '/copilotforms/wsCoPilotSG.asmx/ServiceInfo')

		payload = {
			'sOriginZip': sOriginZip,
			'sDestZip': sDestZip
		}
		encoded_payload = urlencode(payload)
		content_length = str(len(encoded_payload))

		headers = {
			'Content-Type': 'application/x-www-form-urlencoded',
			'Content-Length': content_length
		}

		self.client.headers.update(headers)
		try:
			response = self.client.post(endpoint, data=encoded_payload)
			response.raise_for_status()
			return response
		except Exception as e:
			print(f"Error occurred: {e}")
			return None

	def service_info(self, sOriginZip, sDestZip):
		self.session.headers.update({
			"Content-Type": "application/soap+xml; charset=utf-8",
		})

		wsdl_url = "https://pilotws.pilotdelivers.com/copilotforms/wsCoPilotSG.asmx?WSDL"

		transport = Transport(session=self.session)
		zeep_client = zeep.Client(wsdl=wsdl_url, transport=transport)

		try:
			return zeep_client.service.ServiceInfo(sOriginZip=sOriginZip, sDestZip=sDestZip)
		except Exception as e:
			print("Error:", e)

	def get_rating_rest(self, ratingRootObject, data):
		rating_data = data['Rating']
		ratingRootObject['Rating']['LocationID'] = rating_data['LocationID']
		ratingRootObject['Rating']['Shipper']['Zipcode'] = rating_data['Shipper']['Zipcode']
		ratingRootObject['Rating']['Consignee']['Zipcode'] = rating_data['Consignee']['Zipcode']
		ratingRootObject['Rating']['LineItems'] = rating_data['LineItems']
		ratingRootObject['Rating']['TariffHeaderID'] = rating_data['TariffHeaderID']

		endpoint = 'https://www.pilotssl.com/pilotapi/v1/Ratings'
		payload = ratingRootObject

		headers = {
			'Content-Type': 'application/json',
			'Accept': 'text/plain',
			'api-key': os.getenv('P_MAERSK_API_KEY')
		}

		try:
			with requests.Session() as client:
				client.headers.update(headers)
				response = client.post(endpoint, verify=False, json=payload)
			response.raise_for_status()
			return response.json()
		except Exception as e:
			print(f"Error occurred: {e}")
			return None

	def quote_to_dict(self, xml_string):
		# Parse the XML string
		root = ET.fromstring(xml_string)

		# Define the namespaces
		namespaces = {
			'diffgr': 'urn:schemas-microsoft-com:xml-diffgram-v1',
			'msdata': 'urn:schemas-microsoft-com:xml-msdata',
			'': 'http://tempuri.org/dsTQSQuote.xsd'
		}

		# Find the TQSQuote element
		tqs_quote = root.find('.//diffgr:diffgram/dsTQSQuote/TQSQuote', namespaces)

		if tqs_quote is None:
			raise ValueError("TQSQuote element not found in the XML.")

		# Helper function to extract text from an element
		def get_text(element, tag):
			if element is None:
				return ''
			child = element.find(tag, namespaces)

			return child.text if child is not None else ''

		# Construct the dictionary
		result = {
			"Rating": {
				"TQSQuoteID": tqs_quote.attrib.get('diffgr:id', ''),
				"QuoteID": get_text(tqs_quote, 'QuoteID'),
				"TariffID": get_text(tqs_quote, 'TariffID'),
				"Scale": get_text(tqs_quote, 'Scale'),
				"LocationID": get_text(tqs_quote, 'LocationID'),
				"TransportByAir": get_text(tqs_quote, 'TransportByAir'),
				"CalculateBillCode": get_text(tqs_quote, 'CalculateBillCode'),
				"IsSaveQuote": get_text(tqs_quote, 'IsSaveQuote'),
				"IATA_Classifications": get_text(tqs_quote, 'IATA_Classifications'),
				"PackingContainers": get_text(tqs_quote, 'PackingContainers'),
				"DeclaredValue": get_text(tqs_quote, 'DeclaredValue'),
				"InsuranceValue": get_text(tqs_quote, 'InsuranceValue'),
				"COD": get_text(tqs_quote, 'COD'),
				"TariffName": get_text(tqs_quote, 'TariffName'),
				"Notes": get_text(tqs_quote, 'Notes'),
				"Service": get_text(tqs_quote, 'Service'),
				"QuoteDate": get_text(tqs_quote, 'QuoteDate'),
				"ChargeWeight": get_text(tqs_quote, 'ChargeWeight'),
				"TotalPieces": get_text(tqs_quote, 'TotalPieces'),
				"Shipper": {
					"Name": get_text(tqs_quote.find('Shipper', namespaces), 'Name'),
					"PDArea": get_text(tqs_quote.find('Shipper', namespaces), 'PDArea'),
					"Address1": get_text(tqs_quote.find('Shipper', namespaces), 'Address1'),
					"Address2": get_text(tqs_quote.find('Shipper', namespaces), 'Address2'),
					"City": get_text(tqs_quote.find('Shipper', namespaces), 'City'),
					"State": get_text(tqs_quote.find('Shipper', namespaces), 'State'),
					"Zipcode": get_text(tqs_quote.find('Shipper', namespaces), 'Zipcode'),
					"Airport": get_text(tqs_quote.find('Shipper', namespaces), 'Airport'),
					"Attempted": get_text(tqs_quote.find('Shipper', namespaces), 'Attempted'),
					"PrivateRes": get_text(tqs_quote.find('Shipper', namespaces), 'PrivateRes'),
					"Hotel": get_text(tqs_quote.find('Shipper', namespaces), 'Hotel'),
					"Inside": get_text(tqs_quote.find('Shipper', namespaces), 'Inside'),
					"Liftgate": get_text(tqs_quote.find('Shipper', namespaces), 'Liftgate'),
					"TwoManHours": get_text(tqs_quote.find('Shipper', namespaces), 'TwoManHours'),
					"WaitTimeHours": get_text(tqs_quote.find('Shipper', namespaces), 'WaitTimeHours'),
					"Special": get_text(tqs_quote.find('Shipper', namespaces), 'Special'),
					"DedicatedVehicle": get_text(tqs_quote.find('Shipper', namespaces), 'DedicatedVehicle'),
					"Miles": get_text(tqs_quote.find('Shipper', namespaces), 'Miles'),
					"Canadian": get_text(tqs_quote.find('Shipper', namespaces), 'Canadian'),
					"ServiceCode": get_text(tqs_quote.find('Shipper', namespaces), 'ServiceCode'),
					"Convention": get_text(tqs_quote.find('Shipper', namespaces), 'Convention'),
					"Country": get_text(tqs_quote.find('Shipper', namespaces), 'Country'),
					"IsBeyond": get_text(tqs_quote.find('Shipper', namespaces), 'IsBeyond'),
					"BeyondServiceArea": get_text(tqs_quote.find('Shipper', namespaces), 'BeyondServiceArea'),
					"Station": get_text(tqs_quote.find('Shipper', namespaces), 'Station'),
					"AirtrakNo": get_text(tqs_quote.find('Shipper', namespaces), 'AirtrakNo')
				},
				"Consignee": {
					"Name": get_text(tqs_quote.find('Consignee', namespaces), 'Name'),
					"PDArea": get_text(tqs_quote.find('Consignee', namespaces), 'PDArea'),
					"Address1": get_text(tqs_quote.find('Consignee', namespaces), 'Address1'),
					"Address2": get_text(tqs_quote.find('Consignee', namespaces), 'Address2'),
					"City": get_text(tqs_quote.find('Consignee', namespaces), 'City'),
					"State": get_text(tqs_quote.find('Consignee', namespaces), 'State'),
					"Zipcode": get_text(tqs_quote.find('Consignee', namespaces), 'Zipcode'),
					"Airport": get_text(tqs_quote.find('Consignee', namespaces), 'Airport'),
					"Attempted": get_text(tqs_quote.find('Consignee', namespaces), 'Attempted'),
					"PrivateRes": get_text(tqs_quote.find('Consignee', namespaces), 'PrivateRes'),
					"Hotel": get_text(tqs_quote.find('Consignee', namespaces), 'Hotel'),
					"Inside": get_text(tqs_quote.find('Consignee', namespaces), 'Inside'),
					"Liftgate": get_text(tqs_quote.find('Consignee', namespaces), 'Liftgate'),
					"TwoManHours": get_text(tqs_quote.find('Consignee', namespaces), 'TwoManHours'),
					"WaitTimeHours": get_text(tqs_quote.find('Consignee', namespaces), 'WaitTimeHours'),
					"Special": get_text(tqs_quote.find('Consignee', namespaces), 'Special'),
					"DedicatedVehicle": get_text(tqs_quote.find('Consignee', namespaces), 'DedicatedVehicle'),
					"Miles": get_text(tqs_quote.find('Consignee', namespaces), 'Miles'),
					"Canadian": get_text(tqs_quote.find('Consignee', namespaces), 'Canadian'),
					"ServiceCode": get_text(tqs_quote.find('Consignee', namespaces), 'ServiceCode'),
					"Convention": get_text(tqs_quote.find('Consignee', namespaces), 'Convention'),
					"Country": get_text(tqs_quote.find('Consignee', namespaces), 'Country'),
					"IsBeyond": get_text(tqs_quote.find('Consignee', namespaces), 'IsBeyond'),
					"BeyondServiceArea": get_text(tqs_quote.find('Consignee', namespaces), 'BeyondServiceArea'),
					"Station": get_text(tqs_quote.find('Consignee', namespaces), 'Station'),
					"AirtrakNo": get_text(tqs_quote.find('Consignee', namespaces), 'AirtrakNo')
				},
				"LineItems": [
					{
						"LineRow": get_text(line_item, 'LineRow'),
						"Pieces": get_text(line_item, 'Pieces'),
						"Weight": get_text(line_item, 'Weight'),
						"Description": get_text(line_item, 'Description'),
						"Length": get_text(line_item, 'Length'),
						"Width": get_text(line_item, 'Width'),
						"Height": get_text(line_item, 'Height')
					}
					for line_item in tqs_quote.findall('LineItems', namespaces)
				],
				"Quote": {
					"Service": get_text(tqs_quote.find('Quote', namespaces), 'Service'),
					"DimWeight": get_text(tqs_quote.find('Quote', namespaces), 'DimWeight'),
					"TotalQuote": get_text(tqs_quote.find('Quote', namespaces), 'TotalQuote'),
					"Breakdown": {
						"ChargeCode": get_text(tqs_quote.find('Quote/Breakdown', namespaces), 'ChargeCode'),
						"Charge": get_text(tqs_quote.find('Quote/Breakdown', namespaces), 'Charge'),
						"BillCodeName": get_text(tqs_quote.find('Quote/Breakdown', namespaces), 'BillCodeName'),
						"Steps": get_text(tqs_quote.find('Quote/Breakdown', namespaces), 'Steps')
					},
					"Oversized": get_text(tqs_quote.find('Quote', namespaces), 'Oversized'),
					"OversizedServiceArea": get_text(tqs_quote.find('Quote', namespaces), 'OversizedServiceArea'),
					"AbleToCalculate": get_text(tqs_quote.find('Quote', namespaces), 'AbleToCalculate'),
					"ChargeWeight": get_text(tqs_quote.find('Quote', namespaces), 'ChargeWeight'),
					"Beyond": get_text(tqs_quote.find('Quote', namespaces), 'Beyond'),
					"DisplayService": get_text(tqs_quote.find('Quote', namespaces), 'DisplayService'),
					"TopLine": get_text(tqs_quote.find('Quote', namespaces), 'TopLine'),
					"UpgradeRequiredForServiceArea": get_text(tqs_quote.find('Quote', namespaces), 'UpgradeRequiredForServiceArea'),
					"LinkForShipping": get_text(tqs_quote.find('Quote', namespaces), 'LinkForShipping'),
					"DeliveryDate": get_text(tqs_quote.find('Quote', namespaces), 'DeliveryDate'),
					"ExtendedTopLine": get_text(tqs_quote.find('Quote', namespaces), 'ExtendedTopLine')
				},
				"ShipDate": get_text(tqs_quote, 'ShipDate'),
				"TariffHeaderID": get_text(tqs_quote, 'TariffHeaderID'),
				"UserID": get_text(tqs_quote, 'UserID'),
				"QuoteConfirmationEmail": get_text(tqs_quote, 'QuoteConfirmationEmail'),
				"DebrisRemoval": get_text(tqs_quote, 'DebrisRemoval'),
				"Gateway": get_text(tqs_quote, 'Gateway'),
				"IsInternational": get_text(tqs_quote, 'IsInternational')
			}
		}

		return result

	def shipment_to_dict(self, xml_string):
		# Parse the XML string
		root = ET.fromstring(xml_string)

		# Define the namespaces
		namespaces = {
			'soap': 'http://www.w3.org/2003/05/soap-envelope',
			'diff': 'urn:schemas-microsoft-com:xml-diffgram-v1',
			'ds': 'http://tempuri.org/dsShipment.xsd'
		}

		# Navigate to dsShipment elements
		diffgram = root.find('.//diff:diffgram', namespaces)
		ds_shipment = diffgram.find('.//ds:dsShipment', namespaces)

		if ds_shipment is None:
			raise ValueError("ds_shipment element not found in the XML.")

		# Navigate to dsShipment elements
		diffgram = root.find('.//diff:diffgram', namespaces)
		if diffgram is None:
			raise ValueError("diffgram element not found in the XML.")

		ds_shipment = diffgram.find('.//ds:dsShipment', namespaces)
		if ds_shipment is None:
			raise ValueError("ds_shipment element not found in the XML.")

		# Find the Shipment element
		shipment = ds_shipment.find('ds:Shipment', namespaces)
		if shipment is None:
			raise ValueError("Shipment element not found in ds_shipment.")

		# Helper function to extract text from an element
		def get_text(element, tag):
			if element is None:
				return ''
			child = element.find(f'ds:{tag}', namespaces)

			return child.text if child is not None else ''

		result = {
			"Shipment": {
				"QuoteId": get_text(shipment, 'QuoteID'),
				"LocationId": get_text(shipment, 'LocationID'),
				"TransportByAir": get_text(shipment, 'TransportByAir'),
				"IATA_Classifications": get_text(shipment, 'IATA_Classifications'),
				"PackingContainers": get_text(shipment, 'PackingContainers'),
				"DeclaredValue": get_text(shipment, 'DeclaredValue'),
				"COD": get_text(shipment, 'COD'),
				"TariffId": get_text(shipment, 'TariffID'),
				"TariffName": get_text(shipment, 'TariffName'),
				"TariffCode": get_text(shipment, 'TariffCode'),
				"Notes": get_text(shipment, 'Notes'),
				"Service": get_text(shipment, 'Service'),
				"AirtrakServiceCode": get_text(shipment, 'AirtrakServiceCode'),
				"TariffExtension": get_text(shipment, 'TariffExtension'),
				"QuoteDate": get_text(shipment, 'QuoteDate'),
				"HoldAtAirport": get_text(shipment, 'HoldAtAirport'),
				"ControlStation": get_text(shipment, 'ControlStation'),
				"ProNumber": get_text(shipment, 'ProNumber'),
				"ConsigneeAttn": get_text(shipment, 'ConsigneeAttn'),
				"ThirdPartyAuth": get_text(shipment, 'ThirdPartyAuth'),
				"ShipperRef": get_text(shipment, 'ShipperRef'),
				"ConsigneeRef": get_text(shipment, 'ConsigneeRef'),
				"DeliveryDate": get_text(shipment, 'DeliveryDate'),
				"AmountDueConsignee": get_text(shipment, 'AmountDueConsignee'),
				"ShipDate": get_text(shipment, 'ShipDate'),
				"OverSized": get_text(shipment, 'OverSized'),
				"PayType": get_text(shipment, 'PayType'),
				"POD": get_text(shipment, 'POD'),
				"SatDelivery": get_text(shipment, 'SatDelivery'),
				"SpecialInstructions": get_text(shipment, 'SpecialInstructions'),
				"ReadyTime": get_text(shipment, 'ReadyTime'),
				"CloseTime": get_text(shipment, 'CloseTime'),
				"HomeDelivery": get_text(shipment, 'HomeDelivery'),
				"ShipmentId": get_text(shipment, 'ShipmentId'),
				"LockDate": get_text(shipment, 'LockDate'),
				"LockUser": get_text(shipment, 'LockUser'),
				"LastUpdate": get_text(shipment, 'LastUpdate'),
				"AddressId": get_text(shipment, 'AddressId'),
				"Platinum": get_text(shipment, 'Platinum'),
				"IsShipper": get_text(shipment, 'IsShipper'),
				"GBL": get_text(shipment, 'GBL'),
				"IsInsurance": get_text(shipment, 'IsInsurance'),
				"Condition": get_text(shipment, 'Condition'),
				"Packaging": get_text(shipment, 'Packaging'),
				"TariffHeaderId": get_text(shipment, 'TariffHeaderID'),
				"ProductName": get_text(shipment, 'ProductName'),
				"ProductDescription": get_text(shipment, 'ProductDescription'),
				"DebrisRemoval": get_text(shipment, 'DebrisRemoval'),
				"IsScreeningConsent": get_text(shipment, 'IsScreeningConsent'),
				"EmailBOL": get_text(shipment, 'EmailBOL'),
				"ServiceName": get_text(shipment, 'ServiceName'),
				"Hazmat": get_text(shipment, 'Hazmat'),
				"HazmatNumber": get_text(shipment, 'HazmatNumber'),
				"HazmatClass": get_text(shipment, 'HazmatClass'),
				"HazmatPhone": get_text(shipment, 'HazmatPhone'),
				"IsDistribution": get_text(shipment, 'IsDistribution'),
				"DeliveryStartTime": get_text(shipment, 'DeliveryStartTime'),
				"AirtrakQuoteNo": get_text(shipment, 'AirtrakQuoteNo'),
				"Shipper": {
					"ShipmentId": get_text(shipment.find('Shipper', namespaces), 'ShipmentId'),
					"Name": get_text(shipment.find('Shipper', namespaces), 'Name'),
					"Address1": get_text(shipment.find('Shipper', namespaces), 'Address1'),
					"Address2": get_text(shipment.find('Shipper', namespaces), 'Address2'),
					"Address3": get_text(shipment.find('Shipper', namespaces), 'Address3'),
					"City": get_text(shipment.find('Shipper', namespaces), 'City'),
					"State": get_text(shipment.find('Shipper', namespaces), 'State'),
					"Zipcode": get_text(shipment.find('Shipper', namespaces), 'Zipcode'),
					"Country": get_text(shipment.find('Shipper', namespaces), 'Country'),
					"Airport": get_text(shipment.find('Shipper', namespaces), 'Airport'),
					"Owner": get_text(shipment.find('Shipper', namespaces), 'Owner'),
					"Attempted": get_text(shipment.find('Shipper', namespaces), 'Attempted'),
					"PrivateRes": get_text(shipment.find('Shipper', namespaces), 'PrivateRes'),
					"Hotel": get_text(shipment.find('Shipper', namespaces), 'Hotel'),
					"InsIde": get_text(shipment.find('Shipper', namespaces), 'InsIde'),
					"Liftgate": get_text(shipment.find('Shipper', namespaces), 'Liftgate'),
					"TwoManHours": get_text(shipment.find('Shipper', namespaces), 'TwoManHours'),
					"WaitTimeHours": get_text(shipment.find('Shipper', namespaces), 'WaitTimeHours'),
					"Special": get_text(shipment.find('Shipper', namespaces), 'Special'),
					"DedicatedVehicle": get_text(shipment.find('Shipper', namespaces), 'DedicatedVehicle'),
					"Miles": get_text(shipment.find('Shipper', namespaces), 'Miles'),
					"Canadian": get_text(shipment.find('Shipper', namespaces), 'Canadian'),
					"ServiceCode": get_text(shipment.find('Shipper', namespaces), 'ServiceCode'),
					"Convention": get_text(shipment.find('Shipper', namespaces), 'Convention'),
					"Contact": get_text(shipment.find('Shipper', namespaces), 'Contact'),
					"Phone": get_text(shipment.find('Shipper', namespaces), 'Phone'),
					"Extension": get_text(shipment.find('Shipper', namespaces), 'Extension'),
					"Email": get_text(shipment.find('Shipper', namespaces), 'Email'),
					"SendEmail": get_text(shipment.find('Shipper', namespaces), 'SendEmail')
				},
				"Consignee": {
					"ShipmentId": get_text(shipment.find('Consignee', namespaces), 'ShipmentId'),
					"Name": get_text(shipment.find('Consignee', namespaces), 'Name'),
					"Address1": get_text(shipment.find('Consignee', namespaces), 'Address1'),
					"Address2": get_text(shipment.find('Consignee', namespaces), 'Address2'),
					"Address3": get_text(shipment.find('Consignee', namespaces), 'Address3'),
					"City": get_text(shipment.find('Consignee', namespaces), 'City'),
					"State": get_text(shipment.find('Consignee', namespaces), 'State'),
					"Zipcode": get_text(shipment.find('Consignee', namespaces), 'Zipcode'),
					"Country": get_text(shipment.find('Consignee', namespaces), 'Country'),
					"Airport": get_text(shipment.find('Consignee', namespaces), 'Airport'),
					"Owner": get_text(shipment.find('Consignee', namespaces), 'Owner'),
					"Attempted": get_text(shipment.find('Consignee', namespaces), 'Attempted'),
					"PrivateRes": get_text(shipment.find('Consignee', namespaces), 'PrivateRes'),
					"Hotel": get_text(shipment.find('Consignee', namespaces), 'Hotel'),
					"InsIde": get_text(shipment.find('Consignee', namespaces), 'InsIde'),
					"Liftgate": get_text(shipment.find('Consignee', namespaces), 'Liftgate'),
					"TwoManHours": get_text(shipment.find('Consignee', namespaces), 'TwoManHours'),
					"WaitTimeHours": get_text(shipment.find('Consignee', namespaces), 'WaitTimeHours'),
					"Special": get_text(shipment.find('Consignee', namespaces), 'Special'),
					"DedicatedVehicle": get_text(shipment.find('Consignee', namespaces), 'DedicatedVehicle'),
					"Miles": get_text(shipment.find('Consignee', namespaces), 'Miles'),
					"Canadian": get_text(shipment.find('Consignee', namespaces), 'Canadian'),
					"ServiceCode": get_text(shipment.find('Consignee', namespaces), 'ServiceCode'),
					"Convention": get_text(shipment.find('Consignee', namespaces), 'Convention'),
					"Contact": get_text(shipment.find('Consignee', namespaces), 'Contact'),
					"Phone": get_text(shipment.find('Consignee', namespaces), 'Phone'),
					"Extension": get_text(shipment.find('Consignee', namespaces), 'Extension'),
					"Email": get_text(shipment.find('Consignee', namespaces), 'Email'),
					"SendEmail": get_text(shipment.find('Consignee', namespaces), 'SendEmail')
				},
				"ThirdParty": {
					"ShipmentId": get_text(shipment.find('ThirdParty', namespaces), 'ShipmentId'),
					"Name": get_text(shipment.find('ThirdParty', namespaces), 'Name'),
					"Address1": get_text(shipment.find('ThirdParty', namespaces), 'Address1'),
					"Address2": get_text(shipment.find('ThirdParty', namespaces), 'Address2'),
					"Address3": get_text(shipment.find('ThirdParty', namespaces), 'Address3'),
					"City": get_text(shipment.find('ThirdParty', namespaces), 'City'),
					"State": get_text(shipment.find('ThirdParty', namespaces), 'State'),
					"Zipcode": get_text(shipment.find('ThirdParty', namespaces), 'Zipcode'),
					"Country": get_text(shipment.find('ThirdParty', namespaces), 'Country'),
					"Contact": get_text(shipment.find('ThirdParty', namespaces), 'Contact'),
					"Phone": get_text(shipment.find('ThirdParty', namespaces), 'Phone'),
					"Extension": get_text(shipment.find('ThirdParty', namespaces), 'Extension'),
					"Email": get_text(shipment.find('ThirdParty', namespaces), 'Email'),
					"SendEmail": get_text(shipment.find('ThirdParty', namespaces), 'SendEmail')
				},
				"LineItem": [
					{
						"ShipmentId": get_text(line_item, 'ShipmentId'),
						"LineRow": get_text(line_item, 'LineRow'),
						"PackageType": get_text(line_item, 'PackageType'),
						"Pieces": get_text(line_item, 'Pieces'),
						"Weight": get_text(line_item, 'Weight'),
						"Description": get_text(line_item, 'Description'),
						"Length": get_text(line_item, 'Length'),
						"Width": get_text(line_item, 'Width'),
						"Height": get_text(line_item, 'Height'),
						"Kilos": get_text(line_item, 'Kilos')
					} for line_item in ds_shipment.findall('LineItems', namespaces)
				],
				"Quote": {
					"ShipmentId": get_text(shipment.find('Quote', namespaces), 'ShipmentId'),
					"Service": get_text(shipment.find('Quote', namespaces), 'Service'),
					"DimWeight": get_text(shipment.find('Quote', namespaces), 'DimWeight'),
					"TotalQuote": get_text(shipment.find('Quote', namespaces), 'TotalQuote'),
					"Oversized": get_text(shipment.find('Quote', namespaces), 'Oversized'),
					"AbleToCalculate": get_text(shipment.find('Quote', namespaces), 'AbleToCalculate'),
					"ChargeWeight": get_text(shipment.find('Quote', namespaces), 'ChargeWeight'),
					"Beyond": get_text(shipment.find('Quote', namespaces), 'Beyond'),
					"DisplayService": get_text(shipment.find('Quote', namespaces), 'DisplayService'),
					"TopLine": get_text(shipment.find('Quote', namespaces), 'TopLine'),
					"UpgradeRequiredForServiceArea": get_text(shipment.find('Quote', namespaces), 'UpgradeRequiredForServiceArea'),
					"LinkForShipping": get_text(shipment.find('Quote', namespaces), 'LinkForShipping'),
					"Breakdown": {
						"ShipmentId": get_text(shipment.find('Quote/Breakdown', namespaces), 'ShipmentId'),
						"ChargeCode": get_text(shipment.find('Quote/Breakdown', namespaces), 'ChargeCode'),
						"Charge": get_text(shipment.find('Quote/Breakdown', namespaces), 'Charge'),
						"BillCodeName": get_text(shipment.find('Quote/Breakdown', namespaces), 'BillCodeName')
					}
				},
				"InternationalServices": {
					"ShipmentId": get_text(shipment.find('InternationalServices', namespaces), 'ShipmentId'),
					"ShipmentType": get_text(shipment.find('InternationalServices', namespaces), 'ShipmentType'),
					"Service": get_text(shipment.find('InternationalServices', namespaces), 'Service'),
					"Incoterms": get_text(shipment.find('InternationalServices', namespaces), 'Incoterms'),
					"CustomsValue": get_text(shipment.find('InternationalServices', namespaces), 'CustomsValue')
				},
				"International": {
					"ShipmentId": get_text(shipment.find('International', namespaces), 'ShipmentId'),
					"USPPI_EIN": get_text(shipment.find('International', namespaces), 'USPPI_EIN'),
					"PartiesToTransaction": get_text(shipment.find('International', namespaces), 'PartiesToTransaction'),
					"IntermediateConsignee": get_text(shipment.find('International', namespaces), 'IntermediateConsignee'),
					"MethodOfTransportation": get_text(shipment.find('International', namespaces), 'MethodOfTransportation'),
					"ConsolIdateOrDirect": get_text(shipment.find('International', namespaces), 'ConsolIdateOrDirect'),
					"ShipmentReferenceNumber": get_text(shipment.find('International', namespaces), 'ShipmentReferenceNumber'),
					"EntryNumber": get_text(shipment.find('International', namespaces), 'EntryNumber'),
					"InBondCode": get_text(shipment.find('International', namespaces), 'InBondCode'),
					"RoutedExportTransaction": get_text(shipment.find('International', namespaces), 'RoutedExportTransaction'),
					"LicenseNumber": get_text(shipment.find('International', namespaces), 'LicenseNumber'),
					"ECCN": get_text(shipment.find('International', namespaces), 'ECCN'),
					"HazMat": get_text(shipment.find('International', namespaces), 'HazMat'),
					"LicenseValue": get_text(shipment.find('International', namespaces), 'LicenseValue'),
					"InBondCodeValue": get_text(shipment.find('International', namespaces), 'InBondCodeValue'),
					"MethodOfTransportationValue": get_text(shipment.find('International', namespaces), 'MethodOfTransportationValue')
				},
				"OtherReferences": [
					{
						"ShipmentId": get_text(shipment, 'ShipmentId'),
						"Reference": get_text(shipment, 'Reference'),
						"ReferenceType": get_text(shipment, 'ReferenceType')
					} for reference in ds_shipment.findall('OtherReferences', namespaces)
				],
				"ScheduleBLines": {
					"ScheduleBId": get_text(shipment.find('ScheduleBLines', namespaces), 'ScheduleBId'),
					"ShipmentId": get_text(shipment.find('ScheduleBLines', namespaces), 'ShipmentId'),
					"ScheduleBLine": get_text(shipment.find('ScheduleBLines', namespaces), 'ScheduleBLine'),
					"DForM": get_text(shipment.find('ScheduleBLines', namespaces), 'DForM'),
					"ScheduleBNumber": get_text(shipment.find('ScheduleBLines', namespaces), 'ScheduleBNumber'),
					"Quantity": get_text(shipment.find('ScheduleBLines', namespaces), 'Quantity'),
					"Weight": get_text(shipment.find('ScheduleBLines', namespaces), 'Weight'),
					"VinNumber": get_text(shipment.find('ScheduleBLines', namespaces), 'VinNumber'),
					"DollarValue": get_text(shipment.find('ScheduleBLines', namespaces), 'DollarValue'),
					"ScheduleBCode": get_text(shipment.find('ScheduleBLines', namespaces), 'ScheduleBCode')
				},
				"ShipmentCustomerInfo": {
					"User_Email": get_text(shipment.find('ShipmentCustomerInfo', namespaces), 'User_Email'),
					"User_Name": get_text(shipment.find('ShipmentCustomerInfo', namespaces), 'User_Name'),
					"User_Phone": get_text(shipment.find('ShipmentCustomerInfo', namespaces), 'User_Phone'),
					"Name": get_text(shipment.find('ShipmentCustomerInfo', namespaces), 'Name'),
					"Address1": get_text(shipment.find('ShipmentCustomerInfo', namespaces), 'Address1'),
					"Address2": get_text(shipment.find('ShipmentCustomerInfo', namespaces), 'Address2'),
					"City": get_text(shipment.find('ShipmentCustomerInfo', namespaces), 'City'),
					"State": get_text(shipment.find('ShipmentCustomerInfo', namespaces), 'State'),
					"Zip": get_text(shipment.find('ShipmentCustomerInfo', namespaces), 'Zip'),
					"Country": get_text(shipment.find('ShipmentCustomerInfo', namespaces), 'Country')
				}
			}
		}

		return result

	def save_shipment_rest(self, rootShipmentObject, data, input_data):
		print(f'input_data: {input_data}')
		option = input_data['Shipment']['Option']
		PackageType = input_data['Shipment']['PackageType']
		Shipper = input_data['Shipment']['Shipper']
		Consignee = input_data['Shipment']['Consignee']
		PayType = input_data['Shipment']['PayType']
		IsScreeningConsent = input_data['Shipment']['IsScreeningConsent']
		SpecialInstructions: '****DO NOT REMOVE FREIGHT FROM PALLET******************DO NOT STACK ON TOP OF THIS PALLET**DO NOT LEAVE AT DOOR**'

		rating = data['dsQuote']['Rating'][0]
		rootShipmentObject['Shipment']['QuoteId'] = str(rating['QuoteID'])
		rootShipmentObject['Shipment']['LocationId'] = str(rating['LocationID'])
		rootShipmentObject['Shipment']['TransportByAir'] = str(rating['TransportByAir']).lower()
		rootShipmentObject['Shipment']['IATA_Classifications'] = str(rating['IATA_Classifications'])
		rootShipmentObject['Shipment']['PackingContainers'] = str(rating['PackingContainers'])
		rootShipmentObject['Shipment']['DeclaredValue'] = str(rating['DeclaredValue'])
		rootShipmentObject['Shipment']['COD'] = str(rating['COD'])
		rootShipmentObject['Shipment']['TariffId'] = str(rating['TariffID'])
		rootShipmentObject['Shipment']['TariffName'] = str(rating['TariffName'])
		rootShipmentObject['Shipment']['Notes'] = str(rating['Notes'])
		rootShipmentObject['Shipment']['Service'] = data['dsQuote']['Quote'][option]["Service"]
		rootShipmentObject['Shipment']['QuoteDate'] = rating['QuoteDate']
		rootShipmentObject['Shipment']['ShipDate'] = rating['ShipDate']
		rootShipmentObject['Shipment']['PayType'] = PayType
		rootShipmentObject['Shipment']['IsScreeningConsent'] = IsScreeningConsent
		rootShipmentObject['Shipment']['TariffHeaderId'] = str(rating['TariffHeaderID'])
		rootShipmentObject['Shipment']['DebrisRemoval'] = str(rating['DebrisRemoval']).lower()
		rootShipmentObject['Shipment']['AddressId'] = os.getenv('ADDRESSID')

		# Shipper info
		shipper = data['dsQuote']['Shipper'][0]
		rootShipmentObject['Shipment']['Shipper']['Name'] = Shipper['Name']
		rootShipmentObject['Shipment']['Shipper']['Address1'] = Shipper['Address1']
		rootShipmentObject['Shipment']['Shipper']['Address2'] = Shipper['Address2']
		rootShipmentObject['Shipment']['Shipper']['Address3'] = Shipper['Address3']
		rootShipmentObject['Shipment']['Shipper']['City'] = Shipper['City']
		rootShipmentObject['Shipment']['Shipper']['State'] = shipper['State']
		rootShipmentObject['Shipment']['Shipper']['Zipcode'] = shipper['Zipcode']
		rootShipmentObject['Shipment']['Shipper']['Country'] = shipper['Country']
		rootShipmentObject['Shipment']['Shipper']['Airport'] = shipper['Airport']
		rootShipmentObject['Shipment']['Shipper']['Owner'] = Shipper['Owner']
		rootShipmentObject['Shipment']['Shipper']['Attempted'] = str(shipper['Attempted']).lower()
		rootShipmentObject['Shipment']['Shipper']['PrivateRes'] = str(shipper['PrivateRes']).lower()
		rootShipmentObject['Shipment']['Shipper']['Hotel'] = str(shipper['Hotel']).lower()
		rootShipmentObject['Shipment']['Shipper']['InsIde'] = str(shipper['Inside']).lower()
		rootShipmentObject['Shipment']['Shipper']['Liftgate'] = str(shipper['Liftgate']).lower()
		rootShipmentObject['Shipment']['Shipper']['TwoManHours'] = shipper['TwoManHours']
		rootShipmentObject['Shipment']['Shipper']['WaitTimeHours'] = shipper['WaitTimeHours']
		rootShipmentObject['Shipment']['Shipper']['Special'] = shipper['Special']
		rootShipmentObject['Shipment']['Shipper']['DedicatedVehicle'] = str(shipper['DedicatedVehicle'])
		rootShipmentObject['Shipment']['Shipper']['Miles'] = shipper['Miles']
		rootShipmentObject['Shipment']['Shipper']['Canadian'] = str(shipper['Canadian']).lower()
		rootShipmentObject['Shipment']['Shipper']['ServiceCode'] = shipper['ServiceCode']
		rootShipmentObject['Shipment']['Shipper']['Convention'] = str(shipper['Convention']).lower()
		rootShipmentObject['Shipment']['Shipper']['Contact'] = Shipper['Contact']
		rootShipmentObject['Shipment']['Shipper']['Phone'] = Shipper['Phone']
		rootShipmentObject['Shipment']['Shipper']['Extension'] = Shipper['Extension']
		rootShipmentObject['Shipment']['Shipper']['Email'] = Shipper['Email']
		rootShipmentObject['Shipment']['Shipper']['SendEmail'] = Shipper['SendEmail']

		# Consignee info
		consignee = data['dsQuote']['Consignee'][0]
		rootShipmentObject['Shipment']['Consignee']['Name'] = Consignee['Name']
		rootShipmentObject['Shipment']['Consignee']['Address1'] = Consignee['Address1']
		rootShipmentObject['Shipment']['Consignee']['Address2'] = Consignee['Address2']
		rootShipmentObject['Shipment']['Consignee']['Address3'] = Consignee['Address3']
		rootShipmentObject['Shipment']['Consignee']['City'] = Consignee['City']
		rootShipmentObject['Shipment']['Consignee']['State'] = consignee['State']
		rootShipmentObject['Shipment']['Consignee']['Zipcode'] = consignee['Zipcode']
		rootShipmentObject['Shipment']['Consignee']['Country'] = consignee['Country']
		rootShipmentObject['Shipment']['Consignee']['Airport'] = consignee['Airport']
		rootShipmentObject['Shipment']['Consignee']['Owner'] = Consignee['Owner']
		rootShipmentObject['Shipment']['Consignee']['Attempted'] = str(consignee['Attempted']).lower()
		rootShipmentObject['Shipment']['Consignee']['PrivateRes'] = str(consignee['PrivateRes']).lower()
		rootShipmentObject['Shipment']['Consignee']['Hotel'] = str(consignee['Hotel']).lower()
		rootShipmentObject['Shipment']['Consignee']['InsIde'] = str(consignee['Inside']).lower()
		rootShipmentObject['Shipment']['Consignee']['Liftgate'] = str(consignee['Liftgate']).lower()
		rootShipmentObject['Shipment']['Consignee']['TwoManHours'] = consignee['TwoManHours']
		rootShipmentObject['Shipment']['Consignee']['WaitTimeHours'] = consignee['WaitTimeHours']
		rootShipmentObject['Shipment']['Consignee']['Special'] = consignee['Special']
		rootShipmentObject['Shipment']['Consignee']['DedicatedVehicle'] = str(consignee['DedicatedVehicle'])
		rootShipmentObject['Shipment']['Consignee']['Miles'] = consignee['Miles']
		rootShipmentObject['Shipment']['Consignee']['Canadian'] = str(consignee['Canadian']).lower()
		rootShipmentObject['Shipment']['Consignee']['ServiceCode'] = consignee['ServiceCode']
		rootShipmentObject['Shipment']['Consignee']['Convention'] = str(consignee['Convention']).lower()
		rootShipmentObject['Shipment']['Consignee']['Contact'] = Consignee['Contact']
		rootShipmentObject['Shipment']['Consignee']['Phone'] = Consignee['Phone']
		rootShipmentObject['Shipment']['Consignee']['Extension'] = Consignee['Extension']
		rootShipmentObject['Shipment']['Consignee']['Email'] = Consignee['Email']
		rootShipmentObject['Shipment']['Consignee']['SendEmail'] = Consignee['SendEmail']

		# Line items
		line_items = []
		for i in data['dsQuote']['LineItems']:
			current_item = {}
			current_item["ShipmentId"] = ""
			current_item["LineRow"] = str(i['LineRow'])
			current_item["PackageType"] = PackageType
			current_item["Pieces"] = i['Pieces']
			current_item["Weight"] = i['Weight']
			current_item["Description"] = i['Description']
			current_item["Length"] = i['Length']
			current_item["Width"] = i['Width']
			current_item["Height"] = i['Height']
			current_item["Kilos"] = ''
			line_items.append(current_item.copy())
		rootShipmentObject['Shipment']['LineItem'] = line_items

		# Quote
		rootShipmentObject['Shipment']['Quote']["ShipmentId"] = ''
		rootShipmentObject['Shipment']['Quote']["Service"] = data['dsQuote']['Quote'][option]["Service"]
		rootShipmentObject['Shipment']['Quote']["DimWeight"] = str(data['dsQuote']['Quote'][option]["DimWeight"])
		rootShipmentObject['Shipment']['Quote']["TotalQuote"] = str(data['dsQuote']['Quote'][option]["TotalQuote"])
		rootShipmentObject['Shipment']['Quote']["Oversized"] = str(data['dsQuote']['Quote'][option]["Oversized"]).lower()
		rootShipmentObject['Shipment']['Quote']["AbleToCalculate"] = str(data['dsQuote']['Quote'][option]["AbleToCalculate"]).lower()
		rootShipmentObject['Shipment']['Quote']["ChargeWeight"] = str(data['dsQuote']['Quote'][option]["ChargeWeight"])
		rootShipmentObject['Shipment']['Quote']["Beyond"] = str(data['dsQuote']['Quote'][option]["Beyond"]).lower()
		rootShipmentObject['Shipment']['Quote']["DisplayService"] = data['dsQuote']['Quote'][option]["DisplayService"]
		rootShipmentObject['Shipment']['Quote']["TopLine"] = str(data['dsQuote']['Quote'][option]["TopLine"])
		rootShipmentObject['Shipment']['Quote']["UpgradeRequiredForServiceArea"] = str(data['dsQuote']['Quote'][option]["UpgradeRequiredForServiceArea"]).lower()
		rootShipmentObject['Shipment']['Quote']["LinkForShipping"] = data['dsQuote']['Quote'][option]["LinkForShipping"]

		# Breakdown
		rootShipmentObject['Shipment']['Quote']['Breakdown']["ShipmentId"] = ""
		rootShipmentObject['Shipment']['Quote']['Breakdown']["ChargeCode"] = str(data['dsQuote']['Breakdown'][option]['ChargeCode'])
		rootShipmentObject['Shipment']['Quote']['Breakdown']["Charge"] = str(data['dsQuote']['Breakdown'][option]['Charge'])
		rootShipmentObject['Shipment']['Quote']['Breakdown']["BillCodeName"] = data['dsQuote']['Breakdown'][option]['BillCodeName']

		# Correction
		rootShipmentObject['Shipment']['ProNumber'] = ''
		rootShipmentObject['Shipment']['EmailBOL'] = ''

		endpoint = 'https://www.pilotssl.com/pilotapi/v1/Shipments'

		# payload = json.dumps(ratingRootObject)
		# encoded_payload = urlencode(payload)
		# content_length = str(len(encoded_payload))
		payload = rootShipmentObject

		headers = {
			'Content-Type': 'application/json',
			'Accept': 'text/plain',
			'api-key': os.getenv('P_MAERSK_API_KEY')
		}

		print(f'payload: {payload}')

		try:
			with requests.Session() as client:
				client.headers.update(headers)
				response = client.post(endpoint, verify=False, json=payload)
			response.raise_for_status()
			return response.json()
		except Exception as e:
			print(f"Error occurred: {e}")
			return None

	def void_shipment_rest(self, ProNumber):
		endpoint = f'https://www.pilotssl.com/pilotapi/v1/Shipments/Void/{str(ProNumber)}'
		print(endpoint)

		payload = {
			"LocationId": os.getenv('LOCATIONID'),
			"AddressId": os.getenv('ADDRESSID'),
			"ControlStation": os.getenv('CONTROLSTN'),
			"TariffHeaderID": os.getenv('TARIFFHEADERID'),
			"ProNumber": str(ProNumber)
		}
		print(payload)

		headers = {
			'Content-Type': 'application/json',
			'Accept': 'application/json',
			'api-key': os.getenv('P_MAERSK_API_KEY')
		}

		try:
			with requests.Session() as client:
				client.headers.update(headers)
				response = client.post(endpoint, verify=False, json=payload)
			response.raise_for_status()
			return response
		except Exception as e:
			print(f"Error occurred: {e}")
			return None

	def get_label(self, ProNumber, labelType, Zipcode):
		endpoint = 'https://pilotws.pilotdelivers.com/copilotforms/wsforms.asmx/HAWBLabel'

		params = {
			"shawb": ProNumber,
			"eLabelType": labelType,
			"szip": Zipcode
		}

		try:
			with requests.Session() as client:
				response = client.get(endpoint, verify=False, params=params)
			response.raise_for_status()
			return response
		except Exception as e:
			print(f"Error occurred: {e}")
			return None


if __name__ == '__main__':
	api = MaerskApi()
	# response = api.find_origin_by_zip('30044')
	# response = api.service_info(sOriginZip='90001', sDestZip='30044')

	# response = api.get_new_quote()
	# response = api.get_new_quote_rest()
	# # print(f"quote template : {response.text}")
	# ratingRootObject = api.quote_to_dict(response.text)

	# # Sample Data
	# data = {
	# 	"LocationID": os.getenv('LOCATIONID'),
	# 	"Shipper": {
	# 		"Zipcode": "90001"
	# 	},
	# 	"Consignee": {
	# 		"Zipcode": "30044"
	# 	},
	# 	"LineItems": [
	# 		{
	# 			"Pieces": "1",
	# 			"Weight": "1",
	# 			"Description": "ride on car toys",
	# 			"Length": "1",
	# 			"Width": "1",
	# 			"Height": "1"
	# 		}
	# 	],
	# 	"TariffHeaderID": os.getenv('TARIFFHEADERID')
	# }

	# response = api.get_rating_rest(ratingRootObject, data)

	# # data = {'id': '1234'}
	# # result = api.update_quote(response.text, data)
	# # print(f"updated quote: {result}")

	# rating_data = response

	# response = api.get_new_shipment_rest()
	# print(f'new_shipment: {response.content}')
	# rootShipmentObject = api.shipment_to_dict(response.content)

	# input_data = {
	# 	'Option': 0,
	# 	'PackageType': 'BOX',
	# 	'PayType': '0',
	# 	'IsScreeningConsent': 'false',
	# 	'Shipper': {
	# 		'Name': 'abc',
	# 		'Address1': '123 Main St',
	# 		'Address2': 'Suite 400',
	# 		'Address3': '',
	# 		'City': 'Los Angeles',
	# 		'Owner': 'John Doe',
	# 		'Contact': 'Jane Smith',
	# 		'Phone': '555-123-4567',
	# 		'Extension': '101',
	# 		'Email': 'shipper@example.com',
	# 		'SendEmail': 'true'
	# 	},
	# 	'Consignee': {
	# 		'Name': 'xyz',
	# 		'Address1': '456 Elm St',
	# 		'Address2': 'Apt 12B',
	# 		'Address3': '',
	# 		'City': 'Lawrenceville',
	# 		'Owner': 'Alice Johnson',
	# 		'Contact': 'Bob Williams',
	# 		'Phone': '555-987-6543',
	# 		'Extension': '202',
	# 		'Email': 'contact@xyzshipping.com',
	# 		'SendEmail': 'false'
	# 	}
	# }
	# response = api.save_shipment_rest(rootShipmentObject, rating_data, input_data)

	ProNumber = 400609786
	labelType = 'Label4x6'
	Zipcode = 90001
	# response = api.get_label(ProNumber=ProNumber, labelType=labelType, Zipcode=Zipcode)
	# print(response.text)
	# api.save_pdf_from_xml(response.text, 'label.pdf')
	response = api.void_shipment_rest(ProNumber)
	print(response.status_code)
	print(response.json())