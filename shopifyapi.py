from glob import glob
from time import sleep
import httpx
from dataclasses import dataclass
import json
import os
import pandas as pd
from dotenv import load_dotenv
from datetime import datetime, date
from converter import csv_to_jsonl, get_handles
import re
import logging

load_dotenv()
logging.basicConfig(level=logging.INFO)


@dataclass
class ShopifyApp:
    store_name: str = None
    access_token: str = None
    api_version: str = None
    api_url: str = None
    retries: int = 2
    timeout: float = 3
    version: str = '2025-01'

    # Common Function
    ## Get URL
    def get_file_url(self, response):
        return response['data']['fileCreate']['files'][0]['preview']['image']['url']

    ## Send Request
    def send_request(self, client, query, variables=None):
        for attempt in range(1, self.retries + 1):
            try:
                response = client.post(
                    self.api_url,
                    json={"query": query, "variables": variables},
                    timeout=self.timeout
                )

                # Raise an HTTP error for non-success status codes
                response.raise_for_status()

                data = response.json()

                # Check for API-specific errors
                if 'errors' in data:
                    print(data)
                    raise ValueError(f"Shopify API Error: {data['errors']}")

                return response

            except httpx.TimeoutException:
                logging.warning(f"Timeout on attempt {attempt}/{self.retries}")
            except httpx.RequestError as e:
                logging.error(f"Request failed on attempt {attempt}/{self.retries}: {e}")
            except ValueError as ve:
                logging.error(f"Shopify API returned an error: {ve}")
                raise ve  # Reraise if it's an API error

        # If all retries fail, raise an exception
        raise RuntimeError("Failed to send request after multiple attempts.")

    # Create
    ## Session
    def create_session(self):
        print("Creating session...")
        client = httpx.Client()
        headers = {
            'X-Shopify-Access-Token': self.access_token,
            'Content-Type': 'application/json'
        }
        client.headers.update(headers)
        self.api_url = f'https://{self.store_name}.myshopify.com/admin/api/{self.version}/graphql.json'

        return client

    ## Product
    def create_product(self, client):
        print("Creating product...")
        mutation = '''
                    mutation (
                            $handle: String,
                            $title: String,
                            $vendor: String,
                            $productType: String,
                            $variantTitle: String,
                            $variantPrice: Money,
                            $inventoryManagement: ProductVariantInventoryManagement,
                            $inventoryPolicy: ProductVariantInventoryPolicy,
                            $mediaOriginalSource: String!,
                            $mediaContentType: MediaContentType!
                    )
                    {
                        productCreate(
                            input: {
                                handle: $handle,
                                title: $title,
                                productType: $productType,
                                vendor: $vendor
                                variants: [
                                    {
                                        title: $variantTitle,
                                        price: $variantPrice,
                                        inventoryManagement: $inventoryManagement,
                                        inventoryPolicy: $inventoryPolicy
                                    }
                                ]
                            }
                            media: {
                                originalSource: $mediaOriginalSource,
                                mediaContentType: $mediaContentType
                            }
                        )
                        {
                            product {
                                id
                            }
                        }
                    }
                    '''

        variables = {
            'handle': "BAB063",
            'title': "Xmas Rocks Beavis And Butt-Head Shirt",
            'productType': "Shirts",
            'vendor': "MyStore",
            'variantsTitle': "Default",
            'variantPrice': "79.99",
            'inventoryManagement': 'SHOPIFY',
            'inventoryPolicy': 'DENY',
            'mediaOriginalSource': "https://80steess3.imgix.net/production/products/BAB061/xmas-rocks-beavis-and-butt-head-hoodie.master.png",
            'mediaContentType': 'IMAGE'
        }

        response = client.post(f'https://{self.store_name}.myshopify.com/admin/api/{self.api_version}/graphql.json',
                               json={"query": mutation, 'variables': variables})
        print(response)
        print(response.json())
        print('')

    def create_products(self, client, staged_target):
        print('Creating products...')
        mutation = '''
            mutation ($stagedUploadPath: String!){
                bulkOperationRunMutation(
                    mutation: "mutation call($input: ProductInput!, $media: [CreateMediaInput!]) {
                        productCreate(input: $input, media: $media) {
                            product {
                                id
                                title
                                variants(first: 10) {
                                    edges {
                                        node {
                                            id
                                            title
                                            inventoryQuantity
                                        }
                                    }
                                }
                            }
                            userErrors {
                                message
                                field
                            }
                        }
                    }",
                    stagedUploadPath: $stagedUploadPath
                )   {
                        bulkOperation {
                            id
                            url
                            status
                        }
                        userErrors {
                            message
                            field
                        }
                    }
            }
        '''

        variables = {
            "stagedUploadPath": staged_target['data']['stagedUploadsCreate']['stagedTargets'][0]['parameters'][3]['value']
        }

        response = client.post(f'https://{self.store_name}.myshopify.com/admin/api/{self.api_version}/graphql.json',
                               json={"query": mutation, "variables": variables})

        print(response)
        print(response.json())
        print('')

    ## Variants
    def create_variants(self, client, staged_target):
        print('Creating products...')
        mutation = '''
            mutation ($stagedUploadPath: String!){
                bulkOperationRunMutation(
                    mutation: "mutation call($productId: ID!, $strategy:ProductVariantsBulkCreateStrategy, $variants: [ProductVariantsBulkInput!]!) {
                        productVariantsBulkCreate(productId: $productId, strategy: $strategy, variants: $variants) {
                            product {
                                id
                                title
                                variants(first: 10) {
                                    edges {
                                        node {
                                            id
                                            title
                                            inventoryQuantity
                                        }
                                    }
                                }
                            }
                            userErrors {
                                message
                                field
                            }
                        }
                    }",
                    stagedUploadPath: $stagedUploadPath
                )   {
                        bulkOperation {
                            id
                            url
                            status
                        }
                        userErrors {
                            message
                            field
                        }
                    }
            }
        '''

        variables = {
            "stagedUploadPath": staged_target['data']['stagedUploadsCreate']['stagedTargets'][0]['parameters'][3]['value']
        }

        response = client.post(f'https://{self.store_name}.myshopify.com/admin/api/{self.api_version}/graphql.json',
                               json={"query": mutation, "variables": variables})

        print(response)
        print(response.json())
        print('')

    ## Collection
    def create_collection(self, client, descriptionHtml, image_src, title, appliedDisjuntively, column, relation, condition):
        if pd.isna(descriptionHtml):
            descriptionHtml = ''

        mutation = '''
        mutation createCollection($input: CollectionInput!) {
                             collectionCreate(input: $input)
                             {
                                collection {
                                            id
                                            title
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
                "descriptionHtml": descriptionHtml,
                # "image": {
                #     "src": image_src
                # },
                # "products": product_id,
                "ruleSet": {
                    "appliedDisjunctively": appliedDisjuntively,
                    "rules": {
                        "column": column,
                        "relation": relation,
                        "condition": condition
                    }
                },
                "title": title
            }
        }

        print(variables)
        while 1:
            try:
                response = client.post(f'https://{self.store_name}.myshopify.com/admin/api/{self.api_version}/graphql.json', json={'query': mutation, 'variables': variables})
                print(response)
                print(response.json())
                print('')
                break
            except Exception as e:
                print(e)

    ## Files
    def create_file(self, client, alt, filename, contentType, originalSource):
        if pd.isna(originalSource) or originalSource == '':
            print("Doesn't have images")
        else:
            mutation = '''
                mutation fileCreate($files: [FileCreateInput!]!) {
                  fileCreate(files: $files) {
                    files {
                      id
                      fileStatus
                      preview{
                        image{
                            url
                        }
                      }
                      fileErrors{
                        code
                        details
                        message
                      }
                    }
                    userErrors{
                      code
                      field
                      message
                    }
                  }
                }
            '''
            variables = {
                "files": {
                    "alt": alt,
                    # "filename": filename,
                    "contentType": contentType,
                    "originalSource": originalSource
                }
            }

            while 1:
                try:
                    response = client.post(f'https://{self.store_name}.myshopify.com/admin/api/{self.api_version}/graphql.json',
                                           json={'query': mutation, 'variables': variables})
                    print(response.json())
                    print('')
                    return response.json()
                    break
                except Exception as e:
                    print(e)

    # Read
    ## Shop
    def query_shop(self, client):
        print("Fetching shop data...")
        query = '''
                {
                    shop{
                        name
                    }
                }
                '''

        response = client.post(f'https://{self.store_name}.myshopify.com/admin/api/{self.api_version}/graphql.json',
                               json={"query": query})
        print(response)
        print(response.json())
        print('')

    ## Products
    def query_products(self, client, ):
        print("Fetching product data...")
        query = '''
                {
                    products(first: 3) {
                        edges {
                            node {
                                id
                                title
                            }
                        }
                    }
                }
                '''

        response = client.post(f'https://{self.store_name}.myshopify.com/admin/api/{self.api_version}/graphql.json',
                               json={"query": query})
        print(response)
        print(response.json())
        print('')

    def get_products_id_by_handle(self, client, handles):
        print('Getting product id...')
        f_handles = ','.join(handles)
        query = '''
            query(
                $query: String
            )
            {
                products(first: 250, query: $query) {
                    edges {
                        node {
                            handle
                            id
                        }
                    }
                    pageInfo {
                        endCursor
                        hasNextPage
                    }
                }
            }
        '''
        variables = {'query': "handle:{}".format(f_handles)}
        response = client.post(f'https://{self.store_name}.myshopify.com/admin/api/{self.api_version}/graphql.json',
                               json={"query": query, 'variables':variables})
        print(response)
        print(response.json())
        print('')

        return response.json()

    def get_variants_id_by_query(self, client, variables):
        print('Getting product id...')
        query = '''
            query(
                $query: String
            )
            {
                productVariants(first: 250, query: $query) {
                    edges {
                        node {
                            product {
                                id
                            }
                            id
                            inventoryItem{
                                id
                            }
                        }
                    }
                    pageInfo {
                        endCursor
                        hasNextPage
                    }
                }
            }
        '''
        response = client.post(f'https://{self.store_name}.myshopify.com/admin/api/{self.api_version}/graphql.json',
                               json={"query": query, 'variables':variables})
        print(response)
        print(response.json())
        print('')

        return response.json()

    def get_products_id_by_sku(self, client, skus):
        print('Getting product id...')
        query = '''
            query(
                $query: String
            )
            {
                products(first: 250, query: $query) {
                    edges {
                        node {
                            handle
                            id
                        }
                    }
                    pageInfo {
                        endCursor
                        hasNextPage
                    }
                }
            }
        '''
        variables = {'query': "sku:{}".format(skus)}
        response = client.post(f'https://{self.store_name}.myshopify.com/admin/api/{self.api_version}/graphql.json',
                               json={"query": query, 'variables':variables})
        print(response)
        print(response.json())
        print('')

        return response.json()

    def get_products_id_by_query(self, client, variables):
        print('Getting product id...')
        query = '''
            query(
                $query: String
            )
            {
                products(first: 250, query: $query) {
                    edges {
                        node {
                            handle
                            id
                            publishedAt
                        }
                    }
                    pageInfo {
                        endCursor
                        hasNextPage
                    }
                }
            }
        '''
        response = client.post(f'https://{self.store_name}.myshopify.com/admin/api/{self.api_version}/graphql.json',
                               json={"query": query, 'variables':variables})
        print(response)
        print(response.json())
        print('')

        return response.json()

    def get_product_details_by_query(self, client, variables):
        print('Getting product id...')
        query = '''
            query(
                $query: String
            )
            {
                products(first: 1, query: $query){
                    edges{
                        node{
                            description
                            title
                            totalInventory
                            variants(first: 10){
                                edges{
                                    node{
                                        availableForSale
                                        barcode
                                        compareAtPrice
                                        displayName
                                        inventoryItem{
                                            measurement{
                                                weight{
                                                    unit
                                                    value
                                                }
                                            }
                                            requiresShipping
                                        }
                                        inventoryQuantity
                                        price
                                        selectedOptions{
                                            name
                                            optionValue{
                                                name
                                                swatch{
                                                    color
                                                }
                                            }
                                        }
                                        sku
                                    }
                                }
                            }
                            variantsCount{
                                count
                                precision
                            }
                            vendor
                        }
                    }
                    pageInfo {
                        endCursor
                        hasNextPage
                    }
                }
            }
        '''

        response = self.send_request(client, query=query, variables=variables)

        return response

    def get_variants(self, client, sku):
        print("Getting variant...")
        query = '''
                query getVariantsBySKU($query:String!){
                    productVariants(first:250, query:$query) {
                        edges {
                            node {
                                id
                                }
                            }
                        }
                    }
                '''

        variables = {'query': "sku:{}".format(sku)}

        retries = 0
        while retries < 3:
            response = client.post(f'https://{self.store_name}.myshopify.com/admin/api/{self.api_version}/graphql.json',
                                   json={'query': query, 'variables': variables})
            try:
                result = response.json()
                print(result)
                break
            except Exception as e:
                print(e)
                retries += 1
                sleep(1)
                continue

        return result['data']['productVariants']['edges'][0]['node']['id']

    def query_product_by_handle(self, client, handle):
        # print(handle)
        print("Fetching product data by handle...")
        query = '''
                        query getProductDetailByHandle($handle:String!){
                            productByHandle(handle: $handle) {
                                id
                                status
                                publishedAt
                                resourcePublicationOnCurrentPublication{
                                    isPublished
                                    publishDate
                                }
                            }
                        }
                        '''

        variables = {'handle': "{}".format(handle)}

        response = client.post(
            f'https://{self.store_name}.myshopify.com/admin/api/2023-07/graphql.json',
            json={'query': query, 'variables': variables})

        print(response)
        print(response.json())
        print('')

        return response.json()

    ## Locations
    def query_locations(self, client):
        print("Fetching product data...")
        query = '''
                {
                    locations(first: 3) {
                        edges {
                            node {
                                id
                            }
                        }
                    }
                }
                '''

        response = client.post(f'https://{self.store_name}.myshopify.com/admin/api/{self.api_version}/graphql.json',
                               json={"query": query})
        print(response)
        print(response.json())
        print('')

        return response.json()

    ## Inventories
    def query_inventories(self):
        print('Getting inventories...', end='')
        query = '''
            query inventoryItems {
                inventoryItems(first: 250) {
                    edges {
                        node {
                            id
                            tracked
                            sku
                        }
                    }
                }
            }
        '''
        response = client.post(f'https://{self.store_name}.myshopify.com/admin/api/{self.api_version}/graphql.json',
                               json={"query": query})
        print(response)
        print(response.json())
        print('')

        return response.json()

    ## Publication
    def get_publications(self, client):
        print('Getting publications list...')
        query = '''
        query {
            publications(first: 10){
                edges{
                    node{
                        id
                        name
                    }
                }
            }
        }
        '''

        response = client.post(f'https://{self.store_name}.myshopify.com/admin/api/{self.api_version}/graphql.json',
                               json={"query": query})
        print(response)
        print(response.json())
        print('')

    ## Collections
    def get_collections(self, client, cursor=None):
        print('Getting collection list...')
        if cursor:
            query = '''
                    query getAllCollection($after: String){
                        collections(first: 250, after: $after){
                            nodes{
                                  handle
                                  id
                                  title
                            }
                            pageInfo{
                                     endCursor
                                     hasNextPage
                            }

                        }
                    }
            '''
        else:
            query = '''
                    query {
                        collections(first: 250){
                            nodes{
                                  handle
                                  id
                                  title
                            }
                            pageInfo{
                                     endCursor
                                     hasNextPage
                            }

                        }
                    }
            '''
        variables = {'after': cursor}

        response = client.post(f'https://{self.store_name}.myshopify.com/admin/api/{self.api_version}/graphql.json',
                               json={"query": query, "variables": variables})
        print(response)
        print(response.json())
        print('')

        return response.json()

    ## Files
    def get_file(self, client, created_at, updated_at, after, media_type="Not defined"):
        print("Fetching file data...")
        if media_type in ('IMAGE', 'VIDEO', 'GenericFile'):
            if after == '':
                if media_type == 'IMAGE':
                    query = '''
                            query getFilesByCreatedAt($query:String!){
                                files(first:250, query:$query) {
                                    edges {
                                        node {
                                            id
                                            preview{
                                                image{
                                                    altText
                                                    url
                                                }
                                            }
                                            fileStatus
                                        }
                                    }
                                    pageInfo{
                                        hasNextPage
                                        endCursor
                                    }
                                }
                            }
                            '''
                elif media_type == 'VIDEO':
                    query = '''
                        query getFilesByCreatedAt($query:String!){
                            files(first:250, query:$query) {
                                edges {
                                    node {
                                        id
                                        ... on Video {
                                            sources{
                                                url
                                            }
                                        }
                                        alt
                                        fileStatus
                                    }
                                }
                                pageInfo{
                                    hasNextPage
                                    endCursor
                                }
                            }
                        }
                    '''
                elif media_type == 'GenericFile':
                    query = '''
                        query getFilesByCreatedAt($query:String!){
                            files(first:250, query:$query) {
                                edges {
                                    node {
                                        id
                                        ... on GenericFile {
                                            url
                                        }
                                        alt
                                        fileStatus
                                    }
                                }
                                pageInfo{
                                    hasNextPage
                                    endCursor
                                }
                            }
                        }
                    '''

                # variables = {'query': "(created_at:>={}) AND (updated_at:<={})".format(created_at, updated_at)}
                variables = {'query': "(created_at:>={}) AND (media_type:{})".format(created_at, media_type)}

            else:
                if media_type == "IMAGE":
                    query = '''
                    query getFilesByCreatedAt($query:String!, $after:String!){
                        files(first:250, after:$after, query:$query) {
                            edges {
                                node {
                                    id
                                    preview{
                                        image{
                                            altText
                                            url
                                        }
                                    }
                                    fileStatus
                                }
                            }
                            pageInfo{
                                hasNextPage
                                endCursor
                            }
                        }
                    }
                    '''
                elif media_type == 'VIDEO':
                    query = '''
                    query getFilesByCreatedAt($query:String!, $after:String!){
                        files(first:250, after:$after, query:$query) {
                            edges {
                                node {
                                    id
                                    ... on Video {
                                        altText
                                        url
                                    }
                                    fileStatus
                                }
                            }
                            pageInfo{
                                hasNextPage
                                endCursor
                            }
                        }
                    }
                    '''
                elif media_type == 'GenericFile':
                    query = '''
                    query getFilesByCreatedAt($query:String!, $after:String!){
                        files(first:250, after:$after, query:$query) {
                            edges {
                                node {
                                    id
                                    ... on GenericFile {
                                        url
                                    }
                                    alt
                                    fileStatus
                                }
                            }
                            pageInfo{
                                hasNextPage
                                endCursor
                            }
                        }
                    }
                    '''

                # variables = {'query': "(created_at:>={}) AND (updated_at:<={})".format(created_at, updated_at),
                #              'after': after}
                variables = {'query': "(created_at:>={} AND (media_type:{}))".format(created_at, media_type),
                             'after': after}
            retries = 0
            while retries < 3:
                response = client.post(f'https://{self.store_name}.myshopify.com/admin/api/{self.api_version}/graphql.json',
                                       json={'query': query, 'variables': variables})
                try:
                    result = response.json()
                    break
                except Exception:
                    retries += 1
                    sleep(1)
                    continue

            return result
        else:
            print('File Type is Invalid')

    def bulk_get_file(self):
        # print("Getting bulk file...")
        # mutation = """
        # mutation bulkOperationRunQuery($query: String!) {
        #     bulkOperationRunQuery(query: $query) {
        #         bulkOperation {
        #             # BulkOperation fields
        #             }
        #         userErrors {
        #             field
        #             message
        #         }
        #     }
        # }
        # """
        #
        # response = client.post(f'https://{self.store_name}.myshopify.com/admin/api/{self.api_version}/graphql.json',
        #                        json={'query': mutation, 'variables': variables})
        pass

    ## Access Scopes
    def check_access_scopes(self, client):
        print("Checking access scopes...")
        query = '''
            query {
                appInstallation {
                    accessScopes {
                        handle
                        description
                    }
                }
            }
        '''

        response = client.post(f'https://{self.store_name}.myshopify.com/admin/api/2023-07/graphql.json',
                               json={"query": query})
        print(response)
        print(response.json())
        print('')
        print("Access scopes collected!")

    ## Metafields
    def get_metafields(self, client):
        query = '''
            query {
                metafieldDefinitions(first: 250, ownerType: PRODUCT) {
                    edges {
                        node {
                            id
                            name
                        }
                    }
                }
            }
        '''

        response = client.post(
            f'https://{self.store_name}.myshopify.com/admin/api/2023-07/graphql.json',
            json={'query': query})

        print(response)
        print(response.json())
        print('')

        return response.json()

    ## Order
    def get_orders(self, client, order_number):
        query = '''
                query getOrders($query:String!){
                    orders(first:250, query:$query) {
                        edges {
                            node {
                                name
                                lineItems(first: 250){
                                    edges{
                                        node{
                                            name
                                            currentQuantity
                                            originalUnitPriceSet{
                                                shopMoney{
                                                    amount
                                                    currencyCode
                                                }
                                            }
                                        }
                                    }
                                }
                                currentSubtotalLineItemsQuantity
                                currentSubtotalPriceSet{
                                    shopMoney{
                                        amount
                                        currencyCode
                                    }
                                }
                                currentTotalWeight
                                paymentGatewayNames
                                shippingLines(first: 250){
                                    edges{
                                        node{
                                            title
                                            currentDiscountedPriceSet{
                                                shopMoney{
                                                    amount
                                                    currencyCode
                                                }
                                            }
                                        }
                                    }
                                }
                                fulfillments(first:250){
                                    name
                                    createdAt
                                    deliveredAt
                                    inTransitAt
                                    estimatedDeliveryAt
                                    displayStatus
                                    trackingInfo(first:250){
                                        company
                                        number
                                        url
                                    }
                                }
                                displayFinancialStatus
                                returnStatus
                                cancellation{
                                    staffNote
                                }
                                cancelReason
                                currentTotalWeight
                                cancelledAt
                                createdAt
                                closedAt
                            }
                        }
                    }
                }
                '''

        variables = {'query': "name:{}".format(order_number)}

        response = self.send_request(client, query=query, variables=variables)

        return response

    ## Tracking Link
    def get_tracking_link(self, client, order_number):
        query = '''
                query getOrders($query:String!){
                    orders(first:250, query:$query) {
                        edges {
                            node {
                                fulfillments(first:250){
                                    trackingInfo(first:250){
                                        url
                                    }
                                }
                            }
                        }
                    }
                }
                '''

        variables = {'query': "name:{}".format(order_number)}

        response = self.send_request(client, query=query, variables=variables)

        return response

    ## Online Store Url
    def get_online_store_url(self, client, item_number):
        query = '''
                query getProducts($query:String!){
                    products(first:250, query:$query) {
                        edges {
                            node {
                                onlineStoreUrl
                            }
                        }
                    }
                }
                '''

        variables = {'query': "sku:{}".format(item_number)}

        response = self.send_request(client, query=query, variables=variables)

        return response

    # Update
    ## Product
    def update_product(self, client, handle, tags):
        id = self.query_product_by_handle(client, handle=handle)
        mutation = '''
        mutation productUpdate($input: ProductInput!) {
                             productUpdate(input: $input)
                             {
                                userErrors {
                                            field
                                            message
                                }
                             }
        }
        '''
        variables = {
            "input": {
                "id": id,
                "tags": tags
            }
        }

        while 1:
            try:
                response = client.post(f'https://{self.store_name}.myshopify.com/admin/api/{self.api_version}/graphql.json',
                                       json={'query': mutation, 'variables': variables})
                print(response)
                print(response.json())
                print('')
                break
            except Exception as e:
                print(e)

    def update_products(self, client, staged_target):
        print('Updating products...')
        mutation = '''
            mutation ($stagedUploadPath: String!){
                bulkOperationRunMutation(
                    mutation: "mutation call($input: ProductInput!, $media: [CreateMediaInput!]) {
                        productUpdate(input: $input, media: $media) {
                            product {
                                id
                                title
                                variants(first: 10) {
                                    edges {
                                        node {
                                            id
                                            title
                                            inventoryQuantity
                                        }
                                    }
                                }
                            }
                            userErrors {
                                message
                                field
                            }
                        }
                    }",
                    stagedUploadPath: $stagedUploadPath
                )   {
                        bulkOperation {
                            id
                            url
                            status
                        }
                        userErrors {
                            message
                            field
                        }
                    }
            }
        '''

        variables = {
            "stagedUploadPath": staged_target['data']['stagedUploadsCreate']['stagedTargets'][0]['parameters'][3]['value']
        }

        response = client.post(f'https://{self.store_name}.myshopify.com/admin/api/{self.api_version}/graphql.json',
                               json={"query": mutation, "variables": variables})

        print(response)
        print(response.json())
        print('')

    def update_variants(self, client, staged_target):
        print('Creating products...')
        mutation = '''
            mutation ($stagedUploadPath: String!){
                bulkOperationRunMutation(
                    mutation: "mutation call($allowPartialUpdates: Boolean, $productId: ID!, $variants: [ProductVariantsBulkInput!]!) {
                        productVariantsBulkUpdate(allowPartialUpdates: $allowPartialUpdates, productId: $productId, variants: $variants) {
                            product {
                                id
                                title
                                variants(first: 10) {
                                    edges {
                                        node {
                                            id
                                            title
                                            inventoryQuantity
                                        }
                                    }
                                }
                            }
                            userErrors {
                                message
                                field
                            }
                        }
                    }",
                    stagedUploadPath: $stagedUploadPath
                )   {
                        bulkOperation {
                            id
                            url
                            status
                        }
                        userErrors {
                            message
                            field
                        }
                    }
            }
        '''

        variables = {
            "stagedUploadPath": staged_target['data']['stagedUploadsCreate']['stagedTargets'][0]['parameters'][3]['value']
        }

        response = client.post(f'https://{self.store_name}.myshopify.com/admin/api/{self.api_version}/graphql.json',
                               json={"query": mutation, "variables": variables})

        print(response)
        print(response.json())
        print('')

    def update_inventories(self, client, quantities):
        mutation = '''
        mutation inventorySetQuantities($input: InventorySetQuantitiesInput!) {
                             inventorySetQuantities(input: $input)
                             {
                                userErrors {
                                            field
                                            message
                                }
                             }
        }
        '''

        variables = {
            "input": {
                "ignoreCompareQuantity": True,
                "name": "available",
                "quantities": quantities,
                "reason": "correction"
            }
        }

        while 1:
            try:
                response = client.post(f'https://{self.store_name}.myshopify.com/admin/api/{self.api_version}/graphql.json',
                                       json={'query': mutation, 'variables': variables})
                print(response)
                print(response.json())
                print('')
                break
            except Exception as e:
                print(e)

    ## Collections
    def publish_collection(self, client):
        print('Publishing collection...')
        mutation = '''
        mutation {
            collectionPublish(
                input: {
                    id: "",
                    collectionPublications: {
                        publicationId: "gid://shopify/Publication/178396725562"
                        }
                    }
                )
            )
            {
                collectionPublications{
                    publishDate
                }
                userErrors{
                    field
                    message
            }
        }
        '''

        response = client.post(f'https://{self.store_name}.myshopify.com/admin/api/{self.api_version}/graphql.json',
                               json={"query": mutation})
        print(response)
        print(response.json())
        print('')

    ## Files
    def edit_file(self, client, file_id, file_name, altText):
        print("Update filename...")
        extention = '.' + altText.rsplit('.', 1)[-1]
        mutation = '''
                mutation fileUpdate($files:[FileUpdateInput!]!)
                {
                    fileUpdate(files: $files) {
                        files {
                            id
                        }
                        userErrors {
                            field
                            message
                        }
                    }
                }
                '''

        variables = {
            'files': [
                {
                    'id': file_id,
                    'filename': file_name + extention
                }
            ]
        }

        print(variables)
        while 1:
            try:
                response = client.post(f'https://{self.store_name}.myshopify.com/admin/api/{self.api_version}/graphql.json',
                                       json={'query': mutation, 'variables': variables})
                print(response)
                print(response.json())
                print('')
                break
            except Exception as e:
                print(e)

    ## Publication
    def publish_unpublish(self, client, staged_target):
        print('Publishing products...')
        mutation = '''
            mutation ($stagedUploadPath: String!){
                bulkOperationRunMutation(
                    mutation: "mutation call($id: ID!, $input: [PublicationInput!]!) {
                        publishablePublish(id: $id, input: $input) {
                            publishable {
                                availablePublicationsCount {
                                    count
                                }
                                resourcePublicationsCount {
                                    count
                                }
                            }
                            shop {
                                publicationCount
                            }
                            userErrors {
                                message
                                field
                            }
                        }
                    }",
                    stagedUploadPath: $stagedUploadPath
                )   {
                        bulkOperation {
                            id
                            url
                            status
                        }
                        userErrors {
                            message
                            field
                        }
                    }
            }
        '''

        variables = {
            "stagedUploadPath": staged_target['data']['stagedUploadsCreate']['stagedTargets'][0]['parameters'][3]['value']
        }

        response = client.post(f'https://{self.store_name}.myshopify.com/admin/api/{self.api_version}/graphql.json',
                               json={"query": mutation, "variables": variables})

        print(response)
        print(response.json())
        print('')

    def remove_scheduled_publish_date_updated(self, client, product_id, publication_id=None):
        print(f'Removing scheduled publish date for product {product_id}...')
        mutation = '''
        mutation productPublishOnPublication($id: ID!, $input: ProductPublishInput!) {
            productPublishOnPublication(id: $id, input: $input) {
                product {
                    id
                    title
                    publishedAt
                    resourcePublicationOnCurrentPublication {
                        publishDate
                    }
                }
                userErrors {
                    field
                    message
                }
            }
        }
        '''
        variables = {
            "id": product_id,
            "input": {
                "publicationId": publication_id,
                "publishDate": None
            }
        }

        response = client.post(f'https://{self.store_name}.myshopify.com/admin/api/{self.api_version}/graphql.json',
                               json={"query": mutation, "variables": variables})

        result = response.json()
        print(json.dumps(result, indent=2))

        if 'errors' in result:
            print(f"Error: {result['errors']}")
            return None

        updated_product = result['data']['productPublishOnPublication']['product']
        if updated_product['resourcePublicationOnCurrentPublication']['publishDate'] is None:
            print(f"Successfully removed scheduled publish date for product {updated_product['title']}")
        else:
            print(f"Failed to remove scheduled publish date for product {updated_product['title']}")

        return updated_product

    # Bulk operation support
    ## Stage Upload
    ### Products
    def generate_staged_target(self, client):
        print("Creating stage upload...")
        mutation = '''
                    mutation {
                        stagedUploadsCreate(
                            input:{
                                resource: BULK_MUTATION_VARIABLES,
                                filename: "bulk_op_vars.jsonl",
                                mimeType: "text/jsonl",
                                httpMethod: POST
                            }
                        )
                        {
                            userErrors{
                                field,
                                message
                            }
                            stagedTargets{
                                url,
                                resourceUrl,
                                parameters {
                                    name,
                                    value
                                }
                            }
                        }
                    }
                    '''

        response = client.post(f'https://{self.store_name}.myshopify.com/admin/api/{self.api_version}/graphql.json',
                               json={"query": mutation})
        print(response)
        print(response.json())
        print('')
        return response.json()

    def generate_staged_target_video(self, client, video_json):
        print('Creating stage upload...')
        mutation = """
            mutation generateStagedUploads ($input: [StagedUploadInput!]!){
                stagedUploadsCreate(input: $input){
                    stagedTargets {
                        url
                        resourceUrl
                        parameters {
                            name
                            value
                        }
                    }
                    userErrors {
                      field
                      message
                    }
                }
            }
        """

        # Variables to pass to the query
        variables = {
            "input": video_json
        }

        response = client.post(f'https://{self.store_name}.myshopify.com/admin/api/{self.api_version}/graphql.json',
                               json={"query": mutation, "variables": variables})
        print(response)
        print(response.json())
        print('')
        return response.json()

    def csv_to_jsonl(self, csv_filename, jsonl_filename):
        print("Converting csv to jsonl file...")
        df = pd.read_csv(csv_filename, nrows=2)

        # Create formatted dictionary
        datas = []
        for index in df.index:
            data_dict = {"input": dict(), "media": dict()}
            data_dict['input']['handle'] = df.iloc[index]['Handle']
            data_dict['input']['title'] = df.iloc[index]['Title']
            data_dict['input']['descriptionHtml'] = df.iloc[index]['Body (HTML)']
            data_dict['input']['vendor'] = df.iloc[index]['Vendor']
            data_dict['input']['productCategory'] = df.iloc[index]['Product Category']
            data_dict['input']['productType'] = df.iloc[index]['Type']
            data_dict['input']['tags'] = df.iloc[index]['Tags']
            data_dict['input']['options'] = [df.iloc[index]['Option1 Name'],
                                             df.iloc[index]['Option2 Name'],
                                             df.iloc[index]['Option3 Name']
                                             ]

            # Convert symbol to unit
            if df.iloc[index]['Variant Weight Unit'] == "g":
                df.loc[index, 'Variant Weight Unit'] = "GRAMS"
            elif df.iloc[index]['Variant Weight Unit'] == "kg":
                df.loc[index, 'Variant Weight Unit'] = "KILOGRAMS"
            elif df.iloc[index]['Variant Weight Unit'] == "lb":
                df.loc[index, 'Variant Weight Unit'] = "POUNDS"

            # Variant Attributes
            data_dict['input']['variants'] = [
                {
                    'sku': df.iloc[index]['Variant SKU'],
                    'options': [
                        df.iloc[index]['Option1 Value'],
                        df.iloc[index]['Option2 Value'],
                        df.iloc[index]['Option3 Value']
                    ],
                    'weight': int(df.iloc[index]['Variant Grams']),
                    'weightUnit': df.iloc[index]['Variant Weight Unit'],
                    'inventoryManagement': df.iloc[index]['Variant Inventory Tracker'].upper(),
                    'inventoryPolicy': df.iloc[index]['Variant Inventory Policy'].upper(),
                    'price': str(df.iloc[index]['Variant Price']),
                    'compareAtPrice': str(df.iloc[index]['Variant Compare At Price']),
                    'requiresShipping': bool(df.iloc[index]['Variant Requires Shipping']),
                    'taxable': bool(df.iloc[index]['Variant Taxable']),
                    'imageSrc': f"https:{df.iloc[index]['Image Src']}",
                    'title': 'Default'
                }
            ]

            data_dict['input']['giftCard'] = bool(df.iloc[index]['Gift Card'])
            data_dict['input']['status'] = df.iloc[index]['Status'].upper()
            data_dict['media'] = {'originalSource': f"https:{df.iloc[index]['Image Src']}", 'mediaContentType': 'IMAGE'}

            datas.append(data_dict.copy())
        print(datas)
        with open(os.path.join(jsonl_filename), 'w') as jsonlfile:
            for item in datas:
                json.dump(item, jsonlfile)
                jsonlfile.write('\n')

    def get_remote_file_size(self, url):
        print(f'Getting file size of ({url}) ...')
        try:
            with httpx.Client() as client:
                response = client.head(url)
                if response.status_code == 200:
                    file_size = response.headers.get('Content-Length')
                    if file_size:
                        return str(file_size)
                    else:
                        print(f"Content-Length header not found for {url}")
                        return "0"  # Default value if Content-Length is missing
                else:
                    print(f"Failed to fetch file size for {url}. Status code: {response.status_code}")
                    return "0"  # Default value if the request fails
        except Exception as e:
            print(f"Error fetching file size for {url}: {e}")
            return "0"  # Default value if an exception occurs

    def video_to_json(self, df):
        print('Converting video df to json...')
        converted_df = df[['filename', 'file_type', 'actual_video_links']].copy()
        converted_df['mimeType'] = "video/mp4"
        converted_df.rename(columns={'file_type': 'resource'}, inplace=True)
        converted_df['httpMethod'] = 'POST'
        converted_df['fileSize'] = converted_df['actual_video_links'].apply(lambda x: self.get_remote_file_size(x))
        converted_df.drop(columns='actual_video_links', inplace=True)
        result = converted_df.to_json(orient="records")

        return result

    def doc_to_json(self, df):
        print('Converting doc df to json...')
        converted_df = df[['filename', 'file_type', 'actual_doc_links']].copy()
        converted_df['mimeType'] = "application/pdf"
        converted_df.rename(columns={'file_type': 'resource'}, inplace=True)
        converted_df['httpMethod'] = 'POST'
        converted_df['fileSize'] = converted_df['actual_doc_links'].apply(lambda x: self.get_remote_file_size(x))
        converted_df.drop(columns='actual_doc_links', inplace=True)
        result = converted_df.to_json(orient="records")

        return result

    def download_file(self, url, save_path):
        try:
            with httpx.Client() as client:
                response = client.get(url)
                response.raise_for_status()
                with open(save_path, "wb") as file:
                    file.write(response.content)
            print(f"File downloaded successfully to {save_path}")
        except Exception as e:
            print(f"Failed to download file: {e}")

    def read_staged_target_files(self, directory):
        pattern = os.path.join(directory, "staged_target_*.json")
        matching_files = glob(pattern)

        # Sort files by sequence number
        def extract_sequence_number(file_path):
            match = re.search(r"staged_target_(\d+)\.json", os.path.basename(file_path))
            if match:
                return int(match.group(1))
            return -1

        matching_files.sort(key=extract_sequence_number)

        data_list = []
        for file_path in matching_files:
            try:
                with open(file_path, "r") as file:
                    json_data = json.load(file)
                    stagedTargets = json_data['data']['stagedUploadsCreate']['stagedTargets']
                    for target in stagedTargets:
                        parameters = target['parameters']
                        data = {}
                        data['uploadUrl'] = target['url']
                        data['resourceUrl'] = target['resourceUrl']
                        for i in range(len(parameters)):
                            data[parameters[i]['name']] = parameters[i]['value']
                        data_list.append(data)
                    print(f"Successfully read {file_path}")
            except Exception as e:
                print(f"Failed to read {file_path}: {e}")

        return data_list

    def upload_video_file(self, GoogleAccessId, key, policy, signature, file_path, upload_url):
        print("Uploading video file to staged path...")

        form_data = {
            "GoogleAccessId": GoogleAccessId,
            "key": key,
            "policy": policy,
            "signature": signature,
        }

        try:
            with open(file_path, "rb") as file:
                files = {"file": file}
                with httpx.Client() as client:
                    response = client.post(upload_url, data=form_data, files=files)
                    response.raise_for_status()
                    print("File uploaded successfully")
                    print("Response:", response.content)
        except Exception as e:
            print(f"Failed to upload file: {e}")
            raise

    def upload_doc_file(self, contentType, successActionStatus, acl, key, xGoogDate, xGoogCred, xGoogAlgo, xGoogSign, policy, file_path, upload_url):
        print("Uploading document file to staged path...")

        form_data = {
            "Content-Type": contentType,
            "success_action_status": successActionStatus,
            "acl": acl,
            "key": key,
            "x-goog-date": xGoogDate,
            "x-goog-credential": xGoogCred,
            "x-goog-algorithm": xGoogAlgo,
            "x-goog-signature": xGoogSign,
            "policy": policy,
        }

        try:
            with open(file_path, "rb") as file:
                files = {"file": file}
                with httpx.Client() as client:
                    response = client.post(upload_url, data=form_data, files=files)
                    response.raise_for_status()
                    print("File uploaded successfully")
                    print("Response:", response.content)
        except Exception as e:
            print(f"Failed to upload file: {e}")

    def upload_jsonl(self, staged_target, jsonl_path):
        print("Uploading jsonl file to staged path...")
        url = staged_target['data']['stagedUploadsCreate']['stagedTargets'][0]['url']
        parameters = staged_target['data']['stagedUploadsCreate']['stagedTargets'][0]['parameters']
        files = dict()
        for parameter in parameters:
            files[f"{parameter['name']}"] = (None, parameter['value'])
        files['file'] = open(jsonl_path, 'rb')

        # with httpx.Client(timeout=None, follow_redirects=True) as sess:
        response = httpx.post(url, files=files)

        print(response)
        print(response.content)
        print('')

    def webhook_subscription(self, client):
        print("Subscribing webhook...")
        mutation = '''
                    mutation {
                        webhookSubscriptionCreate(
                            topic: BULK_OPERATIONS_FINISH
                            webhookSubscription: {
                                format: JSON,
                                callbackUrl: "https://12345.ngrok.io/"
                                }
                        )
                        {
                            userErrors {
                                field
                                message
                            }
                            webhookSubscription {
                                id
                            }
                        }
                    }
        '''

        response = client.post(f'https://{self.store_name}.myshopify.com/admin/api/{self.api_version}/graphql.json',
                               json={"query": mutation})
        print(response)
        print(response.json())
        print('')

    def pool_operation_status(self, client):
        print("Pooling operation status...")
        query = '''
                    query {
                        currentBulkOperation(type: MUTATION) {
                            id
                            status
                            errorCode
                            createdAt
                            completedAt
                            objectCount
                            fileSize
                            url
                            partialDataUrl
                        }
                    }
                '''

        response = client.post(f'https://{self.store_name}.myshopify.com/admin/api/{self.api_version}/graphql.json',
                               json={"query": query})
        print(response)
        print(response.json())
        print('')

        return response.json()

    def import_bulk_data(self, client, csv_filename, jsonl_filename):
        self.csv_to_jsonl(csv_filename=csv_filename, jsonl_filename=jsonl_filename)
        staged_target = self.generate_staged_target(client)
        self.upload_jsonl(staged_target=staged_target, jsonl_path=jsonl_filename)
        self.create_products(client, staged_target=staged_target)

    def import_bulk_video(self, client, video_df):
        # Generate Stage Target
        video_json = self.video_to_json(video_df)
        video_json_list = json.loads(video_json)
        chunked_video_json = [video_json_list[i:i + 10] for i in range(0, len(video_json_list), 10)]
        for i, json_video in enumerate(chunked_video_json):
            staged_target = self.generate_staged_target_video(client, json_video)
            with open(f'data/staged_target_{i}.json', 'w', encoding='utf-8') as file:
                json.dump(staged_target, file)

        # Download Video File to Local
        df = video_df.copy()
        df['save_path'] = df['filename'].apply(lambda x: 'data/downloads/video/' + x)
        df.apply(lambda x: self.download_file(x['actual_video_links'], save_path=x["save_path"]), axis=1)
        df.to_csv('data/downloaded_video.csv', index=False)

        # Upload Video
        df = pd.read_csv('data/downloaded_video.csv')
        staged_target = self.read_staged_target_files('data')
        staged_target_df = pd.DataFrame().from_records(staged_target)
        concated_df = pd.concat([df, staged_target_df], axis=1)
        concated_df.to_csv('data/concated_df.csv', index=False)
        concated_df.apply(lambda x: s.upload_video_file(x['GoogleAccessId'], x['key'], x['policy'], x['signature'], x['save_path'], x['uploadUrl']), axis=1)

    def import_bulk_doc(self, client, doc_df):
        # Generate Stage Target
        doc_df.drop_duplicates('actual_doc_links', inplace=True)
        doc_json = self.doc_to_json(doc_df)
        doc_json_list = json.loads(doc_json)
        chunked_doc_json = [doc_json_list[i:i + 10] for i in range(0, len(doc_json_list), 10)]
        for i, json_doc in enumerate(chunked_doc_json):
            staged_target = self.generate_staged_target_video(client, json_doc)
            with open(f'data/staged_target_{i}.json', 'w', encoding='utf-8') as file:
                json.dump(staged_target, file)

        # Download Document File to Local
        df = doc_df.copy()
        df['save_path'] = df['filename'].apply(lambda x: 'data/downloads/doc/' + x)
        df.apply(lambda x: self.download_file(x['actual_doc_links'], save_path=x["save_path"]), axis=1)
        df.to_csv('data/downloaded_doc.csv', index=False)

        # Upload Video
        df = pd.read_csv('data/downloaded_doc.csv')
        staged_target = self.read_staged_target_files('data')
        staged_target_df = pd.DataFrame().from_records(staged_target)
        concated_df = pd.concat([df, staged_target_df], axis=1)
        concated_df.to_csv('data/concated_doc_df.csv', index=False)
        concated_df.apply(lambda x: s.upload_doc_file(x['Content-Type'], x['success_action_status'], x['acl'], x['key'], x['x-goog-date'], x['x-goog-credential'], x['x-goog-algorithm'], x['x-goog-signature'], x['policy'], x['save_path'], x['uploadUrl']), axis=1)

    def check_bulk_operation_status(self, client, bulk_operation_id):
        query = f'''
            query {{
                node(id: "{bulk_operation_id}") {{
                    ... on BulkOperation {{
                        id
                        status
                    }}
                }}
            }}
        '''

        response = client.post(f'https://{self.store_name}.myshopify.com/admin/api/{self.api_version}/graphql.json',
                               json={"query": query})

        response_data = response.json()
        status = response_data['data']['node']['status']
        return status

    def import_status(self, client):
        # Check Bulk Import status
        print('Checking')
        global s
        response = s.pool_operation_status(client)
        if response['data']['currentBulkOperation']['status'] == 'COMPLETED':
            created = True
        else:
            sleep(10)
            created = False

        return created

    # Delete
    ## File
    def delete_file(self, client, fileIds):
        print('Deleting File...')
        mutation = '''
            mutation fileDelete($input: [ID!]!) {
                fileDelete(fileIds: $input) {
                    deletedFileIds
                }
            }
        '''
        variables = {
            "input": fileIds
        }

        while 1:
            try:
                response = client.post(f'https://{self.store_name}.myshopify.com/admin/api/{self.api_version}/graphql.json',
                                       json={'query': mutation, 'variables': variables})
                print(response)
                print(response.json())
                print('')
                break
            except Exception as e:
                print(e)

    ## Collection
    def delete_collection(self, client, collectionIds):
        print('Deleting File...')
        mutation = '''
            mutation collectionDelete($input: CollectionDeleteInput!) {
                collectionDelete(input: $input) {
                    deletedCollectionId
                    shop {
                        id
                        name
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
                "id": collectionIds
            }
        }

        while 1:
            try:
                response = client.post(f'https://{self.store_name}.myshopify.com/admin/api/{self.api_version}/graphql.json',
                                       json={'query': mutation, 'variables': variables})
                print(response)
                print(response.json())
                print('')
                break
            except Exception as e:
                print(e)


if __name__ == '__main__':

    s = ShopifyApp(store_name=os.getenv('TRENDTIME_STORE_NAME'), access_token=os.getenv('TRENDTIME_ACCESS_TOKEN'), api_version='2025-01')
    client = s.create_session()

    # handles = ['38-exit-ez-fx-kit', 'rest-in-peace-cross-tombstone']
    # response = s.get_products_id_by_handle(client, handles=handles)
    # print(response)
    # s.get_metafields(client)

    # activate product
    # has_next_page = True
    # while has_next_page:
    #     variables = {'query': "status:{}".format('DRAFT')}
    #     response = s.get_products_id_by_query(client=client, variables=variables)
    #     has_next_page = response['data']['products']['pageInfo']['hasNextPage']
    #     datas = response['data']['products']['edges']
    #     records = [data['node'] for data in datas]
    #     df = pd.DataFrame.from_records(records)
    #     df.to_csv('data/draft_products_id.csv', index=False)
    #     csv_to_jsonl(csv_filename='data/draft_products_id.csv', jsonl_filename='bulk_op_vars.jsonl', mode='ap')
    #     staged_target = s.generate_staged_target(client)
    #     s.upload_jsonl(staged_target=staged_target, jsonl_path="bulk_op_vars.jsonl")
    #     s.update_products(client, staged_target=staged_target)
    #     created = False
    #     while not created:
    #         created = s.import_status(client)

    # publish unpublish
    # has_next_page = True
    # while has_next_page:
    #     variables = {'query': "published_status:{} AND status:{}".format('unpublished', 'ACTIVE')}
    #     response = s.get_products_id_by_query(client=client, variables=variables)
    #     has_next_page = response['data']['products']['pageInfo']['hasNextPage']
    #     datas = response['data']['products']['edges']
    #     records = [data['node'] for data in datas]
    #     df = pd.DataFrame.from_records(records)
    #     df.to_csv('data/unpublished_products_id.csv', index=False)
    #     csv_to_jsonl(csv_filename='data/unpublished_products_id.csv', jsonl_filename='bulk_op_vars.jsonl', mode='pp')
    #     staged_target = s.generate_staged_target(client)
    #     s.upload_jsonl(staged_target=staged_target, jsonl_path="bulk_op_vars.jsonl")
    #     s.publish_unpublish(client, staged_target=staged_target)
    #     created = False
    #     while not created:
    #         created = s.import_status(client)

    # s.query_product_by_handle(client, handle='812-8-82')

    # s.remove_scheduled_publish_date_updated(client, 'gid://shopify/Product/7625659777081')

    # s.query_locations(client)
    # path = './Product_By_Category2/*.csv'
    # filenames = glob(path)
    # print(filenames)
    # for filename in filenames:
    #     df = pd.read_csv(filename)
    #     df['product_id'] = df.apply(lambda x: s.query_product_by_handle(client, x['Handle']), axis=1)
    #     df.to_csv(filename, index=False)

    # =================================get all collections==============================
    # has_next_page = True
    # cursor = None
    # results = list()
    # while has_next_page:
    #     response = s.get_collections(client, cursor=cursor)
    #     records = response['data']['collections']['nodes']
    #     results.extend(records)
    #     has_next_page = response['data']['collections']['pageInfo']['hasNextPage']
    #     cursor = response['data']['collections']['pageInfo']['endCursor']
    # results_df = pd.DataFrame.from_records(results)
    # results_df.to_csv('data/existing_collection_list.csv', index=False)

    # ============================ create collections ==================================
    # df = pd.read_csv('data/source_collections.csv')
    # df.loc[:, 'appliedDisjuntively'] = True
    # df.loc[:, 'imageSrc'] = ''
    # df.loc[:, 'title'] = df['name'].apply(lambda x: x.strip())
    # df.loc[:, 'column'] = 'TAG'
    # df.loc[:, 'relation'] = 'EQUALS'

    # df.apply(
    #     lambda x: s.create_collection(
    #         client=client,
    #         descriptionHtml=x['caption'],
    #         image_src=x['imageSrc'],
    #         title=x['title'],
    #         appliedDisjuntively=x['appliedDisjuntively'],
    #         column=x['column'],
    #         relation=x['relation'],
    #         condition=x['title']
    #     ),
    #     axis=1
    # )

    # ==================================================================================

    # df = pd.read_csv('products_update_tag_rev1.csv')
    # df = df[df['Handle'].str.contains('lifting-forklift-frame')]
    # df.apply(lambda x: s.update_product(client=client, handle=x['Handle'], tags=x['Tags']), axis=1)

    # df = pd.read_csv('barcode_feed_5.csv')
    # print(df.columns)
    # df.apply(lambda x: s.update_variants(client=client, sku=x['Variant SKU'], barcode=x['New Barcode']), axis=1)

    # s.check_access_scopes(client)

    # rules = [
    #     {"column": "TITLE", "relation": "CONTAINS", "condition": "Animal"},
    #     {"column": "TITLE", "relation": "CONTAINS", "condition": "Horse"},
    #     {"column": "TITLE", "relation": "CONTAINS", "condition": "Llama"}
    # ]
    # s.create_collection(client,
    #                     descriptionHtml='<p>Animal Ride On Toy Description</p>',
    #                     image_src="https://cdn.shopify.com/s/files/1/2245/9711/products/s-l500_4224ddbe-dd74-4287-8057-3521271e1e6f.jpg?v=1696392199",
    #                     rules=rules, title="Animal Ride On Toy")

    # s.get_variants(client, '294329484754-none-$0-none-$0-')
    # s.update_variants(client=client, sku='294329484754-none-$0-none-$/0-', price='1.00', compareAtPrice='2.00')

    # s.query_shop(client)
    # s.query_product(client)
    # s.create_product(client)
    # s.csv_to_jsonl(csv_filename='result.csv', jsonl_filename='test2.jsonl')
    # staged_target = s.generate_staged_target(client)
    # s.upload_jsonl(staged_target=staged_target, jsonl_path="D:/Naru/shopifyAPI/bulk_op_vars.jsonl")
    # s.create_products(client, staged_target=staged_target)
    # s.import_bulk_data(client=client, csv_filename='result.csv', jsonl_filename='bulk_op_vars.jsonl')
    # s.webhook_subscription(client)
    # s.create_collection(client)
    # s.query_products(client)
    # s.get_publications(client)

    # ============================================get product id by handle===============================
    # collection_df = pd.read_csv('data/collection_list.csv')
    # chunked_handles = get_handles('data/collection_list.csv')
    # product_ids = list()
    # for handles in chunked_handles:
    #     product_ids.extend(s.get_products_id_by_handle(client, handles=handles)['data']['products']['edges'])
    # print(f'count:{len(product_ids)}')
    # extracted_product_ids = [x['node'] for x in product_ids]
    # product_id_handle_df = pd.DataFrame.from_records(extracted_product_ids)
    # product_id_handle_df.to_csv('data/product_as_collection_ids.csv', index=False)

    # ============================================get inventories===============================
    # s.query_inventories()

    # s.query_product_by_handle(client, handle='game-of-thrones-drogon-prop')

    # s.pool_operation_status(client)
    # print(s.check_bulk_operation_status(client, bulk_operation_id='gid://shopify/BulkOperation/3252439023930'))
    # handles = ['rest-in-peace-cross-tombstone-1', 'trick-or-treat-yo-self-makeup-bag', '38-exit-ez-fx-kit-1']
    # f_handles = ','.join(handles)
    # s.get_products_id_by_handle(client, handles=f_handles)

    # ====================================== create files =============================
    ## Images
    # files_data = pd.read_csv('data/description_image_link_rev1.csv')
    # files_data = files_data[pd.notna(files_data['actual_image_links'])]
    # Create File should drop duplicate
    # files_data.drop_duplicates('actual_image_links', inplace=True)
    # files_data.apply(lambda x: s.create_file(client, x['origin_image_links'], x['filename'], x['file_type'], x['actual_image_links']), axis=1)

    ## Videos
    # files_data = pd.read_csv('data/description_video_link_rev1.csv')
    # files_data = files_data[pd.notna(files_data['actual_video_links'])]
    # s.import_bulk_video(client, files_data)

    # files_data = pd.read_csv('data/concated_df.csv')
    # Create File should drop duplicate
    # files_data.drop_duplicates('actual_video_links', inplace=True)
    # files_data.apply(lambda x: s.create_file(client, x['origin_video_links'], x['filename'], x['file_type'], x['resourceUrl']), axis=1)

    ## Document
    # files_data = pd.read_csv('data/description_doc_link_rev1.csv')
    # files_data = files_data[pd.notna(files_data['actual_doc_links']) & files_data['filename'].str.contains('.pdf')]
    # s.import_bulk_doc(client, files_data)

    # files_data = pd.read_csv('data/concated_doc_df.csv')
    # Create File should drop duplicate
    # files_data.drop_duplicates('actual_doc_links', inplace=True)
    # files_data.apply(lambda x: s.create_file(client, x['origin_doc_links'], x['filename'], x['file_type'], x['resourceUrl']), axis=1)

    # =================================== get file ====================================
    ## Image
    # sleep(300)
    # updated_at = '2025-02-25T20:00:00Z'
    # created_at = '2025-03-03T00:00:00Z'
    # after = ''
    # has_next_page = True
    # complete_file_ids = []
    # master_shopify_images = []
    # while has_next_page:
    #     file_data = s.get_file(client, created_at=created_at, updated_at=updated_at, after=after, media_type='IMAGE')
    #     after = file_data['data']['files']['pageInfo']['endCursor']
    #     file_edges = file_data['data']['files']['edges']
    #     parsed_files_data = []
    #     file_ids = []  # For deleting files
    #     for data in file_edges:
    #         if data['node']['preview']['image']:
    #             parsed_file_data = data['node']['preview']['image']
    #             parsed_file_data['status'] = data['node']['fileStatus']
    #         else:
    #             parsed_file_data = {'altText': '', 'url': '', 'status': ''}
    #         file_ids.append(data['node']['id'])  # For deleting files
    #         parsed_files_data.append(parsed_file_data)
    #     master_shopify_images.extend(parsed_files_data)
    #     complete_file_ids.extend(file_ids)  # For deleting files
    #     has_next_page = file_data['data']['files']['pageInfo']['hasNextPage']
    # master_shopify_images_df = pd.DataFrame().from_records(master_shopify_images)
    # master_shopify_images_df.to_csv('data/master_shopify_images_rev2.csv', index=False)

    ## Video
    # updated_at = '2025-02-25T20:00:00Z'
    # created_at = '2025-02-28T00:00:00Z'
    # after = ''
    # has_next_page = True
    # complete_file_ids = []
    # master_shopify_video = []
    # while has_next_page:
    #     file_data = s.get_file(client, created_at=created_at, updated_at=updated_at, after=after, media_type="VIDEO")
    #     after = file_data['data']['files']['pageInfo']['endCursor']
    #     file_edges = file_data['data']['files']['edges']
    #     parsed_files_data = []
    #     file_ids = []  # For deleting files
    #     for data in file_edges:
    #         if data['node']['sources']:
    #             parsed_file_data = data['node']['sources'][0]
    #             parsed_file_data['altText'] = data['node']['alt']
    #             parsed_file_data['status'] = data['node']['fileStatus']
    #         else:
    #             parsed_file_data = {'url': '', 'altText': '', 'status': ''}
    #         file_ids.append(data['node']['id'])  # For deleting files
    #         parsed_files_data.append(parsed_file_data)
    #     master_shopify_video.extend(parsed_files_data)
    #     complete_file_ids.extend(file_ids)  # For deleting files
    #     has_next_page = file_data['data']['files']['pageInfo']['hasNextPage']
    # master_shopify_videos_df = pd.DataFrame().from_records(master_shopify_video)
    # master_shopify_videos_df.to_csv('data/master_shopify_videos_rev1.csv', index=False)

    ## Document
    # updated_at = '2025-02-25T20:00:00Z'
    # created_at = '2025-03-02T00:00:00Z'
    # after = ''
    # has_next_page = True
    # complete_file_ids = []
    # master_shopify_docs = []
    # while has_next_page:
    #     file_data = s.get_file(client, created_at=created_at, updated_at=updated_at, after=after, media_type='GenericFile')
    #     after = file_data['data']['files']['pageInfo']['endCursor']
    #     file_edges = file_data['data']['files']['edges']
    #     parsed_files_data = []
    #     file_ids = []  # For deleting files
    #     for data in file_edges:
    #         if data['node']:
    #             parsed_file_data = {}
    #             parsed_file_data['altText'] = data['node']['alt']
    #             parsed_file_data['url'] = data['node']['url']
    #             parsed_file_data['status'] = data['node']['fileStatus']
    #         else:
    #             parsed_file_data = {'altText': '', 'url': '', 'status': ''}
    #         file_ids.append(data['node']['id'])  # For deleting files
    #         parsed_files_data.append(parsed_file_data)
    #     master_shopify_docs.extend(parsed_files_data)
    #     complete_file_ids.extend(file_ids)  # For deleting files
    #     has_next_page = file_data['data']['files']['pageInfo']['hasNextPage']
    # master_shopify_docs_df = pd.DataFrame().from_records(master_shopify_docs)
    # master_shopify_docs_df.to_csv('master_shopify_docs_rev1.csv', index=False)

    # =================================== delete_file =================================
    # chunked_file_ids = [complete_file_ids[i:i + 50] for i in range(0, len(complete_file_ids), 50)]
    # for ids in chunked_file_ids:
    #     s.delete_file(client, ids)

    # =================================== edit file ==================================
    # print(file_data)
    # file_id = file_data['data']['files']['edges'][0]['node']['id']
    # print(file_id)
    # s.edit_file(client, file_id=file_id)

    # ============================== Generate replacer ===============================
    ## Images
    # master_shopify_images_df = pd.read_csv('data/master_shopify_images_rev2.csv')
    # files_data = files_data.merge(master_shopify_images_df, how='left', left_on='origin_image_links', right_on='altText')
    # files_data.drop(columns='altText', inplace=True)
    # files_data.to_csv('data/description_image_link_replacer.csv', index=False)

    ## Videos
    # master_shopify_videos_df = pd.read_csv('data/master_shopify_videos_rev1.csv')
    # files_data = files_data.merge(master_shopify_videos_df, how='left', left_on='origin_video_links', right_on='altText')
    # files_data.drop(columns='altText', inplace=True)
    # files_data.to_csv('data/description_video_link_replacer.csv', index=False)

    ## Document
    # master_shopify_docs_df = pd.read_csv('master_shopify_docs_rev1.csv')
    # files_data = files_data.merge(master_shopify_docs_df, how='left', left_on='origin_doc_links', right_on='altText')
    # files_data.drop(columns='altText', inplace=True)
    # files_data.to_csv('data/description_doc_link_replacer.csv', index=False)

    # =============================== Delete Collections =============================
    # Deduplicated Collections
    # collections_df = pd.read_csv('data/existing_collection_list.csv')
    # collections_df['clean_title'] = collections_df['title'].apply(lambda x: x.strip())
    # duplicated_collections_df = collections_df[collections_df.duplicated('title')]
    # complete_col_ids = duplicated_collections_df['id'].to_list()
    # # print(complete_col_ids)
    # for col_id in complete_col_ids:
    #     s.delete_collection(client, col_id)

    response = s.get_online_store_url(client, item_number='05-030')
    print(response.json())