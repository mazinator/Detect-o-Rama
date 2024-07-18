"""
Script which communicates with the local server given the parameters from the client (client.app).
Outsourced to keep client.app light.
"""
import os, base64, uuid, requests, json, time

"""
Send image to the local server.
"""
def send_image_local(image_path, endpoint):
    with open(image_path, 'rb') as image_file:
        image_data = image_file.read()

    encoded_image = base64.b64encode(image_data).decode('utf-8')
    image_id = str(uuid.uuid4())

    payload = {
        'id': image_id,
        'image_data': encoded_image
    }

    start_time = time.time()
    response = requests.post(endpoint, json=payload)
    end_time = time.time()

    duration = (end_time - start_time)*1000  #in ms

    if response.status_code == 200:
        print(f'Successfully processed: {image_path.name}')
        print(response.json())
    else:
        print(f'Failed to process: {image_path.name} (status code {response.status_code})')
    return response, duration


"""
This function gets called from client.py to send all images
from input_folder to endpoint and store the result in output_path
"""


def local_exec(input_folder, endpoint, output_path):
    output = []

    for image_file in input_folder.glob('*.jpg'):
        response, duration = send_image_local(image_file, endpoint)
        result = response.json()
        result["input_image"] = str(image_file)
        result["duration_ms"] = duration
        output.append(result)

    if os.path.exists(output_path):
        os.remove(output_path)
    with open(output_path, 'w') as f:
        json.dump(output, f)
