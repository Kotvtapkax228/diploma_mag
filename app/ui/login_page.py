from __future__ import annotations
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QLineEdit, QPushButton, QCheckBox, QFrame, QMessageBox, QSizePolicy
)

class LoginPage(QWidget):
    logged_in = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.setObjectName("AppRoot")
        self._build()

    def _build(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(18)

        # Left promo
        left = QFrame()
        left.setObjectName("Card")
        left.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        l = QVBoxLayout(left)
        l.setContentsMargins(26, 26, 26, 26)
        l.setSpacing(12)

        tag = QLabel("Інтелектуальна аналітика соцмереж")
        tag.setObjectName("ChipInfo")
        title = QLabel("Рекомендаційна система тем\nконтенту")
        title.setObjectName("H1")
        subtitle = QLabel("Вхід до кабінету автора для перегляду трендів,\nперсоналізованих тем, A/B-аналітики та показників\nзалученості аудиторії.")
        subtitle.setObjectName("Muted")

        bullet1 = QLabel("• Аналіз інтересів аудиторії на основі NLP та кластеризації")
        bullet2 = QLabel("• Динамічне ранжування тем із урахуванням часових трендів")
        bullet3 = QLabel("• Пояснюваність рекомендацій і зручний планувальник публікацій")

        for b in (bullet1, bullet2, bullet3):
            b.setStyleSheet("padding:10px 12px; border:1px solid #e6eef8; border-radius:12px; background:#ffffff;")

        l.addWidget(tag, 0)
        l.addWidget(title, 0)
        l.addWidget(subtitle, 0)
        l.addSpacing(8)
        l.addWidget(bullet1)
        l.addWidget(bullet2)
        l.addWidget(bullet3)
        l.addStretch(1)

        # Right login card
        right = QFrame()
        right.setObjectName("Card")
        right.setMaximumWidth(440)
        r = QVBoxLayout(right)
        r.setContentsMargins(26, 26, 26, 26)
        r.setSpacing(12)

        logo = QLabel("◼︎")
        logo.setStyleSheet("color:#2563eb; font-size:22px;")
        head = QLabel("Кабінет автора")
        head.setObjectName("H2")
        desc = QLabel("Авторизація для доступу до персоналізованих рекомендацій")
        desc.setObjectName("Muted")

        self.email = QLineEdit()
        self.email.setPlaceholderText("author@example.com")
        self.passwd = QLineEdit()
        self.passwd.setPlaceholderText("••••••••")
        self.passwd.setEchoMode(QLineEdit.EchoMode.Password)

        self.remember = QCheckBox("Запам’ятати мене")
        forgot = QPushButton("Забули пароль?")
        forgot.setObjectName("Ghost")
        forgot.clicked.connect(self._forgot)

        row = QHBoxLayout()
        row.addWidget(self.remember)
        row.addStretch(1)
        row.addWidget(forgot)

        btn = QPushButton("Увійти")
        btn.clicked.connect(self._login)

        orlbl = QLabel("або")
        orlbl.setObjectName("Muted")
        orlbl.setStyleSheet("qproperty-alignment: AlignCenter;")

        sso = QPushButton("Увійти через корпоративний SSO")
        sso.setObjectName("Secondary")
        sso.clicked.connect(self._sso)

        hint = QLabel("Немає акаунта? <span style='color:#2563eb; font-weight:600'>Створити профіль автора</span>")
        hint.setObjectName("Muted")
        hint.setStyleSheet("padding-top:6px;")
        hint.setTextFormat(hint.textFormat())

        r.addWidget(logo, 0)
        r.addWidget(head, 0)
        r.addWidget(desc, 0)
        r.addSpacing(6)

        r.addWidget(QLabel("Електронна пошта або логін"))
        r.addWidget(self.email)
        r.addWidget(QLabel("Пароль"))
        r.addWidget(self.passwd)
        r.addLayout(row)
        r.addWidget(btn)
        r.addSpacing(6)
        r.addWidget(orlbl)
        r.addWidget(sso)
        r.addStretch(1)
        r.addWidget(hint)

        root.addWidget(left, 2)
        root.addWidget(right, 1)

        # Prefill demo
        self.email.setText("author@example.com")
        self.passwd.setText("demo")

    def _forgot(self):
        QMessageBox.information(self, "Відновлення пароля", "Демо-режим: використайте author@example.com / demo.")

    def _sso(self):
        self.logged_in.emit("Author Demo (SSO)")

    def _login(self):
        email = self.email.text().strip()
        pwd = self.passwd.text().strip()
        if not email:
            QMessageBox.warning(self, "Помилка", "Вкажіть email або логін.")
            return
        # demo auth
        if (email == "author@example.com" and pwd == "demo") or pwd:
            name = "Author Demo"
            self.logged_in.emit(name)
        else:
            QMessageBox.warning(self, "Помилка", "Невірні облікові дані.")