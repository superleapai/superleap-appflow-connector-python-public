import urllib3
import logging

CONNECTION_TIMEOUT_SECS = 30
READ_TIMEOUT_SECS = 600

LOGGER = logging.getLogger()
LOGGER.setLevel(logging.INFO)
class SuperleapResponse:
    def __init__(self, status_code: int, response: str, error_reason: str, headers=None):
        self.status_code = status_code
        self.response = response
        self.error_reason = error_reason
        self.headers = headers or {}

class HttpsClient:
    def __init__(self, access_token):
        timeout = urllib3.Timeout(connect=CONNECTION_TIMEOUT_SECS, read=READ_TIMEOUT_SECS)
        self.https_client = urllib3.PoolManager(timeout=timeout)
        self.access_token = access_token
        self.authorization_header = {'Authorization': 'Bearer ' + access_token}

    def rest_get(self, request_uri: str) -> SuperleapResponse:
        headers = self.authorization_header
        # LOGGER.info(f"Making GET request to: {request_uri}")
        try:
            resp = self.https_client.request(method='GET',
                                             url=request_uri,
                                             headers=headers)
            # LOGGER.info(f"Received response with status: {resp.status}")
            return SuperleapResponse(status_code=resp.status,
                                     response=resp.data.decode('utf-8'),
                                     error_reason=resp.reason,
                                     headers=dict(resp.headers))
        except Exception as e:
            LOGGER.info(f"Error while making GET request to: {request_uri}")
            LOGGER.error(f"Error during GET request: {str(e)}", exc_info=True)
            return SuperleapResponse(status_code=500,
                                     response=f"{{\"error\": \"{str(e)}\"}}",
                                     error_reason=str(e),
                                     headers={})

    def rest_post(self, request_uri: str, post_data: str = '{}') -> SuperleapResponse:
        headers = {**self.authorization_header, 'Accept-Encoding': 'gzip', 'Content-Type': 'application/json'}
        # LOGGER.info(f"Making POST request to: {request_uri}")
        try:
            resp = self.https_client.request(method='POST',
                                             url=request_uri,
                                             headers=headers,
                                             body=post_data)
            # LOGGER.info(f"Received response with status: {resp.status}")
            return SuperleapResponse(status_code=resp.status,
                                     response=resp.data.decode('utf-8'),
                                     error_reason=resp.reason,
                                     headers=dict(resp.headers))
        except Exception as e:
            LOGGER.info(f"Error while making POST request to: {request_uri}")
            LOGGER.error(f"Error during POST request: {str(e)}", exc_info=True)
            return SuperleapResponse(status_code=500,
                                     response=f"{{\"error\": \"{str(e)}\"}}",
                                     error_reason=str(e),
                                     headers={})

    def rest_patch(self, request_uri: str, patch_data: str) -> SuperleapResponse:
        headers = {**self.authorization_header, 'Accept-Encoding': 'gzip', 'Content-Type': 'application/json'}
        # LOGGER.info(f"Making PATCH request to: {request_uri}")
        try:
            resp = self.https_client.request(method='PATCH',
                                             url=request_uri,
                                             headers=headers,
                                             body=patch_data)
            # LOGGER.info(f"Received response with status: {resp.status}")
            return SuperleapResponse(status_code=resp.status,
                                     response=resp.data.decode('utf-8'),
                                     error_reason=resp.reason,
                                     headers=dict(resp.headers))
        except Exception as e:
            LOGGER.info(f"Error while making PATCH request to: {request_uri}")
            LOGGER.error(f"Error during PATCH request: {str(e)}", exc_info=True)
            return SuperleapResponse(status_code=500,
                                     response=f"{{\"error\": \"{str(e)}\"}}",
                                     error_reason=str(e),
                                     headers={})

    def rest_put(self, request_uri: str, put_data: str) -> SuperleapResponse:
        headers = {**self.authorization_header, 'Content-Type': 'text/csv'}
        # LOGGER.info(f"Making PUT request to: {request_uri}")
        try:
            resp = self.https_client.request(method='PUT',
                                             url=request_uri,
                                             headers=headers,
                                             body=put_data)
            # LOGGER.info(f"Received response with status: {resp.status}")
            return SuperleapResponse(status_code=resp.status,
                                     response=resp.data.decode('utf-8'),
                                     error_reason=resp.reason,
                                     headers=dict(resp.headers))
        except Exception as e:
            LOGGER.info(f"Error while making PUT request to: {request_uri}")
            LOGGER.error(f"Error during PUT request: {str(e)}", exc_info=True)
            return SuperleapResponse(status_code=500,
                                     response=f"{{\"error\": \"{str(e)}\"}}",
                                     error_reason=str(e),
                                     headers={})

    def rest_delete(self, request_uri: str) -> SuperleapResponse:
        # LOGGER.info(f"Making DELETE request to: {request_uri}")
        try:
            resp = self.https_client.request(method='DELETE',
                                             url=request_uri,
                                             headers=self.authorization_header)
            # LOGGER.info(f"Received response with status: {resp.status}")
            return SuperleapResponse(status_code=resp.status,
                                     response=resp.data.decode('utf-8'),
                                     error_reason=resp.reason,
                                     headers=dict(resp.headers))
        except Exception as e:
            LOGGER.info(f"Error while making DELETE request to: {request_uri}")
            LOGGER.error(f"Error during DELETE request: {str(e)}", exc_info=True)
            return SuperleapResponse(status_code=500,
                                     response=f"{{\"error\": \"{str(e)}\"}}",
                                     error_reason=str(e),
                                     headers={})
