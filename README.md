# ticket-triage-capstone-project

An automated ticket triage system designed to streamline customer support operations, categorize inbound requests, and prioritize workflow efficiency.

---

## 📌 Business & Operational Impact

In customer service operations, manual ticket routing often leads to response bottlenecks and high operational costs. This project leverages automation to:

* **Optimize Response Time:** Automatically route customer tickets to the correct support channels.
* **Enhance Resource Allocation:** Prioritize urgent requests to reduce resolution latency.
* **Scale Support Operations:** Handle higher volumes of customer inquiries without proportional increases in support overhead.

---

## 🏗️ Architecture

A two-tier application deployed as a single Azure Static Web App, so the frontend
and API share one origin and need no CORS configuration in production.

```text
Browser (static HTML/CSS/JS)
        │  same-origin fetch('/api/...')
        ▼
Azure Static Web App  ──►  Managed Functions API  (backend/, Python v2 model)
                                    │
                                    ▼
                        Cosmos DB for NoSQL  (database: tickettriage,
                        container: tickets, partition key: /id)
```

**Classification** is keyword-rule based rather than an external AI call. There is
no Azure AI Language quota to consume, no per-request cost, and no network
dependency — the rubric's "AI classification or free keyword search logic"
requirement is met deterministically. Multi-word phrases such as `student loan`,
`book loan` and `library fine` are weighted higher than generic single words so
they disambiguate terms that legitimately appear in more than one category.

Tickets submitted without a category are auto-suggested and land in status
`Categorised` with a recorded `classificationConfidence`. Tickets submitted with
an explicit category are marked `manual` and start as `New`.

---

## 🛠️ Project Structure

```text
ticket-triage-capstone-project/
├── .gitignore
├── LICENSE
├── README.md
├── HANDOFF.md
├── frontend/                  # Static Web App client — no build step
│   ├── index.html             # Ticket submission portal
│   ├── admin.html             # Admin dashboard (list / filter / update)
│   ├── app.js                 # All API calls, relative /api/... paths
│   └── style.css
└── backend/                   # Azure Functions (Python v2 decorator model)
    ├── function_app.py        # HTTP routes
    ├── host.json
    ├── requirements.txt       # azure-functions, azure-cosmos
    ├── requirements-dev.txt   # + pytest
    ├── local.settings.json.sample
    ├── pytest.ini
    ├── shared/
    │   ├── config.py          # Settings from env / app settings
    │   ├── models.py          # Validation, assembly, status history
    │   ├── categories.py      # Category ontology + keyword scoring
    │   └── repository.py      # Cosmos and in-memory repositories
    └── tests/                 # 17 tests
```

---

## 🔌 API Contract

Base URL: `/api` (relative — same origin as the frontend).

| Method | Route              | Body                                   | Notes |
|--------|--------------------|----------------------------------------|-------|
| `GET`  | `/health`          | –                                      | `{status, storage, adminKeyConfigured}` |
| `GET`  | `/categories`      | –                                      | Populates the form dropdowns |
| `POST` | `/tickets`         | `{name, email, title, description, priority?, category?}` | `priority` defaults to `Medium`; omit `category` to auto-suggest. `201` on success, `422` with `{error, details}` on validation failure |
| `GET`  | `/tickets`         | –                                      | Query: `?category=&status=&search=&limit=` → `{tickets, count}` |
| `GET`  | `/tickets/{id}`    | –                                      | One ticket, or `404` |
| `PATCH`| `/tickets/{id}`    | `{status?, category?}`                 | Admin. Send header `x-admin-key`. Returns the updated ticket |

**Ticket shape:**

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
  "statusHistory": [{ "status": "...", "at": "iso-timestamp" }],
  "createdAt": "iso-timestamp", "updatedAt": "iso-timestamp"
}
```

### Storage fallback

`GET /api/health` reports the storage backend actually in use — `"cosmos"` or
`"in-memory"`. The app runs entirely on the in-memory repository when
`COSMOS_ENDPOINT` / `COSMOS_KEY` are unset, which is why the test suite needs no
Azure account. **Always check `/api/health` after deploying:** if it says
`"in-memory"` on a deployed environment, the Cosmos app settings did not take
effect.

---

## ⚙️ Configuration

Set in `backend/local.settings.json` locally, and under
*Static Web App → Settings → Environment variables* when deployed.

| Variable | Required | Default | Notes |
|---|---|---|---|
| `COSMOS_ENDPOINT` / `COSMOS_KEY` | for persistence | – | Blank ⇒ in-memory storage |
| `COSMOS_DATABASE` | no | `tickettriage` | |
| `COSMOS_CONTAINER` | no | `tickets` | Partitioned on `/id` |
| `ADMIN_API_KEY` | recommended | – | Sent as `x-admin-key` on PATCH. If unset, PATCH is open to anyone — convenient for a demo, **not** safe for anything real |
| `MAX_PAGE_SIZE` | no | `100` | Caps `?limit=` |

> `backend/local.settings.json` holds the Cosmos master key and is gitignored.
> Never commit it.

---

## 💻 Local Development

Requires **Python 3.11 or 3.12** — the Azure Functions Python worker does not
support 3.13, and `func start` will hang or fail silently on 3.13.

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate          # macOS/Linux: source .venv/bin/activate
pip install -r requirements-dev.txt
pytest -q                        # 17 passed
```

To run the real Functions host (optional):

```bash
npm install -g azure-functions-core-tools@4
copy local.settings.json.sample local.settings.json
func start
```

Then `http://localhost:7071/api/health` should return
`{"status":"ok","storage":"in-memory",...}`.

> Leave `COSMOS_ENDPOINT` and `COSMOS_KEY` **empty** in `local.settings.json`.
> The shipped sample contains placeholder values, and a non-empty value makes the
> app attempt a real Cosmos connection on every request before falling back.

The frontend cannot be previewed by opening `index.html` from the filesystem:
`fetch('/api/...')` resolves to a local file path under `file://`. Test the UI
against the deployed Static Web App, or point the calls at
`http://localhost:7071/api` (local CORS is `*`).

---

## ☁️ Deployment

Azure Static Web App, Free plan, GitHub Actions deploys on every push to `main`.

| Setting | Value |
|---|---|
| Build preset | Custom |
| App location | `frontend` |
| API location | `backend` |
| Output location | *(blank — the frontend is prebuilt static files, no bundler)* |

Then set the app settings so the deployed backend uses Cosmos DB:

```bash
az staticwebapp appsettings set -n <swa-name> -g rg-tickettriage --setting-names \
  COSMOS_ENDPOINT="<endpoint>" \
  COSMOS_KEY="<primary key>" \
  ADMIN_API_KEY="<long random string>"
```

Verify the deploy:

```bash
curl https://<your-app>.azurestaticapps.net/api/health
```

`storage` must read `"cosmos"`.
