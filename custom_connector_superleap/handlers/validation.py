from typing import List, Optional
import logging

from custom_connector_sdk.lambda_handler.responses import ErrorDetails, ErrorCode
from custom_connector_sdk.connector.context import ConnectorContext
import custom_connector_sdk.lambda_handler.requests as requests
import custom_connector_superleap.constants as constants

LOGGER = logging.getLogger()
LOGGER.setLevel(logging.INFO)


def validate_connector_runtime_settings(request: requests.ValidateConnectorRuntimeSettingsRequest) -> \
        Optional[ErrorDetails]:
    errors = check_connector_runtime_settings_errors(request.connector_runtime_settings)
    if not errors:
        return None
    
    error_msg = ','.join(errors)
    LOGGER.error(f"Connector runtime settings validation failed: {error_msg}")
    return ErrorDetails(error_code=ErrorCode.InvalidArgument, error_message=error_msg)

def validate_request_connector_context(request) -> Optional[ErrorDetails]:
    errors = check_connector_context_errors(request.connector_context)
    if not errors:
        return None
    
    error_msg = ','.join(errors)
    LOGGER.error(f"Request connector context validation failed: {error_msg}")
    return ErrorDetails(error_code=ErrorCode.InvalidArgument, error_message=error_msg)

def check_connector_context_errors(connector_context: ConnectorContext) -> List[str]:
    errors = check_connector_runtime_settings_errors(connector_context.connector_runtime_settings)
    return errors

def check_connector_runtime_settings_errors(connector_runtime_settings: dict) -> List[str]:
    errors = []
    # if not connector_runtime_settings or constants.BASE_URL_KEY not in connector_runtime_settings:
    #     error_msg = f'{constants.BASE_URL_KEY} should be provided as runtime setting for Superleap connector'
    #     errors.append(error_msg)
    return errors
