import sys
sys.path.append(r"C:\Users\hzy\Programs\myhelper")
sys.path.append(r"C:\Users\hzy\Programs\myhelper\pyside6-settings")
from app_qt.configs import settings
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QPushButton


# Create Qt application
app = QApplication([])

# Use the global settings instance
print(f"配置已加载：{settings.llm_config.provider}")

# Create main window with settings form
window = QMainWindow()

# Create central widget with layout
central_widget = QWidget()
main_layout = QVBoxLayout(central_widget)

# Add save button at the top
save_button = QPushButton("💾 保存配置")
save_button.setStyleSheet("""
    QPushButton {
        background-color: #4CAF50;
        color: white;
        font-weight: bold;
        padding: 10px 20px;
        border-radius: 5px;
    }
    QPushButton:hover {
        background-color: #45a049;
    }
    QPushButton:pressed {
        background-color: #3d8b40;
    }
""")
save_button.clicked.connect(lambda: settings._save_settings())
main_layout.addWidget(save_button)

# Add settings form
settings_form = settings.create_form()
main_layout.addWidget(settings_form)

window.setCentralWidget(central_widget)
window.setWindowTitle("Application Settings")
window.resize(800, 600)
window.show()

# Changes are automatically saved to config.json
# settings.username = "new_user"  # Auto-saved!

app.exec()