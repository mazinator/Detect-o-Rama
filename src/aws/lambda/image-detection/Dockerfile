FROM public.ecr.aws/lambda/python:3.11

RUN pip install boto3 opencv-python-headless numpy

# Copy the YOLO files
COPY yolov3-tiny.weights /opt/yolov3-tiny.weights
COPY yolov3-tiny.cfg /opt/yolov3-tiny.cfg
COPY coco.names /opt/coco.names

# Copy the function code
COPY lambda_function.py ${LAMBDA_TASK_ROOT}

# Set the CMD to your handler
CMD ["lambda_function.lambda_handler"]
