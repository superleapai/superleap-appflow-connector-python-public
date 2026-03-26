import json
import logging
from typing import List, Dict, Any

import custom_connector_sdk.lambda_handler.requests as requests
import custom_connector_sdk.lambda_handler.responses as responses
import custom_connector_sdk.connector.context as context
import custom_connector_sdk.connector.fields as fields
import custom_connector_superleap.handlers.validation as validation
import custom_connector_superleap.handlers.superleap as superleap
from custom_connector_sdk.connector.settings import CacheControl, TimeUnit
from custom_connector_sdk.lambda_handler.handlers import MetadataHandler

LOGGER = logging.getLogger()
LOGGER.setLevel(logging.INFO)

SUPERLEAP_LIST_OBJECTS_URL_FORMAT = '{}{}/appflow/objects/list/'
SUPERLEAP_GET_OBJECT_URL_FORMAT = '{}{}/appflow/objects/{}'

# Superleap response keys
SUCCESS_KEY = "success"
DATA_KEY = "data"
ENTITY_IDENTIFIER_KEY = "entity_identifier"
LABEL_KEY = "label"
DESCRIPTION_KEY = "description"
HAS_NESTED_ENTITIES_KEY = "has_nested_entities"
IS_WRITABLE_KEY = "is_writable"
FIELDS_KEY = "fields"

# Field keys
FIELD_NAME_KEY = "field_name"
DATA_TYPE_KEY = "data_type"
DATA_TYPE_LABEL_KEY = "data_type_label"
FIELD_LABEL_KEY = "label"
FIELD_DESCRIPTION_KEY = "description"
DEFAULT_VALUE_KEY = "default_value"
IS_PRIMARY_KEY_KEY = "is_primary_key"
IS_DEPRECATED_KEY = "is_deprecated"
READ_PROPERTIES_KEY = "read_properties"
WRITE_PROPERTIES_KEY = "write_properties"

# Read properties keys
IS_RETRIEVABLE_KEY = "is_retrievable"
IS_NULLABLE_KEY = "is_nullable"
IS_QUERYABLE_KEY = "is_queryable"
IS_TIMESTAMP_FIELD_KEY = "is_timestamp_field_for_incremental_queries"

# Write properties keys
IS_CREATABLE_KEY = "is_creatable"
IS_UPDATABLE_KEY = "is_updatable"
IS_UPSERTABLE_KEY = "is_upsertable"
IS_DEFAULTED_ON_CREATE_KEY = "is_defaulted_on_create"
WRITE_IS_NULLABLE_KEY = "is_nullable"
SUPPORTED_WRITE_OPERATIONS_KEY = "supported_write_operations"

def parse_entities(json_string: str) -> List[context.Entity]:
    """Parse JSON response from Superleap query into a list of Entities."""
    try:
        parent_object = json.loads(json_string)
    except json.JSONDecodeError as e:
        LOGGER.error(f"Failed to parse JSON response: {e}")
        return []
        
    entity_list = []
    if parent_object.get(SUCCESS_KEY) and parent_object.get(DATA_KEY):
        entities = parent_object.get(DATA_KEY)
        for i, entity in enumerate(entities):
            # Using the direct format from your API response
            entity_list.append(context.Entity(
                entity_identifier=entity.get(ENTITY_IDENTIFIER_KEY),
                label=entity.get(LABEL_KEY),
                description=entity.get(DESCRIPTION_KEY, ""),
                has_nested_entities=entity.get(HAS_NESTED_ENTITIES_KEY, False),
                is_writable=entity.get(IS_WRITABLE_KEY, False)
            ))
    else:
        LOGGER.error(f'Invalid response format or unsuccessful response: {str(parent_object)}')

    return entity_list

def build_entity(entity_data: Dict[str, Any]) -> context.Entity:
    """Build entity object from entity data."""
    # Using the direct format from your API response
    entity = context.Entity(
        entity_identifier=entity_data.get(ENTITY_IDENTIFIER_KEY),
        label=entity_data.get(LABEL_KEY),
        description=entity_data.get(DESCRIPTION_KEY, ""),
        has_nested_entities=entity_data.get(HAS_NESTED_ENTITIES_KEY, False),
        is_writable=entity_data.get(IS_WRITABLE_KEY, False)
    )
    return entity

def parse_entity_definition(json_string: str) -> context.EntityDefinition:
    """Parse JSON response from Superleap query into an entity definition."""
    try:
        parent_object = json.loads(json_string)
    except json.JSONDecodeError as e:
        LOGGER.error(f"Failed to parse JSON response: {e}")
        # Create a default entity and return
        entity = context.Entity(entity_identifier="unknown", label="Unknown Entity")
        return context.EntityDefinition(entity=entity, fields=[])
    
    field_definitions = []
    
    # Check if response follows the expected format
    if parent_object.get(SUCCESS_KEY) and parent_object.get(DATA_KEY):
        entity_data = parent_object.get(DATA_KEY)
        entity = build_entity(entity_data)
        
        # Check if the entity has fields
        if FIELDS_KEY in entity_data:
            field_list = entity_data.get(FIELDS_KEY)
            for i, field in enumerate(field_list):
                field_definition = build_field_definition(field)
                field_definitions.append(field_definition)
                
        else:
            LOGGER.warning(f"No fields found for entity {entity.entity_identifier}")
    else:
        LOGGER.error("Invalid response format or unsuccessful response")
        if SUCCESS_KEY not in parent_object:
            LOGGER.error(f"Missing success key in response")
        if DATA_KEY not in parent_object:
            LOGGER.error(f"Missing data key in response")
        
        entity = context.Entity(entity_identifier="unknown", label="Unknown Entity")
        LOGGER.info("Created default 'unknown' entity")

    entity_definition = context.EntityDefinition(entity=entity, fields=field_definitions)
    
    return entity_definition

def build_field_definition(field: dict) -> context.FieldDefinition:
    """Build FieldDefinition from Superleap field using the new API format."""
    # Map the data type from the API to AppFlow's FieldDataType
    data_type_str = field.get(DATA_TYPE_KEY, "STRING")  # Default to STRING if not specified
    
    # Convert data type string to the appropriate fields.FieldDataType enum
    try:
        data_type = getattr(fields.FieldDataType, data_type_str)
    except AttributeError:
        LOGGER.warning(f"Unknown data type: {data_type_str}, defaulting to STRING")
        data_type = fields.FieldDataType.String
    
    # Get read properties from the field
    read_properties = field.get(READ_PROPERTIES_KEY, {})
    read_operation_property = fields.ReadOperationProperty(
        is_retrievable=read_properties.get(IS_RETRIEVABLE_KEY, True),
        is_nullable=read_properties.get(IS_NULLABLE_KEY, True),
        is_queryable=read_properties.get(IS_QUERYABLE_KEY, False),
        is_timestamp_field_for_incremental_queries=read_properties.get(IS_TIMESTAMP_FIELD_KEY, False)
    )
    
    # Get write properties from the field
    write_properties = field.get(WRITE_PROPERTIES_KEY, {})
    write_operation_property = fields.WriteOperationProperty(
        is_creatable=write_properties.get(IS_CREATABLE_KEY, False),
        is_updatable=write_properties.get(IS_UPDATABLE_KEY, False),
        is_nullable=write_properties.get(WRITE_IS_NULLABLE_KEY, False),
        is_upsertable=write_properties.get(IS_UPSERTABLE_KEY, False),
        is_defaulted_on_create=write_properties.get(IS_DEFAULTED_ON_CREATE_KEY, False),
        supported_write_operations=write_properties.get(SUPPORTED_WRITE_OPERATIONS_KEY, [])
    )
    
    # Create and return the field definition
    field_definition = context.FieldDefinition(
        field_name=field.get(FIELD_NAME_KEY),
        data_type=data_type,
        data_type_label=field.get(DATA_TYPE_LABEL_KEY),
        label=field.get(FIELD_LABEL_KEY),
        description=field.get(FIELD_DESCRIPTION_KEY, ""),
        default_value=field.get(DEFAULT_VALUE_KEY),
        is_primary_key=field.get(IS_PRIMARY_KEY_KEY, False),
        read_properties=read_operation_property,
        write_properties=write_operation_property
    )
    
    return field_definition


class SuperleapMetadataHandler(MetadataHandler):
    """Superleap Metadata handler."""
    def list_entities(self, request: requests.ListEntitiesRequest) -> responses.ListEntitiesResponse:
        
        # Validation will be done by the get_superleap_client function which retrieves the API key from secrets manager
        error_details = validation.validate_request_connector_context(request)
        if error_details:
            LOGGER.error(f'ListEntities request failed with {str(error_details)}')
            return responses.ListEntitiesResponse(is_success=False, error_details=error_details)

        # Build the request URI for listing objects
        request_uri = superleap.build_superleap_request_uri(
            connector_context=request.connector_context,
            url_format=SUPERLEAP_LIST_OBJECTS_URL_FORMAT,
            request_path=''
        )
        
        # Prepare pagination parameters for the API call
        post_data = {}
        if request.max_result:
            post_data['limit'] = request.max_result
        # if request.next_token:
        #     post_data['next_token'] = request.next_token
            
        post_data_str = json.dumps(post_data)
        
        try:
            superleap_client = superleap.get_superleap_client(request.connector_context)
            superleap_response = superleap_client.rest_post(request_uri, post_data_str)
        except Exception as e:
            LOGGER.error(f"Exception during API call to list entities: {str(e)}", exc_info=True)
            error = responses.ErrorDetails(
                error_code=responses.ErrorCode.ServerError,
                error_message=f"API call failed: {str(e)}"
            )
            return responses.ListEntitiesResponse(is_success=False, error_details=error)
        error_details = superleap.check_for_errors_in_superleap_response(superleap_response)

        # Define cache control with 15 mins TTL
        cache_control = CacheControl(
            time_to_live=900,  # 15 mins of cache
            time_to_live_unit=TimeUnit.SECONDS
        )
        
        if error_details:
            LOGGER.error(f'Error in Superleap response: {error_details.error_message}')
            return responses.ListEntitiesResponse(is_success=False, error_details=error_details, cache_control=cache_control)
        
        try:
            # Parse the response to get entities and extract next_token if available
            response_json = json.loads(superleap_response.response)
            entities = parse_entities(superleap_response.response)
            
            # Check if the API response includes a next_token for pagination
            next_token = None
            
            return responses.ListEntitiesResponse(
                is_success=True, 
                entities=entities, 
                next_token=next_token,
                cache_control=cache_control
            )
        except Exception as e:
            LOGGER.error(f"Exception while parsing entities: {str(e)}", exc_info=True)
            error = responses.ErrorDetails(
                error_code=responses.ErrorCode.ServerError,
                error_message=f"Failed to parse entities: {str(e)}"
            )
            return responses.ListEntitiesResponse(is_success=False, error_details=error, cache_control=cache_control)

    def describe_entity(self, request: requests.DescribeEntityRequest) -> responses.DescribeEntityResponse:
        error_details = validation.validate_request_connector_context(request)
        if error_details:
            LOGGER.error(f'DescribeEntity request failed with {str(error_details)}')
            return responses.DescribeEntityResponse(is_success=False, error_details=error_details)

        # Build request URI for Superleap GET object API
        request_uri = superleap.build_superleap_request_uri(
            connector_context=request.connector_context,
            url_format=SUPERLEAP_GET_OBJECT_URL_FORMAT,
            request_path=request.entity_identifier
        )
        
        try:
            # Use rest_get for retrieving entity details
            superleap_client = superleap.get_superleap_client(request.connector_context)
            superleap_response = superleap_client.rest_get(request_uri)
        except Exception as e:
            LOGGER.error(f"Exception during API call: {str(e)}", exc_info=True)
            error = responses.ErrorDetails(
                error_code=responses.ErrorCode.ServerError,
                error_message=f"API call failed: {str(e)}"
            )
            return responses.DescribeEntityResponse(is_success=False, error_details=error)
        
        error_details = superleap.check_for_errors_in_superleap_response(superleap_response)

        if error_details:
            LOGGER.error(f'Error in Superleap response: {error_details.error_message}')
            return responses.DescribeEntityResponse(is_success=False, error_details=error_details)
        
        try:
            entity_definition = parse_entity_definition(superleap_response.response)
            # Define cache control with 15 mins TTL
            cache_control = CacheControl(
                time_to_live=900,  # 15 minutes
                time_to_live_unit=TimeUnit.SECONDS
            )
            return responses.DescribeEntityResponse(
                is_success=True, 
                entity_definition=entity_definition,
                cache_control=cache_control
            )
        except Exception as e:
            LOGGER.error(f"Exception while parsing entity definition: {str(e)}", exc_info=True)
            error = responses.ErrorDetails(
                error_code=responses.ErrorCode.ServerError,
                error_message=f"Failed to parse entity definition: {str(e)}"
            )
            return responses.DescribeEntityResponse(is_success=False, error_details=error)
