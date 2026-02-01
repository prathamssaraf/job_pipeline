# Job Pipeline Tracker

A powerful, automated tool to track job openings from various company career pages. It uses AI (Google Gemini) to parse job listings from HTML, identifies new opportunities, and sends email notifications.

## Features

- **Dashboard**: A modern web interface to view jobs, manage sources, and control the pipeline.
- **Smart Fetching**: Routes requests through a headless browser (Selenium) for dynamic sites or standard HTTP for static pages.
- **AI Parsing**: Uses Google Gemini to intelligently extract job details (Title, Company, Location, URL) from raw HTML.
- **Change Detection**: Alerts you only when *new* jobs appear.
- **Source Management**: Add/remove job sources directly from the UI.
- **Schedule**: Run the pipeline automatically at set intervals.

## Setup

1.  **Clone the repository** (if not already done).
2.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```
3.  **Configure Environment**:
    - Copy `.env.example` to `.env`.
    - Add your **Google Gemini API Key** (`GOOGLE_API_KEY`).
    - Add your **Email Credentials** (`SMTP_EMAIL`, `SMTP_PASSWORD`) for notifications.
    - (Optional) Configure `CHECK_INTERVAL_HOURS`.

## Usage

### Web Dashboard (Recommended)

Start the dashboard server:

```bash
python server.py
```

Open a browser and navigate to: [http://localhost:5000](http://localhost:5000)

From the dashboard, you can:
- **Add Sources**: click "+ Add Source" and paste the URL of a career page.
- **Run Pipeline**: Click "Run Pipeline" to check all sources immediately.
- **View Jobs**: Browse identified jobs, filter by company, or search.
- **Configure Scheduler**: Set the automatic check interval in Settings.

### CLI Mode (Legacy)

You can also run the tracker via command line:

```bash
python tracker.py --run
```

For more options:
```bash
python tracker.py --help
```

## detailed Architecture

- **`server.py`**: Flask web server and API backend.
- **`unified_fetcher.py`**: Handles fetching logic, switching between HTTP and Selenium.
- **`parser.py`**: Interfaces with Google Gemini API to structure job data.
- **`storage.py`**: SQLite database management for jobs and sources.
- **`notifier.py`**: Handles email alerts.
