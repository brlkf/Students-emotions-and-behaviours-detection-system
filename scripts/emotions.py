from datetime import datetime
import cv2
import numpy as np
import mediapipe as mp
import tensorflow as tf
from tensorflow.keras.models import load_model
import torch

# Check PyTorch version and CUDA availability
print("PyTorch version:", torch.__version__)
cuda_available = torch.cuda.is_available()
print("CUDA available:", cuda_available)

if cuda_available:
    print("CUDA version:", torch.version.cuda)
    print("Number of GPUs:", torch.cuda.device_count())
    for i in range(torch.cuda.device_count()):
        print(f"GPU {i}: {torch.cuda.get_device_name(i)}")

# Verify TensorFlow GPU availability
gpus = tf.config.experimental.list_physical_devices('GPU')
if gpus:
    try:
        for gpu in gpus:
            tf.config.experimental.set_memory_growth(gpu, True)
        logical_gpus = tf.config.experimental.list_logical_devices('GPU')
        print(len(gpus), "Physical GPUs,", len(logical_gpus), "Logical GPUs")
    except RuntimeError as e:
        print(e)
else:
    print("No GPUs found for TensorFlow.")

# Initialize MediaPipe Face Mesh
mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(static_image_mode=False, max_num_faces=10, min_detection_confidence=0.2)

# Path to the emotion recognition model file
emotion_model_path = 'models/best_model.h5'
emotion_model = load_model(emotion_model_path)

# Emotion labels
emotion_labels = ['Angry', 'Disgust', 'Fear', 'Happy', 'Sad', 'Surprise', 'Neutral']

def detect_emotion(image):
    if face_mesh is None or emotion_model is None:
        return []

    rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    result = face_mesh.process(rgb_image)

    if not result.multi_face_landmarks:
        return []

    emotions = []
    for face_landmarks in result.multi_face_landmarks:
        landmarks = np.array([(lm.x, lm.y, lm.z) for lm in face_landmarks.landmark])
        h, w, _ = image.shape
        landmarks[:, 0] *= w
        landmarks[:, 1] *= h

        # Debug statements to print shapes
        print(f"Landmarks shape: {landmarks.shape}")
        preprocessed_image = preprocess_face_image(image, landmarks)
        
        if preprocessed_image is not None:
            # Check the shape of preprocessed image
            print(f"Preprocessed image shape: {preprocessed_image.shape}")
            # Ensure the prediction runs on GPU
            with tf.device('/GPU:0'):
                emotion_prediction = emotion_model.predict(np.expand_dims(preprocessed_image, axis=0))
            print(f"Emotion prediction shape: {emotion_prediction.shape}")
            emotion_index = np.argmax(emotion_prediction)
            emotion = emotion_labels[emotion_index]
            emotions.append((emotion, landmarks))
        else:
            print("Preprocessed image is None")

    return emotions

def preprocess_face_image(image, landmarks):
    try:
        x_min = int(min(landmarks[:, 0]))
        x_max = int(max(landmarks[:, 0]))
        y_min = int(min(landmarks[:, 1]))
        y_max = int(max(landmarks[:, 1]))
        
        h, w = image.shape[:2]
        x_min = max(0, x_min)
        x_max = min(w, x_max)
        y_min = max(0, y_min)
        y_max = min(h, y_max)
        
        if x_min >= x_max or y_min >= y_max:
            print(f"Invalid face boundaries: x_min={x_min}, x_max={x_max}, y_min={y_min}, y_max={y_max}")
            return None
        
        face_roi = image[y_min:y_max, x_min:x_max]
        
        if face_roi.size == 0:
            print("Face ROI has zero size")
            return None
        
        face_roi_resized = cv2.resize(face_roi, (48, 48))
        face_gray = cv2.cvtColor(face_roi_resized, cv2.COLOR_BGR2GRAY)
        face_gray_normalized = face_gray / 255.0
        return face_gray_normalized.reshape(48, 48, 1)
    except Exception as e:
        print(f"Error in preprocess_face_image: {e}")
        return None
