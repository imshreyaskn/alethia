# Alethia

Alethia is a self-healing CI/CD GitHub App. It seamlessly hooks into your GitHub webhooks to catch failing CI logs instantly, securely analyzes the trace using AI, generates a fix, and pushes a self-healing PR. If pre-flight checks fail, the system loops and self-corrects until the patch is green.

## Features
- **Zero Config**: Install our GitHub App in one click. No complex YAML required.
- **Auto Healing**: Tests fail? We analyze the logs and open a PR with the fix.
- **Enterprise Secure**: Row-level security ensures your data is strictly siloed.

## Tech Stack
- Frontend: React + Vite + Supabase Auth
- Backend / Database: Supabase

## Getting Started

### Prerequisites
- Node.js
- Supabase account & project

### Development

1. Clone the repository
2. Set up the frontend environment variables:
   Create `frontend/.env` with your Supabase credentials:
   ```env
   VITE_SUPABASE_URL=your_supabase_url
   VITE_SUPABASE_ANON_KEY=your_supabase_anon_key
   ```
3. Run the development server:
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

## Contact
- Email: imshreyaskn@gmail.com
- GitHub: [imshreyaskn](https://github.com/imshreyaskn)
- LinkedIn: [imshreyaskn](https://linkedin.com/in/imshreyaskn)
