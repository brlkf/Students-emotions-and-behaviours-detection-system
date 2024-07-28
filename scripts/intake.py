import sys
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                               QLabel, QLineEdit, QPushButton, QTableWidget, QTableWidgetItem, 
                               QHeaderView, QMessageBox, QDialog, QFormLayout, QFileDialog, QTreeWidget, QTreeWidgetItem)
from PySide6.QtGui import QFont
from PySide6.QtCore import Qt
import pandas as pd
import subprocess
from bson.objectid import ObjectId
from conn import get_db

# Connect to MongoDB
db = get_db()
intake_collection = db["intake"]
student_collection = db["students"]

class IntakeManager(QMainWindow):
    def __init__(self, username):
        super().__init__()
        self.username = username
        self.setWindowTitle("Intake Manager")
        self.setGeometry(100, 100, 800, 600)
        self.setStyleSheet("""
            QMainWindow { background-color: #f0f0f0; }
            QLabel { font-size: 14px; }
            QLineEdit { 
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
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["Intake Name", "Created By"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.layout.addWidget(self.table)

        # Student Tree
        self.student_tree = QTreeWidget()
        self.student_tree.setHeaderLabels(["Name", "TP Number"])
        self.layout.addWidget(self.student_tree)

        # Buttons
        button_layout = QHBoxLayout()
        add_button = QPushButton("Add Intake")
        edit_button = QPushButton("Edit Intake")
        delete_button = QPushButton("Delete Intake")
        import_button = QPushButton("Import Students")
        clear_button = QPushButton("Clear")
        back_button = QPushButton("Back")
        button_layout.addWidget(add_button)
        button_layout.addWidget(edit_button)
        button_layout.addWidget(delete_button)
        button_layout.addWidget(import_button)
        button_layout.addWidget(clear_button)
        button_layout.addWidget(back_button)
        self.layout.addLayout(button_layout)

        # Connect signals
        add_button.clicked.connect(self.add_intake)
        edit_button.clicked.connect(self.edit_intake)
        delete_button.clicked.connect(self.delete_intake)
        import_button.clicked.connect(self.import_students)
        clear_button.clicked.connect(self.clear_students)
        back_button.clicked.connect(self.go_back)
        self.table.itemSelectionChanged.connect(self.load_students_in_intake)

    def load_data(self):
        self.table.setRowCount(0)
        query = {"created_by": self.username}
        cursor = intake_collection.find(query).sort("intake")

        for row, intake in enumerate(cursor):
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(intake["intake"]))
            self.table.setItem(row, 1, QTableWidgetItem(intake["created_by"]))
            # Store the ObjectId as item data
            self.table.item(row, 0).setData(Qt.UserRole, str(intake["_id"]))

    def add_intake(self):
        dialog = IntakeDialog(self, self.username)
        if dialog.exec_():
            self.load_data()

    def edit_intake(self):
        selected_items = self.table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Edit Error", "Please select an intake to edit.")
            return

        selected_row = selected_items[0].row()
        intake_id = self.table.item(selected_row, 0).data(Qt.UserRole)

        dialog = IntakeDialog(self, self.username, intake_id)
        if dialog.exec_():
            self.load_data()

    def delete_intake(self):
        selected_items = self.table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Delete Error", "Please select an intake to delete.")
            return

        if QMessageBox.question(self, "Delete Confirmation", "Are you sure you want to delete the selected intake?") == QMessageBox.Yes:
            selected_row = selected_items[0].row()
            intake_id = self.table.item(selected_row, 0).data(Qt.UserRole)
            intake_collection.delete_one({"_id": ObjectId(intake_id)})
            self.load_data()
            self.student_tree.clear()
            QMessageBox.information(self, "Success", "Intake deleted successfully!")

    def import_students(self):
        selected_items = self.table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Import Error", "Please select an intake to import students into.")
            return

        selected_row = selected_items[0].row()
        intake_id = self.table.item(selected_row, 0).data(Qt.UserRole)
        file_path, _ = QFileDialog.getOpenFileName(self, "Open Excel File", "", "Excel Files (*.xlsx *.xls)")
        if file_path:
            df = pd.read_excel(file_path).drop_duplicates(subset=['Name', 'TP_Number'])
            unique_entries = set()
            duplicate_entries = []
            tp_conflicts = []

            for _, row in df.iterrows():
                student_name = str(row['Name']).strip()
                tp_number = str(row['TP_Number']).strip()

                # Skip rows with missing or blank details
                if not all([student_name, tp_number]):
                    continue

                # Check for existing students with the same TP number
                tp_conflict = student_collection.find_one({"TPNumber": tp_number})
                if tp_conflict:
                    tp_conflicts.append((student_name, tp_number))
                    continue

                # Check for existing students with the same name, TP number, and intake
                existing_student = student_collection.find_one({
                    "name": student_name,
                    "TPNumber": tp_number,
                    "intake": ObjectId(intake_id)
                })

                if existing_student:
                    duplicate_entries.append((student_name, tp_number))
                else:
                    unique_key = (student_name, tp_number)
                    if unique_key not in unique_entries:
                        unique_entries.add(unique_key)
                        student_doc = {
                            "name": student_name,
                            "TPNumber": tp_number,
                            "intake": ObjectId(intake_id),
                            "class_id": []  # Initialize with an empty list
                        }
                        student_collection.insert_one(student_doc)

            self.load_students_in_intake()
            if tp_conflicts:
                conflicts_str = "\n".join([f"Name: {name}, TP Number: {tp}" for name, tp in tp_conflicts])
                QMessageBox.warning(self, "TP Number Conflicts", f"The following TP Numbers already exist and were not imported:\n{conflicts_str}")
            if duplicate_entries:
                duplicates_str = "\n".join([f"Name: {name}, TP Number: {tp}" for name, tp in duplicate_entries])
                QMessageBox.warning(self, "Duplicate Entries Found", f"The following entries already exist and were not imported:\n{duplicates_str}")
            if not tp_conflicts and not duplicate_entries:
                QMessageBox.information(self, "Success", f"Imported {len(unique_entries)} students.")

    def load_students_in_intake(self):
        self.student_tree.clear()
        selected_items = self.table.selectedItems()
        if not selected_items:
            return

        selected_row = selected_items[0].row()
        intake_id = self.table.item(selected_row, 0).data(Qt.UserRole)
        students = student_collection.find({"intake": ObjectId(intake_id)})
        for student in students:
            item = QTreeWidgetItem(self.student_tree)
            item.setText(0, student["name"])
            item.setText(1, student["TPNumber"])

    def clear_students(self):
        self.student_tree.clear()

    def go_back(self):
        self.close()
        subprocess.Popen(["python", "F:/FYP/scripts/main_page.py", self.username])

class IntakeDialog(QDialog):
    def __init__(self, parent, username, intake_id=None):
        super().__init__(parent)
        self.username = username
        self.intake_id = intake_id
        self.setWindowTitle("Add/Edit Intake")
        self.setModal(True)
        self.setup_ui()

    def setup_ui(self):
        layout = QFormLayout(self)
        
        self.intake_input = QLineEdit()
        layout.addRow("Intake Name:", self.intake_input)

        save_button = QPushButton("Save")
        save_button.clicked.connect(self.save_intake)
        layout.addWidget(save_button)

        if self.intake_id:
            self.load_intake_data()

    def load_intake_data(self):
        intake = intake_collection.find_one({"_id": ObjectId(self.intake_id)})
        if intake:
            self.intake_input.setText(intake["intake"])

    def save_intake(self):
        intake_name = self.intake_input.text().strip()
        if not intake_name:
            QMessageBox.warning(self, "Input Error", "Intake name cannot be empty.")
            return

        intake_data = {
            "intake": intake_name,
            "created_by": self.username
        }

        if self.intake_id:
            intake_collection.update_one({"_id": ObjectId(self.intake_id)}, {"$set": intake_data})
            QMessageBox.information(self, "Success", "Intake updated successfully!")
        else:
            intake_collection.insert_one(intake_data)
            QMessageBox.information(self, "Success", "Intake added successfully!")

        self.accept()
        self.parent().load_data()  # Reload data after saving

if __name__ == "__main__":
    if len(sys.argv) > 1:
        username = sys.argv[1]
        app = QApplication(sys.argv)
        window = IntakeManager(username)
        window.show()
        sys.exit(app.exec())
    else:
        print("Username not provided.")
