# CodeReview AI — Automated PR Review & Bug Detection System

CodeReview AI is an intelligent bot that automatically analyzes GitHub Pull Requests, identifies potential bugs, suggests fixes, and provides a centralized dashboard for tracking code quality metrics.

## Features
- **GitHub Integration**: Listen for PR events via webhooks.
- **LLM-Powered Analysis**: Uses GPT-4 or Llama 3 (via Groq) to perform deep code analysis.
- **Inline Feedback**: Automatically posts comments on GitHub PRs.
- **Admin Dashboard**: Visualize bug trends, severity distribution, and team velocity using Flask and Chart.js.
- **PostgreSQL Storage**: Maintains a history of all reviews and quality metrics.

## Project Structure
- `backend/`: FastAPI server for webhook handling and review orchestration.
- `dashboard/`: Flask application for the metrics dashboard.
- `core/`: Core logic for LLM analysis and database management.
- `github_actions/`: Example CI/CD workflows.

## Setup Instructions

### 1. Prerequisites
- Python 3.8+
- PostgreSQL
- OpenAI or Groq API Key
- GitHub Personal Access Token (for posting comments)

### 2. Environment Variables
Create a `.env` file in the root directory:
```env
DATABASE_URL=postgresql://user:pass@localhost:5432/codereview_ai
GITHUB_WEBHOOK_SECRET=your_secret
GITHUB_TOKEN=your_github_token
OPENAI_API_KEY=your_openai_key
# Optional
LLM_PROVIDER=openai # or groq
GROQ_API_KEY=your_groq_key
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Initialize Database
```bash
python -m core.database
```

### 5. Run the Backend
```bash
uvicorn backend.main:app --port 8000
```

### 6. Run the Dashboard
```bash
python dashboard/app.py
```

## Dashboard
Access the dashboard at `http://localhost:5000` to see real-time code quality metrics.
