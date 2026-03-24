import logging
from custom_connector_superleap.handlers.record import SuperleapRecordHandler
from custom_connector_superleap.handlers.metadata import SuperleapMetadataHandler
from custom_connector_superleap.handlers.configuration import SuperleapConfigurationHandler
from custom_connector_sdk.lambda_handler.lambda_handler import BaseLambdaConnectorHandler

LOGGER = logging.getLogger()
LOGGER.setLevel(logging.INFO)

class SuperleapLambdaHandler(BaseLambdaConnectorHandler):
    def __init__(self):
        LOGGER.info("Initializing SuperleapLambdaHandler")
        super().__init__(SuperleapMetadataHandler(), SuperleapRecordHandler(), SuperleapConfigurationHandler())
        LOGGER.info("SuperleapLambdaHandler initialized with handlers")

def superleap_lambda_handler(event, context):
    """Lambda entry point."""
    # LOGGER.info("=== Lambda invocation started ===")
    # LOGGER.info(f"Event: {event}")
    # LOGGER.info(f"Context: {context}")
    
    result = SuperleapLambdaHandler().lambda_handler(event, context)
    
    # LOGGER.info("=== Lambda invocation completed ===")
    return result
