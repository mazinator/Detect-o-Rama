"""
Script to perform an object detection, either local or remote.
"""

from pathlib import Path
import argparse
from src.local.local_exec import *
from src.aws.utils import aws_exec

# Constants
BUCKET = 'image-bucket-11920555'
DYNAMODB_TABLE_NAME = 'ImageRecognitionResults'

def parse_args():
    """
    Defines command line arguments for the script.
    """
    parser = argparse.ArgumentParser(description="Run client for executing image detection")
    parser.add_argument('--input', default='input_folder/', help='Path to folder of image files')
    parser.add_argument('--exec_type', default='local', choices=['aws', 'local'], help='Execution type')
    parser.add_argument('--endpoint', default='http://localhost:5003/api/object_detection',
                        help='Endpoint if local execution')
    parser.add_argument('--output', default='./out/detections_local.json', help='Output path for execution')
    return parser.parse_args()


if __name__ == '__main__':
    args = parse_args()

    input_folder = Path(args.input)

    if args.exec_type == 'local':
        local_exec(input_folder, args.endpoint, args.output)
    elif args.exec_type == "aws":
        aws_exec(input_folder, args.output, BUCKET, DYNAMODB_TABLE_NAME)
