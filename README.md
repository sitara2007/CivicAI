# CivicAI

AI-powered workflow automation engine for government and public sector document triage, classification, and routing.

## 🌐 Live Infrastructure & Deployment

- **Frontend Application:** [https://civic-ai-gray.vercel.app](https://civic-ai-gray.vercel.app)
- **Database Engine:** Managed PostgreSQL on [Railway](https://railway.com) (Driver-level SSL Enforced)
- **Healthcheck Endpoint:** `GET /health` (Returns `200 OK`)

---

## ⚡ Technical Architecture

- **Cryptographic Audit Trail:** Hash-chain audit log where each document state is chained to prevent post-hoc tampering.
- **Strict Data Isolation:** Enforced TLS connections (`sslmode=require`) at driver layer for compliance.
- **Low-Latency Ingestion:** Optimized for high-throughput PII redaction and document triage.

---

## 🛠️ Local Setup

```bash
# Clone repository
git clone [https://github.com/sitara2007/CivicOs.git](https://github.com/sitara2007/CivicOs.git)
cd CivicOs

# Setup virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
cat << 'EOF' > README.md
# govflowai

AI-powered workflow automation engine for government and public sector document triage, classification, and routing.

## 🌐 Live Infrastructure & Deployment

- **Frontend Application:** [https://civic-ai-gray.vercel.app](https://civic-ai-gray.vercel.app)
- **Database Engine:** Managed PostgreSQL on Railway (Driver-level SSL Enforced)
- **Healthcheck Endpoint:** `GET /health` (Returns `200 OK`)

---

## ⚡ Technical Architecture

- **Cryptographic Audit Trail:** Hash-chain audit log where each document state is chained to prevent post-hoc tampering.
- **Strict Data Isolation:** Enforced TLS connections (`sslmode=require`) at driver layer for compliance.
- **Low-Latency Ingestion:** Optimized for high-throughput PII redaction and document triage.

---

## 🛠️ Local Setup

Clone the repository:
  git clone [https://github.com/sitara2007/CivicOs.git](https://github.com/sitara2007/CivicOs.git)
  cd CivicOs

Setup virtual environment:
  python3 -m venv .venv
  source .venv/bin/activate
  pip install -r requirements.txt

---

## 👥 Real Users & Pilots
- Currently onboarding initial pilot users in legal tech & public document processing.
