# Detect-o-Rama
 
Some code to perform object detection either locally or on AWS and compare the runtimes

## Functionality 

### Local server 

A local server which accepts POST-requests consisting of a unique identifier and a base64 encoded image. The local server uses a pretrained YOLO model and openCV python libraries to detect images and return the detected objects (including accuracy) as json together with the unique identifier.

### AWS Execution
The python notebook uses the AWS cloud for the object detection. This is realized by creating a S3 bucket, ECR registry, DynamoDB. Then a lambda function is created using a custom Docker image, which is triggered whenever an image is uploaded to the S3 bucket, which triggers the image processing and finally stores the result into DynamoDB.

## How to run

run client.py, check out the input parameters:

* --input: input folder with the images
* --exec_type: local or remote on AWS
* --endpoint: define local endpoint on which you run the local server (to be found under /src/local/local_server.py)
* --output: defines folder for created output