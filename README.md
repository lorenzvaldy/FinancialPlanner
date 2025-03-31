# Personal Financial Planner

A comprehensive web application for managing personal finances, including budgeting, transaction tracking, financial reporting, and goal setting.

## Features

- **Dashboard**: Overview of financial status with key metrics and visualizations
- **Budget Management**: Monthly and yearly budget tracking with progress monitoring
- **Transaction Tracking**: Record and categorize income and expenses
- **Financial Reports**: Detailed analysis and visualization of financial data
- **Goal Setting**: Track and monitor financial goals with progress indicators

## Technologies Used

- **Backend**: Python with Flask
- **Database**: SQLite
- **Frontend**: HTML5, CSS3, JavaScript
- **UI Framework**: Bootstrap 5
- **Charts**: Chart.js
- **Icons**: Font Awesome

## Prerequisites

- Python 3.8 or higher
- pip (Python package installer)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/financial-planner.git
cd financial-planner
```

2. Create a virtual environment (recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows, use: venv\Scripts\activate
```

3. Install the required packages:
```bash
pip install -r requirements.txt
```

## Running the Application

1. Activate the virtual environment (if not already activated):
```bash
source venv/bin/activate  # On Windows, use: venv\Scripts\activate
```

2. Initialize the database:
```bash
python init_db.py
```

3. Start the Flask development server:
```bash
python app.py
```

4. Open your web browser and navigate to:
```
http://localhost:5000
```

## Project Structure

```
financial-planner/
├── app.py              # Main Flask application
├── init_db.py          # Database initialization script
├── requirements.txt    # Python dependencies
├── static/            # Static files (CSS, JS, images)
│   ├── css/
│   └── js/
└── templates/         # HTML templates
    ├── base.html
    ├── dashboard.html
    ├── budget.html
    ├── transactions.html
    ├── reports.html
    └── goals.html
```

## Contributing

1. Fork the repository
2. Create a new branch for your feature
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Bootstrap for the UI framework
- Chart.js for data visualization
- Font Awesome for icons 