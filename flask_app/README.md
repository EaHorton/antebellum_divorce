# Antebellum Divorce Petitions Flask App

A Flask web application with Plotly visualizations for exploring historical divorce petition data.

## Features

- Interactive Plotly charts:
  - Petitions by State (bar chart)
  - Petitions Over Time (line chart)
  - Petition Results Distribution (pie chart)
  - Top Counties by Petition Count (bar chart)
- Real-time statistics dashboard
- RESTful API endpoints for data access

## Installation

1. Install the required packages:
```bash
pip install -r requirements.txt
```

## Usage

1. Run the Flask app:
```bash
python app.py
```

2. Open your browser and navigate to:
```
http://localhost:5000
```

## API Endpoints

- `GET /` - Main dashboard page
- `GET /api/stats` - Get basic statistics (JSON)
- `GET /plot/petitions_by_state` - State distribution chart data
- `GET /plot/petitions_by_year` - Temporal distribution chart data
- `GET /plot/petitions_by_result` - Results distribution chart data
- `GET /plot/petitions_by_county` - Top counties chart data
- `GET /data/petitions` - Get first 100 petitions (JSON)

## Project Structure

```
flask_app/
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── templates/
│   └── index.html        # Dashboard template
└── README.md             # This file
```

## Database

The app connects to `../dv_petitions.db.bak` and queries the following tables:
- Petitions (main table with divorce petition records)

## Technologies

- **Flask**: Web framework
- **Plotly**: Interactive data visualizations
- **Pandas**: Data manipulation
- **SQLite3**: Database connection
