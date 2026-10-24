# Internship Match Assistant — Feature Increment History

This document records the features requested and introduced as the project
progressed, from the original brief through the Supabase preparation and this
documentation request. It explains the user-facing behavior, how each feature
was added, and the main code involved.

The order follows the requests in the project conversation. Exact implementation
dates are not assigned where the conversation does not establish them. Bug fixes,
exception repairs, import compatibility changes and troubleshooting are excluded.
Questions that only led to explanations are distinguished from implemented features.
No private access codes, passwords, API keys or connection strings are included.
The deliberately public **DUMMY** demo code is the only credential shown.

## Feature timeline

| Increment | Request or milestone | Result |
| --- | --- | --- |
| 1 | Build the application according to the supplied brief | Profile form, curated internship search, account access, saved/hidden jobs, Gemini tools and evaluation |
| 2 | Use the named classmates and simplify the interface | Named accounts and a clearer student interface |
| 3 | Upload a resume and build the profile with Gemini | Latest-resume storage, extraction, editable skills and replacement behavior |
| 4 | Show the signed-in name in the sidebar | Personalized navigation greeting |
| 5 | Add an admin dashboard and 100 web-sourced internships | Role-restricted catalog management, expanded CSV and explicit unknown-eligibility option |
| 6 | Provide deployment guidance | Local launch instructions, hosting guidance and deployment packaging |
| 7 | Prepare a public demonstration account | DUMMY account and login-field hint |
| 8 | Retain data on Streamlit Community Cloud using free Supabase | Optional PostgreSQL storage, initial catalog seeding, persistent catalog and CSV export |
| 9 | Resume Supabase when Streamlit becomes active | Server-side status checks, restore requests and bounded waiting |
| 10 | Keep sensitive information private during deployment | Private configuration template, excluded secret files and sanitized cloud errors |
| 11 | Document feature additions from the beginning | This `INCREMENT.md` history |

## Increment 1 — Original application

### Requested scope

Build a small Internship Match Assistant for approximately 5–10 classmates,
starting with a form and search results over 50–100 manually curated internship
postings, then add a small conversational agent. Use Streamlit, ordinary Python,
SQLite, pandas, Sentence Transformers, NumPy, Gemini and Pydantic.

### Student profiles and assigned accounts

Students sign in with an assigned access code rather than selecting a public
username. The validated account determines which profile and saved jobs are loaded.
Profiles contain skills, interests, graduation year, remote-only preference and
preferred locations.

Implementation:

- `db.py` defines the original four tables: `users`, `profiles`, `jobs` and `feedback`.
- `manage.py` creates invited accounts and generates random access codes.
- The database stores access-code hashes; the local private assignment file is
  outside version control.
- `schemas.py` validates profile fields and normalizes supported aliases, such as
  JS to JavaScript and Bangalore to Bengaluru.
- `app.py` provides authentication, the profile form and user-scoped navigation.

### Curated internship collection

The first completed collection contained 52 employer/ATS postings. Each record
includes its original URL, title, company, concise description, skills, work mode,
location, eligibility information, verification date and active status.

Implementation:

- `data/jobs.csv` holds the curated catalog.
- `import_jobs.py` reads it with pandas and validates every record with the
  `Job` schema before writing changes.
- Source URLs identify listings during imports, preserving job IDs and their
  associated feedback.
- Missing facts remain unknown rather than being invented.

### Matching and explanations

Students receive up to five eligible internships, with matching skills, missing
skills and a link to the source posting. They can choose keyword, semantic or
combined ranking.

Implementation:

1. `embeddings.py` creates normalized vectors with
   `sentence-transformers/all-MiniLM-L6-v2`.
2. Vectors, explicit job IDs and a model/text fingerprint are saved as local
   search-index files.
3. `search.py` filters inactive and hidden roles and applies graduation-year,
   work-mode and verified-location constraints before ranking.
4. NumPy compares the profile/query vector against the job vectors.
5. Combined ranking uses `0.8 × cosine similarity + 0.2 × skill coverage`.
   When required skills are unknown, similarity alone is used.
6. `app.py` renders result cards and structured explanations. Ranking scores are
   not presented as hiring probabilities.

Remote postings are not assumed to accept applicants worldwide. Unknown
graduation eligibility is excluded by default. These constraints apply to form
search and chat search through the same functions.

### Saved and hidden internships

Students can save a role, hide a role from future matches and restore a hidden
role. These actions are associated with the authenticated account.

Implementation:

- `db.set_feedback()` maintains one action per user/job pair using an upsert.
- `db.get_feedback()` loads the account's feedback.
- `app.py` adds card actions, a Saved page and hidden-role controls.
- `search.py` excludes the user's hidden IDs before ranking.

### Gemini conversational tools

Chat can search internships and propose preference changes. A message such as
“Only remote roles in India” can propose remote/location settings, but saving
the change requires confirmation.

Implementation:

- `agent.py` exposes exactly two tools: `search_jobs(query)` and
  `update_preferences(remote_only, preferred_locations)`.
- `schemas.py` validates tool arguments. The tools do not accept a user ID from
  the model; the application binds them to the signed-in account.
- `app.py` presents the proposed changes for confirmation or cancellation.
- Confirmed changes use the same database preference functions as the form.
- A maximum of three tool calls is permitted per message. API requests count
  toward a shared chat/resume browser-session allowance of 20 requests.
- `configuration.py` reads Gemini configuration from environment variables or
  the private Streamlit secrets file. The configured default model is currently
  `gemini-3.1-flash-lite`.

Chat does not add skills or change graduation year. Those fields use the Profile
form or resume extraction. It also does not provide durable conversational memory
or implement a separate recommendation engine.

### Evaluation and project documentation

The original brief also requested a comparison against a keyword baseline.
`evaluate.py` compares keyword, semantic and combined ranking on fictional
profiles in `data/evaluation_cases.json`. Reports include relevance measures,
constraint checks and warmed retrieval latency. `README.md` explains operation
and architecture; `VALIDATION.md` records verification evidence and limitations.

The original retrieval-quality reports describe the original 52-record collection;
they are not new quality measurements of the later expanded catalog.

## Increment 2 — Named classmates and simpler interface

### Request

Use the student names Abhinav, Geetesh, Rohan, Amit and Rishi. Make the UI easier
to understand and remove unnecessary descriptive lines, including small-group
marketing text from the user-facing interface.

### Implementation

- The local invited accounts use the requested display names while retaining
  individual access codes.
- `app.py` organizes the student experience around **Matches**, **Profile**,
  **Saved** and **Chat**.
- Labels, forms, result cards and chat replies were simplified around the
  student's immediate task.
- Theme configuration in `.streamlit/config.toml` and styling in `app.py`
  provide a consistent layout and appearance.

This was an interface and account-personalization increment, not public
registration. Existing local accounts are not automatically copied to a fresh
Supabase database.

## Increment 3 — Resume upload and profile extraction

### Request

Upload and retain the latest resume, use Gemini to create a profile from it,
allow additional manually entered skills, and use those skills when finding roles.
Whenever a new resume is uploaded successfully, keep only skills extracted from
that new resume rather than retaining old or manually added skills.

### Implementation

- `app.py` adds resume upload, **Create profile from resume** and
  **Download latest resume** controls to Profile.
- `resume_profile.py` accepts PDF, DOCX and UTF-8 TXT files up to 5 MB.
  PDFs are sent as inline Gemini input; DOCX text is extracted from document XML;
  TXT content is decoded before extraction.
- Gemini returns structured resume fields. `ResumeExtraction` in `schemas.py`
  validates whether the document is a resume, its explicit skills, professional
  interests and an unambiguous graduation year when available.
- `db.replace_resume()` saves the original file bytes, filename, MIME type,
  upload timestamp and extracted fields in the account's profile record.
- File replacement and profile replacement occur together in a transaction.
- New extracted skills replace the previous skill list, including manual
  additions. The Profile form can then add new manual skills again.
- An extracted graduation year updates that field; an unknown year preserves
  the existing year. Work-mode and location preferences are retained.
- Failed extraction does not replace the previous saved resume or profile.

There is no separate resume-only ranking engine: the updated profile flows into
the existing search pipeline. Gemini performs extraction; MiniLM/NumPy perform
the ordinary matching.

Original resume bytes are private account data in the database. Under the later
Supabase configuration, those bytes are stored in PostgreSQL rather than an
ephemeral Streamlit filesystem. No public resume directory is used.

## Increment 4 — Personalized sidebar greeting

### Request

Show a greeting such as “Hi, Abhinav” on the left navigation bar.

### Implementation

`app.py` loads the authenticated user's display name and renders
`Hi, <display_name>` in the sidebar. The administrator view also displays its
account greeting and Administrator label.

## Increment 5 — Administrator dashboard and larger catalog

### Request

Add an administrator dashboard for custom internships, update the CSV when an
internship is added, store the admin password with the other local access-code
assignments, and add 100 web-sourced internship records.

### Administrator account and dashboard

- `db.py` adds an `is_admin` role field to accounts.
- `catalog_admin.create_admin()` creates an administrator account. Its randomly
  assigned local password is recorded in the same ignored access-code assignment
  file as the student codes; the database stores its hash.
- `app.py` routes an authenticated administrator to `admin_dashboard.py`.
- `catalog_admin.require_admin()` checks the database role before catalog writes
  and exports. Student accounts do not receive admin controls.
- The dashboard collects title, company, source URL, description, skills, work
  arrangement, location compatibility, eligible graduation years, verification
  date and accepting-applications status.
- Administrators can download the CSV and rebuild the search index.

### Local catalog editing

`catalog_admin.add_job()` validates the submitted `Job`, checks duplicate source
URLs, writes the updated CSV through a temporary file and atomic replacement,
imports it to SQLite and rebuilds embeddings. The local CSV remains the catalog
source of truth in this mode.

The later cloud-storage increment changes the authoritative store for cloud
deployments to PostgreSQL while preserving the local workflow.

### The 100 additional postings

Exactly 100 additional web-sourced records were researched on October 24, 2026,
bringing the curated snapshot from 52 to 152 postings.

- `data/web_additions_2026-10-24.json` records the additions.
- `data/web_sources_2026-10-24.json` records source references and evidence.
- The validated records were added to `data/jobs.csv`, imported and indexed.
- Eligibility fields use explicit source evidence; unknown values remain unknown.
- This was a one-time catalog expansion, not an automatic recurring scraper.

At the latest code inspection, `data/jobs.csv` contains **153 rows**. This current
count is distinct from the historical 152-record curated expansion snapshot.
It is not a claim that every role is still open or eligible for every profile.

### Optional inclusion of unstated graduation eligibility

The expanded collection also introduced an explicit Profile checkbox to include
roles whose graduation eligibility is unstated. It is disabled by default.
`schemas.py` stores `allow_unknown_graduation`, `db.py` persists it, and
`search.py` applies it during filtering. Cards flag unknown eligibility as
unverified. Known year mismatches remain excluded, and chat cannot enable the
option on the user's behalf.

## Increment 6 — Launch and deployment preparation

### Request

Explain how to run the project from a fresh terminal and deploy it.

### Delivered support

- `start.ps1` starts the application with the project's virtual environment and
  local model-cache configuration.
- `requirements.txt` defines dependencies; `requirements.lock.txt` records a
  tested environment snapshot.
- `Dockerfile` and `.dockerignore` support a single-process container deployment.
- `settings.py` supports `MATCHER_STATE_DIR` for a host-provided persistent volume.
- `README.md` provides setup, launch, data import, indexing and hosting guidance.

Persistent-disk hosting was discussed first. Streamlit Community Cloud was later
selected as the intended interface host, with separate Supabase storage to retain
runtime changes. Preparing files and instructions did not publish the application.

Localtunnel, ngrok, Cloudflare Tunnel, static-file serving and their security
implications were explained during the conversation. No tunnel was installed or
started, and static-file serving was not enabled as part of those explanations.

## Increment 7 — Public DUMMY demo account

### Request

Prepare for recruiter/demo access with a user named DUMMY, password DUMMY, and
mention the demo credential in the access-code textbox.

### Implementation

- `db.init_db()` idempotently ensures a DUMMY account and default profile exist.
- The public code is hashed before storage, and the account is explicitly kept
  non-administrator.
- Repeated startup does not reset its edited profile.
- `app.py` shows **Try the demo: DUMMY** as the login-field placeholder and
  explains that the account's data is shared.

Anyone using this code shares the same profile, latest resume and saved jobs.
It is intended for fictional demonstration data, not private recruiter/student
resume storage.

## Increment 8 — Supabase persistence for Streamlit Community Cloud

### Request and agreed constraint

Retain admin additions and student data across Streamlit restarts, using Supabase
only on its Free plan for a very small user base.

### Optional PostgreSQL backend

- `cloud_storage.py` reads server-only settings from environment variables or
  the ignored Streamlit secrets file.
- Setting `DATABASE_URL` selects PostgreSQL. Without it, local development
  continues to use SQLite.
- `psycopg[binary]` was added to the dependency files and installed locally.
- `db.connect()` selects the backend. `PostgresConnection` adapts the existing
  application's bound-parameter SQL and schema creation for PostgreSQL.
- `db.init_db()` creates application tables in the separate `internship_match`
  schema, enables row-level security and creates DUMMY plus the configured
  private administrator account.
- Resume bytes use PostgreSQL `BYTEA`; small profile lists continue to use
  JSON-encoded text fields.
- An unavailable configured cloud database does not silently switch to a new,
  empty SQLite database.

### Initial catalog and subsequent additions

- `cloud_startup.prepare_catalog()` seeds the CSV only when the cloud catalog is
  empty. Transaction-scoped advisory locks serialize initial seeding and cloud
  catalog additions.
- `import_jobs.write_jobs()` provides the shared insertion/upsert logic.
- In cloud mode, `catalog_admin.add_job()` writes directly to the durable
  database without replacing existing records from an old local CSV snapshot.
- `catalog_admin.export_catalog()` generates an up-to-date CSV from the database
  for the admin download button.
- `cloud_startup.py` recreates missing or stale local embedding caches from the
  durable catalog after a fresh Streamlit instance starts.

The GitHub CSV is the initial seed in cloud mode. Runtime additions do not commit
back to GitHub. Local accounts, saved jobs and resumes are not automatically
migrated to Supabase; an explicit migration would be a separate operation.

### Configuration and status

`.streamlit/secrets.example.toml` contains placeholders only.
`docs/STREAMLIT_SUPABASE.md` explains Free-project setup, session-pooler connection
settings, startup, persistence and live verification.

This feature is **implemented in code but not connected to a live Supabase
project or deployed**. Private credentials must be entered by the owner first.

## Increment 9 — Resume Supabase on demand

### Request

When someone wakes Streamlit, make it request that a paused Supabase project
resume, instead of requiring a manual dashboard action every time.

### Implementation

- `supabase_wake.py` reads the configured project reference and Management API
  token on the Python backend.
- It checks status with `GET /v1/projects/{ref}` on Supabase's fixed management
  API host.
- For `INACTIVE`, it requests `POST /v1/projects/{ref}/restore`.
- It polls intermediate startup states, briefly caches successful checks and
  throttles repeated restore requests within the process.
- `app.py` runs this check before initializing the cloud database and catalog.
  Visitors see a startup message, then a retry control if restoration takes
  longer than the bounded wait.

An ordinary database request does not perform this restore automatically. The
management token is separate from database and public API credentials. Without
it, manual dashboard restoration remains necessary.

The flow does not guarantee instant startup, prevent all free-tier pausing or
bypass Supabase restoration eligibility. Real restoration permissions and timing
remain to be verified against the owner's project.

## Increment 10 — Private deployment configuration

### Request

Keep sensitive information private while preparing persistent storage and
automatic resume.

### Implementation

- Real `.streamlit/secrets.toml`, runtime data, database files, access-code
  assignments and `.env` files are excluded from Git; container exclusions also
  omit runtime secrets.
- Public templates contain placeholder names rather than credentials.
- Cloud connection and management failures are converted to sanitized errors
  instead of displaying connection strings, tokens or provider response bodies.
- `.streamlit/config.toml` suppresses detailed exception displays to visitors.
- The Supabase application schema is separate from public data APIs, and the
  deployment guide instructs keeping it out of exposed schemas.
- The cloud admin code is read privately from `ADMIN_ACCESS_CODE`; weak-length
  or placeholder values are rejected.

The setup instructions ask the owner to enter secret values directly into local
or hosted Streamlit Secrets and report readiness without sending values in chat.
These controls do not constitute a complete security audit.

## Increment 11 — Feature-history documentation

### Request

Create `INCREMENT.md` describing requested feature additions from the beginning
through the latest point, explaining how they were added and omitting bug fixes.

### Implementation

This document reconstructs the feature sequence from the project brief,
conversation, source modules and existing documentation. It distinguishes
implemented behavior from discussed options, and prepared cloud support from a
verified deployment. The README links to it for future readers.

## Status at this documentation milestone

| Area | Status |
| --- | --- |
| Local student/admin application | Implemented |
| Named accounts, greeting and simpler UI | Implemented |
| Gemini chat and resume extraction | Implemented; require an available configured Gemini API |
| Curated catalog and custom additions | Implemented; current CSV has 153 rows |
| DUMMY demo login | Implemented; shared, non-admin account |
| Optional Supabase storage and on-demand restore | Implemented in code; credentials and live checks pending |
| Regression verification after cloud preparation | 56 tests passed; cloud lifecycle tests use simulated management responses/local test storage |
| Live PostgreSQL persistence and restore timing | Not yet verified |
| Public deployment or tunnel | Not performed |
| Durable per-account/global rate limits | Discussed only; current 20-request browser-session allowance remains |

Feature documentation does not imply that paid services were enabled, remote
accounts were created or existing local personal data was migrated.

## Increment 12 — Neon Free as an alternative database provider

After the Supabase project took too long to start, the user requested an
alternative for deployment within an hour. Neon Free was selected, retaining
Streamlit Community Cloud as the intended interface host.

The existing PostgreSQL adapter is reused: `DATABASE_URL` now targets the privately
configured direct Neon connection. Supabase management settings are left empty,
so startup does not request a Supabase restore. Neon's connection-triggered
compute wake-up handles its idle state instead. Accounts, profiles, resume bytes,
feedback and admin-added jobs remain in the external PostgreSQL database.

The user entered credentials privately in the ignored secrets file. Live checks
on October 25, 2026 verified encrypted database connectivity, schema creation,
153 catalog records, non-admin DUMMY authentication, private administrator
authentication, and catalog preservation across new connections and repeated
initialization. `docs/STREAMLIT_NEON.md` records setup and hosting steps. The
earlier pending-Supabase status above describes that historical milestone;
the Neon connection is now verified. Public Streamlit deployment remains pending.

## Increment 13 — Confirmed skill changes through chat

The user requested that chat support self-reported technologies just as the
manual Profile form does. Chat can now propose adding or removing specific
skills, without requiring those skills to appear in the saved resume.

- `PreferenceArgs` in `schemas.py` adds `add_skills` and `remove_skills` delta
  lists, with existing alias normalization, limits and conflict validation.
- `agent.py` extends the existing `update_preferences` tool rather than adding
  another tool. Its instructions distinguish statements such as “I also know
  Docker” from searches such as “Find React internships”; searches alone must
  not claim the user knows a technology. Related skills are not inferred.
- `app.py` displays additions, removals and the resulting skills before the
  existing Confirm/Cancel decision. A proposal alone does not save anything.
- `db.update_preferences()` applies deltas to the latest stored skills inside
  the preference transaction. PostgreSQL locks the target profile row while
  merging. Unrelated skills, interests, graduation year and resume data remain.
- Confirmed changes are immediately available to matching through the shared
  profile-backed search functions. New successful resume uploads still replace
  all skills, including additions made through chat.
- Tests cover confirmation, cancellation, alias conflicts, invalid arguments,
  account isolation, skill limits, search without mutation and the visible
  confirmation panel. The public app is now reported deployed by the owner;
  hosted verification of this increment follows the GitHub deployment update.
