import sys
from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                               QLabel, QLineEdit, QPushButton, QMessageBox)
from PySide6.QtGui import QFont, QIcon
from PySide6.QtCore import Qt
import re
import subprocess
from conn import get_db

class RegisterWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.db = get_db()
        self.collection = self.db["users"]
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Teacher Registration')
        self.setFixedSize(400, 500)
        self.setStyleSheet("""
            QWidget {
                background-color: #f0f0f0;
                font-family: Arial;
            }
            QLabel {
                color: #333;
            }
            QLineEdit {
                padding: 10px;
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

        title = QLabel('EduTrack')
        title.setAlignment(Qt.AlignCenter)
        title.setFont(QFont('Arial', 24, QFont.Bold))
        layout.addWidget(title)

        self.email = QLineEdit()
        self.email.setPlaceholderText('Email')
        layout.addWidget(self.email)

        self.username = QLineEdit()
        self.username.setPlaceholderText('Username')
        layout.addWidget(self.username)

        self.password = QLineEdit()
        self.password.setPlaceholderText('Password')
        self.password.setEchoMode(QLineEdit.Password)
        layout.addWidget(self.password)

        register_button = QPushButton('Register')
        register_button.clicked.connect(self.register_user)
        layout.addWidget(register_button)

        login_button = QPushButton("Already have an account? Login")
        login_button.setStyleSheet("""
            background-color: transparent;
            color: #3498db;
            text-align: center;
        """)
        login_button.clicked.connect(self.open_login)
        layout.addWidget(login_button)

        self.setLayout(layout)

    def is_valid_email(self, email):
        # Ensure email doesn't start with a number and matches email regex
        if email[0].isdigit():
            return False
        regex = r'^\b[A-Za-z][A-Za-z0-9._%+-]*@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        return re.match(regex, email) is not None

    def is_valid_username(self, username):
        # Ensure username contains only alphabetic characters
        return username.isalpha()

    def register_user(self):
        email = self.email.text().strip()
        username = self.username.text().strip()
        password = self.password.text().strip()

        if not email or not username or not password:
            QMessageBox.warning(self, "Input Error", "Please fill in all fields")
            return

        if not self.is_valid_email(email):
            QMessageBox.warning(self, "Invalid Email", "Invalid email format")
            return

        if not self.is_valid_username(username):
            QMessageBox.warning(self, "Invalid Username", "Username must only contain alphabetic characters")
            return

        if self.collection.find_one({"email": email}):
            QMessageBox.warning(self, "Registration Error", "Email already registered")
            return

        self.collection.insert_one({"email": email, "username": username, "password": password})
        QMessageBox.information(self, "Registration Success", "You have registered successfully!")
        self.email.clear()
        self.username.clear()
        self.password.clear()

    def open_login(self):
        self.close()
        subprocess.Popen(["python", "F:/FYP/scripts/login.py"])

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = RegisterWindow()
    ex.show()
    sys.exit(app.exec())
