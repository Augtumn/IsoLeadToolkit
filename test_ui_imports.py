#!/usr/bin/env python3
"""
测试 PyQt5 导入
"""
import sys

print("Testing PyQt5 imports...")

try:
    from PyQt5.QtWidgets import QApplication
    print("✓ PyQt5.QtWidgets imported successfully")
except ImportError as e:
    print(f"✗ Failed to import PyQt5.QtWidgets: {e}")
    sys.exit(1)

try:
    from PyQt5.QtCore import Qt
    print("✓ PyQt5.QtCore imported successfully")
except ImportError as e:
    print(f"✗ Failed to import PyQt5.QtCore: {e}")
    sys.exit(1)

try:
    from PyQt5.QtGui import QFont
    print("✓ PyQt5.QtGui imported successfully")
except ImportError as e:
    print(f"✗ Failed to import PyQt5.QtGui: {e}")
    sys.exit(1)

try:
    from ui.app import Qt5Application
    print("✓ Qt5Application imported successfully")
except ImportError as e:
    print(f"✗ Failed to import Qt5Application: {e}")
    sys.exit(1)

try:
    from ui.main_window import Qt5MainWindow
    print("✓ Qt5MainWindow imported successfully")
except ImportError as e:
    print(f"✗ Failed to import Qt5MainWindow: {e}")
    sys.exit(1)

try:
    from ui.control_panel import Qt5ControlPanel
    print("✓ Qt5ControlPanel imported successfully")
except ImportError as e:
    print(f"✗ Failed to import Qt5ControlPanel: {e}")
    sys.exit(1)

try:
    from ui.dialogs.file_dialog import Qt5FileDialog
    print("✓ Qt5FileDialog imported successfully")
except ImportError as e:
    print(f"✗ Failed to import Qt5FileDialog: {e}")
    sys.exit(1)

print("\n✓ All imports successful!")
print("\nTo run the application:")
print("  python main_qt5.py")
