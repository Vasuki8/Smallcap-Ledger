# Put Smallcap Ledger on GitHub

This project is prepared for free hosting in a **public repository on GitHub Free**. Your computer and browser can be off: GitHub runs the updater and publishes the resulting site. No deployment or active schedule exists until the setup below succeeds.

## First deployment

1. Extract `Smallcap-Ledger-GitHub.zip`. Open the extracted `Smallcap-Ledger` folder.
2. Sign in to [GitHub](https://github.com/new) and create a **public** repository called `smallcap-ledger`, with `main` as the default branch. Leave initial README, licence and gitignore options empty; the package supplies its own files.
3. Upload the **contents inside** the extracted folder to the repository root using **Add file → Upload files**. Include `README.md`, `pyproject.toml`, `tracker/`, `dist/`, `scripts/`, `bootstrap/` and `.github/workflows/daily.yml`. Do not upload only the ZIP or nest everything inside a second folder. Commit to `main`.
4. Open **Settings → Pages**. Under Build and deployment select **Source: GitHub Actions**.
5. Open **Actions** and enable workflows if prompted. Select **Update and publish small-cap tracker → Run workflow**. For a fast first deployment, uncheck **Fetch new public data before publishing** to use the included historical data. Leave the import field blank.
6. Wait for both `build` and `deploy` to succeed. If an automatic run failed before Pages was enabled, rerun it now.
7. Open the URL shown in **Settings → Pages**, normally `https://YOUR-USERNAME.github.io/smallcap-ledger/`.
8. Open a fund: AUM and expenses are at the top, the comparison chart is on Overview, and official publications are in Fund communications. Change Direct/Growth filters to All when you want every plan and IDCW option.

GitHub Desktop is an alternative to browser upload: add the extracted folder as a local repository, create its first commit, and publish it publicly. The `bootstrap` archive uses 20 MiB pieces, below GitHub's browser-upload limit. Keep every piece and `manifest.json` together.

No paid feed, external server, Cloudflare account, manually created API token or custom domain is required. The workflow uses GitHub's automatically supplied `GITHUB_TOKEN`. The repository, site and data archive are public. This tracker contains fund research, not your personal investment-account holdings.

## Daily midnight updates

The requested start is **00:00 IST, Asia/Kolkata**, every day. In `.github/workflows/daily.yml`:

```yaml
schedule:
  - cron: '30 18 * * *'
```

GitHub interprets cron in UTC. A run at 18:30 UTC starts at midnight on the following calendar date in India. India does not change clocks seasonally.

This is a requested start time, not guaranteed exact execution or publication at midnight. GitHub can queue, delay or occasionally skip a scheduled run, and collection/publishing takes time. AUM and portfolios change when the AMC publishes a report; weekends may have no new NAV. Figure dates, website build time and collection results are shown separately.

The daily workflow restores the latest **SQLite database checkpoint first**, checks NAV/history/fees/AUM/TRI/AMC publications, materializes only source files actually needed by the current operation, builds the website, saves a new database checkpoint plus any newly discovered source-file packs, and publishes Pages. Historical source packs are reused instead of rebuilding a multi-gigabyte cumulative ZIP. It uses a 40-minute collection budget. Completed records survive an interruption; unchecked publication pages are prioritized next time.

You do not need to visit the site to trigger it. For an extra collection, select **Actions → Run workflow** with the refresh box checked.

To change the time, edit the workflow cron and the visible timezone/schedule labels in `scripts/export_site.py` and `dist/app.js`. Account for seasonal UTC changes if using a daylight-saving timezone. The current default is midnight in India, not Canada.

GitHub can disable scheduled workflows in public repositories after 60 days without repository activity. Successful builds commit an actual collection audit to `deployment/update-status.json`. If runs stop, inspect Actions, re-enable a disabled workflow and check repository permissions. No separate reminder or monitoring service is configured.

## Where history is kept

Open **Releases → Smallcap Ledger historical archive** (`tracker-history`). The current `latest.json` uses archive **format 2** and identifies:

- one compact `database-…zip` containing `data/ledger.sqlite3`;
- reusable immutable `sources-…zip` packs containing retained original source files;
- the previous checkpoint metadata for rollback.

Normal daily runs restore the database first and download source packs only when their files are needed. Existing source packs are append-only and reused; newly archived hashes create new packs. This prevents every run from downloading and uploading the entire historical source archive.

Legacy `state-…zip` cumulative checkpoints are currently retained as rollback copies from the migration. Do not delete the `tracker-history` release/tag: it is the active history store. `bootstrap/` is only the initial seed and is not updated daily in git.

A failed download/checksum stops the build instead of resetting history. A failed deployment leaves the previous website online. If updating `latest.json` fails after new assets are uploaded, retry logic verifies and reuses already-uploaded source packs.

## Import official records yourself

1. Wait for the current workflow to finish. In a local project copy with GitHub CLI authenticated to the repository, run `uv run --frozen python scripts/github_state.py restore`. This reconstructs the current `data` folder from the database checkpoint and required source packs.
2. Start `START-WINDOWS.cmd` and use **Data & archive** to import official figures, portfolios, TRI data, complete IDCW distributions or AMC publications.
3. Close the tracker. In PowerShell inside the project:

   ```powershell
   uv run --frozen python scripts/github_state.py pack --path manual-additions.zip
   ```

4. Add `manual-additions.zip` as a new asset to the existing `tracker-history` release. Do not replace its existing files.
5. Run the workflow manually. Enter `manual-additions.zip` in the optional import-archive field. You can leave refresh off for a quicker import.
6. The workflow checks that your archive retains all current historical records and files. If a newer daily run added records after your download, the import can be rejected to prevent losing them. Start from the newer checkpoint and reapply the additions.

The local in-app backup is useful for local recovery; use the `pack` command above for workflow imports.

## Limits and troubleshooting

- GitHub Pages on Free requires a public repository. This project uses standard GitHub-hosted Actions runners for the public repository.
- Pages has a 1 GB published-site limit; this project applies a much lower static-site guard. GitHub release assets have a 2 GiB per-file limit. Source evidence is split into reusable packs and the changing SQLite checkpoint is stored separately, so normal daily checkpoint uploads remain small. Free unlimited retention is not promised.
- **Pages not enabled:** select GitHub Actions in Settings → Pages and rerun.
- **Resource not accessible by integration** or protected-branch push errors: inspect Actions permissions and branch rules. The workflow requests contents write, Pages write and OIDC permissions. Ask the repository owner for a permitted setup if organization policy restricts it.
- **Immutable archive release:** this project needs to update the pointer in `tracker-history`. Use a mutable archive release or adapt storage before enabling release immutability for this dedicated research-data repository.
- **Source 403/404, robots restriction or parse failure:** previous data remains with its original reporting date. Check the site's Update settings or workflow log for the affected source.
- **Generated-site validation failure:** inspect the error before replacing any data. The previous site and release remain available.

## References

- [GitHub Pages availability and limits](https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits)
- [Custom Pages workflows](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages)
- [Scheduled workflow behavior](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule)
- [Actions billing](https://docs.github.com/en/billing/concepts/product-billing/github-actions)
- [Release assets](https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases)

The live URL and active schedule will be established by your first successful deployment.
