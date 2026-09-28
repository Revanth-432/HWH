/**
 * app.js
 * ------
 * Frontend logic for the Support Memory Agent — Phase 2.
 * Wires the DOM to the FastAPI backend running at localhost:8000.
 */

const API_BASE = "http://localhost:8000";

// ─── DOM References ───────────────────────────────────────────────
const customerSelect   = document.getElementById("customer-select");
const channelSelect    = document.getElementById("channel-select");
const channelBadge     = document.getElementById("channel-badge");
const memoryToggle     = document.getElementById("memory-toggle");
const memoryStatus     = document.getElementById("memory-status");
const chatMessages     = document.getElementById("chat-messages");
const chatEmpty        = document.getElementById("chat-empty");
const chatForm         = document.getElementById("chat-form");
const chatInput        = document.getElementById("chat-input");
const chatSendBtn      = document.getElementById("chat-send-btn");
const memoryContent    = document.getElementById("memory-content");
const memoryEmpty      = document.getElementById("memory-empty");
const refreshMemoryBtn = document.getElementById("refresh-memory-btn");
const statCount        = document.getElementById("stat-count");
const statStatus       = document.getElementById("stat-status");
const toastContainer   = document.getElementById("toast-container");

// ─── State ────────────────────────────────────────────────────────
let customers      = [];
let chatHistory    = [];   // { role: 'user'|'agent', text, memoryUsed?, channel? }
let isSending      = false;

// ─── Channel config ───────────────────────────────────────────────
const CHANNEL_MAP = {
    chat:  { icon: "💬", label: "CHAT" },
    email: { icon: "📧", label: "EMAIL" },
    phone: { icon: "📞", label: "PHONE" },
};


// ===================================================================
//  INITIALISATION
// ===================================================================

document.addEventListener("DOMContentLoaded", async () => {
    console.log("🧠 Support Memory Agent frontend loaded.");
    wireEventListeners();
    await loadCustomers();
});


function wireEventListeners() {
    // Memory toggle
    memoryToggle.addEventListener("change", () => {
        const isOn = memoryToggle.checked;
        memoryStatus.textContent = isOn ? "ON" : "OFF";
        memoryStatus.classList.toggle("off", !isOn);
        if (isOn) {
            refreshMemory();
        }
    });

    // Channel select → update badge
    channelSelect.addEventListener("change", () => {
        const ch = channelSelect.value;
        const info = CHANNEL_MAP[ch] || CHANNEL_MAP.chat;
        channelBadge.textContent = info.label;
    });

    // Customer select → refresh memory
    customerSelect.addEventListener("change", () => {
        clearChat();
        refreshMemory();
    });

    // Chat form submit
    chatForm.addEventListener("submit", (e) => {
        e.preventDefault();
        sendMessage();
    });

    // Refresh memory button
    refreshMemoryBtn.addEventListener("click", () => {
        refreshMemory();
    });
}


// ===================================================================
//  LOAD CUSTOMERS
// ===================================================================

async function loadCustomers() {
    try {
        const res = await fetch(`${API_BASE}/customers`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        customers = await res.json();

        customerSelect.innerHTML = "";

        if (customers.length === 0) {
            customerSelect.innerHTML = '<option value="">No customers found</option>';
            return;
        }

        customers.forEach((c) => {
            const opt = document.createElement("option");
            opt.value = c.email;
            opt.textContent = `${c.name}`;
            customerSelect.appendChild(opt);
        });

        // Trigger initial memory fetch
        refreshMemory();
    } catch (err) {
        console.error("Failed to load customers:", err);
        customerSelect.innerHTML = '<option value="">⚠ Error loading</option>';
        showToast("Failed to connect to backend. Is the server running?", "error");
    }
}


// ===================================================================
//  SEND MESSAGE
// ===================================================================

async function sendMessage() {
    const message     = chatInput.value.trim();
    const customerId  = customerSelect.value;
    const channel     = channelSelect.value;
    const memoryOff   = !memoryToggle.checked;

    if (!message || !customerId || isSending) return;

    isSending = true;
    chatInput.value = "";
    chatSendBtn.disabled = true;

    // Hide empty state
    chatEmpty.style.display = "none";

    // Add user bubble
    addChatBubble("user", message, { channel, memoryUsed: !memoryOff });

    // Show typing indicator
    const typingEl = addTypingIndicator();

    // Update stats
    setStatus("loading", "Thinking…");

    try {
        const res = await fetch(`${API_BASE}/message`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                customer_id: customerId,
                channel: channel,
                message: message,
                memory_off: memoryOff,
            }),
        });

        if (!res.ok) {
            const errData = await res.json().catch(() => ({}));
            throw new Error(errData.detail || `HTTP ${res.status}`);
        }

        const data = await res.json();

        // Remove typing indicator
        typingEl.remove();

        // Add agent bubble
        addChatBubble("agent", data.reply, {
            channel,
            memoryUsed: data.memory_used,
            memoryCount: data.memory_results_count,
        });

        setStatus("ready", "Ready");

        // Refresh memory panel
        await refreshMemory();

    } catch (err) {
        typingEl.remove();
        console.error("Message send failed:", err);
        showToast(`Error: ${err.message}`, "error");
        setStatus("error", "Error");
    } finally {
        isSending = false;
        chatSendBtn.disabled = false;
        chatInput.focus();
    }
}


// ===================================================================
//  CHAT BUBBLES
// ===================================================================

function addChatBubble(role, text, opts = {}) {
    const bubble = document.createElement("div");
    bubble.className = `msg msg--${role}`;

    const metaHtml = buildMetaHtml(role, opts);

    bubble.innerHTML = `
        ${metaHtml}
        <div class="msg__body">${escapeHtml(text)}</div>
    `;

    chatMessages.appendChild(bubble);
    chatMessages.scrollTop = chatMessages.scrollHeight;

    chatHistory.push({ role, text, ...opts });
    return bubble;
}


function addTypingIndicator() {
    const el = document.createElement("div");
    el.className = "msg msg--agent msg--typing";
    el.innerHTML = `
        <div class="msg__meta">
            <span>SupportBot</span>
        </div>
        <div class="typing-dots">
            <span></span><span></span><span></span>
        </div>
    `;
    chatMessages.appendChild(el);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    return el;
}


function buildMetaHtml(role, opts) {
    if (role === "user") {
        const chInfo = CHANNEL_MAP[opts.channel] || CHANNEL_MAP.chat;
        return `
            <div class="msg__meta">
                <span>${chInfo.icon} Customer</span>
            </div>
        `;
    }

    // Agent meta
    let memBadge = "";
    if (opts.memoryUsed !== undefined) {
        if (opts.memoryUsed) {
            memBadge = `<span class="msg__memory-badge msg__memory-badge--on">🧠 Memory ON (${opts.memoryCount || 0})</span>`;
        } else {
            memBadge = `<span class="msg__memory-badge msg__memory-badge--off">🚫 Memory OFF</span>`;
        }
    }

    return `
        <div class="msg__meta">
            <span>🤖 SupportBot</span>
            ${memBadge}
        </div>
    `;
}


function clearChat() {
    chatHistory = [];
    chatMessages.innerHTML = "";
    chatEmpty.style.display = "";
    chatMessages.appendChild(chatEmpty);
}


// ===================================================================
//  MEMORY PANEL
// ===================================================================

async function refreshMemory() {
    const customerId = customerSelect.value;
    if (!customerId) return;

    refreshMemoryBtn.classList.add("spinning");
    setStatus("loading", "Loading…");

    try {
        const res = await fetch(`${API_BASE}/customers/${encodeURIComponent(customerId)}/history`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);

        const data = await res.json();
        renderMemory(data);
    } catch (err) {
        console.error("Memory fetch failed:", err);
        setStatus("error", "Error");
    } finally {
        refreshMemoryBtn.classList.remove("spinning");
    }
}


function renderMemory(data) {
    // Clear existing
    memoryContent.innerHTML = "";

    const results = data.results || [];
    statCount.textContent = results.length;

    if (results.length === 0) {
        memoryContent.innerHTML = `
            <div class="memory-empty">
                <div class="memory-empty__icon">📭</div>
                <p>No memories found for this customer.</p>
                <p class="memory-empty__sub">Interactions will appear here once messages are sent.</p>
            </div>
        `;
        setStatus("ready", "Empty");
        return;
    }

    results.forEach((item, idx) => {
        const card = document.createElement("div");
        card.className = "memory-card";
        card.style.animationDelay = `${idx * 0.06}s`;

        const text = item.text || "";
        const parsed = parseMemoryText(text);

        card.innerHTML = buildMemoryCardHtml(parsed, idx);
        memoryContent.appendChild(card);
    });

    setStatus("ready", "Ready");
}


function parseMemoryText(text) {
    const fields = { _raw: text };
    const lines = text.split("\n");

    lines.forEach((line) => {
        const match = line.match(/^([^:]+):\s*(.+)$/);
        if (match) {
            const key = match[1].trim();
            const val = match[2].trim();
            fields[key] = val;
        } else if (line.startsWith("[")) {
            fields["_header"] = line.replace(/[\[\]]/g, "").trim();
        }
    });

    return fields;
}


function buildMemoryCardHtml(fields, index) {
    const header = fields["_header"] || `Fact #${index + 1}`;
    const channel = fields["Channel"] || "";
    const chInfo = CHANNEL_MAP[channel] || { icon: "🧠", label: "MEMORY" };

    const status = (fields["Resolution Status"] || "").toLowerCase();
    let statusBadgeClass = "";
    if (status.includes("open")) statusBadgeClass = "status-badge--open";
    else if (status.includes("resolved")) statusBadgeClass = "status-badge--resolved";
    else if (status.includes("escalated")) statusBadgeClass = "status-badge--escalated";

    // Fields to display
    const displayFields = [
        { label: "Customer Message", key: "Customer Message" },
        { label: "Issue Summary", key: "Issue Summary" },
        { label: "Attempted Fix", key: "Attempted Fix" },
        { label: "Sentiment", key: "Customer Sentiment" },
        { label: "Contact Count", key: "Contact Count (for this issue)" },
    ];

    let fieldsHtml = "";
    let foundStructured = false;

    displayFields.forEach((f) => {
        const val = fields[f.key];
        if (val) {
            foundStructured = true;
            fieldsHtml += `
                <div class="memory-card__field">
                    <div class="memory-card__field-label">${f.label}</div>
                    <div class="memory-card__field-value">${escapeHtml(val)}</div>
                </div>
            `;
        }
    });

    // Fallback: If no structured fields were parsed, it's a natural language fact from Hindsight's knowledge graph.
    if (!foundStructured && fields._raw) {
        fieldsHtml += `
            <div class="memory-card__field">
                <div class="memory-card__field-value" style="font-family: var(--font-body); font-size: 0.8rem; margin-top: 0.2rem; color: var(--text-primary); line-height: 1.5;">${escapeHtml(fields._raw)}</div>
            </div>
        `;
    }

    // Resolution status badge
    let statusHtml = "";
    if (fields["Resolution Status"]) {
        statusHtml = `
            <div class="memory-card__field">
                <div class="memory-card__field-label">Status</div>
                <span class="status-badge ${statusBadgeClass}">${escapeHtml(fields["Resolution Status"])}</span>
            </div>
        `;
    }

    // Timestamp
    let timeHtml = "";
    if (fields["Timestamp"]) {
        const ts = new Date(fields["Timestamp"]);
        const formatted = ts.toLocaleString("en-IN", {
            month: "short",
            day: "numeric",
            hour: "2-digit",
            minute: "2-digit",
        });
        timeHtml = `<span style="font-size:0.62rem; color:var(--text-muted); margin-left:auto;">${formatted}</span>`;
    }

    return `
        <div class="memory-card__header">
            <span class="memory-card__channel-icon">${chInfo.icon}</span>
            ${escapeHtml(header)}
            ${timeHtml}
        </div>
        ${statusHtml}
        ${fieldsHtml}
    `;
}


// ===================================================================
//  STATUS & TOASTS
// ===================================================================

function setStatus(state, text) {
    statStatus.textContent = text;
    statStatus.className = `stat-value stat-value--${state}`;
}


function showToast(message, type = "info") {
    const toast = document.createElement("div");
    toast.className = `toast toast--${type}`;
    toast.textContent = message;
    toastContainer.appendChild(toast);

    setTimeout(() => {
        toast.style.animation = "toast-out 0.3s var(--ease-out) forwards";
        setTimeout(() => toast.remove(), 350);
    }, 4000);
}


// ===================================================================
//  UTILITIES
// ===================================================================

function escapeHtml(str) {
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
}
