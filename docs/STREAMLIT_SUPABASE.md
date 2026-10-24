# Streamlit Community Cloud with Supabase Free

## What you need to enter privately

Create a project under a **Free** Supabase organization. No paid add-ons are needed.
In Streamlit's app settings, open **Secrets** and copy the structure from
`.streamlit/secrets.example.toml`. Enter the real values there, never in Git or chat.
For local verification, add the same fields to the existing ignored
`.streamlit/secrets.toml`, preserving the existing Gemini key.

| Setting | Where to obtain it |
| --- | --- |
| `GEMINI_API_KEY` | Your existing free-tier Gemini key |
| `DATABASE_URL` | Supabase project **Connect > Session pooler**, port **5432**; replace the password placeholder and percent-encode reserved characters in the password |
| `SUPABASE_PROJECT_REF` | Project reference ID in Supabase project settings (also in its dashboard URL) |
| `SUPABASE_MANAGEMENT_TOKEN` | A Management API access token created in Supabase account settings; it must permit reading the project's status and restoring it. Use project-specific permissions if available. This is separate from publishable/anon/service-role keys. |
| `ADMIN_ACCESS_CODE` | Copy your private existing admin password from `runtime/demo_access_codes.txt`, or choose a random code of at least 24 characters. Do not use DUMMY. |

Do not send these secrets to the assistant. After entering them, report only that
the settings are ready. We can verify success without printing secret values.
Do not upload the `runtime` directory, database, access-code file or real secrets
to GitHub. The example file contains placeholders and is safe to commit.

## First startup and persistent data

The app uses PostgreSQL whenever `DATABASE_URL` is configured; otherwise local
development continues to use SQLite. An invalid cloud connection never silently
falls back to a new local database. Tables live in a separate `internship_match`
schema, with RLS enabled and no client access policies. Keep this schema out of
Supabase's exposed Data API schemas. All queries originate on the Python backend.
The initial connection uses the database owner to create the application schema;
database credentials must therefore remain server-only.

On an empty cloud database the app creates the public DUMMY account, the private
admin account and imports the committed CSV once. Subsequent restarts do not
re-import the CSV over admin additions. In cloud mode PostgreSQL is authoritative:
admin additions go there; **Download jobs.csv** exports the latest catalog. The
GitHub CSV is not automatically modified. Locally, existing CSV editing remains.

Profiles, saved jobs and original resume bytes are stored in PostgreSQL. For this
small demo there is no separate storage bucket to configure. Resume size remains
limited to 5 MB; the latest upload replaces the previous one. The shared DUMMY
account's profile and resume can be read or replaced by anyone using DUMMY. Use
fictional documents there. Private student accounts remain separate.

Existing local student accounts, saved jobs and resumes are **not migrated
automatically**. They remain on your laptop. Ask for an explicit migration if
you want them copied; do not commit the SQLite file as a deployment shortcut.
Keep the configured admin code stable; changing it does not revoke previous
admin accounts automatically. Revoke/rotate existing credentials explicitly.

Embedding files and downloaded model weights are disposable caches. A fresh
Streamlit instance rebuilds its search index from the durable database. This can
make first startup slow, and model downloads still require available memory and
network access on Streamlit Community Cloud.

## Resume after inactivity

If a management token is configured, startup checks project status using
`GET https://api.supabase.com/v1/projects/{ref}`. When status is INACTIVE it sends
`POST https://api.supabase.com/v1/projects/{ref}/restore`. Other intermediate
states are polled. Checks are briefly cached within each Python process; restore
requests are throttled in-process. The project reference is validated and the
request destination is fixed to Supabase's management host.

The first visitor sees a startup message. The app waits in bounded intervals and
offers **Retry connection** if restoration is still running. Startup does not
promise instant recovery, prevent future free-tier pausing or bypass restoration
eligibility. Management failures show sanitized messages, never provider bodies,
tokens or connection strings. Without the token, resume manually in Supabase.

## Deploy and verify

1. Commit source, requirements and `data/jobs.csv` to your repository. Confirm
   `.gitignore` excludes real secrets and runtime data before publishing.
2. Deploy `app.py` on Streamlit Community Cloud using Python 3.12 and
   `requirements.txt`. Add the private Secrets above.
3. Sign in with DUMMY, then verify matches. Sign out and sign in with the private
   admin code; add a clearly labeled test listing.
4. Reboot the Streamlit app and verify the test listing and a changed profile
   remain. Download jobs.csv to confirm it includes the addition.
5. To verify wake-up, pause the **test Free project** from Supabase, open the app,
   and verify restore/startup/retry behavior. Do not run this experiment while
   another person is using the project.

Cloud connection and real resume behavior must be verified after you configure
credentials; offline tests cannot demonstrate actual Supabase permissions or
restore times. No deployment, cloud writes or paid plan changes are performed
just by preparing this code.

The existing Gemini cap is still browser-session based. Persistent rate limiting
has not been added in this storage change. Public-demo usage can exhaust the
shared free-tier Gemini quota; configure account/global limits before broad sharing.

References:
- https://supabase.com/docs/guides/database/connecting-to-postgres
- https://supabase.com/docs/reference/api/v1-restore-a-project
- https://supabase.com/docs/guides/platform/free-project-pausing
- https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/secrets-management
