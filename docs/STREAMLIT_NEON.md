# Deploy with Streamlit Community Cloud and Neon Free

The app supports Neon through its existing PostgreSQL backend. The application's
`internship_match` schema name is retained; Supabase-specific wake logic is
disabled by leaving both Supabase configuration fields empty.

1. Create a **Free** Neon PostgreSQL project. Enable only Postgres; no object
   storage, Functions, AI gateway, Realtime or Better Auth is required.
2. In **Connect**, switch pooling **off** for the initial setup and copy the
   complete connection string including its SSL parameters.
3. Add these top-level settings to your private local `.streamlit/secrets.toml`,
   preserving the existing Gemini key. Every value must be quoted:

   ```toml
   DATABASE_URL = "YOUR_COMPLETE_NEON_CONNECTION_STRING"
   ADMIN_ACCESS_CODE = "YOUR_EXISTING_PRIVATE_ADMIN_CODE"
   SUPABASE_PROJECT_REF = ""
   SUPABASE_MANAGEMENT_TOKEN = ""
   ```

4. Keep the connection string and admin password private. Never commit them or
   send them in chat. Runtime files and the real secrets file are ignored by Git.
5. Push the application source and `data/jobs.csv` to your GitHub repository.
   Deploy `app.py` on Streamlit Community Cloud with **Python 3.12**. Dependencies
   are installed from `requirements.txt`.
6. In Streamlit's private **Secrets** editor, enter the actual settings above
   plus the existing `GEMINI_API_KEY`. Do not upload the real secrets file to Git.
7. Verify the public DUMMY login, then use your private admin code to check the
   catalog and its CSV download. A clean instance downloads model weights and
   initializes its index, so the initial startup can take longer.
8. Verify an admin addition survives a Streamlit reboot before sharing widely.

Accounts, profiles, original resume bytes, feedback and catalog additions persist
in Neon, not on Streamlit's local disk. The CSV seeds an empty database only;
admin downloads export current database contents. Existing local student accounts
and resumes are not copied automatically. The public DUMMY account shares all of
its data; use fictional resumes for that account.

Neon wakes idle compute when a connection arrives; it does not require the
Supabase Management API token. Free-plan compute/storage limits still apply.
Current provider plan details: https://neon.com/pricing
Connection behavior: https://neon.com/docs/introduction/scale-to-zero

## Live verification on 2026-10-25

The configured Neon connection succeeded with encrypted PostgreSQL transport.
Schema initialization completed; the catalog contains 153 records. DUMMY was
verified non-admin and the configured private admin login authenticated.
New connections and repeated startup preserved the catalog. No credentials or
personal profile contents were printed during verification.

This verifies the database connection and initialization, not a deployed
Streamlit Community Cloud URL. Public deployment still needs repository selection
and the private hosted Secrets settings.
