import sys
import requests
import threading
import time
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                               QLabel, QLineEdit, QPushButton, QComboBox, QTableWidget, 
                               QTableWidgetItem, QHeaderView, QMessageBox, QTextEdit)
from PySide6.QtCore import Qt, QTimer, QMetaObject, Q_ARG
from pymongo import MongoClient
from bson import ObjectId
from conn import get_db
import subprocess
from api import get_gemini_suggestions  # Import the Gemini API function

# Connect to MongoDB
db = get_db()

def fetch_record_details(username):
    pipeline = [
        {
            '$match': {
                'created_by': username  # Filter records by the username
            }
        },
        {
            '$addFields': {  # Ensure classID is treated as ObjectId
                'classID': { '$toObjectId': '$classID' }
            }
        },
        {
            '$lookup': {
                'from': 'classes',
                'localField': 'classID',
                'foreignField': '_id',
                'as': 'class_info'
            }
        },
        {
            '$unwind': {
                'path': '$class_info',
                'preserveNullAndEmptyArrays': True
            }
        },
        {
            '$lookup': {
                'from': 'users',
                'localField': 'created_by',
                'foreignField': 'username',
                'as': 'creator_info'
            }
        },
        {
            '$unwind': {
                'path': '$creator_info',
                'preserveNullAndEmptyArrays': True
            }
        },
        {
            '$lookup': {
                'from': 'behavior_history',
                'localField': '_id',
                'foreignField': 'recordID',
                'as': 'behavior_info'
            }
        },
        {
            '$lookup': {
                'from': 'emotion_history',
                'localField': '_id',
                'foreignField': 'recordID',
                'as': 'emotion_info'
            }
        },
        {
            '$lookup': {
                'from': 'students',
                'let': {
                    'behavior_student_ids': '$behavior_info.studentID',
                    'emotion_student_ids': '$emotion_info.studentID'
                },
                'pipeline': [
                    {
                        '$match': {
                            '$expr': {
                                '$or': [
                                    { '$in': ['$_id', '$$behavior_student_ids'] },
                                    { '$in': ['$_id', '$$emotion_student_ids'] }
                                ]
                            }
                        }
                    }
                ],
                'as': 'students'
            }
        },
        {
            '$addFields': {
                'behavior_students': {
                    '$filter': {
                        'input': '$students',
                        'as': 'student',
                        'cond': { '$in': ['$$student._id', '$behavior_info.studentID'] }
                    }
                },
                'emotion_students': {
                    '$filter': {
                        'input': '$students',
                        'as': 'student',
                        'cond': { '$in': ['$$student._id', '$emotion_info.studentID'] }
                    }
                }
            }
        },
        {
            '$project': {
                'class_name': {'$ifNull': ['$class_info.name', 'N/A']},
                'class_type': {'$ifNull': ['$class_info.type', 'N/A']},
                'date': 1,
                'creator_name': {'$ifNull': ['$creator_info.username', 'N/A']},
                'overall_performance': 1,
                'behaviors': {
                    '$map': {
                        'input': '$behavior_info',
                        'as': 'behavior',
                        'in': {
                            'student': {
                                '$arrayElemAt': [
                                    {
                                        '$filter': {
                                            'input': '$behavior_students',
                                            'as': 'student',
                                            'cond': { '$eq': ['$$student._id', '$$behavior.studentID'] }
                                        }
                                    },
                                    0
                                ]
                            },
                            'behavior': '$$behavior.behaviors'
                        }
                    }
                },
                'emotions': {
                    '$map': {
                        'input': '$emotion_info',
                        'as': 'emotion',
                        'in': {
                            'student': {
                                '$arrayElemAt': [
                                    {
                                        '$filter': {
                                            'input': '$emotion_students',
                                            'as': 'student',
                                            'cond': { '$eq': ['$$student._id', '$$emotion.studentID'] }
                                        }
                                    },
                                    0
                                ]
                            },
                            'emotions': '$$emotion.emotions'
                        }
                    }
                }
            }
        }
    ]

    results = db.records.aggregate(pipeline)
    return list(results)

class ModernRecordDetailsApp(QMainWindow):
    def __init__(self, username):
        super().__init__()
        self.username = username
        self.setWindowTitle("Record Details")
        self.setGeometry(100, 100, 1000, 800)
        self.setStyleSheet("""
            QMainWindow { background-color: #f0f0f0; }
            QLabel { font-size: 14px; }
            QLineEdit, QComboBox { 
                padding: 5px; 
                border: 1px solid #ccc; 
                border-radius: 3px; 
            }
            QPushButton { 
                background-color: #4CAF50; 
                color: white; 
                padding: 8px 15px; 
                border: none; 
                border-radius: 3px; 
            }
            QPushButton:hover { background-color: #45a049; }
            QTableWidget { 
                border: 1px solid #ddd;
                gridline-color: #ddd;
            }
            QHeaderView::section {
                background-color: #f2f2f2;
                padding: 5px;
                border: 1px solid #ddd;
                font-weight: bold;
            }
        """)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)

        self.setup_ui()
        self.load_data()

    def setup_ui(self):
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Class", "Date", "Created By", "Overall Performance"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.layout.addWidget(self.table)

        # Details Text Area
        self.details_text = QTextEdit()
        self.details_text.setReadOnly(True)
        self.layout.addWidget(self.details_text)

        # Buttons Layout
        buttons_layout = QHBoxLayout()
        
        # Delete Button
        delete_button = QPushButton("Delete")
        delete_button.setStyleSheet("background-color: #f44336;")
        delete_button.clicked.connect(self.delete_record)
        buttons_layout.addWidget(delete_button)
        
        # Back Button
        back_button = QPushButton("Back")
        back_button.clicked.connect(self.go_back)
        buttons_layout.addWidget(back_button)
        
  

        # Generate Suggestions Button
        suggestions_button = QPushButton("Generate Suggestions")
        suggestions_button.clicked.connect(self.generate_suggestions)
        buttons_layout.addWidget(suggestions_button)

        self.layout.addLayout(buttons_layout)

        # Connect signals
        self.table.itemSelectionChanged.connect(self.show_details)

        # Animation
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_animation)
        self.loading_text = QLabel("")
        self.loading_text.setAlignment(Qt.AlignCenter)
        self.loading_text.setVisible(False)
        self.layout.addWidget(self.loading_text)

    def load_data(self):
        self.table.setRowCount(0)
        self.records = fetch_record_details(self.username)

        for row, record in enumerate(self.records):
            self.table.insertRow(row)

            class_name = record.get('class_name', 'N/A')
            class_type = record.get('class_type', 'N/A')
            date = record.get('date', 'N/A')
            creator_name = record.get('creator_name', 'N/A')
            overall_performance = record.get('overall_performance', 'N/A')

            self.table.setItem(row, 0, QTableWidgetItem(f"{class_name} ({class_type})"))
            self.table.setItem(row, 1, QTableWidgetItem(str(date)))
            self.table.setItem(row, 2, QTableWidgetItem(str(creator_name)))
            self.table.setItem(row, 3, QTableWidgetItem(str(overall_performance)))

    def show_details(self):
        selected_items = self.table.selectedItems()
        if not selected_items:
            return

        row = selected_items[0].row()
        record = self.records[row]

        class_name = record.get('class_name', 'N/A')
        class_type = record.get('class_type', 'N/A')
        date = record.get('date', 'N/A')
        creator_name = record.get('creator_name', 'N/A')
        overall_performance = record.get('overall_performance', 'N/A')

        details = f"Class: {class_name} ({class_type})\n"
        details += f"Date: {date}\n"
        details += f"Created by: {creator_name}\n"
        details += f"Overall Performance: {overall_performance}\n\n"
        details += "Students and their behaviors:\n"
        
        behaviors = []
        for behavior in record.get('behaviors', []):
            student_name = behavior.get('student', {}).get('name', 'Unknown')
            behavior_list = behavior.get('behavior', [])
            behaviors.append({'student': student_name, 'behavior': behavior_list})
            details += f"  - {student_name} ({behavior_list})\n"
        
        details += "\nStudents and their emotions:\n"
        emotions = []
        for emotion in record.get('emotions', []):
            student_name = emotion.get('student', {}).get('name', 'Unknown')
            emotion_list = emotion.get('emotions', [])
            emotions.append({'student': student_name, 'emotions': emotion_list})
            details += f"  - {student_name} ({emotion_list})\n"

        self.details_text.setPlainText(details)

    def generate_suggestions(self):
        selected_items = self.table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Generate Suggestions", "No record selected")
            return

        row = selected_items[0].row()
        record = self.records[row]

        behaviors = []
        for behavior in record.get('behaviors', []):
            student_name = behavior.get('student', {}).get('name', 'Unknown')
            behavior_list = behavior.get('behavior', [])
            behaviors.append({'student': student_name, 'behavior': behavior_list})
        
        emotions = []
        for emotion in record.get('emotions', []):
            student_name = emotion.get('student', {}).get('name', 'Unknown')
            emotion_list = emotion.get('emotions', [])
            emotions.append({'student': student_name, 'emotions': emotion_list})

        self.loading_text.setVisible(True)
        self.loading_text.setText("Generating suggestions...")
        self.loading_animation_index = 0
        self.timer.start(100)  # Start the animation timer

        threading.Thread(target=self.fetch_suggestions, args=(emotions, behaviors,)).start()

    def fetch_suggestions(self, emotions, behaviors):
        try:
            suggestions = get_gemini_suggestions(emotions, behaviors)
            details = self.details_text.toPlainText()
            details += "\nSuggestions for Lecturer:\n"
            for suggestion in suggestions.get('suggestions', []):
                details += f"  - {suggestion}\n"
            QMetaObject.invokeMethod(self.details_text, "setPlainText", Qt.QueuedConnection, Q_ARG(str, details))
        except Exception as e:
            error_message = f"\nFailed to get suggestions: {str(e)}"
            QMetaObject.invokeMethod(self.details_text, "append", Qt.QueuedConnection, Q_ARG(str, error_message))
        finally:
            self.timer.stop()  # Stop the animation timer
            QMetaObject.invokeMethod(self.loading_text, "setVisible", Qt.QueuedConnection, Q_ARG(bool, False))

    def update_animation(self):
        dots = "." * (self.loading_animation_index % 4)
        self.loading_text.setText(f"Generating suggestions{dots}")
        self.loading_animation_index += 1

    def delete_record(self):
        selected_items = self.table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Delete Record", "No record selected")
            return

        row = selected_items[0].row()
        record = self.records[row]

        confirm = QMessageBox.question(self, "Delete Record", "Are you sure you want to delete this record?",
                                       QMessageBox.Yes | QMessageBox.No)
        if confirm == QMessageBox.Yes:
            db.records.delete_one({"_id": record['_id']})
            self.table.removeRow(row)
            self.details_text.clear()
            QMessageBox.information(self, "Delete Record", "Record deleted successfully")

    def go_back(self):
        self.close()  # Close the current window
        subprocess.Popen(["python", "F:/FYP/scripts/main_page.py", self.username])  # Replace with the correct path to main_page.py
    


if __name__ == "__main__":
    if len(sys.argv) > 1:
        username = sys.argv[1]
        app = QApplication(sys.argv)
        window = ModernRecordDetailsApp(username)
        window.show()
        sys.exit(app.exec())
    else:
        print("Username not provided.")
