import sys
from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                               QLabel, QLineEdit, QPushButton, QMessageBox)
from PySide6.QtGui import QFont
from PySide6.QtCore import Qt
import subprocess
from conn import get_db

class ProfilePage(QWidget):
    def __init__(self, username):
        super().__init__()
        self.username = username
        self.db = get_db()
        self.collection = self.db['users']
        self.user = self.collection.find_one({"username": self.username})
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Profile')
        self.setFixedSize(400, 300)
        self.setStyleSheet("""
            QWidget {
                background-color: #f0f0f0;
                font-family: Arial;
            }
            QLabel {
                color: #333;
                font-size: 16px;
            }
            QLineEdit {
                padding: 8px;
                border: 2px solid #ddd;
                border-radius: 5px;
                font-size: 16px;
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
        """)

        layout = QVBoxLayout()
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)

        # Profile Header
        header_label = QLabel("Profile")
        header_label.setAlignment(Qt.AlignCenter)
        header_label.setFont(QFont('Arial', 24, QFont.Bold))
        layout.addWidget(header_label)

        # Username
        username_layout = QHBoxLayout()
        username_layout.addWidget(QLabel("Username:"))
        username_label = QLabel(self.user['username'])
        username_label.setStyleSheet("font-weight: bold;")
        username_layout.addWidget(username_label)
        layout.addLayout(username_layout)

        # Password
        password_layout = QHBoxLayout()
        password_layout.addWidget(QLabel("New Password:"))
        self.password_entry = QLineEdit()
        self.password_entry.setEchoMode(QLineEdit.Password)
        password_layout.addWidget(self.password_entry)
        layout.addLayout(password_layout)

        # Update Password Button
        update_button = QPushButton("Update Password")
        update_button.clicked.connect(self.update_password)
        layout.addWidget(update_button)

        # Back Button
        back_button = QPushButton("Back to Main Page")
        back_button.clicked.connect(self.back)
        layout.addWidget(back_button)

        self.setLayout(layout)

    def update_password(self):
        new_password = self.password_entry.text().strip()
        if new_password:
            self.collection.update_one({"username": self.username}, {"$set": {"password": new_password}})
            QMessageBox.information(self, "Update Successful", "Password updated successfully")
            self.password_entry.clear()
        else:
            QMessageBox.warning(self, "Input Error", "Please enter a valid new password")

    def back(self):
        self.close()
        subprocess.Popen(["python", "F:/FYP/scripts/main_page.py", self.username])

def main(username):
    app = QApplication(sys.argv)
    ex = ProfilePage(username)
    ex.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    username = sys.argv[1] if len(sys.argv) > 1 else 'User'
    main(username)
