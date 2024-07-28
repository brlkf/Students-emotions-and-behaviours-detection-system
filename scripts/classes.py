import sys
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                               QLabel, QLineEdit, QPushButton, QComboBox, QTableWidget, 
                               QTableWidgetItem, QHeaderView, QMessageBox, QDialog, QFormLayout)
from PySide6.QtGui import QFont
from PySide6.QtCore import Qt
import subprocess
from conn import get_db
from bson.objectid import ObjectId
from datetime import datetime

# Connect to MongoDB
db = get_db()
class_collection = db["classes"]
student_collection = db["students"]
intake_collection = db["intake"]

class ModernClassesTable(QMainWindow):
    def __init__(self, username):
        super().__init__()
        self.username = username
        self.setWindowTitle("Classes Table")
        self.setGeometry(100, 100, 1200, 700)
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
        # Search and Sort area
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search by Class Name")
        self.sort_combo = QComboBox()
        self.sort_combo.addItems(["name", "type", "weekday", "time", "intake", "status", "createdBy", "created_at"])
        search_button = QPushButton("Search")
        sort_button = QPushButton("Sort")
        
        search_layout.addWidget(QLabel("Search:"))
        search_layout.addWidget(self.search_input)
        search_layout.addWidget(QLabel("Sort by:"))
        search_layout.addWidget(self.sort_combo)
        search_layout.addWidget(search_button)
        search_layout.addWidget(sort_button)
        
        self.layout.addLayout(search_layout)
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels(["Name", "Type", "Weekday", "Time", "Intake", "Status", "Created By", "Created At"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.layout.addWidget(self.table)
        
        # Buttons
        button_layout = QHBoxLayout()
        edit_button = QPushButton("Edit")
        delete_button = QPushButton("Delete")
        back_button = QPushButton("Back")  # Add back button
        button_layout.addWidget(edit_button)
        button_layout.addWidget(delete_button)
        button_layout.addWidget(back_button)  # Add back button to layout
        self.layout.addLayout(button_layout)
        
        # Connect signals
        search_button.clicked.connect(self.load_data)
        sort_button.clicked.connect(self.load_data)
        edit_button.clicked.connect(self.edit_class)
        delete_button.clicked.connect(self.delete_class)
        back_button.clicked.connect(self.go_back)  # Connect back button to go_back method

    def load_data(self):
        self.table.setRowCount(0)
        search_query = self.search_input.text()
        sort_field = self.sort_combo.currentText()

        query = {"createdBy": self.username}
        if search_query:
            query["name"] = {"$regex": search_query, "$options": "i"}

        cursor = class_collection.find(query).sort(sort_field)

        for row, class_ in enumerate(cursor):
            self.table.insertRow(row)
            intake_id = class_["intake"]
            intake = intake_collection.find_one({"_id": intake_id})
            intake_name = intake["intake"] if intake else "Unknown"
            
            self.table.setItem(row, 0, QTableWidgetItem(class_["name"]))
            self.table.setItem(row, 1, QTableWidgetItem(class_["type"]))
            self.table.setItem(row, 2, QTableWidgetItem(class_["weekday"]))
            self.table.setItem(row, 3, QTableWidgetItem(class_["time"]))
            self.table.setItem(row, 4, QTableWidgetItem(intake_name))
            self.table.setItem(row, 5, QTableWidgetItem(class_["status"]))
            self.table.setItem(row, 6, QTableWidgetItem(class_["createdBy"]))
            self.table.setItem(row, 7, QTableWidgetItem(class_["created_at"]))
            
            # Store the ObjectId as item data
            self.table.item(row, 0).setData(Qt.UserRole, str(class_["_id"]))

    def edit_class(self):
        selected_items = self.table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Edit Error", "Please select a class to edit.")
            return

        selected_row = selected_items[0].row()
        class_id = self.table.item(selected_row, 0).data(Qt.UserRole)
        
        dialog = EditClassDialog(self, class_id)
        if dialog.exec_():
            self.load_data()

    def delete_class(self):
        selected_items = self.table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Delete Error", "Please select a class to delete.")
            return

        if QMessageBox.question(self, "Delete Confirmation", "Are you sure you want to delete the selected class?") == QMessageBox.Yes:
            selected_row = selected_items[0].row()
            class_id = self.table.item(selected_row, 0).data(Qt.UserRole)
            class_collection.delete_one({"_id": ObjectId(class_id)})
            self.load_data()
            QMessageBox.information(self, "Success", "Class deleted successfully!")

    def go_back(self):
        self.close()
        subprocess.Popen(["python", "F:/FYP/scripts/main_page.py", self.username])

class EditClassDialog(QDialog):
    def __init__(self, parent, class_id):
        super().__init__(parent)
        self.class_id = class_id
        self.setWindowTitle("Edit Class")
        self.setModal(True)
        self.setup_ui()

    def setup_ui(self):
        layout = QFormLayout(self)
        
        self.name_input = QLineEdit()
        self.type_combo = QComboBox()
        self.type_combo.addItems(["Lecture", "Tutorial"])
        self.weekday_combo = QComboBox()
        self.weekday_combo.addItems(["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"])
        self.start_time_combo = QComboBox()
        self.end_time_combo = QComboBox()
        self.intake_input = QLineEdit()
        self.status_combo = QComboBox()
        self.status_combo.addItems(["Active", "Inactive"])

        times = [f"{h:02}:{m:02}" for h in range(8, 19) for m in (0, 15, 30, 45)] + ["19:00"]
        self.start_time_combo.addItems(times)
        self.end_time_combo.addItems(times[1:])
        
        layout.addRow("Class Name:", self.name_input)
        layout.addRow("Class Type:", self.type_combo)
        layout.addRow("Weekday:", self.weekday_combo)
        layout.addRow("Start Time:", self.start_time_combo)
        layout.addRow("End Time:", self.end_time_combo)
        layout.addRow("Intake:", self.intake_input)
        layout.addRow("Status:", self.status_combo)
        
        save_button = QPushButton("Save")
        save_button.clicked.connect(self.save_changes)
        layout.addRow(save_button)
        
        self.load_class_data()
        self.start_time_combo.currentIndexChanged.connect(self.update_end_time_options)

    def load_class_data(self):
        class_data = class_collection.find_one({"_id": ObjectId(self.class_id)})
        if class_data:
            self.name_input.setText(class_data["name"])
            self.type_combo.setCurrentText(class_data["type"])
            self.weekday_combo.setCurrentText(class_data["weekday"])
            start_time, end_time = class_data["time"].split(" - ")
            self.start_time_combo.setCurrentText(start_time)
            self.end_time_combo.setCurrentText(end_time)
            intake = intake_collection.find_one({"_id": class_data["intake"]})
            self.intake_input.setText(intake["intake"] if intake else "")
            self.status_combo.setCurrentText(class_data["status"])

    def update_end_time_options(self):
        start_index = self.start_time_combo.currentIndex()
        self.end_time_combo.clear()
        self.end_time_combo.addItems(self.start_time_combo.itemText(i) for i in range(start_index + 1, self.start_time_combo.count()))

    def save_changes(self):
        name = self.name_input.text().strip()
        class_type = self.type_combo.currentText().strip()
        weekday = self.weekday_combo.currentText().strip()
        start_time = self.start_time_combo.currentText().strip()
        end_time = self.end_time_combo.currentText().strip()
        intake_name = self.intake_input.text().strip()
        status = self.status_combo.currentText().strip()

        if not all([name, class_type, weekday, start_time, end_time, intake_name, status]):
            QMessageBox.warning(self, "Input Error", "All fields must be filled in.")
            return

        intake = intake_collection.find_one({"intake": intake_name})
        if not intake:
            QMessageBox.warning(self, "Input Error", "Invalid intake name.")
            return

        updated_data = {
            "name": name,
            "type": class_type,
            "weekday": weekday,
            "time": f"{start_time} - {end_time}",
            "intake": intake["_id"],
            "status": status,
            "created_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        class_collection.update_one({"_id": ObjectId(self.class_id)}, {"$set": updated_data})
        QMessageBox.information(self, "Success", "Class updated successfully!")
        self.accept()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        username = sys.argv[1]
        app = QApplication(sys.argv)
        window = ModernClassesTable(username)
        window.show()
        sys.exit(app.exec())
    else:
        print("Username not provided.")
