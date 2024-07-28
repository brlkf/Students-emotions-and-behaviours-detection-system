import os
import sys
from bson import ObjectId
import tkinter as tk
from tkinter import Label, Frame
import cv2
import traceback
from PIL import Image, ImageTk
import time
import numpy as np
from datetime import datetime
from conn import get_db
from face_recognition import detect_and_encode, recognize_faces, load_known_faces
from emotions import detect_emotion
from behavior_detection import detect_behavior
from mtcnn_init import mtcnn  # Import MTCNN from the new module
import main_page  # Import main_page

# MongoDB setup
db = get_db()

def save_record(db, class_id, created_by):
    record = {
        "classID": class_id,
        "date": datetime.now(),
        "created_by": created_by,
        "overall_performance": 0  # Initialize overall_performance
    }
    return db['records'].insert_one(record).inserted_id

def get_behavior_weights():
    behavior_weights = {}
    behaviors = db['behavior'].find()
    for behavior in behaviors:
        behavior_weights[behavior['behavior']] = behavior['weight']
    return behavior_weights

class CombinedApp:
    def __init__(self, window, window_title, class_id, username):
        self.window = window
        self.window.title(window_title)

        self.class_id = class_id
        self.created_by = username
        self.record_id = None

        # Load known faces
        self.known_face_encodings, self.known_face_names, self.known_face_ids = load_known_faces(db)

        # Create a main frame
        self.main_frame = tk.Frame(window)
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # Create a frame for the video and controls
        self.video_frame = tk.Frame(self.main_frame)
        self.video_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Open the video source
        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            print("Failed to open video source")
            return

        # Set the resolution to a larger size
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)

        # Create a canvas to display the video
        self.canvas = tk.Canvas(self.video_frame, width=1280, height=720)
        self.canvas.pack()

        # Create a frame for the buttons
        self.button_frame = tk.Frame(self.video_frame)
        self.button_frame.pack(side=tk.BOTTOM, fill=tk.X)

        # Button to start the camera
        self.btn_start = tk.Button(self.button_frame, text="Start", width=15, command=self.start_camera)
        self.btn_start.pack(side=tk.LEFT)

        # Button to pause the camera
        self.btn_pause = tk.Button(self.button_frame, text="Pause", width=15, command=self.pause_camera)
        self.btn_pause.pack(side=tk.LEFT)

        # Button to stop the camera
        self.btn_stop = tk.Button(self.button_frame, text="Stop", width=15, command=self.stop_camera)
        self.btn_stop.pack(side=tk.LEFT)

        # Create a frame for the right panel
        self.right_panel = tk.Frame(self.main_frame)
        self.right_panel.pack(side=tk.RIGHT, fill=tk.Y)

        # Add toggle buttons
        self.emotion_var = tk.BooleanVar(value=True)
        self.face_var = tk.BooleanVar(value=True)
        self.behavior_var = tk.BooleanVar(value=True)

        tk.Checkbutton(self.right_panel, text="Emotion Detection", variable=self.emotion_var).pack(pady=5)
        tk.Checkbutton(self.right_panel, text="Face Recognition", variable=self.face_var).pack(pady=5)
        tk.Checkbutton(self.right_panel, text="Behavior Detection", variable=self.behavior_var).pack(pady=5)
        
        # Label to display FPS
        self.label_fps = tk.Label(self.video_frame, text="FPS: 0", font=("Helvetica", 16))
        self.label_fps.pack(anchor=tk.CENTER, expand=True)

        # Create a frame for class details
        self.details_frame = tk.Frame(self.main_frame)
        self.details_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self.window.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.running = False
        self.paused = False

        # Track detection history
        self.behavior_history = {}
        self.emotion_history = {}

        # Display class details
        self.display_class_details()

        self.update()

    def display_class_details(self):
        try:
            class_info = db['classes'].find_one({"_id": ObjectId(self.class_id)})
            if class_info:
                details = (
                    f"Class Name: {class_info['name']}\n"
                    f"Class Type: {class_info['type']}\n"
                    f"Weekday: {class_info['weekday']}\n"
                    f"Time: {class_info['time']}\n"
                    f"Created By: {class_info['createdBy']}\n"
                    f"Summary: {class_info['summary']} students"
                )
                tk.Label(self.details_frame, text=details, font=("Helvetica", 14)).pack(pady=10)
            else:
                tk.Label(self.details_frame, text="Class details not found.", font=("Helvetica", 14)).pack(pady=10)
        except Exception as e:
            tk.Label(self.details_frame, text=f"Error retrieving class details: {e}", font=("Helvetica", 14)).pack(pady=10)

    def start_camera(self):
        self.running = True
        self.paused = False
        self.record_id = save_record(db, self.class_id, self.created_by)  # Save the record when starting the camera
        self.update() 
        
    def pause_camera(self):
        self.paused = not self.paused
        if self.paused:
            self.btn_pause.config(text="Resume")
        else:
            self.btn_pause.config(text="Pause")

    def stop_camera(self):
        self.running = False
        self.cap.release()

        self.save_all_to_db()
        self.calculate_overall_performance()  # Calculate overall performance
        self.window.destroy()
        
        # Run the main_page script
        main_page.main_page(self.created_by)
    
    def save_all_to_db(self):
        for student_id, emotions in self.emotion_history.items():
            for emotion, timestamp in emotions.items():
                save_emotion_to_db(db, student_id, emotion, self.class_id, self.record_id)
        for student_id, behaviors in self.behavior_history.items():
            for behavior, timestamp in behaviors.items():
                save_behavior_to_db(db, student_id, behavior, self.class_id, self.record_id)



    def calculate_overall_performance(self):
          # Get weights for each behavior from the behavior collection
        behavior_weights = get_behavior_weights()
        
        total_weight = 0
        total_behaviors = 0

        for student_id, behaviors in self.behavior_history.items():
            for behavior in behaviors:
                total_weight += behavior_weights.get(behavior, 0)
                total_behaviors += 1

        overall_performance = (total_weight / (total_behaviors * 20)) * 100 if total_behaviors > 0 else 0

        # Update the record with the overall performance
        db['records'].update_one(
            {"_id": ObjectId(self.record_id)},
            {"$set": {"overall_performance": overall_performance}}
        )

    def update(self):
        if self.running and not self.paused:
            start_time = time.time()
            ret, frame = self.cap.read()
            if ret:
                # Face detection and recognition
                if self.face_var.get():
                    try:
                        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        test_face_encodings = detect_and_encode(frame_rgb)
                        print(f"Detected {len(test_face_encodings)} faces")

                        if test_face_encodings:
                            for test_encoding, box in zip(test_face_encodings, mtcnn.detect(frame_rgb)[0]):
                                student_id, student_name = self.get_student_info(test_encoding, "face")
                                print(f"Student ID: {student_id}, Student Name: {student_name}")
                                if student_id and student_name and box is not None:
                                    (x1, y1, x2, y2) = map(int, box)
                                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                                    cv2.putText(frame, student_name, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2, cv2.LINE_AA)

                                    # Save the student information based on the detected name
                                    if student_name:
                                        detected_student_id, detected_student_name = self.get_student_info(test_encoding, "face")
                                        if detected_student_id and detected_student_name:
                                            # Add logic to save or handle detected student information
                                            print(f"Detected student for saving: ID={detected_student_id}, name={detected_student_name}")
                    except Exception as e:
                        print(f"Face recognition failed: {e}")


                # Detect emotions
                if self.emotion_var.get():
                    try:
                        emotions = self.process_emotion_detection(frame)
                        current_time = time.time()
                        for emotion, landmarks in emotions:
                            # Convert landmarks to a format suitable for get_student_info
                            face_encoding = self.get_face_encoding(frame, landmarks)
                            print(f"Face encoding shape: {face_encoding.shape}")
                            print(f"Landmarks shape: {landmarks.shape}")
                            try:
                                emotion_student_id, emotion_student_name = self.get_student_info(face_encoding, "emotion")
                                print(f"Emotion Detection: Student ID: {emotion_student_id}, Student Name: {emotion_student_name}")
                            except Exception as e:
                                print(f"Error in get_student_info: {e}")
                                print(f"Traceback: {traceback.format_exc()}")
                                continue
                            
                            if emotion_student_id and emotion_student_name:
                                if emotion_student_id not in self.emotion_history:
                                    self.emotion_history[emotion_student_id] = {}
                                if emotion not in self.emotion_history[emotion_student_id]:
                                    self.emotion_history[emotion_student_id][emotion] = current_time

                                # Draw landmarks and emotion label
                                for (x, y, _) in landmarks:
                                    cv2.circle(frame, (int(x), int(y)), 1, (0, 255, 0), -1)
                                
                                # Use the first landmark for text positioning
                                text_x, text_y, _ = landmarks[0]
                                cv2.putText(frame, f'Emotion: {emotion}', (int(text_x), int(text_y) - 10), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2, cv2.LINE_AA)
                    except Exception as e:
                        print(f"Emotion detection failed: {e}")
                        print(f"Traceback: {traceback.format_exc()}")


                # Perform YOLOv5 inference for behavior detection
                if self.behavior_var.get():
                    try:
                        results = detect_behavior(frame)
                        if isinstance(results, list):
                            print(f"YOLOv5 inference results: {results}")  # Debug statement
                            current_time = time.time()
                            for behavior in results:
                                behavior_label = behavior['name']
                                xmin, ymin, xmax, ymax = behavior['xmin'], behavior['ymin'], behavior['xmax'], behavior['ymax']
                                # Here we extract an encoding for the detected region
                                region = frame[int(ymin):int(ymax), int(xmin):int(xmax)]
                                region_rgb = cv2.cvtColor(region, cv2.COLOR_BGR2RGB)
                                test_face_encodings = detect_and_encode(region_rgb)
                                if test_face_encodings:
                                    detected_encoding = test_face_encodings[0]
                                    student_id, student_name = self.get_student_info(detected_encoding, "behavior")
                                    if student_id and student_name:
                                        if student_id not in self.behavior_history:
                                            self.behavior_history[student_id] = {}
                                        if behavior_label not in self.behavior_history[student_id]:
                                            self.behavior_history[student_id][behavior_label] = current_time
                                        else:
                                            if current_time - self.behavior_history[student_id][behavior_label] >= 10:
                                                save_behavior_to_db(db, student_id, behavior_label, self.class_id, self.record_id)
                                                del self.behavior_history[student_id][behavior_label]

                                        # Optionally, draw bounding boxes on the image
                                        cv2.rectangle(frame, (int(xmin), int(ymin)), (int(xmax), int(ymax)), (0, 0, 255), 2)
                        else:
                            print(f"YOLOv5 inference failed: Invalid results object")
                    except Exception as e:
                        print(f"YOLOv5 inference failed: {e}")

                # Convert the frame to RGB
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

                # Convert the frame to a format suitable for Tkinter
                frame_pil = Image.fromarray(frame)
                frame_tk = ImageTk.PhotoImage(image=frame_pil)

                # Update the canvas with the new frame
                self.canvas.create_image(0, 0, anchor=tk.NW, image=frame_tk)
                self.canvas.image = frame_tk

                # Calculate and display FPS
                end_time = time.time()
                fps = 1 / (end_time - start_time)
                self.label_fps.config(text=f"FPS: {fps:.2f}")

            self.window.after(10, self.update)

    def get_student_info(self, detected_encoding, type):
        if not self.known_face_encodings:
            return None, None

        print(f"Detected encoding shape: {detected_encoding.shape}")
        print(f"Known encoding shape: {self.known_face_encodings[0].shape}")

        if detected_encoding.shape != self.known_face_encodings[0].shape:
            print("Shape mismatch detected. Using alternative comparison method.")
            
            from scipy.spatial.distance import cosine
            distances = [cosine(detected_encoding, known_encoding[:3]) for known_encoding in self.known_face_encodings]
            print(f"Using cosine similarity distances: {distances}")
        else:
            distances = [np.linalg.norm(detected_encoding - known_encoding) for known_encoding in self.known_face_encodings]
            print(f"Using Euclidean distances: {distances}")

        if not distances:
            return None, None

        min_distance_index = np.argmin(distances)
        min_distance = distances[min_distance_index]
        print(f"Min distance: {min_distance}")

        threshold = 0.3 if detected_encoding.shape != self.known_face_encodings[0].shape else 0.7

        if min_distance < threshold:
            student_id = self.known_face_ids[min_distance_index]
            student_name = self.known_face_names[min_distance_index]
            print(f"Identified student: ID={student_id}, name={student_name}, type={type}")
            return student_id, student_name
        return None, None


    def on_closing(self):
        self.running = False
        self.cap.release()
        self.window.destroy()
        
    def process_emotion_detection(self, frame):
        try:
            emotions = detect_emotion(frame)
            detected_emotions = []  # List to store detected emotions and their landmarks
            
            for emotion, landmarks in emotions:
                face_encoding = self.get_face_encoding(frame, landmarks)  # Get face encoding using the same method as face recognition
                print(f"Emotion Detection: Face encoding shape: {face_encoding.shape}")
                print(f"Emotion Detection: Landmarks shape: {landmarks.shape}")
                try:
                    student_id, student_name = self.get_student_info(face_encoding, "emotion")
                    print(f"Emotion Detection: Student ID: {student_id}, Student Name: {student_name}")
                except Exception as e:
                    print(f"Error in get_student_info during emotion detection: {e}")
                    print(f"Traceback: {traceback.format_exc()}")
                    continue

                if student_id and student_name:
                    if student_id not in self.emotion_history:
                        self.emotion_history[student_id] = {}
                    if emotion not in self.emotion_history[student_id]:
                        self.emotion_history[student_id][emotion] = time.time()
                    detected_emotions.append((emotion, landmarks))
                    for (x, y, _) in landmarks:
                        cv2.circle(frame, (int(x), int(y)), 1, (0, 255, 0), -1)

                    text_x, text_y, _ = landmarks[0]
                    cv2.putText(frame, f'Emotion: {emotion}', (int(text_x), int(text_y) - 10), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2, cv2.LINE_AA)
                        
            return detected_emotions
        except Exception as e:
            print(f"Emotion detection failed: {e}")
            print(f"Traceback: {traceback.format_exc()}")
            return []

    def get_face_encoding(self, frame, landmarks):
        # Convert landmarks to a format suitable for face_recognition
        face_encoding = detect_and_encode(frame)  # Use the same method as face recognition
        if face_encoding:
            return face_encoding[0]
        else:
            return np.zeros((512,))  # Return a zero vector if no encoding is found



def save_emotion_to_db(db, student_id, emotion_label, class_id, record_id):
    try:
        # Check if an entry already exists for the student and record
        existing_record = db['emotion_history'].find_one({"studentID": student_id, "recordID": record_id})
        
        if existing_record:
            # Update the existing record with the new emotion
            db['emotion_history'].update_one(
                {"_id": existing_record["_id"]},
                {"$addToSet": {"emotions": emotion_label}}  # Use addToSet to avoid duplicates in the list
            )
        else:
            # Insert a new record
            db['emotion_history'].insert_one({
                "studentID": student_id,
                "emotions": [emotion_label],  # Store emotions as a list
                "recordID": record_id
            })
    except Exception as e:
        print(f"Failed to save emotion {emotion_label} for student {student_id}: {e}")

def save_behavior_to_db(db, student_id, behavior_label, class_id, record_id):
    try:
        # Check if an entry already exists for the student and record
        existing_record = db['behavior_history'].find_one({"studentID": student_id, "recordID": record_id})
        
        if existing_record:
            # Update the existing record with the new behavior
            db['behavior_history'].update_one(
                {"_id": existing_record["_id"]},
                {"$addToSet": {"behaviors": behavior_label}}  # Use addToSet to avoid duplicates in the list
            )
        else:
            # Insert a new record
            db['behavior_history'].insert_one({
                "studentID": student_id,
                "behaviors": [behavior_label],  # Store behaviors as a list
                "recordID": record_id
            })
    except Exception as e:
        print(f"Failed to save behavior {behavior_label} for student {student_id}: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 2:
        class_id = sys.argv[1]
        username = sys.argv[2]
        root = tk.Tk()
        app = CombinedApp(root, "Student Behavior Detection", class_id, username)
        root.mainloop()
    else:
        print("Class ID or Username not provided.")