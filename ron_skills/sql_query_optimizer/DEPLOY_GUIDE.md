# SQL Query Optimizer - Railway Deployment Guide

Step-by-step instructions for getting the paid API live on Railway.

---

## Prerequisites

Before starting, you need:
- A GitHub account (you have this)
- A Railway account (you just created this)
- Your Anthropic API key (the new one for Ron, not your personal one)

---

## Step 1: Push Your Code to GitHub (~5 min)

You need a GitHub repo first. Open Terminal on your Mac:

```bash
cd /Users/debbieshapiro/projects/side_hustle

# Initialize the repo
git init
git add .
git commit -m "Initial commit: SQL Query Optimizer skill + API"

# Create the repo on GitHub (requires gh CLI, or do it on github.com)
# Option A: Using GitHub CLI
gh repo create side_hustle --private --source=. --push

# Option B: If you don't have gh CLI
#   1. Go to https://github.com/new
#   2. Name it "side_hustle"
#   3. Set to Private
#   4. Do NOT add a README (you already have files)
#   5. Click "Create repository"
#   6. Then run:
git remote add origin https://github.com/YOUR_USERNAME/side_hustle.git
git branch -M main
git push -u origin main
```

**Double-check:** Make sure your `.env` file did NOT get pushed. Run `git status` -- it should NOT show `.env` as tracked. The `.gitignore` we created should prevent this.

---

## Step 2: Create a Railway Project (~3 min)

1. Go to **https://railway.app/dashboard**
2. Click the **"New Project"** button (purple button, top-right of dashboard)
3. In the menu that appears, click **"Deploy from GitHub Repo"**
4. You will see a list of your GitHub repos. Find and click **"side_hustle"**
   - If you don't see it, click **"Configure GitHub App"** to grant Railway access to the repo
5. **IMPORTANT:** When it shows "Deploy Now" and "Add Variables" -- click **"Add Variables"** first (do NOT click Deploy Now yet)

---

## Step 3: Add Your Environment Variables (~2 min)

After clicking "Add Variables" you will see a screen with a table for key-value pairs.

Click **"New Variable"** and add each of these one at a time:

| Variable Name       | Value                          |
|---------------------|--------------------------------|
| `ANTHROPIC_API_KEY` | `sk-ant-...` (paste your Ron API key) |
| `OPTIMIZER_MODEL`   | `claude-sonnet-4-5-20250514`   |
| `LOG_LEVEL`         | `INFO`                         |

To add each one:
1. Click in the **"Variable Name"** field on the left, type the name exactly as shown
2. Click in the **"Variable Value"** field on the right, paste or type the value
3. Click **"Add"** (or press Enter)
4. Repeat for the next variable

---

## Step 4: Set the Root Directory (~1 min)

This is critical because your API code is in a subfolder, not the repo root.

1. On the Project Canvas (the main screen with your service box), click on your **service** (it shows as a rectangular card/box)
2. In the panel that opens on the right, click the **"Settings"** tab (at the top of the panel -- you'll see tabs like Deployments, Variables, Settings, etc.)
3. Scroll down to the **"Build"** section
4. Find **"Root Directory"** -- it will show `/` by default
5. Click the field and change it to:
   ```
   ron_skills/sql_query_optimizer/api
   ```
6. Railway auto-saves this -- no save button needed

---

## Step 5: Generate a Public URL (~1 min)

Your API needs a public URL so the ClawHub skill can reach it.

1. Still in your service panel, click the **"Settings"** tab
2. Scroll down to the **"Networking"** section
3. Find **"Public Networking"** and click **"Generate Domain"**
4. Railway will create a URL like: `sql-query-optimizer-api-production-XXXX.up.railway.app`
5. **Copy this URL** -- you will need it in Step 7

---

## Step 6: Deploy (~2 min)

1. Go back to the Project Canvas (click the back arrow or your project name at the top)
2. Click the **"Deploy"** button at the top of the canvas
   - If you don't see a Deploy button, Railway may have already started deploying after you set the root directory
3. Watch the **build logs** -- click on your service, then the **"Deployments"** tab to see progress
4. You should see:
   - "Building..." (Docker build running)
   - "Deploying..." (starting uvicorn)
   - A green checkmark when it is live

**If the build fails:** The most common issue is the root directory being wrong. Double-check Step 4.

---

## Step 7: Test That It Works (~1 min)

Open a new Terminal tab on your Mac and run:

```bash
# Replace YOUR_RAILWAY_URL with the URL from Step 5
curl https://YOUR_RAILWAY_URL/health
```

You should see:
```json
{"status": "healthy", "version": "1.0.0", "timestamp": "2026-03-21T..."}
```

If you see that, your API is live and ready to accept paid optimization requests.

---

## Step 8: Generate Your First API Key (~1 min)

You need at least one API key to test the optimizer. On your Mac, in the `api/` folder:

```bash
cd /Users/debbieshapiro/projects/side_hustle/ron_skills/sql_query_optimizer/api
python -c "
from dotenv import load_dotenv
load_dotenv()
from credits import CreditManager
mgr = CreditManager()
key = mgr.generate_key(plan='starter', credits=50, email='debbie.wonderkitty@gmail.com')
print(f'Your test API key: {key}')
print('Save this somewhere safe -- it cannot be retrieved later.')
"
```

---

## Step 9: Test a Real Optimization (~1 min)

```bash
curl -X POST https://YOUR_RAILWAY_URL/v1/optimize \
  -H "Authorization: Bearer YOUR_API_KEY_FROM_STEP_8" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "SELECT * FROM Orders o JOIN Customers c ON o.CustomerID = c.CustomerID WHERE YEAR(o.OrderDate) = 2025",
    "dialect": "tsql"
  }'
```

You should get back an optimized query with changes, index recommendations, and execution analysis.

---

## What Comes Next

- **Update the SKILL.md:** Replace `api.sqloptimizer.ronagent.com` with your Railway URL
- **Submit to ClawHub:** Fork github.com/openclaw/clawhub, add the skill folder, open a PR
- **Set up Stripe:** For accepting real payments (we will do this together in a future session)

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Build fails | Check root directory is exactly `ron_skills/sql_query_optimizer/api` |
| "ANTHROPIC_API_KEY not set" in logs | Go to Variables tab, verify the key is there and spelled correctly |
| 502 errors | Check Deployments tab for crash logs. Usually a missing dependency. |
| "No credits remaining" | Generate a new API key with credits (Step 8) |
| Can't see the repo in Railway | Click "Configure GitHub App" and grant access to the repo |
