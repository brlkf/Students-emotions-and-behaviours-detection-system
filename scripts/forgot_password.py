import sys
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox
from PySide6.QtGui import QFont
from PySide6.QtCore import Qt
import subprocess
from conn import get_db  # Make sure this import works with your project structure

class ForgotPasswordWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.db = get_db()
        self.collection = self.db["users"]
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Forgot Password')
        self.setFixedSize(400, 400)
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

        title = QLabel('Reset Password')
        title.setAlignment(Qt.AlignCenter)
        title.setFont(QFont('Arial', 24, QFont.Bold))
        layout.addWidget(title)

        self.username = QLineEdit()
        self.username.setPlaceholderText('Enter your username')
        layout.addWidget(self.username)

        self.new_password = QLineEdit()
        self.new_password.setPlaceholderText('Enter new password')
        self.new_password.setEchoMode(QLineEdit.Password)
        layout.addWidget(self.new_password)

        self.confirm_password = QLineEdit()
        self.confirm_password.setPlaceholderText('Confirm new password')
        self.confirm_password.setEchoMode(QLineEdit.Password)
        layout.addWidget(self.confirm_password)

        reset_button = QPushButton('Reset Password')
        reset_button.clicked.connect(self.reset_password)
        layout.addWidget(reset_button)

        back_button = QPushButton("Back to Login")
        back_button.setStyleSheet("""
            background-color: transparent;
            color: #3498db;
            text-align: center;
        """)
        back_button.clicked.connect(self.open_login)
        layout.addWidget(back_button)

        self.setLayout(layout)

    def reset_password(self):
        username = self.username.text().strip()
        new_password = self.new_password.text().strip()
        confirm_password = self.confirm_password.text().strip()

        if not username or not new_password or not confirm_password:
            QMessageBox.warning(self, "Input Error", "Please fill in all fields")
            return

        if new_password != confirm_password:
            QMessageBox.warning(self, "Password Error", "Passwords do not match")
            return

        user = self.collection.find_one({"username": username})
        if user:
            self.collection.update_one({"username": username}, {"$set": {"password": new_password}})
            QMessageBox.information(self, "Password Reset", "Your password has been reset successfully!")
        else:
            QMessageBox.warning(self, "Error", "Username not registered")

    def open_login(self):
        self.close()
        subprocess.Popen(["python", "F:/FYP/scripts/login.py"])

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = ForgotPasswordWindow()
    ex.show()
    sys.exit(app.exec())
