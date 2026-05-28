<p align="center">
  <img src="frontend/src/assets/mesh.png" width="120" alt="Alethia Logo" />
  <h1 align="center">Alethia</h1>
</p>

<p align="center">
  <strong>The self-healing CI/CD GitHub App powered by AI.</strong><br>
  <a href="https://alethia-gamma.vercel.app/">Live Application</a>
</p>

---

## 🚀 What is Alethia?

Alethia is a self-healing CI/CD GitHub App that seamlessly hooks into your development workflow. When your CI pipeline fails, Alethia doesn't just notify you — it securely analyzes the trace using AI, generates a fix, validates the patch, and opens a Pull Request automatically. 

With Human-in-the-Loop (HITL) approval gates and robust multi-tenant security, Alethia ensures you stay in control while automating away the tedious work of fixing failing tests.

## 🔗 Live Application

Access the platform here: **[https://alethia-gamma.vercel.app/](https://alethia-gamma.vercel.app/)**

---

## 📖 User Documentation

Using Alethia is designed to be frictionless. No complex YAML configurations or dedicated servers are required. 

### 1. Installation and Setup

1. **Log In:** Navigate to the [live application](https://alethia-gamma.vercel.app/) and click "Login with GitHub".
2. **Authorize the App:** Authorize Alethia to read your repositories and workflows.
3. **Install the GitHub App:** You will be prompted to install the Alethia GitHub App on your account or organization. You can choose to grant access to **All Repositories** or **Only Select Repositories**.
   * *Note: You can manage repository access at any time from your GitHub Settings -> Applications -> Installed GitHub Apps.*

### 2. How the Self-Healing Pipeline Works

Once installed, Alethia operates quietly in the background until a pipeline fails.

1. **Detection:** A CI run (like GitHub Actions) fails. GitHub immediately sends a webhook to Alethia with the error trace and logs.
2. **AI Classification:** Alethia's AI analyzes the trace to determine if the error is a fixable issue (e.g., a test mismatch, syntax error, or logical bug).
3. **Human Approval:** If the issue is fixable, it appears on your Alethia dashboard with a status of `WAITING_FOR_APPROVAL`. You review the AI's classification and can optionally provide a "hint" (e.g., "Use a mock object here").
4. **Patch Generation & Validation:** Upon approval, Alethia generates the code fix and automatically runs a sandboxed validation to ensure the tests pass with the new patch.
5. **Pull Request:** If validation succeeds, Alethia opens a Pull Request on your repository with the fix, ready for you to merge.

### 3. Managing Your Dashboard

The Alethia dashboard provides a real-time view of all pipeline runs across your connected repositories. 

* **Global View:** See all recent runs and their current statuses (e.g., `CLASSIFYING`, `WAITING_FOR_APPROVAL`, `FIXING`, `DELIVERED`).
* **Detailed Run View:** Click on any run to see the exact patch diff, the failure classification, and the raw validation output.
* **Retry Actions:** If an AI-generated patch fails validation (`VALIDATION_FAILED`), you can review the error, provide a new hint, and click **Retry Patch** to have the AI attempt a new fix.

---

## 🔒 Security & Data Isolation

Alethia is built with enterprise-grade security from the ground up.

* **Row-Level Security (RLS):** All data is strictly siloed. You will only ever see pipeline runs for repositories where you have explicitly installed the Alethia GitHub App.
* **Backend Authentication:** All actionable requests (like approving or retrying a run) require secure JWT token validation.
* **Minimal Scopes:** Alethia requests only the specific GitHub permissions needed to fetch file contents and open pull requests.

---

## 🛠️ For Developers

Interested in running Alethia locally or contributing? 

### Tech Stack
* **Frontend:** React + Vite
* **Backend:** FastAPI (Python) + Supabase
* **AI Engine:** LangGraph + Groq
* **Database:** PostgreSQL (via Supabase)

### Local Setup
1. Clone the repository.
2. Configure your environment variables for both the `frontend` and `backend` directories.
3. Start the backend: `cd backend && fastapi dev app/main.py`
4. Start the frontend: `cd frontend && npm install && npm run dev`

---

<p align="center">
  <i>Built to keep your pipelines green.</i>
</p>
