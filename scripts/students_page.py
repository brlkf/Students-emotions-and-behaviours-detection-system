import re
import subprocess
import sys
import gridfs
import cv2
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QTreeWidget, QTreeWidgetItem, QMessageBox, QScrollArea, QDialog, QFormLayout, QComboBox
from PySide6.QtGui import QFont
from PySide6.QtCore import Qt
from PIL import Image
from io import BytesIO
from bson import ObjectId
from conn import get_db
from mtcnn_init import mtcnn  # Ensure this is correctly imported

# Connect to MongoDB
db = get_db()
student_collection = db["students"]
intake_collection = db["intake"]
class_collection = db["classes"]
fs = gridfs.GridFS(db)

class StudentsPage(QWidget):
    def __init__(self, username):
        super().__init__()
        self.username = username
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Students Details')
        self.setFixedSize(800, 700)
        self.setStyleSheet("""
            QWidget {
                background-color: #f0f0f0;
                font-family: Arial;
            }
            QLabel {
                color: #333;
                font-size: 14px;
            }
            QLineEdit {
                padding: 8px;
                border: 2px solid #ddd;
                border-radius: 5px;
                font-size: 14px;
            }
            QPushButton {
                padding: 10px;
                background-color: #3498db;
                color: white;
                border: none;
                border-radius: 5px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QTreeWidget {
                border: 2px solid #ddd;
                border-radius: 5px;
            }
        """)

        main_layout = QVBoxLayout(self)
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)

        # Title
        title = QLabel("Students Details")
        title.setAlignment(Qt.AlignCenter)
        title.setFont(QFont('Arial', 24, QFont.Bold))
        scroll_layout.addWidget(title)

        # Student Tree
        self.student_tree = QTreeWidget()
        self.student_tree.setHeaderLabels(["Name", "TP Number"])
        scroll_layout.addWidget(self.student_tree)
        self.load_students()

        # Buttons
        button_layout = QHBoxLayout()
        add_button = QPushButton("Add Student")
        add_button.clicked.connect(self.add_student)
        delete_button = QPushButton("Delete Student")
        delete_button.clicked.connect(self.delete_student)
        upload_button = QPushButton("Capture and Upload Image")
        upload_button.clicked.connect(self.capture_and_upload_image)
        back_button = QPushButton("Back")
        back_button.clicked.connect(self.go_back)

        button_layout.addWidget(add_button)
        button_layout.addWidget(delete_button)
        button_layout.addWidget(upload_button)
        button_layout.addWidget(back_button)

        scroll_layout.addLayout(button_layout)

        scroll_area.setWidget(scroll_content)
        main_layout.addWidget(scroll_area)

    def load_students(self):
        self.student_tree.clear()

        # Find all intakes created by the user
        user_intakes = list(intake_collection.find({"created_by": self.username}))
        user_intake_ids = [intake["_id"] for intake in user_intakes]

        # Find all students whose intake is in the user's intakes
        students = student_collection.find({"intake": {"$in": user_intake_ids}})
        
        # Group students by intake
        intake_groups = {}
        for student in students:
            intake_id = student.get('intake')
            if intake_id:
                intake = next((item for item in user_intakes if item['_id'] == intake_id), None)
                intake_name = intake['intake'] if intake else 'N/A'
            else:
                intake_name = 'N/A'
            
            if intake_name not in intake_groups:
                intake_groups[intake_name] = []
            intake_groups[intake_name].append(student)

        # Display students under their respective intake categories
        for intake_name, students in intake_groups.items():
            intake_item = QTreeWidgetItem(self.student_tree)
            intake_item.setText(0, intake_name)
            font = intake_item.font(0)
            font.setPointSize(12)  # Smaller font size for intake items
            intake_item.setFont(0, font)

            for student in students:
                student_item = QTreeWidgetItem(intake_item)
                student_item.setText(0, student.get('name', 'N/A'))
                student_item.setText(1, student.get('TPNumber', 'N/A'))
                student_item.setData(0, Qt.UserRole, str(student['_id']))

    def add_student(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Add Student")
        dialog.setFixedSize(500, 300)  # Increased size for better visibility
        
        layout = QVBoxLayout(dialog)
        form_layout = QFormLayout()
        
        name_edit = QLineEdit()
        form_layout.addRow("Student Name:", name_edit)
        
        tp_number_edit = QLineEdit()
        form_layout.addRow("TP Number:", tp_number_edit)
        
        class_combo = QComboBox()
        form_layout.addRow("Select Class:", class_combo)

        # Get the list of classes created by the user
        user_classes = list(class_collection.find({"createdBy": self.username}))
        for cls in user_classes:
            intake = intake_collection.find_one({"_id": cls["intake"]})
            intake_name = intake["intake"] if intake else "N/A"
            display_text = f"{cls['name']} ({cls['type']}, {cls['weekday']}, {cls['time']}, {intake_name})"
            class_combo.addItem(display_text, cls["_id"])
        
        layout.addLayout(form_layout)
        
        add_button = QPushButton("Add")
        add_button.clicked.connect(lambda: self.save_student(dialog, name_edit, tp_number_edit, class_combo, user_classes))
        layout.addWidget(add_button)
        
        dialog.setLayout(layout)
        dialog.exec_()

    def save_student(self, dialog, name_edit, tp_number_edit, class_combo, user_classes):
        name = name_edit.text().strip()
        tp_number = tp_number_edit.text().strip()
        class_id = class_combo.currentData()
        class_obj = next(cls for cls in user_classes if cls['_id'] == class_id)

        if not name:
            QMessageBox.warning(self, "Input Error", "Student name cannot be empty.")
            return

        if not tp_number:
            QMessageBox.warning(self, "Input Error", "TP Number cannot be empty.")
            return

        # Validate TP Number format
        if not re.match(r'^TP\d+$', tp_number):
            QMessageBox.warning(self, "Input Error", "TP Number must start with 'TP' followed by digits.")
            return

        # Check if the TP number already exists
        existing_student = student_collection.find_one({"TPNumber": tp_number})
        if existing_student:
            QMessageBox.warning(self, "Input Error", "This TP Number already exists.")
            return

        new_student = {
            "name": name,
            "TPNumber": tp_number,
            "intake": class_obj["intake"],
            "class_id": [class_obj["_id"]]
        }
        student_collection.insert_one(new_student)

        # Update class summary
        class_collection.update_one(
            {"_id": class_obj["_id"]},
            {"$inc": {"summary": 1}}
        )

        dialog.accept()
        self.load_students()  # Refresh the students list after adding

    def delete_student(self):
        selected_item = self.student_tree.currentItem()
        if selected_item and selected_item.parent():
            student_id = selected_item.data(0, Qt.UserRole)
            student = student_collection.find_one({"_id": ObjectId(student_id)})
            if student:
                class_id = student['class_id'][0]
                reply = QMessageBox.question(self, 'Delete Student', 'Are you sure you want to delete this student?', QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
                if reply == QMessageBox.Yes:
                    student_collection.delete_one({"_id": ObjectId(student_id)})
                    
                    # Update class summary
                    class_collection.update_one(
                        {"_id": class_id},
                        {"$inc": {"summary": -1}}
                    )
                    self.load_students()
        else:
            QMessageBox.warning(self, "Selection Error", "Please select a student to delete.")

    def capture_and_upload_image(self):
        selected_item = self.student_tree.currentItem()
        if not selected_item or not selected_item.parent():
            QMessageBox.warning(self, "Selection Error", "Please select a student.")
            return
        
        student_id = selected_item.data(0, Qt.UserRole)
        
        # Check if the student already has an image
        existing_image = student_collection.find_one({"_id": ObjectId(student_id), "profile_image_id": {"$exists": True}})
        if existing_image:
            reply = QMessageBox.question(self, 'Image Exists', 'This student already has an image. Do you want to recapture?', QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply == QMessageBox.No:
                return

        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            QMessageBox.critical(self, "Camera Error", "Failed to open camera.")
            return

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            boxes, _ = mtcnn.detect(frame)
            if boxes is not None and len(boxes) > 1:
                cv2.putText(frame, "Multiple faces detected. Please ensure only one face is visible.", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2, cv2.LINE_AA)
            elif boxes is not None and len(boxes) == 1:
                for box in boxes:
                    x1, y1, x2, y2 = map(int, box)
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

            cv2.imshow('Press Space to capture or ESC to exit', frame)

            key = cv2.waitKey(1)
            if key % 256 == 32:  # Space key pressed
                if boxes is not None and len(boxes) == 1:
                    img_name = "captured_image.png"
                    cv2.imwrite(img_name, frame)
                    break
                else:
                    QMessageBox.warning(self, "Face Detection Error", "Please ensure only one face is visible.")
            elif key % 256 == 27:  # ESC key pressed
                cap.release()
                cv2.destroyAllWindows()
                return

        cap.release()
        cv2.destroyAllWindows()

        if not ret or boxes is None or len(boxes) != 1:
            return

        # Convert the captured frame to an image
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(frame_rgb)

        # Save the image in a buffer
        buffer = BytesIO()
        pil_image.save(buffer, format="JPEG")
        img_binary = buffer.getvalue()

        # Store the image in MongoDB using GridFS
        try:
            self.store_image_in_mongo(img_binary, student_id)
            QMessageBox.information(self, "Success", "Image captured and uploaded successfully.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to upload image: {str(e)}")

    def store_image_in_mongo(self, img_binary, student_id):
        # Validate image
        try:
            image = Image.open(BytesIO(img_binary))
            image.verify()
        except (IOError, SyntaxError) as e:
            raise ValueError("Invalid image file")

        # Check if the student already has an image and delete it if exists
        existing_image = student_collection.find_one({"_id": ObjectId(student_id), "profile_image_id": {"$exists": True}})
        if existing_image:
            old_image_id = existing_image["profile_image_id"]
            fs.delete(ObjectId(old_image_id))

        # Store the new image using GridFS
        image_id = fs.put(img_binary, filename=f"{student_id}_profile_image")
        
        # Update the student document with the GridFS file ID
        student_collection.update_one(
            {"_id": ObjectId(student_id)},
            {"$set": {"profile_image_id": image_id}}
        )

    def go_back(self):
        self.close()
        subprocess.Popen(["python", "F:/FYP/scripts/main_page.py", self.username])

def main(username):
    app = QApplication(sys.argv)
    ex = StudentsPage(username)
    ex.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    if len(sys.argv) > 1:
        username = sys.argv[1]
        main(username)
    else:
        print("Username not provided.")
