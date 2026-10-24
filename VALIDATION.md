# Validation record — October 24, 2026

The expanded source dataset contains 152 distinct employer/ATS listing URLs. The SQLite database and the MiniLM embedding index were generated locally. Five private accounts are named Abhinav, Geetesh, Rohan, Amit and Rishi; existing access codes and student data were preserved. Codes are in the git-ignored `runtime/demo_access_codes.txt`.

## Held-out comparison (original 52-record snapshot)

Five held-out fictional student profiles; ten jobs pass their shared graduation-year constraint. No ranking weights were adjusted after seeing these results.

| Method | Mean Precision@5 | Constraint violations | Median warmed search latency |
|---|---:|---:|---:|
| Keyword baseline | 0.44 | 0 | 0.049 ms |
| Semantic similarity | 0.52 | 0 | 15.550 ms |
| Combined (0.8 / 0.2) | 0.48 | 0 | 15.692 ms |

Development profiles: keyword 0.44, semantic 0.48, combined 0.52. These are small author-labeled comparisons, not proof of general superiority. Semantic-only outperformed the prescribed combined formula on this held-out set; the original weights remain unchanged.

Hardware: Windows 11, AMD64 Family 23 Model 104 Stepping 1 (AuthenticAMD), 12 logical CPUs, CPU inference. Initial model loading excluded; model warmed before measurement. Each case/method uses the median of five query encoding + in-memory filtering/ranking runs. Summary latency is the median across cases. SQLite reads and UI rendering are outside this timing.

Full per-profile outputs, labels, dataset fingerprints and hardware are saved in `docs/evaluation_dev.json` and `docs/evaluation_test.json`. Reports can be regenerated using the commands in README.md.

## Checked behavior

- Automated tests cover constraints, unknown graduation eligibility, remote geography, hidden jobs, zero/fewer-than-five results, skill aliases and ranking arithmetic.
- SQLite checks cover account isolation, hashed codes, preference preservation/clearing, feedback upserts and persistence, four tables, and stable IDs after reimport.
- Embedding tests deliberately shuffle vector rows and reject stale text fingerprints.
- Simulated Gemini responses check confirmation before mutation, cancellation, argument validation, provider failure and the three-tool bound.
- Streamlit's AppTest exercises sign-in → profile save → search → save → hide → restore → sign-out/sign-in without UI exceptions. It also checks chat configuration errors and the confirmation UI.
- The running application's login page was visually inspected in the in-app browser.

## Repair and recheck

**41 automated tests pass.** The provided API key was initially unquoted in secrets.toml; the syntax was repaired without exposing the key. The old default model returned 404 in a real call. The app now uses `gemini-3.1-flash-lite`, verified with the configured key. Provider responses are mapped to safe, actionable errors, with one bounded retry for transient server failures and no retry for authentication/quota failures.

All five live acceptance cases passed using an isolated synthetic student profile: Python internship search, remote-only update, Bengaluru location update, clearing locations, and the unsupported saved-jobs request. The three preference changes were checked for no mutation before confirmation. Search used the actual MiniLM index. The redacted boolean results are in `docs/live_chat_validation.json`.

The UI now has Matches, Profile, Saved and Chat pages, short labels, and expandable role details. Promotional headers, classroom descriptions and nonessential counters have been removed. Local secrets are read on each Chat page run; malformed configuration cannot break the rest of the app.

Docker deployment and classmate user testing have **not** been performed. Google service availability and account quotas remain external dependencies.


## Resume and login regression verification

The exact missing-`get_user` condition was reproduced by removing the function from the cached module before a Streamlit sign-in. Startup refreshed the module and sign-in completed successfully. Legacy profile rows migrate in place; all five student account names and records remain available.

Resume tests verify PDF signature and file limits, DOCX text parsing, structured-schema compatibility, per-account storage, atomic failure behavior, new-resume replacement of extracted and manually added skills, preserved location preferences, and updated search ordering. A Streamlit UI test uploads a resume, manually adds a skill, then uploads a second resume and checks that both database and visible skill field reset.

The configured Gemini API successfully processed a fictional PDF and a replacement TXT resume. Old Python/SQL and manually added Docker skills were removed; JavaScript/React from the latest resume became the profile. Actual MiniLM search from that profile returned five roles. Boolean-only results are saved in `docs/live_resume_validation.json`. No real student resume was used in this live test.


## Shared import and chat startup regression

Shared provider errors now live in `ai_errors.py`; resume extraction no longer imports them from the chat agent. Startup fingerprints local source modules and refreshes changed modules with their dependencies before rendering pages. It also detects an old Agent constructor lacking the model argument, while preserving the configured SQLite location.

Regression tests remove `provider_error` from a cached agent module and simulate its old constructor, then sign in, open Profile, initialize Chat and send a message. The sidebar greeting is checked as `Hi, Abhinav`. All 34 tests pass. A fresh live Gemini diagnostic with the configured key returned a `search_jobs` function call after this change.


## Admin dashboard and expanded catalog

A role-checked Admin dashboard now adds custom internships to CSV, imports them to SQLite and regenerates vectors. Tests cover ordinary-user write denial, duplicate URL rejection, stable IDs, CSV/database/index synchronization, failed-index recovery, and CSV restoration if import fails. An AppTest signs in as admin, saves a listing, signs out, then verifies that a student does not see admin controls. The random admin password was appended to the existing private access-code file and its hashed account authentication was verified without printing the password.

The collection now has 152 records after adding exactly 100 web-sourced listings. Twenty-seven additions have explicit graduation years. The real MiniLM index was rebuilt after testing. Keyword eligibility checks found 30 candidates for a 2027 profile, 34 for 2028 and two for 2029 before applying location/remote constraints. Strict filtering still returns none for 2026/2030 in this snapshot. The optional, explicitly enabled unknown-year policy makes 112 unknown-year records discoverable with clear warnings, without admitting known year mismatches. A 2028 India example returns six candidates with that option enabled. Counts and authentication checks are in `docs/catalog_validation.json`.

The 52-record retrieval-evaluation reports above remain historical. Their frozen relevance labels do not comprehensively cover the extra postings; no new quality metric is claimed for the larger collection.
# Supabase preparation (2026-10-25)

56 regression tests passed in 23.15 seconds after adding optional PostgreSQL
storage, bounded Management API restore polling, durable catalog initialization,
and current-database CSV export. New tests simulate paused/starting/healthy
states, repeated restore suppression, sanitized failures, credential-safe SQL
binding, no SQLite fallback on cloud errors, DUMMY role isolation, and catalog
survival across repeated startup initialization. The catalog behavior test uses
a local transactional test store, not a live PostgreSQL server.

The PostgreSQL driver is installed. Real Supabase connection permissions, schema
creation, pause/restore timing and deployed startup remain unverified until the
owner enters credentials privately. No cloud project or deployment was created.
See `docs/STREAMLIT_SUPABASE.md` for setup and live checks.

