from datetime import datetime
import torch
import cv2
import numpy as np

# Path to the YOLOv5 model file
yolo_model_path = 'F:/FYP/yolov5/runs/train/exp3/weights/best.pt'  # Update this to the correct path

# Load the YOLOv5 model
yolo_model = torch.hub.load('ultralytics/yolov5', 'custom', path=yolo_model_path, force_reload=True)

def detect_behavior(frame):
    if yolo_model is None:
        return []

    results = yolo_model(frame)
    results.render()
    behavior_results = results.pandas().xyxy[0].to_dict(orient="records")
    return behavior_results

def save_behavior_to_db(db, student_id, behavior):
    behavior_history_collection = db['behavior_history']
    behavior_collection = db['behavior']

    try:
        existing_record = behavior_history_collection.find_one({"studentID": student_id})
        behavior_id = behavior_collection.find_one({"behavior": behavior})["_id"]
        if existing_record:
            behavior_history_collection.update_one(
                {"studentID": student_id},
                {"$addToSet": {"behavior": behavior_id}}
            )
        else:
            behavior_history_collection.insert_one({
                "studentID": student_id,
                "behavior": [behavior_id],
                "recordID": datetime.now().strftime('%Y%m%d%H%M%S')
            })
    except Exception as e:
        print(f"Failed to save behavior {behavior} for student {student_id}: {e}")