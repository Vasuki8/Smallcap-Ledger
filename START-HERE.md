# Start Smallcap Ledger

**For a website that updates while your computer is off, follow GITHUB-SETUP.md.** This GitHub-ready edition also includes local Windows mode.

## Windows local mode

1. Extract the entire ZIP to a normal folder, for example `Documents\Smallcap-Ledger`. Do not run files from inside the ZIP.
2. If uv is not installed, use its official PowerShell installation command:

   ```powershell
   powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
   ```

3. Close and reopen PowerShell after installing uv. Double-click `START-WINDOWS.cmd`.
4. uv installs Python 3.12 and locked dependencies if needed. The first local launch restores the included historical archive. No virtual-environment activation is needed.
5. Open `http://127.0.0.1:8765` if the browser does not open automatically. Keep the command window open for local updates. Use Ctrl+C to stop.

The `data` folder contains your growing local archive. Back it up before replacing it. Local records are separate from the GitHub release archive; the GitHub setup guide explains how to publish imported additions.

Use plan/option filters to show all variants, including IDCW. Each fund has Overview, Performance, Portfolio, Fees & history, and Fund communications pages. Missing figures are explicitly unavailable.

## PowerShell / VS Code

Open a terminal in this project's folder:

```powershell
uv run --frozen python -m tracker
```

Optional: `uv run --frozen python -m tracker --no-browser --port 8766`.

Use this project's `pyproject.toml` and `uv.lock`. You do not need `uv init`, pip or a Python 3.14 environment. The launcher also checks `%USERPROFILE%\.local\bin\uv.exe` if uv is missing from PATH.

On macOS/Linux, use `sh start.sh`. Local mode runs on your computer; GitHub mode updates independently online.
