import json
import logging
from typing import List
import urllib.parse
import time

import custom_connector_sdk.lambda_handler.requests as requests
import custom_connector_sdk.lambda_handler.responses as responses
import custom_connector_superleap.handlers.validation as validation
import custom_connector_superleap.handlers.superleap as superleap
from custom_connector_sdk.lambda_handler.handlers import RecordHandler
from custom_connector_sdk.connector.fields import WriteOperationType, FieldDataType
from custom_connector_sdk.connector.context import ConnectorContext
from custom_connector_superleap.query.builder import QueryObject, build_query
import custom_connector_superleap.constants as constants

LOGGER = logging.getLogger()
LOGGER.setLevel(logging.INFO)

SUPERLEAP_QUERY_FORMAT = '{}{}/appflow/objects/{}/records/'
# Superleap response keys
RECORDS_KEY = 'records'
NEXT_TOKEN_KEY = 'next_token'
SUCCESS_KEY = 'success'
DATA_KEY = 'data'
ID_KEY = 'id'
ERRORS_KEY = 'errors'

def get_query_body(query_object: QueryObject) -> dict:
    """Build query string and encode special characters."""
    # LOGGER.info(f"Building query string for object: {query_object.entity_identifier}")
    query = build_query(query_object)
    return query

def get_query_connector_response(query_object: QueryObject, connector_context: ConnectorContext) ->\
        superleap.SuperleapResponse:
    """Build query string and make GET request to Superleap"""
    queryBody = get_query_body(query_object)
    # LOGGER.info(f"Encoded query body: {queryBody}")
    
    request_uri = superleap.build_superleap_request_uri(connector_context, SUPERLEAP_QUERY_FORMAT, query_object.entity_identifier)
    # LOGGER.info(f"Request URI: {request_uri}")
    
    https_client = superleap.get_superleap_client(connector_context)
    # LOGGER.info("Making API call to Superleap")

    # make these calls 3 times if it fails with backoff
    retry_count = 0
    while retry_count < 3:
        response = https_client.rest_post(request_uri, post_data=json.dumps(queryBody))
        if response.status_code == 200:
            return response
        retry_count += 1
        LOGGER.info(f"Request failed. Retrying in 1 second... (Attempt {retry_count+1} of 3)")
        time.sleep(1)

    return response

def parse_query_response(json_response: str) -> List[str]:
    """Parse JSON response from Superleap query to a list of records."""
    # LOGGER.info(f"Parsing response: {json_response[:200]}..." if len(json_response) > 200 else json_response)

    try:
        parent_object = json.loads(json_response)
        if parent_object.get(SUCCESS_KEY) is not None and parent_object.get(SUCCESS_KEY) is True:
            if parent_object.get(DATA_KEY) is not None:
                # LOGGER.info("Data key found in response")
                data = parent_object.get(DATA_KEY, {})
                records = data.get(RECORDS_KEY, [])
                if records is None:
                    LOGGER.info("records is None, returning empty list")
                    return []
                # LOGGER.info(f"Found {len(records)} records in response")
                return [json.dumps(record) for record in records]
            else:
                LOGGER.error("No data key found in response")
                return []
        else:
            LOGGER.info("No records found in response")
            return []
    except json.JSONDecodeError as e:
        LOGGER.error(f"Error parsing JSON response: {str(e)}")
        return []

def get_next_page(json_response: str) -> str:
    """Parse JSON response from Superleap query to get the next page token."""
    # LOGGER.info(f"Parsing response to get next page number")
    try:
        parent_object = json.loads(json_response)
        if parent_object.get(SUCCESS_KEY) is not None and parent_object.get(SUCCESS_KEY) is True:
            if parent_object.get(DATA_KEY) is not None:
                # LOGGER.info("Data key found in response")
                data = parent_object.get(DATA_KEY, {})
                next_token = data.get(NEXT_TOKEN_KEY, None)
                # convert it to string and return
                LOGGER.info(f"Found next page token: {next_token}")
                return str(next_token)
            else:
                LOGGER.error("No data key found in response")
                return None
        else:
            LOGGER.info("No records found in response")
            return None
    except json.JSONDecodeError as e:
        LOGGER.error(f"Error parsing JSON response: {str(e)}")
        return None


class SuperleapRecordHandler(RecordHandler):
    """Superleap Record handler."""
    def retrieve_data(self, request: requests.RetrieveDataRequest) -> responses.RetrieveDataResponse:
        LOGGER.info("=== START: retrieve_data ===")
        LOGGER.info(f"Retrieve data request entity: {request.entity_identifier}")
        LOGGER.info(f"Retrieve data selected fields: {request.selected_field_names}")
        LOGGER.info(f"Retrieve data ID field name: {request.id_field_name}")
        LOGGER.info(f"Retrieve data IDs: {request.ids}")
        LOGGER.info("Retrieve data not supported by Superleap, please get in touch with the dev team")

        
        error_details = validation.validate_request_connector_context(request)
        if error_details:
            LOGGER.error('RetrieveData request validation failed with ' + str(error_details))
            return responses.RetrieveDataResponse(is_success=False, error_details=error_details)


        return responses.RetrieveDataResponse(is_success=False,
                                              records=[])

    # Is not implemented right now in Superleap, but can be implemented in the future.
    def write_data(self, request: requests.WriteDataRequest) -> responses.WriteDataResponse:
        LOGGER.info("=== START: write_data ===")
        LOGGER.info(f"Write data request entity: {request.entity_identifier}")
        LOGGER.info(f"Write data operation: {request.operation}")
        LOGGER.info(f"Write data ID field names: {request.id_field_names}")
        LOGGER.info(f"Number of records to write: {len(request.records)}")
        LOGGER.info("Write data not supported by Superleap, please get in touch with the dev team")
        return responses.WriteDataResponse(is_success=False)

    def query_data(self, request: requests.QueryDataRequest) -> responses.QueryDataResponse:
        LOGGER.info("=== START: query_data ===")
        LOGGER.info(f"Query data request entity: {request.entity_identifier}")
        LOGGER.info(f"Query data filter expression: {request.filter_expression}")
        
        error_details = validation.validate_request_connector_context(request)
        if error_details:
            LOGGER.error(f'QueryData request failed with {error_details}')
            return responses.QueryDataResponse(is_success=False, error_details=error_details)
        
        # # Get runtime settings
        # runtime_settings = request.connector_context.connector_runtime_settings or {}
        # enable_dynamic_fields = runtime_settings.get(constants.ENABLE_DYNAMIC_FIELD_UPDATE, False) # By default it should be False.
        # LOGGER.info(f"Enable dynamic field update setting: {enable_dynamic_fields}")

        # # If map_all and dynamic fields enabled, fetch fresh field list
        # if enable_dynamic_fields == True or enable_dynamic_fields == "true":
        #     # Get all current fields from entity definition
        #     LOGGER.info("Fetching all retrievable fields from entity definition")
        #     all_field_names = []
        #     if request.connector_context.entity_definition and request.connector_context.entity_definition.fields:
        #         all_field_names = [field.field_name for field in request.connector_context.entity_definition.fields
        #                            if field.read_properties.is_retrievable]  # Should we also not take in deprecated fields?
        #         LOGGER.info(f"Fetching all {len(all_field_names)} retrievable fields")
        #         selected_fields = all_field_names
        #         # Trying to set request selected_fields as well
        #         request.selected_field_names = all_field_names # maybe this will work if we have map all? Idk
        #         LOGGER.info(f"Request updated to: {request}")
        #     else:
        #         LOGGER.warning("No entity definition or fields found, falling back to selected fields from request")
        #         selected_fields = request.selected_field_names
        # else:
        #     LOGGER.info("Dynamic field update not enabled, using selected fields from request")
        #     selected_fields = request.selected_field_names
        
        # LOGGER.info(f"Final selected fields: {selected_fields}")


        # LOGGER.info("Creating query object for filter query")
        query_object = QueryObject(entity_identifier=request.entity_identifier,
                                   selected_field_names=request.selected_field_names,
                                   filter_expression=request.filter_expression,
                                   entity_definition=request.connector_context.entity_definition,
                                   next_token=request.next_token)
        # LOGGER.info(f"Query object created: {query_object}")

        # LOGGER.info("Sending query to Superleap")
        superleap_response = get_query_connector_response(query_object, request.connector_context)
        LOGGER.info(f"Received response with status: {superleap_response.status_code}")
        
        error_details = superleap.check_for_errors_in_superleap_response(superleap_response)

        if error_details:
            LOGGER.error(f"Error in Superleap response: {error_details}")
            return responses.QueryDataResponse(is_success=False, error_details=error_details)


        # LOGGER.info("Parsing query response")
        parsed_records = parse_query_response(superleap_response.response)
        # Get next token if present and save it, it will use that to continue pulling data.
        next_page = get_next_page(superleap_response.response)
        LOGGER.info(f"next page is : {next_page}")
        LOGGER.info("=== END: query_data ===")

        if len(parsed_records) == 0 or next_page is None or next_page == "" or next_page == "None":
            LOGGER.info("Setting next page to None again since parsed records are 0")
            return responses.QueryDataResponse(is_success=True,
                                           records=parsed_records)
        
        return responses.QueryDataResponse(is_success=True,
                                           records=parsed_records,
                                           next_token=next_page)
