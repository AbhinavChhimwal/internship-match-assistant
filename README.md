# Internship Match Assistant 🌱

See [INCREMENT.md](INCREMENT.md) for the requested feature additions, their
implementation, and the current deployment status from the start of the project.

A small invite-only Streamlit application for 5–10 classmates. It stores profiles in SQLite, searches a curated English internship collection using MiniLM sentence embeddings, enforces hard constraints, explains skill overlap, and offers optional Gemini tool calling over the same search functions.

## Run locally (Windows / PowerShell)

For Streamlit Community Cloud with durable storage and on-demand Supabase resume,
see [the Supabase deployment guide](docs/STREAMLIT_SUPABASE.md). The shared demo
access code is **DUMMY**. Keep real resumes out of this public demo account.

The currently configured cloud database is Neon. Follow
[the Neon deployment guide](docs/STREAMLIT_NEON.md) for that configuration.

Python 3.12 is recommended. From this project directory:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python import_jobs.py
python embeddings.py
python manage.py create-users --names Abhinav Geetesh Rohan Amit Rishi
python -m streamlit run app.py
```

The checked-in `data/jobs.csv` is ready to import. The embedding command downloads `sentence-transformers/all-MiniLM-L6-v2` on first use and generates `job_embeddings.npy`, `job_ids.json`, and a fingerprint manifest in `runtime/`. Internet is needed for installation and the first model download; subsequent searches use the cached model. Keyword search works without the model or a Gemini key. Access codes print **once**: distribute privately. Only SHA-256 hashes of high-entropy random codes enter the database; no public registration or user chooser exists. Losing a code means assigning a new demo account.

For an already prepared workspace, run `start.ps1`. The script uses the local virtual environment. Do not commit runtime data, access codes or API secrets.

This workspace has already been prepared with five demo accounts; open `runtime/demo_access_codes.txt` for the assigned codes. See `VALIDATION.md` for measured evaluation results and verification limits.

Optional chat: set `GEMINI_API_KEY` as an environment variable or in `.streamlit/secrets.toml`:

```toml
GEMINI_API_KEY = "your-key"
```

`GEMINI_MODEL` optionally selects another Gemini model available to your account; default `gemini-3.1-flash-lite`. No credential is bundled. A missing key, provider failure, invalid tool argument or exhausted chat budget leaves the ordinary form and search available. Every API request (including confirmation continuations) counts toward a 20-request browser-session budget. This is a small invited demo, so use host/provider quotas too; reconnecting starts a new Streamlit session.

## Try the demo

1. Sign in with an assigned code.
2. Open **Profile**. Add `python, sql`, interests and your actual graduation year. Save.
3. Open **Matches**, choose semantic-plus-skills or keyword ranking and search.
4. Save or hide a result; restart/sign in again to verify persistence.
5. In chat, try “Only remote roles in India.” Review the proposed values and confirm or cancel. An empty result is expected when eligibility cannot be verified; constraints never relax automatically.

The source collection has 152 employer/ATS records: the original 52 plus 100 additional web-sourced internships researched on October 24, 2026. Fields not established by the listing remain unknown. Some passed deadlines are deliberately retained as inactive examples. Unknown graduation-year eligibility excludes many postings, giving a smaller eligible collection. This behavior implements the brief's strict missing-information policy. **The application checks the stated graduation year and selected work/location constraints; it does not certify degree, exact graduation month, visa, enrollment, citizenship, or all hiring requirements.** Those details are summarized when available and must be checked at the original listing. See `data/README.md` for curation limitations.

## How retrieval works

```text
Manually curated CSV → pandas + Pydantic validation → SQLite jobs
                                           ↓
                       MiniLM embeddings + explicit row IDs + fingerprint

Authenticated profile → hard filters → cosine similarity → ranking → ≤5 cards
                          ↑                                  ↓
                inactive / hidden / remote             save or hide in SQLite
                year / verified location

Gemini → validate two allowed tools → same search/preferences functions
                         ↓
                  confirm before mutation
```

- Four tables only: `users`, `profiles`, `jobs`, `feedback`. Lists use JSON text; SQL uses bound parameters. One feedback action per user/job, updated with an upsert.
- Filters run before ranking for all three methods. By default, unknown hard requirements exclude jobs and appear in omission counts. Students may explicitly include unknown graduation eligibility using the labeled Profile option. Remote-only additionally requires a verified compatible geographic preference; an unknown scope is never worldwide. City/country matching uses explicit normalized entries, not substring guesses.
- `semantic`: cosine similarity; `keyword`: normalized required-skill keyword coverage; `combined`: **0.8 × cosine similarity + 0.2 × required skill coverage**. Unknown skills use similarity alone. The fixed weights were not tuned using held-out labels.
- `js` → `javascript`, `postgres` → `postgresql`; related skills are not automatically equated. Alternative requirements are not silently interpreted as requiring every alternative.
- Ranking scores order results only. They never represent hiring probability or percentage qualified. Job-card explanations are generated from structured data, not the LLM.
- Reimport deactivates absent records and retains stable URL-based IDs and feedback. Regenerate the complete embedding index after every import. The manifest rejects stale job text/ID/model combinations; vectors map through `job_ids.json`, never database row order.
- `search.py` can be called from ordinary Python independently of Streamlit. Chat has exactly two tools, `search_jobs(query)` and `update_preferences(remote_only, preferred_locations, add_skills, remove_skills)`, bound to the signed-in user. No tool accepts a user ID. A maximum of three tool calls is allowed per message, including confirmation continuations. SDK automatic execution is disabled.
- `None` leaves a preference unchanged; `[]` clears locations. Chat can propose explicit skill additions/removals with confirmation; graduation year uses the Profile form or resume extraction. Temporary chat history stays in session state; durable memory is the database-backed profile. “Show my saved jobs” is unsupported by chat; the Saved page handles that directly.

## Validation and evaluation

```powershell
python -m pytest -q --basetemp runtime/pytest-local
python evaluate.py --split dev
python evaluate.py --split test
```

`data/evaluation_cases.json` contains ten fictional profiles, five development and five held-out cases. Relevant source URLs and rationales are fixed before running rankings. All methods share the same hard constraints. Reports in `runtime/evaluation_dev.json` and `runtime/evaluation_test.json` include P@5 (only for cases with at least five eligible jobs), independently checked constraint violations, returned URLs, warmed search latency and hardware. Use `--keyword-only` to evaluate before downloading the model. Loading is excluded; query encoding plus in-memory filtering/ranking is timed. Zero and fewer-than-five results have separate automated tests.

These are author-labeled examples on a small, incomplete collection. They measure retrieval against these labels, not general quality or hiring outcomes. The held-out skills/constraints vary while the eligible subset is small; collect blinded classmate relevance judgments for a stronger follow-up evaluation. The tests also exercise strict tool validation, confirmation/cancellation, provider failure, budget bounds, profile isolation, stable IDs, feedback persistence, stale index rejection and the authenticated UI journey.

Manual live chat acceptance checks (requires your API key):

| Message | Expected behavior |
|---|---|
| Only remote roles. | Propose remote-only; wait for confirmation. If no location is set, explain remote geography requirement. |
| Bengaluru is okay now. | Propose location update; retain unrelated preferences. |
| Find Python backend internships. | Search without mutating profile. |
| Forget my location preference. | Propose empty location list; require confirmation. |
| Show my saved jobs. | Explain unsupported chat action and point to Saved page. |

## Files

| File | Responsibility |
|---|---|
| `app.py` | Authentication, forms, cards, feedback, chat confirmation |
| `db.py` | Four-table schema and parameterized queries |
| `import_jobs.py` | Validate entire CSV, then import transactionally |
| `embeddings.py` | Single model, vector generation and index validation |
| `search.py` | Hard filters and transparent ranking |
| `agent.py` / `schemas.py` | Bounded provider loop and strict arguments |
| `evaluate.py` | Three-method evaluation and hardware/latency reporting |
| `prepare_data.py` | One-time conversion of the manual local source ledger; never scrapes |
| `manage.py` | Assign random private demo codes |

## One-instance deployment with persistent storage

The included Dockerfile runs one Streamlit process. Set `MATCHER_STATE_DIR=/state` and mount a persistent volume at `/state`; it contains SQLite, embeddings, and cached model weights. Keep one replica. A writable ephemeral host directory is not sufficient for durable profiles. Keep `GEMINI_API_KEY` in host secrets and set a provider-side quota. Do not deploy until local setup and tests pass.

```sh
docker build -t internship-match .
docker volume create internship-state
docker run --rm -v internship-state:/state internship-match python import_jobs.py
docker run --rm -v internship-state:/state internship-match python embeddings.py
docker run --rm -v internship-state:/state internship-match python manage.py create-users --names Student1 Student2 Student3 Student4 Student5
docker run -p 8501:8501 -v internship-state:/state -e GEMINI_API_KEY internship-match
```

Configure HTTPS through the host, keep the classroom link private, and back up the state volume. No deployment, public release, or invitations are performed automatically. Students can enter skills manually or upload a resume in Profile. Resume processing sends the document to Gemini; the latest file is stored privately with the account.

## Documentation references

- [Sentence Transformers semantic search](https://www.sbert.net/examples/sentence_transformer/applications/semantic-search/README.html)
- [Gemini function calling](https://ai.google.dev/gemini-api/docs/function-calling)
- [Streamlit session state](https://docs.streamlit.io/develop/api-reference/caching-and-state/st.session_state)

The project intentionally contains no scraping, model training, vector database, separate API service, public registration, or complex conversation memory.


## Chat troubleshooting

The UI now uses four sidebar pages: Matches, Profile, Saved, and Chat. Existing accounts were renamed Abhinav, Geetesh, Rohan, Amit and Rishi without changing access codes or stored preferences.

Use **quoted** values in `.streamlit/secrets.toml`. The file is re-read when you open Chat, so edits do not depend on Streamlit's secrets cache:

```toml
GEMINI_API_KEY = "your-api-key"
GEMINI_MODEL = "gemini-3.1-flash-lite"
```

The model is optional; Flash-Lite is the verified default. `python diagnose_chat.py` checks secret syntax and a real Gemini tool-call response without printing the key or sending student data. `python live_chat_check.py` runs the five acceptance messages against an isolated synthetic account and writes `runtime/live_chat_validation.json`; it makes real billable API requests. Automated pytest tests use simulated provider responses and incur no API calls.

Transient server errors receive one retry, charged to the session request budget. Invalid keys, unavailable models and quota limits receive specific messages; quota and authentication failures are not retried. A confirmation that saved preferences remains acknowledged even if the provider fails while summarizing afterward. Form search stays available independently.


## Resume profiles

In **Profile → Resume**, choose a PDF, DOCX or UTF-8 TXT file (maximum 5 MB), then click **Create profile from resume**. Gemini extracts explicit skills, grounded project/interests text and an unambiguous graduation year. PDF documents are sent as inline document input; DOCX/TXT text is passed to the same structured extraction flow. The returned fields are validated in Python before saving.

The latest successfully processed resume is stored as a BLOB on that user's existing `profiles` row, with its filename, MIME type, extracted skill baseline and upload time. Only that latest resume is offered for download to the authenticated user. Runtime databases are git-ignored; no separate public file directory or additional database table is created.

A new successful upload **replaces** the skills list and interests. Previously extracted skills and manually added skills are not merged into the new profile. Students can add skills in the form or through confirmed chat updates afterward; those additions remain until the next successful resume upload. A missing graduation year leaves the student's selected year unchanged. Work-arrangement and location preferences remain unchanged. Failed extraction, invalid files and provider errors leave the previous file and profile intact.

Matches and Chat both read this database-backed profile, so resume-extracted and subsequently added skills automatically drive the existing search/ranking engine. Uploading clears previous search/chat results to prevent displaying a shortlist based on the old resume. Resume requests share the session's AI request budget with chat.

`python live_resume_check.py` verifies PDF extraction, replacement by a second fictional resume, removal of manually added skills, persisted latest-file download data, and real semantic matching. It sends fictional data to Gemini and incurs API requests. `pytest` uses fake provider responses instead.

The login startup now refreshes an outdated cached `db` module if required functions are missing, and migrates existing seven-column profiles without losing student data. If a long-running terminal still shows an old traceback, stop it with Ctrl+C and run `.\start.ps1` from this project root.


## Admin dashboard and custom internships

Sign in at the same app URL using the **Admin password** line in `runtime/demo_access_codes.txt`. The password is stored beside the student access codes as requested; only its random-token hash is stored in SQLite. Account role is checked in the database on every admin operation. Student accounts cannot add jobs or rebuild the catalog.

The administrator sees a separate dashboard with an Add internship form, collection table, CSV download and index-rebuild control. Enter the source URL, title, company, concise description, skills, work arrangement, supported locations and any **explicitly stated** graduation years. Blank eligibility stays unknown. Duplicate source URLs are rejected.

**Save internship** writes a validated row to `data/jobs.csv`, imports the updated collection into SQLite while retaining existing IDs, then rebuilds embeddings automatically. CSV writes use a temporary file and atomic replacement; an import failure restores the previous CSV. If embedding generation fails, the listing remains saved and searchable by keywords, and the dashboard reports that the index needs rebuilding. Use Rebuild search index to retry. Keep `data/jobs.csv` writable; the dashboard does not need a second server or a Gemini call to add listings.

### Expanded web collection

Exactly 100 additional records from 18 employers were added, for 152 total. Most were researched through employers' public Greenhouse board data, plus Cargill's own listing. Titles, qualification excerpts and locations were reviewed; the app has no scheduled scraping or automatic job-feed importer. The expanded snapshot is `data/web_additions_2026-10-24.json`; per-posting source URLs, public-board endpoints and short graduation evidence appear in `data/web_sources_2026-10-24.json`. Some posts are explicitly graduate-level; check the degree requirements at the source.

Twenty-seven new records have explicit graduation-year information. Other records remain unknown rather than assuming that an internship in 2027 requires graduation in 2027. The collection spans several countries; remote work never implies worldwide eligibility.

In **Profile**, students may explicitly enable **Include roles with unstated graduation eligibility**. It is off by default. Such cards show an eligibility-unverified warning; known graduation-year mismatches, inactive listings, hidden roles, remote requirements and location compatibility continue to be enforced. Chat cannot change this setting. This makes additional postings discoverable without falsely claiming verified eligibility.

Catalog checks found 30 matching graduation-year records for 2027 and 34 for 2028 before applying location/remote preferences. With the explicit unknown-eligibility option enabled, the 2028 India sample has six candidates. These are checks against modeled constraints, not verification of every degree, residency or hiring requirement. See `docs/catalog_validation.json`.

The previously published Precision@5 reports describe the older 52-record snapshot. The extra 100 records have not received complete relevance labels for those evaluation profiles, so those historical metrics should not be presented as a comparison for the expanded collection. The current functionality is covered by 41 automated tests including admin authorization, CSV/database/vector synchronization and rollback.
