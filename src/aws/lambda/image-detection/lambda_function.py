import json
import boto3
import cv2
import numpy as np
from decimal import Decimal
from time import time

# Local file paths
YOLO_WEIGHTS_PATH = '/opt/yolov3-tiny.weights'
YOLO_CFG_PATH = '/opt/yolov3-tiny.cfg'
COCO_NAMES_PATH = '/opt/coco.names'

DYNAMODB_TABLE_NAME = 'ImageRecognitionResults'


def lambda_handler(event, context):

    for record in event['Records']:

        t = time()

        bucket_name = record['s3']['bucket']['name']
        image_name = record['s3']['object']['key'] 

        s3_client = boto3.client('s3', region_name='us-west-2')
        image_obj = s3_client.get_object(Bucket=bucket_name, Key=image_name)
        image_content = image_obj['Body'].read()

        # Load YOLO model
        net = cv2.dnn.readNetFromDarknet(YOLO_CFG_PATH, YOLO_WEIGHTS_PATH)
        layer_names = net.getLayerNames()
        output_layers = [layer_names[i - 1] for i in net.getUnconnectedOutLayers()]

        # Read coco.names file
        with open(COCO_NAMES_PATH, 'r') as f:
            labels = f.read().strip().split('\n')

        nparr = np.frombuffer(image_content, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        # Perform object detection
        blob = cv2.dnn.blobFromImage(img, 0.00392, (416, 416), (0, 0, 0), True, crop=False)
        net.setInput(blob)
        outs = net.forward(output_layers)

        confidences = []
        class_ids = []
        boxes = []

        for out in outs:
            for detection in out:
                scores = detection[5:]
                class_id = np.argmax(scores)
                confidence = scores[class_id]   
                if confidence > 0.5:
                    center_x = int(detection[0] * img.shape[1])
                    center_y = int(detection[1] * img.shape[0])
                    w = int(detection[2] * img.shape[1])
                    h = int(detection[3] * img.shape[0])
                    x = int(center_x - w / 2)
                    y = int(center_y - h / 2)
                    boxes.append([x, y, w, h])
                    confidences.append(float(confidence))
                    class_ids.append(class_id)
        
        indexes = cv2.dnn.NMSBoxes(boxes, confidences, 0.5, 0.4)
        
        detected_objects = []
        for i in range(len(boxes)):
            if i in indexes:
                label = str(labels[class_ids[i]])
                confidence = confidences[i]
                detected_objects.append({
                    "label": label,
                    "accuracy": confidence
                })

        result = { "id": image_name, "time": time() - t, "objects": detected_objects }
        print(json.dumps(result))
        result = json.loads(json.dumps(result), parse_float=Decimal)

        try:

            dynamodb_client = boto3.resource('dynamodb', region_name='us-west-2')
            table = dynamodb_client.Table(DYNAMODB_TABLE_NAME)
            
            table.put_item(
                Item=result
            )
            print("Results stored in DynamoDB successfully")
        except Exception as e:
            print(f"Error storing results in DynamoDB: {e}")
            return {
                'statusCode': 500,
                'body': json.dumps({'error': str(e)})
            }