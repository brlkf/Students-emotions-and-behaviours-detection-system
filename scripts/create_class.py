import sys
from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
                               QPushButton, QComboBox, QTreeWidget, QTreeWidgetItem, QFileDialog,
                               QMessageBox, QScrollArea)
from PySide6.QtGui import QFont
from PySide6.QtCore import Qt
import pandas as pd
import subprocess
from datetime import datetime
from bson import ObjectId
from conn import get_db

# Connect to MongoDB
db = get_db()
class_collection = db["classes"]
student_collection = db["students"]
intake_collection = db["intake"]

class CreateClassPage(QWidget):
    def __init__(self, username):
        super().__init__()
        self.username = username
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Create Class')
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
            QLineEdit, QComboBox {
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
        title = QLabel("Create New Class")
        title.setAlignment(Qt.AlignCenter)
        title.setFont(QFont('Arial', 24, QFont.Bold))
        scroll_layout.addWidget(title)

        # Class details
        form_layout = QVBoxLayout()

        self.class_name = self.create_form_row("Class Name", QLineEdit(), form_layout)
        self.class_type = self.create_form_row("Class Type", QComboBox(), form_layout)
        self.class_type.addItems(["Lecture", "Tutorial"])
        self.class_weekday = self.create_form_row("Class Weekday", QComboBox(), form_layout)
        self.class_weekday.addItems(["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"])

        times = [f"{h:02}:{m:02}" for h in range(8, 19) for m in (0, 15, 30, 45)] + ["19:00"]
        self.start_time = self.create_form_row("Start Time", QComboBox(), form_layout)
        self.start_time.addItems(times)
        self.end_time = self.create_form_row("End Time", QComboBox(), form_layout)
        self.end_time.addItems(times[1:])

        self.start_time.currentIndexChanged.connect(self.update_end_time_options)

        self.intake_combo = self.create_form_row("Intake", QComboBox(), form_layout)
        self.intake_combo.addItem("Select intake", None)
        self.load_intake_options()
        self.intake_combo.currentIndexChanged.connect(self.load_students_in_intake)

        self.status = self.create_form_row("Status", QComboBox(), form_layout)
        self.status.addItems(["Active", "Inactive"])
        self.summary = self.create_form_row("Summary", QLineEdit(), form_layout)
        self.summary.setReadOnly(True)
        self.created_by = self.create_form_row("Created By", QLineEdit(), form_layout)
        self.created_by.setText(self.username)
        self.created_by.setReadOnly(True)

        scroll_layout.addLayout(form_layout)

        # Student Tree
        self.student_tree = QTreeWidget()
        self.student_tree.setHeaderLabels(["Name", "TP Number"])
        scroll_layout.addWidget(self.student_tree)

        # Buttons
        button_layout = QHBoxLayout()
        create_button = QPushButton("Create")
        create_button.clicked.connect(self.create_class)
        clear_button = QPushButton("Clear")
        clear_button.clicked.connect(self.clear_students)
        manage_intakes_button = QPushButton("Manage Intakes")  # Add button to manage intakes
        manage_intakes_button.clicked.connect(self.manage_intakes)
        back_button = QPushButton("Back")
        back_button.clicked.connect(self.go_back)

        button_layout.addWidget(create_button)
        button_layout.addWidget(clear_button)
        button_layout.addWidget(manage_intakes_button)  # Add button to layout
        button_layout.addWidget(back_button)

        scroll_layout.addLayout(button_layout)

        scroll_area.setWidget(scroll_content)
        main_layout.addWidget(scroll_area)

    def create_form_row(self, label_text, widget, layout):
        row_layout = QHBoxLayout()
        label = QLabel(label_text)
        row_layout.addWidget(label)
        row_layout.addWidget(widget)
        layout.addLayout(row_layout)
        return widget

    def load_intake_options(self):
        # Load intake options from the intake collection
        intakes = intake_collection.find({"created_by": self.username})
        for intake in intakes:
            self.intake_combo.addItem(intake["intake"], intake["_id"])

    def load_students_in_intake(self):
        self.student_tree.clear()
        intake_id = self.intake_combo.currentData()
        if intake_id:
            students = student_collection.find({"intake": intake_id})
            for student in students:
                item = QTreeWidgetItem(self.student_tree)
                item.setText(0, student["name"])
                item.setText(1, student["TPNumber"])
        self.summary.setText(str(self.student_tree.topLevelItemCount()))  # Update summary with student count

    def update_end_time_options(self):
        start_index = self.start_time.currentIndex()
        self.end_time.clear()
        self.end_time.addItems(self.start_time.itemText(i) for i in range(start_index + 1, self.start_time.count()))

    def create_class(self):
        class_name = self.class_name.text().strip()
        class_type = self.class_type.currentText().strip()
        class_weekday = self.class_weekday.currentText().strip()
        start_time = self.start_time.currentText().strip()
        end_time = self.end_time.currentText().strip()
        intake_id = self.intake_combo.currentData()
        status = self.status.currentText().strip()
        summary = self.student_tree.topLevelItemCount()  # Summary as a numeric value
        created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        if intake_id is None:
            QMessageBox.warning(self, "Input Error", "Please select a valid intake.")
            return

        if not all([class_name, class_type, class_weekday, start_time, end_time, intake_id, status]):
            QMessageBox.warning(self, "Input Error", "Please fill in all fields")
            return

        # Check if class with the same name, type, and weekday already exists
        if class_collection.find_one({"name": class_name, "type": class_type, "weekday": class_weekday}):
            QMessageBox.warning(self, "Creation Error", "Class with the same name, type, and weekday already exists")
            return

        # Insert class into class collection
        new_class = {
            "name": class_name,
            "type": class_type,
            "weekday": class_weekday,
            "time": f"{start_time} - {end_time}",
            "intake": intake_id,
            "status": status,
            "summary": summary,
            "createdBy": self.username,
            "created_at": created_at
        }
        class_collection.insert_one(new_class)
        class_id = new_class["_id"]

        # Insert students into student collection
        for i in range(self.student_tree.topLevelItemCount()):
            item = self.student_tree.topLevelItem(i)
            student_name = item.text(0).strip()
            tp_number = item.text(1).strip()

            if not all([student_name, tp_number]):
                QMessageBox.warning(self, "Input Error", "Student fields cannot contain only blank spaces")
                return

            student_doc = {
                "name": student_name,
                "TPNumber": tp_number,
                "intake": intake_id,
                "class_id": [class_id]  # Store class_id as an array
            }
            
            # Check if student already exists
            existing_student = student_collection.find_one({
                "name": student_doc["name"],
                "TPNumber": student_doc["TPNumber"],
                "intake": student_doc["intake"]
            })

            if existing_student:
                # Ensure class_id is an array
                if not isinstance(existing_student.get("class_id"), list):
                    existing_student["class_id"] = [existing_student["class_id"]]

                # Update the class_id array if the student already exists
                student_collection.update_one(
                    {"_id": existing_student["_id"]},
                    {"$addToSet": {"class_id": class_id}}
                )
            else:
                # Insert the new student document
                student_collection.insert_one(student_doc)

        QMessageBox.information(self, "Success", "Class and student details saved successfully!")
        self.clear_form()
        self.go_back()  # Navigate back to the main page

    def clear_students(self):
        self.student_tree.clear()
        self.summary.clear()

    def manage_intakes(self):
        self.close()
        subprocess.Popen(["python", "F:/FYP/scripts/intake.py", self.username])

    def go_back(self):
        self.close()
        subprocess.Popen(["python", "F:/FYP/scripts/main_page.py", self.username])

    def clear_form(self):
        self.class_name.clear()
        self.class_type.setCurrentIndex(0)
        self.class_weekday.setCurrentIndex(0)
        self.start_time.setCurrentIndex(0)
        self.end_time.setCurrentIndex(0)
        self.intake_combo.setCurrentIndex(0)
        self.status.setCurrentIndex(0)
        self.summary.clear()
        self.student_tree.clear()

def main(username):
    app = QApplication(sys.argv)
    ex = CreateClassPage(username)
    ex.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    if len(sys.argv) > 1:
        username = sys.argv[1]
        main(username)
    else:
        print("Username not provided.")
