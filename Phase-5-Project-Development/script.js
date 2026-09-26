const expenseRows = document.getElementById("expenseRows");
const budgetForm = document.getElementById("budgetForm");
const addExpenseBtn = document.getElementById("addExpenseBtn");
const formMessage = document.getElementById("formMessage");
const results = document.getElementById("results");

function addExpenseRow(category = "", amount = "") {
    const row = document.createElement("div");
    row.className = "expense-row";

    row.innerHTML = `
        <label>
            Category
            <input class="expense-category" type="text"
                   placeholder="Food, Rent, Travel..." value="${escapeHtml(category)}">
        </label>
        <label>
            Amount (₹)
            <input class="expense-amount" type="number"
                   min="0" step="0.01" placeholder="0" value="${amount}">
        </label>
        <button type="button" class="delete-btn">Remove</button>
    `;

    row.querySelector(".delete-btn").addEventListener("click", () => {
        row.remove();
        if (!expenseRows.children.length) {
            addExpenseRow();
        }
    });

    expenseRows.appendChild(row);
}

function escapeHtml(value) {
    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}

function getExpenses() {
    return [...document.querySelectorAll(".expense-row")]
        .map((row) => ({
            category: row.querySelector(".expense-category").value.trim(),
            amount: row.querySelector(".expense-amount").value
        }))
        .filter((item) => item.category && item.amount);
}

function formatMoney(value) {
    return `₹${Number(value).toLocaleString("en-IN", {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    })}`;
}

function showCategoryAnalysis(categories) {
    const container = document.getElementById("categoryAnalysis");

    if (!categories.length) {
        container.innerHTML = `<p class="empty-state">No expenses were entered.</p>`;
        return;
    }

    container.innerHTML = categories.map((item) => `
        <div class="category-item">
            <div class="category-line">
                <strong>${escapeHtml(item.category)}</strong>
                <span>${formatMoney(item.amount)} • ${item.percentage}%</span>
            </div>
            <div class="progress-track">
                <div class="progress-bar" style="width:${Math.min(item.percentage, 100)}%"></div>
            </div>
        </div>
    `).join("");
}

function showAI(ai) {
    document.getElementById("aiSummary").textContent = ai.summary || "";

    const list = document.getElementById("suggestions");
    list.innerHTML = "";

    (ai.suggestions || []).forEach((suggestion) => {
        const li = document.createElement("li");
        li.textContent = suggestion;
        list.appendChild(li);
    });
}

async function loadHistory() {
    try {
        const response = await fetch("/api/history");
        const data = await response.json();

        const history = document.getElementById("history");

        if (!data.history.length) {
            history.innerHTML = `<p class="empty-state">No previous analyses yet.</p>`;
            return;
        }

        history.innerHTML = `
            <div style="overflow-x:auto;">
                <table class="history-table">
                    <thead>
                        <tr>
                            <th>Date</th>
                            <th>Income</th>
                            <th>Expenses</th>
                            <th>Balance</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${data.history.map((item) => `
                            <tr>
                                <td>${escapeHtml(item.created_at)}</td>
                                <td>${formatMoney(item.income)}</td>
                                <td>${formatMoney(item.total_expenses)}</td>
                                <td>${formatMoney(item.remaining_balance)}</td>
                            </tr>
                        `).join("")}
                    </tbody>
                </table>
            </div>
        `;
    } catch (error) {
        console.error(error);
    }
}

budgetForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const income = document.getElementById("income").value;
    const savingsGoal = document.getElementById("savingsGoal").value || 0;
    const preferences = document.getElementById("preferences").value.trim();
    const expenses = getExpenses();

    if (!income || Number(income) <= 0) {
        formMessage.textContent = "Please enter a valid monthly income.";
        return;
    }

    const button = document.getElementById("analyzeBtn");
    button.disabled = true;
    button.textContent = "Analyzing...";
    formMessage.textContent = "";

    try {
        const response = await fetch("/api/analyze", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                income,
                savings_goal: savingsGoal,
                preferences,
                expenses
            })
        });

        const data = await response.json();

        if (!response.ok || !data.success) {
            throw new Error(data.error || "Unable to analyze the budget.");
        }

        document.getElementById("totalExpenses").textContent =
            formatMoney(data.budget.total_expenses);

        document.getElementById("remainingBalance").textContent =
            formatMoney(data.budget.remaining_balance);

        document.getElementById("expenseRatio").textContent =
            `${data.budget.expense_ratio}%`;

        document.getElementById("healthStatus").textContent =
            data.budget.health;

        document.getElementById("aiBadge").textContent =
            data.ai_used ? "Gemini AI connected" : "Local analysis";

        showCategoryAnalysis(data.budget.categories);
        showAI(data.ai);

        results.classList.remove("hidden");
        results.scrollIntoView({ behavior: "smooth" });

        formMessage.textContent =
            data.message || "Budget analysis completed successfully.";

        await loadHistory();
    } catch (error) {
        formMessage.textContent = error.message;
    } finally {
        button.disabled = false;
        button.textContent = "Analyze My Budget";
    }
});

addExpenseBtn.addEventListener("click", () => addExpenseRow());

addExpenseRow("Food", "");
addExpenseRow("Rent", "");
addExpenseRow("Transport", "");

loadHistory();
