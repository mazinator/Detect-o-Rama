"""
Local rest server performing the object detection on the local machine.

Notes:
    - cv2 needs a numpy version < 2, e.g. 1.26.4 works fine
    - To run in debug mode, include the following 2 lines
      in .venv/bin/activate at the end of the file:
        export FLASK_ENV=development
        export FLASK_DEBUG=1
"""
import base64, cv2, os
import numpy as np
from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)
app.config['DEBUG'] = os.getenv('FLASK_DEBUG', 'False').lower() in ['true', '1', 't', 'yes']

class Yolo:
    def __init__(self, config_path, weights_path, names_path):

        """
        - Load weights, config, labels
        - Set output_layers
        """
        self.net = cv2.dnn.readNetFromDarknet(config_path, weights_path)
        self.layer_names = self.net.getLayerNames()
        self.output_layers = [self.layer_names[i - 1] for i in self.net.getUnconnectedOutLayers()]
        self.labels = open(names_path).read().strip().split('\n')

    """
    Detects objects in image and returns the result as json-object
    """
    def detect(self, image):

        # Scale image and perform mean subtraction, get network output
        blob = cv2.dnn.blobFromImage(image, 0.00392, (416, 416), (0, 0, 0), True, crop=False)
        self.net.setInput(blob)
        outs = self.net.forward(self.output_layers)

        confidences = []
        class_ids = []

        for out in outs:
            for detection in out:
                scores = detection[5:]
                class_id = np.argmax(scores)
                confidence = scores[class_id]

                # only take objects with accuracy > 0.5
                if confidence > 0.5:
                    confidences.append(float(confidence))
                    class_ids.append(class_id)

        objects = [{"label": str(self.labels[class_ids[i]]), "accuracy": confidences[i]} for i in range(len(confidences))]

        return {
            "objects": objects
        }


# Set paths + load YOLOv3-tiny model
config_path = '../../yolo_tiny_configs/yolov3-tiny.cfg'
weights_path = '../../yolo_tiny_configs/yolov3-tiny.weights'
names_path = '../../yolo_tiny_configs/coco.names'
yolo = Yolo(config_path, weights_path, names_path)


"""
endpoint for receiving image requests
returns json-file containing uuid + detected objects
"""
@app.route('/api/object_detection', methods=['POST'])
def receive_image():
    data = request.get_json()

    # Respond with 400 if (parts of) content is missing
    if 'id' not in data or 'image_data' not in data:
        return jsonify({"error": "Invalid input"}), 400

    # Convert image to binary
    image_id = data['id']
    image_data = data['image_data']
    image_bytes = base64.b64decode(image_data)
    image = np.frombuffer(image_bytes, np.uint8)
    image = cv2.imdecode(image, cv2.IMREAD_COLOR)

    objects = yolo.detect(image)

    return jsonify({"id": image_id, "objects": objects})


"""
Specify port here if needed
"""
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5003)
