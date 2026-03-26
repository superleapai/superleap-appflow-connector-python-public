import logging
import custom_connector_sdk.lambda_handler.requests as requests
import custom_connector_sdk.lambda_handler.responses as responses
import custom_connector_sdk.connector.settings as settings
import custom_connector_sdk.connector.configuration as config
import custom_connector_sdk.connector.context as context
import custom_connector_sdk.connector.auth as auth
import custom_connector_superleap.constants as constants
import custom_connector_superleap.handlers.validation as validation
import custom_connector_superleap.handlers.superleap as superleap
from custom_connector_sdk.lambda_handler.handlers import ConfigurationHandler

CONNECTOR_OWNER = 'Superleap'
CONNECTOR_NAME = 'SuperleapConnector'
CONNECTOR_VERSION = '1.0'

SUPERLEAP_VERIFY_URL_FORMAT = '{}{}/appflow/verify/'

LOGGER = logging.getLogger()
LOGGER.setLevel(logging.INFO) # Set to DEBUG for detailed logs
class SuperleapConfigurationHandler(ConfigurationHandler):
    """Superleap Configuration Handler."""
    def validate_connector_runtime_settings(self, request: requests.ValidateConnectorRuntimeSettingsRequest) -> \
            responses.ValidateConnectorRuntimeSettingsResponse:
        errors = validation.validate_connector_runtime_settings(request)
        if errors:
            LOGGER.error(f"Validation errors found: {errors}")
            return responses.ValidateConnectorRuntimeSettingsResponse(is_success=False, error_details=errors)
        return responses.ValidateConnectorRuntimeSettingsResponse(is_success=True)

    def validate_credentials(self, request: requests.ValidateCredentialsRequest) -> \
            responses.ValidateCredentialsResponse:
        # Get API key and base URL directly from connector runtime settings

        connector_context = context.ConnectorContext(credentials=request.credentials,
                                                     api_version=constants.API_VERSION,
                                                     connector_runtime_settings=request.connector_runtime_settings)

        request_uri = superleap.build_superleap_request_uri(connector_context=connector_context,
                                                                  url_format=SUPERLEAP_VERIFY_URL_FORMAT,
                                                                  request_path="")
        
        # Create a client with the API key
        try:
            client = superleap.get_superleap_client(connector_context)
            response = client.rest_get(request_uri)
            
            # Check if the request was successful
            if response.status_code != 200:
                error_message = f"API key validation failed: {response.error_reason}"
                LOGGER.error(error_message)
                return responses.ValidateCredentialsResponse(
                    is_success=False,
                    error_details=responses.ErrorDetails(
                        error_code=str(response.status_code),
                        error_message=error_message
                    )
                )
            
            return responses.ValidateCredentialsResponse(is_success=True)
        except Exception as e:
            error_message = f"Error validating credentials: {str(e)}"
            LOGGER.error(error_message, exc_info=True)
            return responses.ValidateCredentialsResponse(
                is_success=False,
                error_details=responses.ErrorDetails(
                    error_code=responses.ErrorCode.ServerError,
                    error_message=error_message
                )
            )

    def describe_connector_configuration(self, request: requests.DescribeConnectorConfigurationRequest) -> \
            responses.DescribeConnectorConfigurationResponse:
        connector_modes = [config.ConnectorModes.SOURCE]

        # Define the base_url setting
        base_url_setting = settings.ConnectorRuntimeSetting(
            key=constants.BASE_URL_KEY,
            data_type=settings.ConnectorRuntimeSettingDataType.String,
            required=True,
            label='Superleap API URL',
            description='Base URL for Superleap API',
            scope=settings.ConnectorRuntimeSettingScope.CONNECTOR_PROFILE
        )

        # # Flow-level settings with Boolean type
        # import_new_fields_setting = settings.ConnectorRuntimeSetting(
        #     key=constants.ENABLE_DYNAMIC_FIELD_UPDATE,
        #     data_type=settings.ConnectorRuntimeSettingDataType.Boolean,  # Boolean type
        #     required=True,
        #     label='Map all fields by default',
        #     description='Enable new fields to be mapped and imported in future flow runs. Your selected fields will not matter.',
        #     scope=settings.ConnectorRuntimeSettingScope.SOURCE
        # )

        # Configure authentication to use API key from runtime settings
        authentication_config = auth.AuthenticationConfig(
            is_api_key_auth_supported=True
        )

        response = responses.DescribeConnectorConfigurationResponse(
            is_success=True,
            connector_owner=CONNECTOR_OWNER,
            connector_name=CONNECTOR_NAME,
            connector_version=CONNECTOR_VERSION,
            connector_modes=connector_modes,
            connector_runtime_setting=[base_url_setting],
            authentication_config=authentication_config,
            supported_api_versions=[constants.API_VERSION],  
            logo_url="https://dsm6sohylf53x.cloudfront.net/superleap.png"
        )
        return response