#!/usr/bin/env python3

import argparse
import collections
import csv
import json
import logging
import os.path
import re
import sys

import boto3

API_NAME = "VitalServices"
DUMMY_LAMBDA_KEY = "dummylambda.zip"
LAMBDA_NAME = "vitalservices2"
LAMBDA_ROLE = "vital_lambdaexecutionrole_MOBILEHUB_700194776"
LAMBDA_TIMEOUT = 35
LAMBDA_MEM_LIMIT = 512
LAMBDA_FUNCTION_URI = "arn:aws:apigateway:us-east-1:lambda:path/2015-03-31/functions/arn:aws:lambda:us-east-1:" \
                    "103014156873:function:%LAMBDA_NAME%/invocations"

LAMBDA_FUNCTION_BUCKET = "vital-lambda-function-bucket-us-east-1-1473284567134"
PAGED_REQUEST_LIMIT = 500
REQUEST_TEMPLATE_FORMAT = "##  See http://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-mapping" \
                          "-template-reference.html\n##  This template will pass through all parameters including " \
                          "path, querystring, header, stage variables, and context through to the integration " \
                          "endpoint via the body/payload\n#set($allParams = $input.params())\n{{\n\"operation\": \"{" \
                          "operation}\",\n\"{inputName}\" : $input.json('$'),\n\"params\" : {{\n#foreach($type in " \
                          "$allParams.keySet())\n    #set($params = $allParams.get($type))\n\"$type\" : {{\n    " \
                          "#foreach($paramName in $params.keySet())\n    \"$paramName\" : \"$util.escapeJavaScript(" \
                          "$params.get($paramName))\"\n        #if($foreach.hasNext),#end\n    #end\n}}\n    #if(" \
                          "$foreach.hasNext),#end\n#end\n}},\n\"stage-variables\" : {{\n#foreach($key in " \
                          "$stageVariables.keySet())\n\"$key\" : \"$util.escapeJavaScript($stageVariables.get(" \
                          "$key))\"\n    #if($foreach.hasNext),#end\n#end\n}},\n\"requestContext\" : {{\n    " \
                          "\"accountId\" : \"$context.identity.accountId\",\n    \"apiId\" : \"$context.apiId\"," \
                          "\n    \"apiKey\" : \"$context.identity.apiKey\",\n    \"authorizerPrincipalId\" : " \
                          "\"$context.authorizer.principalId\",\n    \"caller\" : \"$context.identity.caller\"," \
                          "\n    \"cognitoAuthenticationProvider\" : " \
                          "\"$context.identity.cognitoAuthenticationProvider\",\n    \"cognitoAuthenticationType\" : " \
                          "\"$context.identity.cognitoAuthenticationType\",\n    \"cognitoIdentityId\" : " \
                          "\"$context.identity.cognitoIdentityId\",\n    \"cognitoIdentityPoolId\" : " \
                          "\"$context.identity.cognitoIdentityPoolId\",\n    \"httpWethod\" : " \
                          "\"$context.httpMethod\",\n    \"stage\" : \"$context.stage\",\n    \"sourceIp\" : " \
                          "\"$context.identity.sourceIp\",\n    \"user\" : \"$context.identity.user\"," \
                          "\n    \"userAgent\" : \"$context.identity.userAgent\",\n    \"userarn\" : " \
                          "\"$context.identity.userArn\",\n    \"requestId\" : \"$context.requestId\"," \
                          "\n    \"resourceId\" : \"$context.resourceId\",\n    \"resourcePath\" : " \
                          "\"$context.resourcePath\"\n    }}\n}} "
SCHEMA_INDENT = 4
UNSUPPORTED_MODEL_SCHEMA_KEYWORDS = ("javaType", "referencedModels")
GATEWAY_ID_FILE = os.path.expanduser("~/.my-gateway-id")


def main():
    """
    The main routine.
    @return An exit code.
    """
    root_resource_id = None
    # Configure logging.
    logging.basicConfig(level=logging.WARNING)
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.WARNING)

    # Get command-line arguments.
    parser = argparse.ArgumentParser(
        description="Update vitalservices2's API gateway.")

    parser.add_argument("api_description_file")
    parser.add_argument("models_dir")
    parser.add_argument("dummy_lambda_dir")
    arguments = parser.parse_args()

    # Getting current user information
    iam = boto3.resource("iam")
    user = iam.CurrentUser()
    user_name = user.user_name
    user_api_name = "{}-{}".format(API_NAME, user_name)
    new_lambda_name = "{}-{}".format(LAMBDA_NAME, user_name)

    # Create Lambda function
    role = iam.Role(LAMBDA_ROLE)
    lambda_client = boto3.client("lambda")

    # Trying to delete function if exists
    try:
        lambda_client.delete_function(FunctionName=new_lambda_name)
    except:
        pass

    lambda_function = lambda_client.create_function(
        FunctionName=new_lambda_name,
        Runtime="java8",
        Role=role.arn,
        Handler="vitalservices2.LambdaFunctionHandler",
        Timeout=LAMBDA_TIMEOUT,
        MemorySize=LAMBDA_MEM_LIMIT,
        Code={
            "S3Bucket": LAMBDA_FUNCTION_BUCKET,
            "S3Key": DUMMY_LAMBDA_KEY,
        }
    )

    # Check if API gateway already exists
    client = boto3.client("apigateway")
    avialible_apis = {item["name"]: item["id"] for item in client.get_rest_apis()["items"]}
    if user_api_name in avialible_apis:
        API_ID = avialible_apis[user_api_name]
    else:
        result = client.create_rest_api(
            name=user_api_name,
            description="{} API Gateway for {}".format(API_NAME, user_name),
        )
        API_ID = result["id"]

    # Writing API_ID to file at $HOME
    with open(GATEWAY_ID_FILE, "w") as gw_id_file:
        gw_id_file.write("{}".format(API_ID))

    # Delete all of the API's resources.
    result = client.get_resources(restApiId=API_ID, limit=PAGED_REQUEST_LIMIT)
    for resource in result["items"]:
        # Don't attempt to delete the root resource. Also, save its ID,
        # which will be required later.
        if resource["path"] == "/":
            root_resource_id = resource["id"]
            continue

        client.delete_resource(restApiId=API_ID, resourceId=resource["id"])

    # Delete all of the API's models.
    result = client.get_models(restApiId=API_ID, limit=PAGED_REQUEST_LIMIT)
    for model in result["items"]:
        client.delete_model(restApiId=API_ID, modelName=model["name"])

    # Process the API description CSV file.
    with open(arguments.api_description_file) as api_description_file:
        api_description_reader = csv.DictReader(api_description_file)

        # Create a named tuple class "Service" to wrap each line of the CSV
        # file.
        Service = collections.namedtuple("Service",
                                         api_description_reader.fieldnames)
        existing_models = set()

        # Iterate over the services described in the CSV file.
        for row in api_description_reader:
            service = Service(**row)
            logger.debug("service={}".format(service))
            if not service.resource or not service.input_name or not service.request_model:
                get_logger().error(
                    "A required field is missing from this service: {}".format(
                        service))

            # Create the models that this service's method will use.
            create_model(client, API_ID, existing_models, arguments.models_dir,
                         service.request_model)

            if service.response_model:
                create_model(client, API_ID, existing_models, arguments.models_dir,
                             service.response_model)

            # Create the service's resource, and configure its POST method.
            resource = client.create_resource(
                restApiId=API_ID,
                parentId=root_resource_id,
                pathPart=service.resource)

            put_method_args = {
                "restApiId": API_ID,
                "resourceId": resource["id"],
                "httpMethod": "POST",
                "authorizationType": "AWS_IAM",
                "apiKeyRequired": False
            }

            if service.request_model:
                put_method_args["requestModels"] = {
                    "application/json": service.request_model
                }

            method = client.put_method(**put_method_args)
            request_template = REQUEST_TEMPLATE_FORMAT.format(
                operation=service.operation, inputName=service.input_name)

            # Put new API_ID into LAMBDA_URI
            lambda_function_uri = LAMBDA_FUNCTION_URI.replace("%LAMBDA_NAME%", new_lambda_name)
            integration = client.put_integration(
                restApiId=API_ID,
                resourceId=resource["id"],
                httpMethod="POST",
                type="AWS",
                integrationHttpMethod="POST",
                uri=lambda_function_uri,
                credentials="arn:aws:iam::*:user/*",
                requestTemplates={"application/json": request_template},
                passthroughBehavior="WHEN_NO_TEMPLATES")

            put_method_response_args = {
                "restApiId": API_ID,
                "resourceId": resource["id"],
                "httpMethod": "POST",
                "statusCode": "200",
            }

            if service.response_model:
                put_method_response_args["responseModels"] = {
                    "application/json": service.response_model
                }

            method_response = client.put_method_response(
                **put_method_response_args)

            method_response = client.put_method_response(
                restApiId=API_ID,
                resourceId=resource["id"],
                httpMethod="POST",
                statusCode="400")

            integration_response = client.put_integration_response(
                restApiId=API_ID,
                resourceId=resource["id"],
                httpMethod="POST",
                statusCode="200",
                responseTemplates={"application/json": ""})

            integration_response = client.put_integration_response(
                restApiId=API_ID,
                resourceId=resource["id"],
                httpMethod="POST",
                statusCode="400",
                selectionPattern=".+")

    # Deploy the API.
    deployment = client.create_deployment(restApiId=API_ID, stageName="prod")
    return 0


def fix_schema_ref_uri(schema, api_id):
    """
    Fixes schema ref URI replacing API id
    :param schema: Schema as String to be processed
    :param api_id: API ID to be placed instead of existing
    :return: Schema as String
    """
    return re.sub(r"restapis/(.+?)/models", "restapis/" + api_id + "/models", schema)


def create_model(client, api_id, existing_models, models_dir, model_name):
    """
    Creates a model in the gateway.
    @param client The API gateway client to use.
    @param api_id: API ID to use
    @param existing_models A set containing the names of models that have
    already been created. This routine does nothing if the model is to be
    created already exists.
    @param models_dir The path to the directory containing the model's schema.
    @param model_name The model's name.
    """
    get_logger().debug("client={}, models_dir={}, model_name={}".format(
        client, models_dir, model_name))

    if model_name in existing_models:
        return

    base_name = "{}.schema".format(model_name)
    model_path = os.path.join(models_dir, base_name)
    with open(model_path) as model_schema_file:
        model_schema = json.load(
            model_schema_file, object_pairs_hook=collections.OrderedDict)

        # First create any models that this model references.
        for referenced_model in model_schema.get("referencedModels", []):
            create_model(client, api_id, existing_models, models_dir, referenced_model)

        # Sanitize the schema for AWS.
        sanitize_model_schema(model_schema)

        # Create the model and fix schema ref URI
        client.create_model(
            restApiId=api_id,
            name=model_name,
            schema=fix_schema_ref_uri(json.dumps(model_schema), api_id),
            contentType="application/json")

    existing_models.add(model_name)


def sanitize_model_schema(schema):
    for keyword in UNSUPPORTED_MODEL_SCHEMA_KEYWORDS:
        if keyword in schema:
            del schema[keyword]


def get_logger():
    """
    Gets this module's logger.
    """
    return logging.getLogger(__name__)


if __name__ == "__main__":
    sys.exit(main())
