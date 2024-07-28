import sys
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox
from PySide6.QtGui import QFont
from PySide6.QtCore import Qt
import subprocess
from conn import get_db  # Make sure this import works with your project structure

class LoginWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.db = get_db()
        self.collection = self.db["users"]
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Login')
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

        self.password = QLineEdit()
        self.password.setPlaceholderText('Password')
        self.password.setEchoMode(QLineEdit.Password)
        layout.addWidget(self.password)

        login_button = QPushButton('Login')
        login_button.clicked.connect(self.login_user)
        layout.addWidget(login_button)

        forgot_password_button = QPushButton("Forgot Password?")
        forgot_password_button.setStyleSheet("""
            background-color: transparent;
            color: #3498db;
            text-align: center;
        """)
        forgot_password_button.clicked.connect(self.open_forgot_password)
        layout.addWidget(forgot_password_button)

        register_button = QPushButton("Don't have an account? Register")
        register_button.setStyleSheet("""
            background-color: transparent;
            color: #3498db;
            text-align: center;
        """)
        register_button.clicked.connect(self.open_register)
        layout.addWidget(register_button)

        self.setLayout(layout)

    def login_user(self):
        email = self.email.text().strip()
        password = self.password.text().strip()

        if not email or not password:
            QMessageBox.warning(self, "Input Error", "Please fill in both fields")
            return

        user = self.collection.find_one({"email": email})
        if user:
            if password == user['password']:
                QMessageBox.information(self, "Login Success", "You have logged in successfully!")
                self.open_main_page(user['username'])
            else:
                QMessageBox.warning(self, "Login Error", "Invalid password")
        else:
            QMessageBox.warning(self, "Login Error", "Email not registered")

    def open_main_page(self, username):
        self.close()
        subprocess.Popen(["python", "F:/FYP/scripts/main_page.py", username])

    def open_register(self):
        self.close()
        subprocess.Popen(["python", "F:/FYP/scripts/register.py"])

    def open_forgot_password(self):
        self.close()
        subprocess.Popen(["python", "F:/FYP/scripts/forgot_password.py"])

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = LoginWindow()
    ex.show()
    sys.exit(app.exec())
