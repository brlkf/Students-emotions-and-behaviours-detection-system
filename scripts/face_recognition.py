import cv2
import numpy as np
import torch
from mtcnn_init import mtcnn, resnet  # Import MTCNN and Resnet from the new module

# Function to detect and encode faces
def detect_and_encode(image):
    with torch.no_grad():
        boxes, _ = mtcnn.detect(image)
        if boxes is not None:
            faces = []
            for box in boxes:
                face = image[int(box[1]):int(box[3]), int(box[0]):int(box[2])]
                if face.size == 0:
                    continue
                face = cv2.resize(face, (160, 160))
                face = np.transpose(face, (2, 0, 1)).astype(np.float32) / 255.0
                face_tensor = torch.tensor(face).unsqueeze(0)
                encoding = resnet(face_tensor).detach().numpy().flatten()
                faces.append(encoding)
            return faces
    return []

# Function to recognize faces
def recognize_faces(known_encodings, known_names, test_encodings, threshold=0.6):
    recognized_names = []
    for test_encoding in test_encodings:
        distances = np.linalg.norm(known_encodings - test_encoding, axis=1)
        if distances.size == 0:
            recognized_names.append('No match found')
        else:
            min_distance_idx = np.argmin(distances)
            if distances[min_distance_idx] < threshold:
                recognized_names.append(known_names[min_distance_idx])
            else:
                recognized_names.append('Not Recognized')
    return recognized_names

# Function to load known faces from MongoDB
def load_known_faces(db):
    import gridfs
    collection = db['students']
    fs = gridfs.GridFS(db)
    known_face_encodings = []
    known_face_names = []
    known_face_ids = []

    for student in collection.find():
        profile_image_id = student.get("profile_image_id")
        if profile_image_id:
            try:
                image_data = fs.get(profile_image_id).read()
                image_np = np.frombuffer(image_data, np.uint8)
                image = cv2.imdecode(image_np, cv2.IMREAD_COLOR)
                image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                encodings = detect_and_encode(image_rgb)
                if encodings:
                    known_face_encodings.append(encodings[0])
                    known_face_names.append(student["name"])
                    known_face_ids.append(student["_id"])
            except Exception as e:
                print(f"Failed to load or encode image for student {student['name']}: {e}")

    print(f"Loaded {len(known_face_encodings)} known faces.")

    return known_face_encodings, known_face_names, known_face_ids


