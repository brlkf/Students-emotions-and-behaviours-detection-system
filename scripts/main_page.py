import sys
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox, QMessageBox, QDialog, QFormLayout
from PySide6.QtGui import QFont
from PySide6.QtCore import Qt
import subprocess
from conn import get_db

class MainWindow(QWidget):
    def __init__(self, username):
        super().__init__()
        self.username = username
        self.db = get_db()
        self.collection = self.db["classes"]
        self.intake_collection = self.db["intake"]
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Main Page')
        self.setFixedSize(600, 500)
        self.setStyleSheet("""
            QWidget {
                background-color: #f0f0f0;
                font-family: Arial;
            }
            QLabel {
                color: #333;
            }
            QPushButton {
                padding: 10px;
                background-color: #3498db;
                color: white;
                border: none;
                border-radius: 5px;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QComboBox {
                padding: 5px;
                border: 2px solid #ddd;
                border-radius: 5px;
                font-size: 16px;
            }
        """)

        layout = QVBoxLayout()
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)

        # Header
        header_layout = QHBoxLayout()
        welcome_label = QLabel(f"Hi, {self.username}")
        welcome_label.setFont(QFont('Arial', 24, QFont.Bold))
        header_layout.addWidget(welcome_label)
        
        profile_button = QPushButton("Profile")
        profile_button.clicked.connect(self.open_profile)
        header_layout.addWidget(profile_button)
        
        logout_button = QPushButton("Logout")
        logout_button.clicked.connect(self.logout)
        header_layout.addWidget(logout_button)
        
        layout.addLayout(header_layout)

        # Class Selection
        layout.addWidget(QLabel("Select Class", font=QFont('Arial', 18)))
        
        self.class_dropdown = QComboBox()
        self.populate_class_dropdown()
        layout.addWidget(self.class_dropdown)

        confirm_button = QPushButton("Confirm")
        confirm_button.clicked.connect(self.confirm_selection)
        layout.addWidget(confirm_button)

        create_class_button = QPushButton("Create New Class")
        create_class_button.clicked.connect(self.open_create_class)
        layout.addWidget(create_class_button)
        
        classes_button = QPushButton("Open Classes")
        classes_button.clicked.connect(self.open_classes)
        layout.addWidget(classes_button)
        
        students_button = QPushButton("Open Students")
        students_button.clicked.connect(self.open_students)
        layout.addWidget(students_button)

        # New button to open records.py
        records_button = QPushButton("Open Records")
        records_button.clicked.connect(self.open_records)
        layout.addWidget(records_button)

        self.setLayout(layout)

    def populate_class_dropdown(self):
        # Filter to get only active classes
        classes = list(self.collection.find({"createdBy": self.username, "status": "Active"}))
        if not classes:
            self.class_dropdown.addItem("No class available")
        else:
            for class_ in classes:
                intake_info = self.intake_collection.find_one({"_id": class_["intake"]})
                intake_name = intake_info["intake"] if intake_info else "Unknown"
                class_option = f"{class_['name']} - {class_['type']} on {class_['weekday']} ({intake_name})"
                self.class_dropdown.addItem(class_option)

    def open_profile(self):
        self.close()
        subprocess.Popen(["python", "F:/FYP/scripts/user_profile.py", self.username])

    def logout(self):
        self.close()
        subprocess.Popen(["python", "F:/FYP/scripts/login.py"])

    def confirm_selection(self):
        class_selected = self.class_dropdown.currentText().split(" - ")[0]
        class_info = self.collection.find_one({"name": class_selected, "createdBy": self.username})
        if class_info:
            intake_info = self.intake_collection.find_one({"_id": class_info["intake"]})
            intake_name = intake_info["intake"] if intake_info else "Unknown"
            details = (
                f"Class Type & Date: {class_info['type']} on {class_info['weekday']}\n"
                f"Class Time: {class_info['time']}\n"
                f"Summary: {class_info['summary']} students\n"
                f"Intake: {intake_name}\n"
                f"Created By: {class_info['createdBy']}"
            )

            dialog = QDialog(self)
            dialog.setWindowTitle("Class Details")
            dialog.setFixedSize(400, 300)

            dialog_layout = QVBoxLayout(dialog)
            details_label = QLabel(details)
            details_label.setFont(QFont('Arial', 14))
            dialog_layout.addWidget(details_label)

            button_layout = QHBoxLayout()

            back_button = QPushButton("Back")
            back_button.clicked.connect(dialog.reject)
            button_layout.addWidget(back_button)

            confirm_button = QPushButton("Confirm")
            confirm_button.clicked.connect(lambda: self.proceed_to_test(dialog, class_info))
            button_layout.addWidget(confirm_button)

            dialog_layout.addLayout(button_layout)

            dialog.exec_()

    def proceed_to_test(self, dialog, class_info):
        class_id = str(class_info['_id'])
        dialog.accept()
        self.close()
        self.open_test(class_id)

    def open_create_class(self):
        self.close()
        subprocess.Popen(["python", "F:/FYP/scripts/create_class.py", self.username])
        
    def open_classes(self):
        self.close()
        subprocess.Popen(["python", "F:/FYP/scripts/classes.py", self.username])

    def open_records(self):
        self.close()
        subprocess.Popen(["python", "F:/FYP/scripts/records.py", self.username])
    
    def open_students(self):
        self.close()
        subprocess.Popen(["python", "F:/FYP/scripts/students_page.py", self.username])

    def open_test(self, class_id):
        self.close()
        subprocess.Popen(["python", "F:/FYP/scripts/detect.py", class_id, self.username])

def main_page(username):
    app = QApplication(sys.argv)
    ex = MainWindow(username)
    ex.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    if len(sys.argv) > 1:
        username = sys.argv[1]
        main_page(username)
    else:
        print("Username not provided.")
