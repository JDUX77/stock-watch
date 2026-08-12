# Deploying this as a web app (no local install needed)

This puts your dashboard on the internet at your own private URL
(something like `yourname-dashboard.streamlit.app`), so you just open it
in a browser on any device — no Python install, no terminal commands, ever
again after this one-time setup.

We'll use **Streamlit Community Cloud** — it's free, made by the same
people who make Streamlit, and doesn't need a credit card.

This whole setup takes about 15 minutes and only needs a web browser.

## Step 1: Create a GitHub account (skip if you already have one)

1. Go to https://github.com/signup and create a free account.

## Step 2: Create a private repository and upload the code

1. Once logged in, click the **+** icon top-right → **New repository**.
2. Name it something like `stock-dashboard`.
3. Set it to **Private** (important — this keeps your code, though not
   your secrets, from being publicly visible).
4. Click **Create repository**.
5. On the next page, click **"uploading an existing file"**.
6. Open the `stock-dashboard-web` folder on your computer and drag in
   every file and folder **except**:
   - `.env` (if you have one from local testing)
   - `.streamlit/secrets.toml` (if you have one)
   - the `data/` folder contents (empty cache files - not needed)
   - You CAN and should upload `.env.example` and `.streamlit/secrets.toml.example` — they contain no real secrets, just templates.
7. Scroll down and click **Commit changes**.

You don't need to install Git or use any command line for this — GitHub's
website lets you drag and drop files directly.

## Step 3: Deploy on Streamlit Community Cloud

1. Go to https://share.streamlit.io and sign in with your GitHub account.
2. Click **"Create app"** → **"Deploy a public app from GitHub"** (it'll
   still only be usable by people who know the URL, but choose "Private"
   under app visibility if you want to restrict who can open it).
3. Select your `stock-dashboard` repository, branch `main`, and set the
   main file path to `app.py`.
4. Before clicking Deploy, click **"Advanced settings"** → **Secrets**.
   Paste in your real credentials in this exact format:
   ```
   ANGEL_API_KEY = "your_real_api_key"
   ANGEL_CLIENT_ID = "your_real_client_id"
   ANGEL_MPIN = "your_real_mpin"
   ANGEL_TOTP_SECRET = "your_real_totp_secret"
   ```
   (See the main README for how to get these from Angel One if you
   haven't already.)
5. Click **Deploy**.

Streamlit Cloud will install everything automatically from
`requirements.txt` and give you a live URL in a minute or two.

## Important: your secrets stay safe

- The values you paste into the "Secrets" box in step 4 are stored
  securely by Streamlit Cloud and are **never** visible in your GitHub
  repository, even though the repo itself only needs to be private as an
  extra precaution.
- Anyone who doesn't know your app's secrets can't see your credentials
  even if they somehow found your app URL — they'd just see the (empty,
  until you click Refresh) dashboard, not your keys.
- If you ever need to change a credential, go to your app on
  share.streamlit.io → Settings → Secrets, edit it, and the app restarts
  automatically with the new values. No re-uploading files needed.

## Using the app day to day

- Just visit your app's URL — works from your phone, laptop, anyone's
  browser.
- Click "Refresh data now" once a day after market close, same as before.
- Free-tier Streamlit Cloud apps go to sleep after a period of no
  visitors and wake up automatically (takes ~30 seconds) the next time
  someone opens the link — this is normal, not a bug.

## Updating the app later

If you ever want to change the watchlist or any code:
1. Edit the file directly on GitHub's website (click the pencil icon on
   any file) and commit the change.
2. Streamlit Cloud automatically redeploys within a minute — no other
   steps needed.

## Troubleshooting

- **"Angel One login failed" after deploying**: double check the secrets
  you pasted in Step 4 exactly match your real credentials, with quotes
  around each value as shown.
- **App URL shows "This app has gone to sleep"**: just click "Wake it back
  up" — this happens after inactivity on the free tier, it's expected.
- **Changes not showing up**: make sure you committed the change on
  GitHub and check the "Manage app" logs on Streamlit Cloud for errors.
