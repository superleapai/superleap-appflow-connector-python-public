import json
import logging
import boto3
from typing import Optional
import custom_connector_superleap.constants as constants
from custom_connector_sdk.connector.context import ConnectorContext
from custom_connector_sdk.lambda_handler.responses import ErrorDetails, ErrorCode
from custom_connector_sdk.connector.auth import ACCESS_TOKEN
from custom_connector_superleap.handlers.client import HttpsClient, SuperleapResponse

HTTP_STATUS_CODE_RANGE = range(200, 300)
LOGGER = logging.getLogger()
LOGGER.setLevel(logging.INFO)  # Set to DEBUG for detailed logs

def get_superleap_client(connector_context: ConnectorContext):
    # Get the secret from AWS Secrets Manager
    secret_name = connector_context.credentials.secret_arn
    if not secret_name:
        raise ValueError("Secret name is not provided in the connector runtime settings.")
    
    
    try:
        session = boto3.session.Session()
        client = session.client('secretsmanager')
        get_secret_value_response = client.get_secret_value(SecretId=secret_name)
        if 'SecretString' in get_secret_value_response:
            secret = get_secret_value_response['SecretString']
        else:
            secret = get_secret_value_response['SecretBinary']
                    
        # Convert the secret string to a dictionary
        secret_dict = json.loads(secret)
        apiSecret = secret_dict.get('apiSecretKey')    
        return HttpsClient(access_token=apiSecret)
    except client.exceptions.ResourceNotFoundException:
        LOGGER.error(f"Secret {secret_name} not found")
        raise ValueError(f"Secret {secret_name} not found.")
    except client.exceptions.AccessDeniedException as e:
        LOGGER.error(f"Access denied to secret {secret_name}: {str(e)}")
        raise ValueError(f"Access denied to secret {secret_name}. Please check IAM permissions.")
    except Exception as e:
        LOGGER.error(f"Error accessing secret {secret_name}: {str(e)}")
        raise ValueError(f"Error accessing secret {secret_name}: {str(e)}")
    except json.JSONDecodeError as e:
        LOGGER.error(f"Error decoding JSON from secret {secret_name}: {str(e)}")
        raise ValueError(f"Error decoding JSON from secret {secret_name}: {str(e)}")


# Check this again and see if it works properly for our use case
def check_for_errors_in_superleap_response(response: SuperleapResponse) -> Optional[ErrorDetails]:
    """Parse Superleap response for errors and convert them to an ErrorDetails object."""
    status_code = response.status_code

    if status_code in HTTP_STATUS_CODE_RANGE:
        return None

    LOGGER.warning(f"Received error status code: {status_code}")
    if status_code == 401:
        error_code = ErrorCode.InvalidCredentials
        LOGGER.warning("Authentication error detected")
    elif status_code == 400:
        error_code = ErrorCode.InvalidArgument
        LOGGER.warning("Invalid argument error detected")
    else:
        error_code = ErrorCode.ServerError
        LOGGER.warning(f"Server error detected with status code: {status_code}")

    error_message = f'Request failed with status code {status_code}'

    return ErrorDetails(error_code=error_code, error_message=error_message)

def build_superleap_request_uri(connector_context: ConnectorContext, url_format: str, request_path: str) -> str:
    connector_runtime_settings = connector_context.connector_runtime_settings
    
    # Get base URL from settings or use default
    instance_url = connector_runtime_settings.get(constants.BASE_URL_KEY, constants.DEFAULT_BASE_URL)
    
    # Add API path if needed
    instance_url = add_path(instance_url)
    
    # Get API version
    api_version = connector_context.api_version

    # Format the final URI
    request_uri = url_format.format(instance_url, api_version, request_path)

    return request_uri


def get_string_value(response: dict, field_name: str) -> Optional[str]:
    if field_name is None or response.get(field_name) is None:
        return None
    elif isinstance(response.get(field_name), bool):
        return str(response.get(field_name)).lower()
    else:
        return str(response.get(field_name))

def get_boolean_value(response: dict, field_name: str) -> bool:
    if field_name is None:
        return False
    elif field_name == 'true':
        return True
    elif response.get(field_name) is None:
        return False
    else:
        return bool(response.get(field_name))


def add_path(url: str) -> str:
    if url.endswith('/'):
        return url + "api/"
    return url + '/api/'
