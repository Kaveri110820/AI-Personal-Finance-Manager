<div align="center">

# 💰 AI Personal Finance Manager

**Track, budget, and grow your money — with AI-powered insights.**

A modern, dark-themed [Streamlit](https://streamlit.io) application that consolidates your bank statements,
budgets, bills, and investments into one clean dashboard. Gemini AI automates expense categorization and
delivers personalized savings advice, financial insights, and executive monthly summaries.

</div>

---

## 📋 Project Overview

Managing personal finances is fragmented: expenses live in one app, budgets in a spreadsheet, bills on a
calendar, and investments in yet another portal. **AI Personal Finance Manager** brings everything into a
single, privacy-first application.

- **Import once** — upload Excel (`.xlsx`/`.xls`/`.csv`) or PDF bank statements; dates, descriptions, and
  amounts are detected automatically.
- **Get organized instantly** — AI categorizes every transaction and maintains a running balance.
- **Stay in control** — set monthly and per-category budgets, track bills with reminders, and monitor
  investment allocation.
- **Understand the "why"** — Gemini analyzes your spending to suggest concrete savings, surface insights,
  and write an executive summary each month, exportable to a polished PDF.
- **Built to last** — a SQLAlchemy ORM data layer over SQLite with typed repositories, audit logging, and
  automatic table creation.

> **No API key? No problem.** Without `GEMINI_API_KEY`, the app runs on a built-in rule-based engine so every
> feature keeps working offline.

---

## ✨ Features

| Area | What it does |
| --- | --- |
| 🔐 **Authentication** | Local account registration and login (hashed passwords), per-user data isolation. |
| 📊 **Dashboard** | At-a-glance income, spending, savings, and net change with trend charts. |
| 📈 **Analytics** | Monthly income/expense series, category distribution, top expenses, and savings rates. |
| 🧾 **Transactions** | Add/edit/delete transactions, running balance, search, filters, and **AI categorization** (single + batch). |
| 🎯 **Budget** | Monthly overall budget plus per-category limits with live spent/remaining/overspent tracking. |
| 🗓️ **Bills** | Recurring bill tracker with status, due-today/overdue/upcoming windows and reminders. |
| 📉 **Investments** | Track holdings by type with allocation breakdown and portfolio totals. |
| 🤖 **AI Advisor** | Gemini-powered savings suggestions, financial insights, and an executive monthly summary. |
| 📄 **Reports** | Monthly report with all metrics, stored as historical snapshots, **exportable to PDF**. |
| ⬆️ **Upload** | Bulk-import bank statements from Excel or PDF with duplicate detection. |
| 🎨 **Theming** | Professional dark financial theme (Inter font, custom accent palette). |

---

## 📁 Folder Structure

```
AI-Personal-Finance-Manager/
├── app.py                    # Entry point — auth gate + page navigation
├── requirements.txt          # Pinned Python dependencies
├── .env.example              # Environment variable template
├── .streamlit/
│   └── config.toml           # Dark financial dashboard theme
├── pages/                    # Streamlit pages
│   ├── login.py              #   Login / registration screen
│   ├── dashboard.py          #   Overview dashboard
│   ├── analytics.py          #   Spending analytics
│   ├── transactions.py       #   Transactions + AI categorization + import
│   ├── budget.py             #   Monthly & category budgets
│   ├── bills.py              #   Bill tracker
│   ├── investments.py        #   Investment tracker
│   ├── reports.py            #   Monthly report + PDF export
│   ├── ai_advisor.py         #   AI savings advice & insights
│   ├── upload.py             #   Bulk statement import
│   └── settings.py           #   App settings
├── services/                 # Business logic
│   ├── auth_service.py       #   Registration, login, password hashing
│   ├── transaction_service.py#   Transactions CRUD, dedup, import, stats
│   ├── budget_service.py     #   Budget CRUD, spending vs. limits
│   ├── bill_service.py       #   Bill CRUD, due/overdue windows
│   ├── investment_service.py #   Investment CRUD, allocation
│   ├── report_service.py     #   Monthly report generation + snapshots
│   ├── analytics_service.py  #   Aggregations, series, distributions
│   └── ai_service.py         #   Gemini AI + rule-based fallback engine
├── database/                 # Data layer (SQLAlchemy ORM + SQLite)
│   ├── models.py             #   7 tables: transactions, budgets, bills,
│   │                         #   investments, users, reports, history
│   ├── crud.py               #   Generic + per-table repositories, audit log
│   └── database.py           #   Engine/session management, auto table creation
├── utils/
│   ├── charts.py             #   Chart helpers
│   ├── excel_reader.py       #   Excel/CSV bank statement parsing
│   ├── pdf_reader.py         #   PDF bank statement parsing
│   └── pdf_report.py         #   PDF monthly report rendering
└── data/                     # Runtime data (gitignored)
```

---

## 🚀 Installation

### Prerequisites
- **Python 3.10+** (developed and tested on 3.14)
- **pip**

### 1. Clone the repository

```bash
git clone https://github.com/your-username/AI-Personal-Finance-Manager.git
cd AI-Personal-Finance-Manager
```

### 2. Create and activate a virtual environment

```bash
python -m venv venv
```

- **Windows (PowerShell):**
  ```powershell
  venv\Scripts\Activate.ps1
  ```
- **macOS / Linux:**
  ```bash
  source venv/bin/activate
  ```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables (optional)

```bash
copy .env.example .env
```

Then open `.env` and add your key:

```
# Get a free key at https://aistudio.google.com/apikey
GEMINI_API_KEY=your_key_here

# Gemini model used for categorization, advice, insights and summaries
GEMINI_MODEL=gemini-3.5-flash
```

> **Tip:** leave `GEMINI_API_KEY` empty to run fully offline with the rule-based fallback engine.

### 5. Run the app

```bash
streamlit run app.py
```

Open [http://localhost:8501](http://localhost:8501), register an account, and start importing statements.

The SQLite database (`database/finance.db`) and all 7 tables are **created automatically on first run**.

---

## 🛠️ Technology Stack

| Layer | Technology |
| --- | --- |
| **Frontend / UI** | [Streamlit](https://streamlit.io) 1.61 + Material icons, dark financial theme |
| **AI** | Google Gemini (`google-genai`) — categorization, savings advice, insights, report summaries |
| **Data layer** | [SQLAlchemy](https://www.sqlalchemy.org/) 2.0 ORM + SQLite (WAL mode, foreign keys) |
| **Data processing** | pandas 3.x, NumPy |
| **Charts** | Plotly, Altair |
| **File parsing** | openpyxl, pdfplumber, pdfminer.six |
| **PDF export** | reportlab |
| **Config** | python-dotenv |

---

## 📸 Screenshots

*Add screenshots of your app and reference them here — e.g. place images in `docs/screenshots/`.*

### Dashboard
<p align="center">
  <img src="docs/screenshots/dashboard.png" alt="Dashboard" width="720">
</p>

### AI Advisor
<p align="center">
  <img src="docs/screenshots/ai_advisor.png" alt="AI Advisor" width="720">
</p>

### Reports
<p align="center">
  <img src="docs/screenshots/reports.png" alt="Monthly Report" width="720">
</p>

### Transactions
<p align="center">
  <img src="docs/screenshots/transactions.png" alt="Transactions" width="720">
</p>

---

## ☁️ Deployment

### Streamlit Community Cloud (recommended)

1. Push this repository to GitHub.
2. Go to [share.streamlit.io](https://share.streamlit.io) and create a new app from the repo.
3. Set `app.py` as the main script.
4. Add your `GEMINI_API_KEY` under **Advanced settings → Secrets**:
   ```toml
   GEMINI_API_KEY = "your_key_here"
   ```
5. Deploy. The app is served over HTTPS with no further configuration.

### Self-hosting

```bash
pip install -r requirements.txt
streamlit run app.py --server.port 8501 --server.address 0.0.0.0
```

> Note: the app is multi-user with per-user data isolation, but the default SQLite backend is
> single-instance. For concurrent production hosting, pair it with a shared/networked database file or
> run behind a reverse proxy (e.g. Nginx + systemd) on a VM.

---

## 🔮 Future Improvements

- [ ] Multi-user server-side sessions and shared/multi-process database backend (e.g. PostgreSQL).
- [ ] Bank/fintech API integrations for automatic statement syncing (Plaid, etc.).
- [ ] Scheduled bill reminders via email or push notifications.
- [ ] Currency conversion and multi-currency account support.
- [ ] AI chat assistant for natural-language questions about your finances.
- [ ] Recurring transaction detection and subscription tracking.
- [ ] Investment performance tracking with live price feeds.
- [ ] Import rule engine (auto-categorize by merchant or regex).
- [ ] Data export (CSV/JSON) and full backup/restore.
- [ ] Mobile-responsive layout refinements and PWA support.

---

## 📄 License

Distributed under the **MIT License**.

```
MIT License

Copyright (c) 2026 AI Personal Finance Manager

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

<div align="center">

**Made with ❤️ using Streamlit + Google Gemini**

</div>
