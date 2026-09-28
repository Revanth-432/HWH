# Memory Architecture — Customer Support Memory Agent

## Overview

The Customer Support Memory Agent uses **Hindsight** as a persistent, semantic memory store to give support agents instant context about a customer's full history — regardless of which channel (chat, email, or phone) the customer used.

## Why Memory Matters

Traditional support systems are **stateless**: each interaction starts from scratch. This means:

- Customers repeat themselves across channels.
- Agents waste time gathering context already provided in previous tickets.
- Escalations happen too late because nobody sees the full picture.

Our agent solves this by maintaining a **cross-channel memory graph** keyed by the customer's email address (stable ID).

## How It Works

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Chat Msg   │     │  Email Msg   │     │  Phone Call   │
└──────┬───────┘     └──────┬───────┘     └──────┬───────┘
       │                    │                    │
       └────────────┬───────┘────────────────────┘
                    ▼
         ┌─────────────────────┐
         │  Memory Agent (LLM) │
         │  - Summarise        │
         │  - Detect patterns  │
         │  - Flag escalations │
         └─────────┬───────────┘
                   ▼
         ┌─────────────────────┐
         │   Hindsight Store   │
         │  (Persistent Memory)│
         └─────────────────────┘
```

### Step-by-step Flow

1. **Ingest**: A new interaction arrives (from any channel).
2. **Identify**: The customer is identified by their email (`customer_id`).
3. **Recall**: The agent queries Hindsight for all prior context on this customer.
4. **Enrich**: The LLM (via Groq) summarises the history and assesses whether escalation is warranted.
5. **Store**: The new interaction + updated summary are written back to Hindsight.
6. **Respond**: The support agent (or automated reply) receives a context-rich brief before engaging the customer.

## Memory Schema

Each customer's memory record contains:

| Field                   | Description                                        |
|-------------------------|----------------------------------------------------|
| `customer_id`           | Email address (stable cross-channel identifier)    |
| `context_summary`       | LLM-generated summary of all past interactions     |
| `interaction_count`     | Total number of interactions across all channels    |
| `has_unresolved_issues` | Whether any interaction is still `open`             |
| `escalation_recommended`| Whether the LLM recommends escalation              |
| `recent_interactions`   | Last N interaction records for quick reference      |

## Escalation Logic

A ticket is flagged for escalation when **any** of these conditions are met:

- The customer has contacted support **3+ times** about the **same issue**.
- The customer's sentiment is classified as `frustrated` in **2+ consecutive** interactions.
- An issue has been `open` for **more than 5 business days**.
- The customer explicitly requests a manager or threatens churn.

## Technology Stack

| Component       | Technology              |
|-----------------|-------------------------|
| Backend API     | FastAPI + Uvicorn       |
| Memory Store    | Hindsight               |
| LLM Provider    | Groq (qwen/qwen3-32b)  |
| Data Validation | Pydantic                |
| Frontend        | Vanilla HTML/CSS/JS     |
