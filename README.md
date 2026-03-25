<img width="494" height="113" alt="superleap" src="https://github.com/user-attachments/assets/0b9e01ff-6cf1-473b-ab88-d3ad9f1e8a13" />

# Superleap AppFlow Connector


Amazon AppFlow custom connector for [Superleap](https://superleap.com/), built with the [AWS AppFlow Custom Connector SDK](https://github.com/awslabs/aws-appflow-custom-connector-python) for Python.

This connector enables Amazon AppFlow to pull data from Superleap as a **source** connector, supporting on-demand and scheduled incremental data transfers to any AppFlow-supported destination (e.g. Amazon S3, Redshift).


## Features

- **Source connector** for Amazon AppFlow
- **API Key authentication** (stored in AWS Secrets Manager)
- **Dynamic entity discovery** — entities and field metadata are fetched from the Superleap API
- **Query filtering** — supports AppFlow filter expressions for selective data pulls
- **Incremental sync** — scheduled flows pull only records modified since the last execution
- **Pagination** — handles large result sets via `next_token`
- **Retry logic** — query operations retry up to 3 times with backoff on failure
- **Metadata caching** — entity definitions cached for 15 minutes


## Setup

For step-by-step instructions on deploying the connector and setting up AppFlow, follow the guide at:

**[https://docs.superleap.com/appflow](https://docs.superleap.com/appflow)**

You will need the two zip files included in this repository:

| File | Purpose |
|------|---------|
| `superleap-connector-python.zip` | Lambda function code |
| `python.zip` | Lambda layer (dependencies) |


## Architecture

The connector is deployed as an AWS Lambda function and implements three handler interfaces required by AppFlow:

| Handler                | Purpose                                                        |
|------------------------|----------------------------------------------------------------|
| `ConfigurationHandler` | Declares supported auth types, runtime settings, and connector modes |
| `MetadataHandler`      | Lists available entities and describes their field-level schema |
| `RecordHandler`        | Queries data from Superleap via the Superleap REST API         |

**Lambda Handler:** `custom_connector_superleap.handlers.lambda_handler.superleap_lambda_handler`


## Superleap API Endpoints

| Operation          | Method | Endpoint                                            |
|--------------------|--------|-----------------------------------------------------|
| Verify Credentials | GET    | `{base_url}/v1/appflow/verify/`                     |
| List Entities      | POST   | `{base_url}/v1/appflow/objects/list/`                |
| Describe Entity    | GET    | `{base_url}/v1/appflow/objects/{entity_id}`          |
| Query Records      | POST   | `{base_url}/v1/appflow/objects/{entity_id}/records/` |

Default base URL: `https://app.superleap.com/` (or your custom domain)


## Configuration

### Runtime Settings

| Setting    | Scope             | Description                                                     |
|------------|-------------------|-----------------------------------------------------------------|
| `base_url` | Connector Profile | Superleap instance URL — your custom domain or `https://app.superleap.com/` |

### Authentication

API Key authentication via AWS Secrets Manager. The secret must contain a field named `apiSecretKey`. All requests are authenticated with `Authorization: Bearer {apiSecretKey}`.


## Project Structure

```
custom_connector_superleap/   # Superleap connector implementation
  handlers/                   #   Lambda handler, config, metadata, record handlers
  query/                      #   Query filter translation
  constants.py                #   URLs, keys, defaults

custom_connector_sdk/         # AppFlow Custom Connector SDK
custom_connector_queryfilter/ # Filter expression parser (AppFlow DSL)
```


## Using the API Directly

If you need to pull data from Superleap without AppFlow (e.g. from your own application or scripts), see the [API Reference](API_REFERENCE.md) for endpoint details, authentication, filtering, and pagination.
