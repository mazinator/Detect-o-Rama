import os
import boto3
import json
import time
import concurrent.futures
import subprocess
from decimal import Decimal
from pathlib import Path
from botocore.exceptions import ClientError


def create_s3_bucket(bucket: str, region: str ='us-west-2'):
    """
    Create a S3 bucket in the specified region.
    """
    try:
        client = boto3.client('s3', region_name=region)
        client.create_bucket(
            Bucket=bucket,
            CreateBucketConfiguration={'LocationConstraint': region}
        )

    except ClientError as e:
        created = e.response['Error']['Code'] == 'BucketAlreadyOwnedByYou'
        print('Bucket already created.' if created else f'Unexpected error: {e}')


def create_ecr_repository(repository_name, region):
    ecr_client = boto3.client('ecr', region_name=region)

    # Create ECR repository
    try:
        ecr_client.create_repository(repositoryName=repository_name)
        print(f"Repository {repository_name} created.")
    except ecr_client.exceptions.RepositoryAlreadyExistsException:
        print(f"Repository {repository_name} already exists.")


def list_ecr_repositories(region):
    ecr_client = boto3.client('ecr', region_name=region)
    repositories = ecr_client.describe_repositories()

    print("Available ECR repositories:")
    for repo in repositories['repositories']:
        print(f"Repository Name: {repo['repositoryName']}, URI: {repo['repositoryUri']}")


def build_and_push_docker_image(repository_name, region, account_id):
    # Get login command for Docker
    login_command = (
        f"aws ecr get-login-password --region {region} | "
        f"docker login --username AWS --password-stdin {account_id}.dkr.ecr.{region}.amazonaws.com"
    )
    subprocess.run(login_command, shell=True, check=True)

    # Build Docker image
    image_tag = f"{account_id}.dkr.ecr.{region}.amazonaws.com/{repository_name}:latest"
    subprocess.run(f"docker build -t {repository_name} .", shell=True, check=True)
    subprocess.run(f"docker tag {repository_name}:latest {image_tag}", shell=True, check=True)

    # Push Docker image to ECR
    subprocess.run(f"docker push {image_tag}", shell=True, check=True)

    print(f"Docker image {image_tag} pushed to ECR.")

    return image_tag


def list_s3_bucket_objects(bucket_name, region: str ='us-west-2'):
    s3_client = boto3.client('s3', region_name=region)
    
    try:
        paginator = s3_client.get_paginator('list_objects_v2')
        page_iterator = paginator.paginate(Bucket=bucket_name)
        
        print(f'Objects in bucket "{bucket_name}":')
        for page in page_iterator:
            if 'Contents' in page:
                for obj in page['Contents']:
                    print(f" - {obj['Key']}")
            else:
                print(f"No objects found in bucket {bucket_name}")
                break
                
    except Exception as e:
        print(f'Error listing objects in bucket: {e}')


def invoke_lambda_function(function_name, event, region: str ='us-west-2'):
    lambda_client = boto3.client('lambda', region_name=region)
    
    try:
        response =  lambda_client.invoke(
            FunctionName=function_name,
            InvocationType='Event', 
            Payload=json.dumps(event)
        )
        print(f'Invoked Lambda function {function_name} successfully.')
        return response

    except ClientError as e:
        print(f'Error invoking Lambda function: {e}')


def delete_lambda_function(function_name, region: str ='us-west-2'):
    lambda_client = boto3.client('lambda', region_name=region)
    
    try:
        response = lambda_client.delete_function(
            FunctionName=function_name
        )
        print(f'Lambda function {function_name} deleted successfully.')
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            print(f'Lambda function {function_name} not found.')
        else:
            print(f'Error deleting Lambda function: {e}')


def get_current_iam_role():
    sts_client = boto3.client('sts')
    response = sts_client.get_caller_identity()
    return response


def upload_file_to_s3(bucket: str, file: str, name: str = None, region: str ='us-west-2'):
    """
    Upload a file to a S3 bucket.
    """
    try:
        s3_client = boto3.client('s3', region_name=region)
        s3_client.upload_file(file, bucket, file if name is None else name)
        print(f'File {file} uploaded to {bucket}/{name}.')

    except ClientError as e:
        print(f'Unexpected error: {e}')


def list_iam_roles(region: str ='us-west-2'):
    iam_client = boto3.client('iam', region_name=region)
    roles = iam_client.list_roles()
    
    print("Available IAM roles:")
    for role in roles['Roles']:
        print(f"Role Name: {role['RoleName']}, ARN: {role['Arn']}")


def get_role_policies(role_name, region: str ='us-west-2'):
    iam_client = boto3.client('iam', region_name=region)
    response = iam_client.list_attached_role_policies(RoleName=role_name)
    policies = response['AttachedPolicies']
    return policies


def attach_policy_to_role(role_name, policy_arn):
    """Attach the specified policy to the IAM role."""
    iam_client = boto3.client('iam')

    try:
        iam_client.attach_role_policy(
            RoleName=role_name,
            PolicyArn=policy_arn
        )
        print(f'Policy {policy_arn} attached to role {role_name} successfully.')
    except Exception as e:
        print(f'Error attaching policy to role: {e}')


def upload_folder_to_s3(bucket_name, folder_path, s3_prefix='', region: str ='us-west-2'):
    s3_client = boto3.client('s3', region_name=region)
    
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            local_path = os.path.join(root, file)
            relative_path = os.path.relpath(local_path, folder_path)
            s3_path = os.path.join(s3_prefix, relative_path).replace("\\", "/")
            
            s3_client.upload_file(local_path, bucket_name, s3_path)
            print(f'Uploaded {local_path} to s3://{bucket_name}/{s3_path}')



def deploy_lambda_function(function_name, image_uri, role_arn, timeout, memory, region = 'us-west-2'):
    lambda_client = boto3.client('lambda', region_name=region)
    try:
        response = lambda_client.create_function(
            FunctionName=function_name,
            PackageType='Image',
            Code={'ImageUri': image_uri},
            Role=role_arn,
            Publish=True,
            Timeout=timeout,
            MemorySize=memory 
        )
        print(f"Lambda function {function_name} created.")
        return response
    
    except lambda_client.exceptions.ResourceConflictException:
        response = lambda_client.update_function_code(
            FunctionName=function_name,
            ImageUri=image_uri,
            Publish=True
        )
        print(f"Lambda function {function_name} updated.")
        return response


def create_s3_lambda_trigger(bucket_name, lambda_function_arn, region = 'us-west-2'):

    lambda_client = boto3.client('lambda', region_name=region)
    lambda_client.add_permission(FunctionName=lambda_function_arn,
                                StatementId='response2-id-2',
                                Action='lambda:InvokeFunction',
                                Principal='s3.amazonaws.com',
    )

    s3_client = boto3.client('s3', region_name=region)
    notification_configuration = {
        'LambdaFunctionConfigurations':[
            {
                'LambdaFunctionArn': lambda_function_arn,
                'Events': ['s3:ObjectCreated:*']
            }
        ]
    }

    response = s3_client.put_bucket_notification_configuration(
        Bucket=bucket_name,
        NotificationConfiguration=notification_configuration
    )
    print(f'S3 event notification added: {response}')


def get_recent_lambda_logs(function_name, n: int=1, region: str ='us-west-2'):
    logs_client = boto3.client('logs', region_name=region)
    
    log_group_name = f'/aws/lambda/{function_name}'
    
    try:
        # Get the log streams
        log_streams = logs_client.describe_log_streams(
            logGroupName=log_group_name,
            orderBy='LastEventTime',
            descending=True,
            limit=n 
        )
        
        for log_stream in log_streams['logStreams']:
            log_stream_name = log_stream['logStreamName']
            
            # Get log events from the log stream
            log_events = logs_client.get_log_events(
                logGroupName=log_group_name,
                logStreamName=log_stream_name,
                startFromHead=True
            )
            
            print(f"Log stream: {log_stream_name}")
            for event in log_events['events']:
                print(event['message'])
    
    except ClientError as e:
        print(f'Error retrieving logs: {e}')


def create_dynamodb_table(table_name='ImageRecognitionResults', region='us-west-2'):
    dynamodb = boto3.client('dynamodb', region_name=region)

    existing_tables = dynamodb.list_tables()['TableNames']

    if table_name in existing_tables:
        print(f"Table {table_name} already exists. Deleting...")
        dynamodb.delete_table(TableName=table_name)
        dynamodb.get_waiter('table_not_exists').wait(TableName=table_name)
        print(f"Table {table_name} deleted successfully.")

    response = dynamodb.create_table(
        TableName=table_name,
        AttributeDefinitions=[
            {
                'AttributeName': 'id',
                'AttributeType': 'S'
            },
            {
                'AttributeName': 'time',
                'AttributeType': 'N'  # 'N' is used for numbers (integers, floats, decimals)
            },
        ],
        KeySchema=[
            {
                'AttributeName': 'id',
                'KeyType': 'HASH'
            },
            {
                'AttributeName': 'time',
                'KeyType': 'RANGE'
            }
        ],
        ProvisionedThroughput={
            'ReadCapacityUnits': 5,
            'WriteCapacityUnits': 5
        }
    )
    print(f"Creating {table_name} table...")
    dynamodb.get_waiter('table_exists').wait(TableName=table_name)
    print(f"Table {table_name} created successfully.")


def read_dynamodb_table(table_name, region: str ='us-west-2'):
    dynamodb_client = boto3.resource('dynamodb', region_name='us-west-2')
    table = dynamodb_client.Table(table_name)

    try:
        response = table.scan()
        data = response['Items']

        while 'LastEvaluatedKey' in response:
            response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
            data.extend(response['Items'])

        return data

    except Exception as e:
        print(f"Error reading from DynamoDB: {e}")
        return None
    

def convert_decimals(obj):
    """
    Helper function to convert DynamoDB Decimals to float for JSON serialization.
    """
    if isinstance(obj, list):
        return [convert_decimals(i) for i in obj]
    elif isinstance(obj, dict):
        return {k: convert_decimals(v) for k, v in obj.items()}
    elif isinstance(obj, Decimal):
        return float(obj)
    else:
        return obj
    
def upload_and_track_time(bucket, image_file):
    """
    Uploads a single image to S3 and tracks the time taken.
    """
    start_time = time.time()
    upload_file_to_s3(bucket, image_file, image_file.name)
    end_time = time.time()
    elapsed_time = end_time - start_time
    return image_file.name, elapsed_time

def aws_exec(input_folder: Path, output_path: str, bucket: str, dynamo_table_name: str):
    """
    Uploads images to S3 to trigger Lambda and retrieves predictions from DynamoDB.
    """
    upload_times = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(upload_and_track_time, bucket, image_file) for image_file in input_folder.glob('*.jpg')]
        for future in concurrent.futures.as_completed(futures):
            image_name, elapsed_time = future.result()
            upload_times.append({'image_name': image_name, 'upload_time': elapsed_time})
            print(f"Uploaded {image_name} in {elapsed_time:.2f} seconds")

    # Allow some time for Lambda processing (adjust as necessary)
    time.sleep(120) 

    predictions = read_dynamodb_table(dynamo_table_name)
    predictions = convert_decimals(predictions)

    with open(output_path, 'w') as f:
        json.dump(predictions, f, indent=2)

    with open(output_path.replace('.', '_transfer_time.'), 'w') as f:
        json.dump(upload_times, f, indent=2)

    print(f"AWS predictions saved to {output_path}")