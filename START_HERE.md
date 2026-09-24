# Fresh Windows setup — repaired edition

1. Stop your old ResolveIQ server using Ctrl+C. Keep your old folder as a backup.
2. Extract this ZIP into a new folder. Do not copy the old data folder during this fresh setup.
3. Open the extracted folder containing run.py in VS Code.
4. Open Terminal > New Terminal and run `.\start_windows.bat`.
5. Open SETUP_CODE.txt in this folder after startup. Copy only the code on the second line.
6. Open http://127.0.0.1:8000. Name: Amogha C V. Username: amogha_cv.
7. Paste the actual setup code and choose your own password (15+ characters).
8. Click Create administrator. Later logins use your username and password.

No fixed setup code or default password exists. Codes like 1929 will not work.
The setup code changes on restart. Close and reopen SETUP_CODE.txt after a restart.
If you get 'Too many attempts', wait 15 minutes before trying the correct code.
Do not upload SETUP_CODE.txt or the data folder to GitHub.
The ZIP includes all current project features and sample incidents, but no personal database or accounts.
Your old saved incidents remain in your old project folder.

---

# ResolveIQ v2 — start here (Windows + VS Code)

## Upgrade safely from your existing ResolveIQ

1. In the OLD server terminal, press **Ctrl+C** and wait for shutdown. Close the old browser tab.
2. Keep your old project folder as a backup. Extract the updated ZIP into a **different folder**, for example `Desktop\ResolveIQ_v2`.
3. To preserve your incidents, copy the entire OLD `data` folder into the NEW `resolveiq` folder. Do this only after the old server has stopped. Do not replace or delete your old backup. If you want a fresh demo instead, skip copying data.
4. In VS Code choose **File → Open Folder** and select the NEW `resolveiq` folder containing `run.py` and `start_windows.bat`.
5. Choose **Terminal → New Terminal**, then run:

```powershell
.\start_windows.bat
```

The launcher creates a fresh virtual environment, installs the packages, and starts two localhost services. It preserves an existing database and adds the v2 fields automatically. The compiled React frontend is included, so Node.js is not needed just to run it.

## First login

1. Wait for startup. Open **SETUP_CODE.txt** in the project folder. Copy only the code on its second line. It is also printed in the terminal.
2. Open **http://127.0.0.1:8000**.
3. On **Create your workspace**, enter your name, the setup code, a username such as `amogha_cv` (no @ or spaces), and a password of at least **15 characters**. A memorable passphrase is easier than random letters.
4. Click **Create administrator**. Keep your password somewhere safe. There is no default password.
5. On later starts, use your username and password. Setup is disabled after the first account is created. If you restart before completing setup, use the newly printed code.

Your first account owns this local workspace, including incidents copied from v1. Keep the terminal open. **Ctrl+C stops both services.** No API key or paid AI subscription is required for the main app.

## Demonstrate real local monitoring

1. Open **Live monitoring**. Within a few seconds, the checkout demo should report **Up**.
2. Click **Simulate database failure**. This changes only the included synthetic service, never your laptop's database or another application.
3. Wait about **10–15 seconds**. Two consecutive failed HTTP probes create one incident. Additional failures update the same incident rather than making duplicates.
4. Click **Open linked incident**. Inspect the error-line evidence and similar historical fixes.
5. Return to **Live monitoring** and click **Restore healthy service**.
6. Wait for **Up**. Reopen the linked incident to load its latest version. Its history records HTTP recovery; it does not automatically close.
7. Add a note such as: `Demo: restored the isolated checkout service and verified its successful HTTP health probe. Reviewed the recorded recovery event.`
8. Choose **Resolved → Save changes**. Closure is blocked while the monitor is down, paused, or stale.
9. Export JSON. This gives you a meaningful end-to-end demo backed by actual HTTP responses.

The fixed monitor target is `http://127.0.0.1:8010/health`. Arbitrary external URLs are intentionally unsupported in this version. The monitor uses five-second intervals after each probe, retains up to 720 checks, and the page polls every five seconds. Availability is the percentage of successful retained probes, not a production SLA.

## Create team accounts

1. As Admin, open **Team & access**.
2. Create an **Engineer** and a **Viewer** with separate usernames and passwords (15+ characters).
3. Share credentials privately; the app does not send email invitations.
4. Open a Chrome Incognito window at the SAME address and sign in as Viewer. The Viewer can read/export but cannot change incidents or run fault scenarios.
5. Sign in as Engineer to create/update incidents and assign them to active Engineers or Admins.
6. Admins can change other members' roles and deactivate accounts. Those actions revoke the affected member's sessions. Users can change their own password under Team & access.

All members belong to one shared local workspace. This is not multi-tenant software, and the provided launcher does not expose your app over the internet or LAN.

## Optional real AI explanations (Ollama)

The core app works without this. This optional feature generates explanations with a locally installed language model; it does not replace rule evidence or human verification.

1. Install Ollama from **https://ollama.com/download** and start it. Model downloads need internet and several GB of storage; speed depends on your laptop.
2. In a new terminal, run:

```text
ollama pull qwen2.5:3b
```

3. Stop ResolveIQ with Ctrl+C. In a **PowerShell** terminal inside the new project folder, run:

```powershell
$env:RESOLVEIQ_AI="1"
$env:RESOLVEIQ_MODEL="qwen2.5:3b"
.\start_windows.bat
```

If your terminal says **cmd**, use these instead:

```cmd
set RESOLVEIQ_AI=1
set RESOLVEIQ_MODEL=qwen2.5:3b
start_windows.bat
```

4. Open an incident with a supported error pattern. Under Investigation, scroll to **Local AI explanation → Explain this evidence**.
5. The backend sends bounded matched evidence to Ollama on `127.0.0.1:11434`; no hosted AI service is called. Review the answer and its cited lines. Generated statements may be wrong, and log instructions are treated as untrusted data. No commands are executed.

Only the adapter contract is tested automatically with a mock. A real model was not installed in the build environment. If the model is unavailable or slow, a clear error appears and rule-based analysis remains available.

## Run without the Windows launcher

Python 3.11+ is required. If `py` is unavailable but `python` works:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe run.py
```

For Linux/macOS, use `.venv/bin/python` instead. Open the folder containing `run.py` before running the commands.

## Run with F5

After installing dependencies, install the VS Code Python and Python Debugger extensions. Select `.venv\Scripts\python.exe` using **Python: Select Interpreter**. Stop an existing server, then press **F5 → ResolveIQ: launch both services**.

## Edit the React frontend

Install Node.js 22+ if you want to edit the interface. Stop the server and restart it with development origin support in PowerShell:

```powershell
$env:RESOLVEIQ_DEV="1"
.\start_windows.bat
```

In a second terminal:

```powershell
cd frontend
npm ci
npm run dev
```

Open `http://127.0.0.1:5173`. Use the same hostname consistently; do not switch between localhost and 127.0.0.1 while signing in. After edits run `npm run build` from `frontend`, restart ResolveIQ, and open port 8000. Run without `RESOLVEIQ_DEV` for the normal compiled version.

## Troubleshooting

- **`start_windows.bat` not recognized:** your terminal is in the wrong folder. Open the folder containing that file. In VS Code you can right-click that folder and choose **Open in Integrated Terminal**.
- **Port 8000 or 8010 already in use:** stop the old ResolveIQ terminal with Ctrl+C. Do not start two copies against the same database.
- **Login page does not appear:** confirm the new folder is running, then press Ctrl+Shift+R in Chrome.
- **Setup code rejected:** copy the current terminal's code, not a code from an earlier launch.
- **Too many login attempts:** wait 15 minutes. There is no email password-reset flow in this local edition.
- **Incident changed / 409:** another user or monitor updated it. Copy your unsaved note, reopen the incident, and apply your edit to the latest version.
- **Demo service unavailable:** start with `run.py` or the launcher so both services get the same private control token. Starting only `backend.main` is insufficient for the Failure lab.
- **Monitor down:** check the server terminal; if you intentionally triggered a failure, use Restore healthy service.
- **AI unavailable:** check Ollama, model installation, and the environment flags above. It is optional.

This is a tested local portfolio application. Before public production hosting it still needs TLS, deployment-specific security review, stronger operational controls, load tests, backups, and a recovery plan. Do not publish the runtime `data` folder or real incident logs to GitHub.
