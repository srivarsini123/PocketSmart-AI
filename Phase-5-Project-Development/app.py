import json
import os
import sqlite3
from datetime import datetime

import requests
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request

load_dotenv()

app = Flask(__name__)

DATABASE_PATH = os.path.join(app.root_path, "database", "pocketsmart.db")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash").strip()
GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    f"{GEMINI_MODEL}:generateContent"
)


def get_db_connection():
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_database():
    connection = get_db_connection()
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS analyses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            income REAL NOT NULL,
            total_expenses REAL NOT NULL,
            remaining_balance REAL NOT NULL,
            savings_goal REAL NOT NULL DEFAULT 0,
            preferences TEXT,
            expenses_json TEXT NOT NULL,
            analysis_json TEXT NOT NULL,
            ai_suggestions TEXT,
            created_at TEXT NOT NULL
        )
        """
    )
    connection.commit()
    connection.close()


def clean_number(value, field_name):
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{field_name} must be a valid number.")

    if number < 0:
        raise ValueError(f"{field_name} cannot be negative.")

    return round(number, 2)


def calculate_budget(income, expenses, savings_goal):
    total_expenses = round(sum(item["amount"] for item in expenses), 2)
    remaining = round(income - total_expenses, 2)

    categories = []
    for item in expenses:
        percentage = (
            round((item["amount"] / total_expenses) * 100, 1)
            if total_expenses > 0
            else 0
        )
        categories.append(
            {
                "category": item["category"],
                "amount": item["amount"],
                "percentage": percentage,
            }
        )

    categories.sort(key=lambda item: item["amount"], reverse=True)

    if income == 0:
        health = "No income entered"
    elif remaining < 0:
        health = "Overspending"
    elif savings_goal > remaining:
        health = "Savings goal is higher than the current balance"
    elif total_expenses / income >= 0.80:
        health = "High spending"
    elif total_expenses / income >= 0.50:
        health = "Moderate spending"
    else:
        health = "Healthy spending"

    expense_ratio = round((total_expenses / income) * 100, 1) if income else 0

    return {
        "total_expenses": total_expenses,
        "remaining_balance": remaining,
        "expense_ratio": expense_ratio,
        "health": health,
        "categories": categories,
    }


def fallback_suggestions(income, budget, savings_goal, preferences):
    suggestions = []

    if budget["remaining_balance"] < 0:
        suggestions.append(
            "Your expenses are higher than your income. Review the largest categories first and reduce non-essential spending."
        )
    elif budget["remaining_balance"] == 0:
        suggestions.append(
            "Your income is fully used by expenses. Try creating a small emergency buffer before adding optional spending."
        )
    else:
        suggestions.append(
            f"You currently have ₹{budget['remaining_balance']:.2f} remaining after expenses."
        )

    if savings_goal > 0:
        if budget["remaining_balance"] >= savings_goal:
            suggestions.append(
                f"Your current balance can cover the ₹{savings_goal:.2f} savings goal."
            )
        else:
            suggestions.append(
                f"Your ₹{savings_goal:.2f} savings goal is above the current remaining balance. Consider lowering expenses or adjusting the goal."
            )

    if budget["categories"]:
        largest = budget["categories"][0]
        suggestions.append(
            f"Your largest expense category is {largest['category']} at ₹{largest['amount']:.2f} ({largest['percentage']:.1f}% of expenses)."
        )

    if preferences:
        suggestions.append(
            f"Keep your stated preference in mind while planning: {preferences}."
        )

    suggestions.append(
        "Use the spending breakdown regularly so you can identify categories that can be reduced."
    )

    return suggestions


def get_gemini_suggestions(income, expenses, budget, savings_goal, preferences):
    if not GEMINI_API_KEY:
        return fallback_suggestions(income, budget, savings_goal, preferences), False, (
            "Gemini API key is not configured. Showing local budget suggestions."
        )

    expense_lines = "\n".join(
        f"- {item['category']}: ₹{item['amount']:.2f}" for item in expenses
    )

    prompt = f"""
You are PocketSmart AI, a beginner-friendly personal budgeting assistant.

Analyze the following monthly budget information:
Monthly income: ₹{income:.2f}
Total expenses: ₹{budget['total_expenses']:.2f}
Remaining balance: ₹{budget['remaining_balance']:.2f}
Savings goal: ₹{savings_goal:.2f}
User preferences/needs: {preferences or 'Not provided'}

Expenses:
{expense_lines or '- No expenses entered'}

Provide practical, non-judgmental budgeting suggestions.

Return exactly this JSON structure:
{{
  "summary": "2-3 sentence summary",
  "suggestions": [
    "suggestion 1",
    "suggestion 2",
    "suggestion 3"
  ],
  "priority": "Low, Medium, or High"
}}

Do not invent income or expenses. Use Indian Rupee amounts when mentioning money.
This is educational budgeting guidance, not professional financial advice.
"""

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.4,
            "responseMimeType": "application/json",
        },
    }

    try:
        response = requests.post(
            GEMINI_URL,
            headers={
                "Content-Type": "application/json",
                "x-goog-api-key": GEMINI_API_KEY,
            },
            json=payload,
            timeout=45,
        )
        response.raise_for_status()
        data = response.json()

        text = data["candidates"][0]["content"]["parts"][0]["text"]
        result = json.loads(text)

        suggestions = result.get("suggestions", [])
        if not isinstance(suggestions, list):
            suggestions = []

        return (
            {
                "summary": str(result.get("summary", "AI analysis completed.")),
                "suggestions": [str(item) for item in suggestions],
                "priority": str(result.get("priority", "Medium")),
            },
            True,
            None,
        )

    except (requests.RequestException, KeyError, IndexError, json.JSONDecodeError) as error:
        print(f"Gemini API error: {error}")
        return (
            {
                "summary": "Gemini could not be reached, so PocketSmart used its local budget analysis.",
                "suggestions": fallback_suggestions(
                    income, budget, savings_goal, preferences
                ),
                "priority": "Medium",
            },
            False,
            "Gemini request failed. Showing local suggestions instead.",
        )


def save_analysis(income, savings_goal, preferences, expenses, budget, ai_result):
    connection = get_db_connection()
    connection.execute(
        """
        INSERT INTO analyses (
            income,
            total_expenses,
            remaining_balance,
            savings_goal,
            preferences,
            expenses_json,
            analysis_json,
            ai_suggestions,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            income,
            budget["total_expenses"],
            budget["remaining_balance"],
            savings_goal,
            preferences,
            json.dumps(expenses),
            json.dumps(budget),
            json.dumps(ai_result),
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        ),
    )
    connection.commit()
    connection.close()


@app.route("/")
def home():
    return render_template("index.html")


@app.get("/api/health")
def health():
    return jsonify(
        {
            "status": "ok",
            "gemini_configured": bool(GEMINI_API_KEY),
            "database": os.path.exists(DATABASE_PATH),
        }
    )


@app.post("/api/analyze")
def analyze():
    try:
        data = request.get_json(silent=True) or {}

        income = clean_number(data.get("income"), "Income")
        savings_goal = clean_number(
            data.get("savings_goal", 0), "Savings goal"
        )
        preferences = str(data.get("preferences", "")).strip()

        if income <= 0:
            raise ValueError("Monthly income must be greater than 0.")

        raw_expenses = data.get("expenses", [])
        if not isinstance(raw_expenses, list):
            raise ValueError("Expenses must be a list.")

        expenses = []
        for item in raw_expenses:
            category = str(item.get("category", "")).strip()
            amount = clean_number(item.get("amount"), "Expense amount")

            if not category:
                continue
            if amount <= 0:
                continue

            expenses.append(
                {
                    "category": category[:50],
                    "amount": amount,
                }
            )

        budget = calculate_budget(income, expenses, savings_goal)
        ai_result, ai_used, ai_message = get_gemini_suggestions(
            income,
            expenses,
            budget,
            savings_goal,
            preferences,
        )

        save_analysis(
            income,
            savings_goal,
            preferences,
            expenses,
            budget,
            ai_result,
        )

        return jsonify(
            {
                "success": True,
                "budget": budget,
                "ai": ai_result,
                "ai_used": ai_used,
                "message": ai_message,
            }
        )

    except ValueError as error:
        return jsonify({"success": False, "error": str(error)}), 400
    except Exception as error:
        print(f"Application error: {error}")
        return (
            jsonify(
                {
                    "success": False,
                    "error": "Something went wrong while processing your budget.",
                }
            ),
            500,
        )


@app.get("/api/history")
def history():
    connection = get_db_connection()
    rows = connection.execute(
        """
        SELECT id, income, total_expenses, remaining_balance,
               savings_goal, created_at
        FROM analyses
        ORDER BY id DESC
        LIMIT 10
        """
    ).fetchall()
    connection.close()

    return jsonify(
        {
            "history": [dict(row) for row in rows]
        }
    )


init_database()

if __name__ == "__main__":
    app.run(debug=True)
