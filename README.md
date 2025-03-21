# Email Analytics

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org/downloads/)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](http://makeapullrequest.com)

A Python application that analyzes your Gmail inbox to extract tasks and visualize email communication networks.

## Key Features

• **Task Extraction & Organization**: Automatically extracts tasks from emails with priority-based organization and deadline tracking

• **Analytics Dashboard**: Interactive interface displaying email response times and communication patterns with data visualization

• **Task Management System**: Comprehensive task management with filtering, sorting, and status tracking capabilities, plus CSV/JSON export functionality

## Setup Instructions

1. **Create a Google Cloud Project**
   - Go to the [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select an existing one
   - Enable the Gmail API for your project

2. **Get Your Credentials**
   - In the Google Cloud Console, go to APIs & Services > Credentials
   - Click "Create Credentials" and select "OAuth client ID"
   - Choose "Desktop Application" as the application type
   - Download the credentials and save as `credentials.json` in the project root directory

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the Application**
   ```bash
   python src/main.py
   ```
   - On first run, a browser window will open asking you to authenticate with your Google account
   - Grant the requested permissions to allow the application to read your emails

## Features

- Fetches emails from the last 2 months
- Extracts tasks from email content using keyword detection
- Prioritizes tasks based on urgency and deadlines
- Generates email communication network visualization

## Project Architecture

```
src/
├── analytics/      # Email analysis and visualization logic
├── auth/           # Gmail authentication handling
├── tasks/          # Task extraction and management
└── ui/             # User interface components
```

## Contributing

Contributions are welcome! Here's how you can help:

1. Fork the repository
2. Create a new branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Commit your changes (`git commit -m 'Add some amazing feature'`)
5. Push to the branch (`git push origin feature/amazing-feature`)
6. Open a Pull Request

## Security Note

This application requires read-only access to your Gmail account. The authentication tokens are stored locally in `token.pickle` and your credentials are never shared with third parties.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.