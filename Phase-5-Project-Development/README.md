# PocketSmart AI

PocketSmart AI is a beginner-friendly smart budget and recommendation assistant built with:

- Python
- Flask
- HTML
- CSS
- JavaScript
- SQLite
- Google Gemini API

## Features

1. Enter monthly income.
2. Add expense categories and amounts.
3. Calculate total expenses.
4. Calculate remaining balance.
5. Analyze spending by category.
6. Set a savings goal.
7. Add user needs/preferences.
8. Get Gemini AI budgeting suggestions.
9. Store recent analyses in SQLite.
10. Continue using local suggestions if Gemini is not configured or temporarily unavailable.

## Project structure

```text
PocketSmart-AI/
├── app.py
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
├── templates/
│   └── index.html
├── static/
│   ├── style.css
│   └── script.js
└── database/
    └── pocketsmart.db   # created automatically when the app starts
```

## Windows VS Code setup

Open the project folder in VS Code and run:

```powershell
python --version
```

Create a virtual environment:

```powershell
python -m venv .venv
```

Activate it:

```powershell
.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, you can run the project without activating the environment, or use Command Prompt with:

```cmd
.venv\Scripts\activate
```

Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

Create your environment file:

```powershell
copy .env.example .env
```

Open `.env` and replace:

```text
GEMINI_API_KEY=YOUR_GEMINI_API_KEY_HERE
```

with your own key.

Do not upload `.env` to GitHub.

## Run

```powershell
python app.py
```

Open:

```text
http://127.0.0.1:5000
```

## Test

Try:

- Income: 30000
- Savings goal: 5000
- Food: 4000
- Rent: 8000
- Transport: 2000
- Preferences: Save money for a laptop.

Click **Analyze My Budget**.

You should see:

- Total expenses
- Remaining balance
- Expense ratio
- Spending status
- Category analysis
- AI suggestions
- Recent analyses

## API endpoints

### Health

```text
GET /api/health
```

### Analyze budget

```text
POST /api/analyze
```

### History

```text
GET /api/history
```
