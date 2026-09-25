# Ticket Triage — Backend Handoff

The backend is done and tested. What's left is provisioning + deployment on
Azure, and wiring the frontend to the API. This doc has everything needed to
do both.

**Where the code is:** `backend/` folder in this same zip/folder. 17 tests,
all passing. Runs locally with zero Azure account needed (in-memory storage),
and automatically switches to real Cosmos DB once the environment variables
below are set.

---

## Part 1 — Local check (2 minutes, confirms nothing is broken)

Requires **Python 3.11 or 3.12** specifically — the Azure Functions Python
worker does not support 3.13 yet, and `func start` will hang silently if you
create the venv with 3.13. Check with `python --version` first.

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate              # macOS/Linux: source .venv/bin/activate
pip install -r requirements-dev.txt
pytest -q                            # should show: 17 passed
```

Optional, run the real Azure Functions host locally:
```bash
npm install -g azure-functions-core-tools@4
copy local.settings.json.sample local.settings.json
func start
```
Then check `http://localhost:7071/api/health` returns
`{"status":"ok","storage":"in-memory",...}`.

---

## Part 2 — Azure setup (under YOUR subscription)

Install once: [Azure CLI](https://aka.ms/installazurecliwindows), then:
```bash
az login
az account show --output table       # confirm it shows YOUR subscription
```

Run these to create everything the backend needs. Pick any Azure region
close to you (`southeastasia`, `eastus`, etc.) and keep it consistent.

```bash
RG=rg-tickettriage
LOC=southeastasia

az group create -n $RG -l $LOC

# Cosmos DB, free tier — ONE per subscription, must opt in at creation.
# If this account already has a free-tier Cosmos account elsewhere, drop
# --enable-free-tier true (you'll just pay nothing extra at this scale anyway).
az cosmosdb create -n cosmos-tickettriage -g $RG \
  --enable-free-tier true --default-consistency-level Session

az cosmosdb sql database create -a cosmos-tickettriage -g $RG \
  -n tickettriage --throughput 400

az cosmosdb sql container create -a cosmos-tickettriage -g $RG \
  -d tickettriage -n tickets --partition-key-path /id
```

Get the Cosmos keys you'll need in Part 3:
```bash
az cosmosdb keys list -n cosmos-tickettriage -g $RG --query primaryMasterKey -o tsv
az cosmosdb show -n cosmos-tickettriage -g $RG --query documentEndpoint -o tsv
```

---

## Part 3 — Deploy (Static Web App, Free plan)

This is the easiest path because Azure wires up the GitHub Actions deploy
pipeline automatically:

1. Push this repo (including the `backend/` and, once ready, a `frontend/`
   folder) to your team's GitHub repo, on `main`.
2. In the Azure Portal: **Create a resource → Static Web App**
   - Plan: **Free**
   - Deployment: **GitHub** → sign in, pick your repo/branch
   - Build presets: **Custom**
   - App location: `frontend`
   - Api location: `backend`
   - Output location: *(leave blank)*
3. Click Create. It commits a `.github/workflows/azure-static-web-apps-*.yml`
   file to the repo and deploys automatically on every push to `main`.

**Set the app settings** (Static Web App → Settings → Environment variables,
or via CLI) so the deployed backend actually uses Cosmos DB:

```bash
az staticwebapp appsettings set -n <your-swa-name> -g $RG --setting-names \
  COSMOS_ENDPOINT="<endpoint from Part 2>" \
  COSMOS_KEY="<key from Part 2>" \
  ADMIN_API_KEY="<any long random string — this protects the admin PATCH endpoint>"
```

**Verify:**
```bash
curl https://<your-app>.azurestaticapps.net/api/health
```
`storage` must say `"cosmos"`. If it says `"in-memory"`, the Cosmos env vars
didn't take — double check they're set exactly as above and re-check spelling.
Screenshot this response — it's evidence for the rubric.

---

## Part 4 — API contract for the frontend person

Base URL once deployed: `https://<your-app>.azurestaticapps.net/api`
(locally: `http://localhost:7071/api`)

| Method | Route | Body | Notes |
|---|---|---|---|
| `GET` | `/health` | – | `{status, storage, adminKeyConfigured}` |
| `GET` | `/categories` | – | `{categories: [...], priorities: [...], statuses: [...]}` — use this to populate form dropdowns |
| `POST` | `/tickets` | `{name, email, title, description, priority?, category?}` | `priority` defaults to `Medium`. Omit `category` to let the backend auto-suggest it. Returns the created ticket (201) or `{error, details}` (422) |
| `GET` | `/tickets` | – | Query params: `?category=&status=&search=&limit=`. Returns `{tickets: [...], count}` |
| `GET` | `/tickets/{id}` | – | Single ticket, or 404 |
| `PATCH` | `/tickets/{id}` | `{status?, category?}` | Admin only — send header `x-admin-key: <ADMIN_API_KEY value>`. Returns updated ticket |

**Ticket object shape:**
```json
{
  "id": "uuid",
  "name": "string", "email": "string",
  "title": "string", "description": "string",
  "priority": "Low | Medium | High",
  "category": "IT Support | Facilities | Course Registration | Student Finance | Library Services | General Enquiry",
  "classificationMethod": "manual | keyword-rules",
  "classificationConfidence": 0.0,
  "status": "New | Categorised | In Progress | Resolved",
  "statusHistory": [{"status": "...", "at": "iso-timestamp"}],
  "createdAt": "iso-timestamp", "updatedAt": "iso-timestamp"
}
```

CORS is wide open locally (`local.settings.json` has `"CORS": "*"`). On the
deployed Static Web App, frontend and API share the same origin automatically
(both served from `*.azurestaticapps.net`), so no CORS config is needed there
— just call `/api/...` as a relative path from the frontend JS.

---

## Troubleshooting

- **`func start` hangs with no error** → you're on Python 3.13. Rebuild the
  venv with 3.11/3.12.
- **`/api/health` says `"in-memory"` after deploying** → Cosmos env vars are
  missing/misspelled on the Static Web App's settings, or the Cosmos account
  itself failed to provision. Check `az cosmosdb show -n cosmos-tickettriage -g rg-tickettriage`.
- **Free-tier Cosmos creation fails** → the subscription already has a
  free-tier Cosmos account (one allowed per subscription, ever). Just drop
  `--enable-free-tier true`; 400 RU/s is still effectively free at this scale.
- **PATCH returns 401** → missing or wrong `x-admin-key` header. If
  `ADMIN_API_KEY` isn't set at all, PATCH is open to anyone (fine for a demo,
  not for anything real).
