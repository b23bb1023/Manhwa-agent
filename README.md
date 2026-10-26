# Manhwa Agent

A local reading-list prototype that combines a Playwright scraper, an n8n workflow, and a Flet desktop dashboard to track chapter availability and reading progress.

**Status: integration work required.** The committed checkout is not a working end-to-end installation: Compose expects files in directories that are not present, and the exported workflow has execution defects. The scraper also needs access controls before network exposure. See [the improvement plan](improvement_repo.md) for ordered tasks and acceptance checks.

## Components

| Component | Source | Current behavior |
| --- | --- | --- |
| Scraper | [main.py](main.py) | FastAPI `GET /scrape?url=...` launches headless Chromium, looks for chapter labels, and returns a chapter number and thumbnail URL. |
| Automation | [n8n.json](n8n.json) | Defines a six-hour schedule and `/refresh` webhook, reads the shared JSON list, and intends to scrape and update each entry. The export needs repair before use. |
| Dashboard | [widget.py](widget.py) | Reads `data/reading_list.json`, sorts updates before caught-up entries, opens series URLs, and updates reading progress. |
| Containers | [docker-compose.yml](docker-compose.yml), [Dockerfile](Dockerfile) | Define n8n and the scraper. The Flet dashboard runs on the host, outside Compose. |

The intended flow is reading list → n8n → scraper → availability update → dashboard. Both the dashboard and n8n currently write the same JSON file; there is no concurrency protocol.

Browser rendering and fixed selectors do not guarantee access to a website or successful extraction. This project has no demonstrated general challenge-solving capability. Use only sources you are permitted to access and respect their access and rate limits.

## Repository layout

The committed files are at the repository root:

```text
Dockerfile
README.md
docker-compose.yml
main.py
n8n.json
reading_list.json
requirements.txt
widget.py
```

Three runtime paths currently disagree with that layout:

- Compose builds from `./scraper`, but `Dockerfile`, `main.py`, and `requirements.txt` are at the root.
- Compose mounts `./data` at `/data_shared`; the seed [reading_list.json](reading_list.json) is at the root.
- The dashboard reads `data/reading_list.json` relative to the process working directory.

Resolve these paths as one implementation change before following a backend startup flow. Creating directories alone does not repair the workflow or data-integrity defects.

## Inspect the prototype

Clone the repository and inspect the workflow and sample data without starting network services:

```sh
git clone https://github.com/b23bb1023/Manhwa-agent.git
cd Manhwa-agent
python3 -m json.tool n8n.json
python3 -m json.tool reading_list.json
```

These commands check JSON syntax only. They do not validate n8n node compatibility or prove that the workflow runs.

For development, the intended prerequisites are Docker with Compose, Python, and a desktop environment for Flet. A tested Python/Flet/n8n compatibility matrix has not been committed. [requirements.txt](requirements.txt) pins Playwright to `1.48.0`, matching the Docker image tag, but leaves FastAPI, Uvicorn, and BeautifulSoup unpinned. Flet is not included in that manifest. Pin and test the full environment before publishing installation instructions as reproducible.

## Configuration reference

| Setting | Location | Value or purpose |
| --- | --- | --- |
| Dashboard data path | `widget.py`, `DATA_FILE` | `data/reading_list.json`, relative to the launch directory |
| Dashboard update trigger | `widget.py`, `WEBHOOK_URL` | `http://localhost:5678/webhook/refresh` |
| Workflow scraper URL | `n8n.json`, Scraper API | `http://scraper:8000/scrape`, on the Compose network |
| Workflow data path | `n8n.json` | `/data_shared/reading_list.json` |
| Scraper image | `Dockerfile` | `mcr.microsoft.com/playwright/python:v1.48.0-jammy` |
| n8n image | `docker-compose.yml` | Floating `n8nio/n8n:latest`; no tested release is pinned |

The current Compose configuration publishes host ports `5678` and `8000` without a loopback binding and sets `N8N_SECURE_COOKIE=false`. The scraper accepts caller-supplied destinations without authentication or destination restrictions. Do not treat this configuration as ready for remote access. The [first improvement task](improvement_repo.md#1-restrict-scraper-access-and-destinations) describes the required boundary.

## Reading-list format

The root JSON file contains placeholders, not a verified live feed. The current shape of one item is:

```json
{
  "id": "example-series",
  "title": "Example Series",
  "url": "https://example.com/series/example",
  "thumbnail": "",
  "last_read": 5,
  "latest_available": 6,
  "hype_message": "New Chapter 6 is out!"
}
```

Use stable unique IDs, a permitted series URL, and nonnegative chapter values. `last_read` is user progress; `latest_available` is scraper-owned availability. These are intended invariants, not a schema currently enforced by the code. The example domain above illustrates the format and is not a supported scraper source.

The parser extracts integer chapters below `2000`. A label such as `Chapter 12.5` is currently reduced to `12`; fractional chapters and higher chapter numbers are not reliably represented.

## Dashboard behavior

After repairing setup, pinning dependencies, and initializing the data file, the dashboard entry point is `python3 widget.py` from the project root. There is no packaged `MangaWidget.app` in this repository.

- Startup sends one refresh request to n8n in a background thread, with a one-second request timeout. A timeout does not establish whether n8n accepted or completed the workflow.
- The **Reload** button rereads the local file; it does not trigger another scrape.
- Clicking **Read Ch. N** opens the series URL and immediately marks that latest chapter as read. It does not wait for confirmation that the chapter was read.
- Brave is attempted first; the default browser is used if that fails. Private browsing is not guaranteed by the fallback.
- Thumbnail requests currently run during rendering without a timeout or size limit, so a slow image host can freeze the dashboard.

## Known limitations and troubleshooting

| Symptom | Current cause or next check |
| --- | --- |
| Compose cannot find the build context | `./scraper` is missing; reconcile the checkout paths before building. |
| Dashboard shows **No Data** | Missing file, malformed JSON, or a non-list value all appear as an empty list. Validate the file and preserve a backup before editing. |
| Workflow never updates entries | Repair the loop outputs, versioned node parameters, helper calls, and writer configuration described in the improvement plan. |
| Latest availability becomes zero | Navigation/parse failures can currently produce chapter zero. Preserve the previous cache until failure handling is implemented. |
| Progress reverts after a refresh | Whole-file writes from n8n and the widget can overwrite one another. Avoid concurrent writers until transactional updates exist. |
| Dashboard hangs on reload | Thumbnail downloads block rendering; an image failure is not evidence that the list file is broken. |

Rebuilding the same pinned Playwright image is not a general fix for a changed selector or an access challenge. Record the actual error, use an offline fixture to reproduce it, and keep the last known availability intact.

## Contributing and release readiness

Start with [improvement_repo.md](improvement_repo.md). Proposed behavior changes should include offline fixtures, preserve reading progress, and state the exact dependency versions tested. A release should pass the clean-checkout, workflow, persistence, and request-boundary checks listed there.

The repository currently contains no test suite or CI workflow. Documentation updates do not establish that the implementation defects are fixed.

## Reuse terms

The project previously stated an intent for personal, non-commercial use. No separate `LICENSE` file is committed. The owner needs to choose and commit explicit reuse terms; this README does not grant a new license.
