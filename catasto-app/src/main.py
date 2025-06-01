import sys
from PyQt5.QtWidgets import QApplication
from gui import MainWindow  # Assuming MainWindow is defined in gui.py
from db.catasto_db_manager import CatastoDBManager  # Assuming CatastoDBManager is defined in catasto_db_manager.py

def main():
    app = QApplication(sys.argv)
    db_manager = CatastoDBManager()  # Initialize the database manager
    main_window = MainWindow(db_manager)  # Pass the db_manager to the main window
    main_window.show()  # Show the main window
    sys.exit(app.exec_())  # Start the event loop

if __name__ == "__main__":
    main()