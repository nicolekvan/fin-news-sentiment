# Deployment (Vercel, free Hobby plan)

The public site is a static build of the committed snapshot in `frontend/snapshots/real`.
No environment variables, API keys or database are needed on Vercel.

## First deployment

1. Sign in at vercel.com and choose **Add New… → Project**.
2. Under **Import Git Repository**, connect GitHub if asked, and allow Vercel access to the
   `fin-news-sentiment` repository (choosing "Only select repositories" is fine).
3. Select the repository and click **Import**.
4. Set **Root Directory** to `frontend` (click **Edit** next to it). The framework is detected
   as Next.js; `frontend/vercel.json` supplies the build and install commands, the `SNAPSHOT`
   setting and the security headers, so leave the other settings as they are.
5. Do **not** add any environment variables.
6. Click **Deploy**. After a minute or two you get a URL like
   `https://fin-news-sentiment.vercel.app`.

Every push to `main` redeploys automatically.

## Checking a deployment

- Every page loads and shows "Historical snapshot · prices as of …".
- The browser console shows no Content Security Policy errors.
- Response headers include `Content-Security-Policy`, `X-Frame-Options: DENY` and
  `X-Content-Type-Options: nosniff`.

## Updating the data

```bash
cd backend
python -m marketlens.jobs.export --out ../frontend/snapshots/real
```

Commit and push `frontend/snapshots/real`; Vercel rebuilds.

## Switching the public site to synthetic data

Change `"SNAPSHOT": "real"` to `"demo"` in `frontend/vercel.json` and push.

## Production path (not deployed)

For a live, scheduled version: run the jobs from GitHub Actions on a schedule with provider keys
stored as repository secrets; host Postgres on Supabase (apply `supabase/migrations`, create login
users granted `marketlens_reader` / `marketlens_writer`); deploy the FastAPI app (e.g. Render)
with `DATABASE_URL_READONLY` and `ADMIN_API_TOKEN` as server-side environment variables; and
point the frontend at the API instead of the static snapshot. Keys never go in `NEXT_PUBLIC_*`
variables.
