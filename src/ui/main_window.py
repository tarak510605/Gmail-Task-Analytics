from PyQt6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem, QLabel, QTabWidget, QHeaderView, QComboBox, QPushButton, QFileDialog, QApplication
from PyQt6.QtCore import Qt
from datetime import datetime, timedelta
import plotly.graph_objects as go
import csv
import json

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Email Analytics Dashboard")
        self.setGeometry(100, 100, 1200, 800)
        self.tasks = []
        self.original_tasks = []  # Store original tasks
        
        # Create main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        
        # Create tab widget
        tab_widget = QTabWidget()
        main_layout.addWidget(tab_widget)
        
        # Tasks tab
        tasks_tab = QWidget()
        tasks_layout = QVBoxLayout(tasks_tab)
        
        # Task controls
        controls_layout = QHBoxLayout()
        
        # Filter controls
        filter_group = QWidget()
        filter_layout = QHBoxLayout(filter_group)
        
        # Priority filter
        self.priority_filter = QComboBox()
        self.priority_filter.addItems(['All', 'High', 'Moderate'])
        self.priority_filter.currentTextChanged.connect(self.apply_filters)
        filter_layout.addWidget(QLabel("Priority:"))
        filter_layout.addWidget(self.priority_filter)
        
        # Status filter
        self.status_filter = QComboBox()
        self.status_filter.addItems(['All', 'Pending', 'Completed'])
        self.status_filter.currentTextChanged.connect(self.apply_filters)
        filter_layout.addWidget(QLabel("Status:"))
        filter_layout.addWidget(self.status_filter)
        
        controls_layout.addWidget(filter_group)
        
        # Sort controls
        sort_group = QWidget()
        sort_layout = QHBoxLayout(sort_group)
        
        self.sort_by = QComboBox()
        self.sort_by.addItems(['Priority', 'Deadline', 'Status'])
        self.sort_by.currentTextChanged.connect(self.apply_sort)
        sort_layout.addWidget(QLabel("Sort by:"))
        sort_layout.addWidget(self.sort_by)
        
        controls_layout.addWidget(sort_group)
        
        # Export button
        self.export_btn = QPushButton("Export Tasks")
        self.export_btn.clicked.connect(self.export_tasks)
        controls_layout.addWidget(self.export_btn)
        
        # Refresh button
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self.refresh_data)
        controls_layout.addWidget(self.refresh_btn)
        
        # Logout button
        self.logout_btn = QPushButton("Logout")
        self.logout_btn.clicked.connect(self.logout)
        controls_layout.addWidget(self.logout_btn)

        tasks_layout.addLayout(controls_layout)
        
        # Create table for tasks
        self.task_table = QTableWidget()
        self.task_table.setColumnCount(5)
        self.task_table.setHorizontalHeaderLabels(["Priority", "Task Description", "Deadline", "Status", "From"])
        self.task_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.task_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.task_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.task_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.task_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        
        # Disable editing
        self.task_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        
        # Enable context menu
        self.task_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.task_table.customContextMenuRequested.connect(self.show_context_menu)
        
        # Enable word wrap for better text display
        self.task_table.setWordWrap(True)
        self.task_table.setTextElideMode(Qt.TextElideMode.ElideNone)
        
        # Adjust row height automatically
        self.task_table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        
        tasks_layout.addWidget(QLabel("Prioritized Tasks"))
        tasks_layout.addWidget(self.task_table)
        tab_widget.addTab(tasks_tab, "Tasks")
        
        # Analytics tab with scroll area
        analytics_tab = QWidget()
        analytics_layout = QVBoxLayout(analytics_tab)
        analytics_layout.setSpacing(20)
        analytics_layout.setContentsMargins(20, 20, 20, 20)
        
        # Response times section
        response_times_label = QLabel("Email Response Times")
        response_times_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        self.response_times_widget = QLabel()
        self.response_times_widget.setMinimumWidth(400)
        analytics_layout.addWidget(response_times_label)
        analytics_layout.addWidget(self.response_times_widget)
        
        # Communication patterns section
        patterns_label = QLabel("Communication Patterns")
        patterns_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        self.patterns_widget = QLabel()
        self.patterns_widget.setMinimumWidth(400)
        analytics_layout.addWidget(patterns_label)
        analytics_layout.addWidget(self.patterns_widget)
        
        # Add stretching space at the bottom
        analytics_layout.addStretch()
        
        tab_widget.addTab(analytics_tab, "Analytics")
    
    def display_tasks(self, tasks):
        self.tasks = tasks
        self.original_tasks = tasks.copy()  # Store a copy of original tasks
        self.apply_filters()
    
    def apply_filters(self):
        filters = {}
        
        if self.priority_filter.currentText() != 'All':
            filters['priority'] = self.priority_filter.currentText().lower()
        
        if self.status_filter.currentText() != 'All':
            filters['status'] = self.status_filter.currentText().lower()
        
        filtered_tasks = self.original_tasks.copy()  # Use original tasks as base
        if filters:
            from tasks.task_extractor import TaskExtractor
            task_extractor = TaskExtractor()
            filtered_tasks = task_extractor.filter_tasks(filtered_tasks, filters)
        
        self.tasks = filtered_tasks  # Update current tasks
        self.update_task_table(filtered_tasks)
    
    def apply_sort(self):
        from tasks.task_extractor import TaskExtractor
        task_extractor = TaskExtractor()
        sorted_tasks = task_extractor.prioritize_tasks(
            self.tasks,
            sort_by=self.sort_by.currentText().lower()
        )
        self.update_task_table(sorted_tasks)
    
    def show_context_menu(self, position):
        menu = QMenu()
        row = self.task_table.rowAt(position.y())
        if row >= 0:
            mark_completed = menu.addAction("Mark as Completed")
            action = menu.exec(self.task_table.viewport().mapToGlobal(position))
            if action == mark_completed:
                self.mark_task_completed(row)
    
    def mark_task_completed(self, row):
        task = self.tasks[row]
        task['status'] = 'completed'
        self.apply_filters()

    def update_task_table(self, tasks):
        self.task_table.setRowCount(0)
        current_time = datetime.now()
        active_tasks = []
        
        for task in tasks:
            # Skip completed tasks
            if task.get('status', '').lower() == 'completed':
                continue
                
            # Check if deadline has passed
            deadline = task.get('deadline', '')
            if deadline:
                try:
                    deadline_date = datetime.fromisoformat(deadline)
                    if deadline_date < current_time:
                        continue
                    # Add visual indicator for approaching deadlines (within 24 hours)
                    time_until_deadline = deadline_date - current_time
                    if time_until_deadline <= timedelta(hours=24):
                        task['approaching_deadline'] = True
                except ValueError:
                    pass  # Keep task if deadline format is invalid
                    
            active_tasks.append(task)
            
        # Update the tasks list with only active tasks
        self.tasks = active_tasks
        
        for task in active_tasks:
            row = self.task_table.rowCount()
            self.task_table.insertRow(row)
            
            # Priority column with persistent color
            priority = 'low' if not task.get('deadline') else task['priority']
            priority_item = QTableWidgetItem(priority.upper())
            if priority.lower() == 'high':
                priority_item.setBackground(Qt.GlobalColor.red)
            elif priority.lower() == 'moderate':
                priority_item.setBackground(Qt.GlobalColor.yellow)
            else:
                priority_item.setBackground(Qt.GlobalColor.white)
            self.task_table.setItem(row, 0, priority_item)
            
            # Task description column with deadline context
            description = task['text']
            description_item = QTableWidgetItem(description)
            description_item.setTextAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
            self.task_table.setItem(row, 1, description_item)
            
            # Deadline column with formatting and warning indicator
            deadline = task.get('deadline', '')
            if deadline:
                try:
                    deadline_date = datetime.fromisoformat(deadline)
                    deadline_str = deadline_date.strftime('%Y-%m-%d %H:%M')
                    deadline_item = QTableWidgetItem(deadline_str)
                    if task.get('approaching_deadline'):
                        deadline_item.setBackground(Qt.GlobalColor.yellow)
                        deadline_item.setToolTip("Deadline approaching within 24 hours!")
                    self.task_table.setItem(row, 2, deadline_item)
                except ValueError:
                    self.task_table.setItem(row, 2, QTableWidgetItem(deadline))
            else:
                self.task_table.setItem(row, 2, QTableWidgetItem(''))
            
            # Status column with persistent color
            status = task.get('status', 'pending')
            status_item = QTableWidgetItem(status.capitalize())
            if status.lower() == 'completed':
                status_item.setBackground(Qt.GlobalColor.green)
                status_item.setForeground(Qt.GlobalColor.white)
            else:
                status_item.setBackground(Qt.GlobalColor.lightGray)
                status_item.setForeground(Qt.GlobalColor.black)
            self.task_table.setItem(row, 3, status_item)
            
            # From column
            from_email = task.get('from', '')
            from_item = QTableWidgetItem(from_email)
            from_item.setBackground(Qt.GlobalColor.white)
            self.task_table.setItem(row, 4, from_item)
    
    def on_task_edited(self, item):
        if not item:
            return
            
        row = item.row()
        col = item.column()
        task = self.tasks[row]
        
        if col == 1:  # Task description
            task['text'] = item.text()
        elif col == 2:  # Deadline
            task['deadline'] = item.text()
        elif col == 3:  # Status
            from tasks.task_extractor import TaskExtractor
            task_extractor = TaskExtractor()
            task_extractor.update_task_status(task, item.text().lower())
            
            if item.text().lower() == 'completed':
                item.setBackground(Qt.GlobalColor.green)
            else:
                item.setBackground(Qt.GlobalColor.white)
    
    def export_tasks(self):
        file_name, _ = QFileDialog.getSaveFileName(
            self,
            "Export Tasks",
            "",
            "CSV Files (*.csv);;JSON Files (*.json)"
        )
        
        if not file_name:
            return
            
        if file_name.endswith('.csv'):
            with open(file_name, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=['priority', 'text', 'deadline', 'status', 'from'])
                writer.writeheader()
                writer.writerows(self.tasks)
        elif file_name.endswith('.json'):
            with open(file_name, 'w') as f:
                json.dump(self.tasks, f, indent=2)
    
    def display_analytics(self, response_times, patterns):
        # Display response times with HTML formatting
        response_text = "<h3>Response Time Analysis</h3>"
        response_text += f"<p><b>Average response time:</b> {response_times['average']:.2f} hours</p>"
        response_text += f"<p><b>Fastest response:</b> {response_times['min']:.2f} hours</p>"
        response_text += f"<p><b>Slowest response:</b> {response_times['max']:.2f} hours</p>"
        self.response_times_widget.setText(response_text)
        self.response_times_widget.setTextFormat(Qt.TextFormat.RichText)
        
        # Display communication patterns with HTML formatting
        patterns_text = "<h3>Peak Email Hours</h3>"
        for hour, count in patterns['peak_hours'].items():
            patterns_text += f"<p>{hour}:00 - <b>{count}</b> emails</p>"
        
        patterns_text += "<h3>Most Frequent Contacts</h3>"
        for contact, count in patterns['frequent_contacts'].items():
            patterns_text += f"<p>{contact}: <b>{count}</b> emails</p>"
        
        self.patterns_widget.setText(patterns_text)
        self.patterns_widget.setTextFormat(Qt.TextFormat.RichText)
        self.patterns_widget.setWordWrap(True)

    def logout(self):
        # Clear the task table and cache
        self.task_table.setRowCount(0)
        self.tasks = []
        self.original_tasks = []
        
        # Clear filters and sort
        self.priority_filter.setCurrentText('All')
        self.status_filter.setCurrentText('All')
        self.sort_by.setCurrentText('Priority')
        
        # Clear analytics
        self.response_times_widget.setText('')
        self.patterns_widget.setText('')
        
    def refresh_data(self):
        # Re-apply filters and sort to refresh the task table
        self.apply_filters()
        self.apply_sort()
