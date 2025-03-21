from analytics.email_analyzer import EmailAnalyzer
from tasks.task_extractor import TaskExtractor
from PyQt6.QtWidgets import QApplication
from ui.main_window import MainWindow
import sys
import os

def main():
    # Set Qt WebEngine paths before creating QApplication
    os.environ['QTWEBENGINE_DICTIONARIES_PATH'] = os.path.join(os.path.dirname(sys.executable), 'qtwebengine_dictionaries')
    os.environ['QTWEBENGINE_CHROMIUM_FLAGS'] = '--disable-gpu'

    # Create Qt Application
    app = QApplication(sys.argv)
    
    # Initialize the analyzers
    email_analyzer = EmailAnalyzer()
    task_extractor = TaskExtractor()

    # Connect to Gmail
    if not email_analyzer.connect():
        print("Failed to connect to Gmail")
        return

    # Fetch emails from the last 2 months with force refresh
    emails = email_analyzer.fetch_emails(months_back=2, force_refresh=True)
    if not emails:
        print("No emails found or error occurred")
        return

    # Extract and prioritize tasks
    tasks = task_extractor.extract_tasks(emails)
    prioritized_tasks = task_extractor.prioritize_tasks(tasks)
    
    # Create and show main window
    window = MainWindow()
    window.display_tasks(prioritized_tasks)

    # Analyze email patterns and response times
    response_times = email_analyzer.analyze_response_times(emails)
    patterns = email_analyzer.analyze_communication_patterns(emails)
    window.display_analytics(response_times, patterns)
    
    window.show()

    # Start Qt event loop
    sys.exit(app.exec())

if __name__ == '__main__':
    main()