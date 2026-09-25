# Ticket Triage — Backend

Azure Functions (Python v2 model) API for the AI-200 capstone. Ticket storage
is Cosmos DB for NoSQL (free tier) when configured, and falls back to an
in-memory store automatically otherwise, so it runs and tests with no Azure
account.

## Endpoints

| Method | Route              | Purpose                                      |
|--------|--------------------|-----------------------------------------------|
| POST   | `/api/tickets`     | Submit a ticket (auto-suggests a category)   |
| GET    | `/api/tickets`     | List/filter tickets (`category`, `status`, `search`, `limit`) |
| GET    | `/api/tickets/{id}`| Fetch one ticket                             |
| PATCH  | `/api/tickets/{id}`| Update `status` and/or `category` (admin)    |
| GET    | `/api/categories`  | Category/priority/status reference lists     |
| GET    | `/api/health`      | Reports actual storage backend in use        |

## Local setup

```bash
python -m venv .venv
.venv\Scripts\activate            # macOS/Linux: source .venv/bin/activate
pip install -r requirements-dev.txt
pytest -q                          # run the test suite (no Azure needed)

cp local.settings.json.sample local.settings.json
func start                         # runs the real Azure Functions host on :7071
```

> Requires Python 3.11 or 3.12. The Azure Functions Python worker does not
> yet support 3.13 — `func start` will hang/fail silently if your venv is on
> 3.13. Check with `python --version` before creating the venv.

## Environment variables

Set locally in `local.settings.json`, and on the deployed Static Web App via
*Settings → Environment variables* (or `az staticwebapp appsettings set`).

| Variable | Required | Default | Notes |
|---|---|---|---|
| `COSMOS_ENDPOINT` / `COSMOS_KEY` | for persistence | – | Leave blank to use in-memory storage |
| `COSMOS_DATABASE` | no | `tickettriage` | |
| `COSMOS_CONTAINER` | no | `tickets` | Partitioned on `/id` |
| `ADMIN_API_KEY` | recommended | – | Sent as `x-admin-key` header on PATCH; if unset, PATCH is open (classroom-safe default, not production-safe) |
| `MAX_PAGE_SIZE` | no | `100` | Caps `?limit=` on list |

Always check `/api/health` after deploying — `storage` tells you whether
Cosmos actually connected or silently fell back to in-memory.

## Category suggestion

Keyword-based scoring in `shared/categories.py` — no external AI call, no
cost, no quota. Multi-word phrases (`student loan`, `book loan`, `library
fine`) are weighted to correctly disambiguate terms that appear in more than
one category.

## Data model

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
