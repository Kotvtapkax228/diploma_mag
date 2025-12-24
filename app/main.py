from __future__ import annotations
import os
import sys

from PyQt6.QtWidgets import QApplication, QStackedWidget
from app.ui.login_page import LoginPage
from app.ui.main_window import MainWindow

def resource_path(*parts: str) -> str:
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(here, *parts)

def main():
    app = QApplication(sys.argv)

    qss_path = resource_path("assets", "style.qss")
    reports_dir = resource_path("reports")

    stack = QStackedWidget()
    stack.setWindowTitle("Рекомендаційна система тем контенту (PyQt6)")
    stack.resize(1280, 780)

    login = LoginPage()

    def on_login(user_name: str):
        mw = MainWindow(user_name=user_name, qss_path=qss_path, reports_dir=reports_dir)
        stack.addWidget(mw)
        stack.setCurrentWidget(mw)

    login.logged_in.connect(on_login)
    stack.addWidget(login)
    stack.setCurrentWidget(login)
    stack.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()