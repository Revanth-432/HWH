# 🧠 Customer Support Memory Agent

> **Hackathon Project** — An AI-powered support agent that remembers every customer interaction across chat, email, and phone, so no one ever has to repeat themselves.

## ✨ What It Does

- **Cross-channel memory**: Links customer interactions across chat, email, and phone using email as a stable ID.
- **Smart summarisation**: Uses an LLM (via Groq) to generate concise briefs of a customer's full history.
- **Escalation detection**: Automatically flags tickets where customers have contacted 3+ times about the same unresolved issue.
- **Persistent memory**: Stores and retrieves customer context via [Hindsight](https://hindsight.dev).

## 📁 Project Structure

```
support-memory-agent/
├── backend/
│   ├── app.py                      # FastAPI entry-point
│   ├── hindsight_client.py         # Hindsight API wrapper
│   ├── llm_client.py               # Groq LLM wrapper
│   ├── memory_schema.py            # Pydantic data models
│   ├── requirements.txt            # Python dependencies
│   ├── .env.example                # Environment variable template
│   ├── test_hindsight_connection.py # Hindsight smoke test
│   └── test_groq_connection.py     # Groq smoke test
├── frontend/
│   ├── index.html                  # Dashboard UI
│   ├── app.js                      # Frontend logic
│   └── styles.css                  # Styling
├── data/
│   └── seed_customers.json         # Synthetic test data (5 customers)
├── docs/
│   └── memory_explanation.md       # Architecture documentation
├── .gitignore
└── README.md
```

## 🚀 Quick Start

### 1. Clone & enter the project

```bash
git clone <your-repo-url>
cd support-memory-agent
```

### 2. Set up the Python environment

```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS / Linux
pip install -r requirements.txt
```

### 3. Configure environment variables

```bash
cp .env.example .env
# Edit .env with your actual API keys
```

### 4. Run smoke tests

```bash
python test_groq_connection.py
python test_hindsight_connection.py
```

### 5. Start the backend

```bash
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at **http://localhost:8000**.  
Interactive docs at **http://localhost:8000/docs**.

## 🔌 API Endpoints

| Method | Endpoint              | Description                          |
|--------|-----------------------|--------------------------------------|
| GET    | `/`                   | Health check                         |
| GET    | `/health`             | Health status                        |
| GET    | `/customers`          | List all customers                   |
| GET    | `/customers/{email}`  | Get a single customer by email       |
| POST   | `/summarise/{email}`  | Generate LLM summary of interactions |
| POST   | `/escalate/{email}`   | Assess escalation for a customer     |

## 🧪 Seed Data

The `data/seed_customers.json` file contains 5 synthetic customers:

| Customer         | Interactions | Channels          | Key Scenario                     |
|------------------|-------------|-------------------|----------------------------------|
| Priya Sharma     | 4           | chat, email, phone | 🔴 Repeat unresolved billing issue (escalation test) |
| Marcus Johnson   | 2           | email, chat        | ✅ Bug reported & resolved with workaround |
| Aisha Patel      | 3           | chat, email, phone | ✅ Onboarding journey, fully resolved |
| David Chen       | 3           | phone, chat, email | 🟡 Compounding API integration issues |
| Fatima Al-Rashid | 2           | email, chat        | ✅ Plan upgrade, smooth experience |

## 🛠 Tech Stack

- **Backend**: Python · FastAPI · Uvicorn
- **Memory**: Hindsight
- **LLM**: Groq (qwen/qwen3-32b)
- **Frontend**: HTML · CSS · JavaScript
- **Validation**: Pydantic

## 📄 License

MIT
