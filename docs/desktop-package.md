# Desktop Packaging Notes (Electron + React UI)

This project can be packaged as a desktop application using Electron as the desktop shell and `apps/dsa-web`'s React UI as the interface.

## Architecture Notes

- React UI (built with Vite) is served by a local FastAPI service
- Electron automatically starts the backend service on launch, waits for `/api/health` to be ready, then loads the UI
- Windows portable/installer mode stores user configuration `.env` and database in the same directory as the exe; macOS packaged version uses the Electron user data directory for runtime configuration
- The desktop client automatically selects an available port from `8000-8100` on the local machine and synchronizes the actual port to the built-in backend; the desktop client does not rely on `.env`'s `WEBUI_PORT` for the window connection address, preventing Electron from waiting for the old port after users change it

## Local Development

One-click startup (development mode):

```bash
powershell -ExecutionPolicy Bypass -File scripts\run-desktop.ps1
```

Or manually:

1) Build React UI (output to `static/`)

```bash
cd apps/dsa-web
npm install
npm run build
```

2) Start Electron application (automatically starts backend)

```bash
cd apps/dsa-desktop
npm install
npm run dev
```

On first run, `.env` is automatically copied from `.env.example`.

## Packaging (Windows)

### Prerequisites

- Node.js 18+
- Python 3.10+
- Windows developer mode enabled (electron-builder needs to create symlinks)
  - Settings > Privacy & Security > Developer Options > Developer Mode

### One-Click Packaging

```bash
powershell -ExecutionPolicy Bypass -File scripts\build-all.ps1
```

This script executes sequentially:
1. Build React UI
2. Install Python dependencies
3. PyInstaller packages the backend
4. electron-builder packages the desktop application

Current Windows installers use the NSIS wizard-based installation flow, supporting only current user installation with administrator elevation disabled; users can manually select the target directory during installation (e.g., non-C: drive). The installer prevents selection of system-protected directories like `Program Files` and `Windows` via the NSIS `.onVerifyInstDir` callback—the "Next" button is automatically disabled when these paths are selected. After installation, the desktop client still follows existing logic to generate/read `.env`, `data/stock_analysis.db` (including `data/stock_analysis.db-wal` / `data/stock_analysis.db-shm`), and `logs/desktop.log` alongside the installation directory. It's recommended to use the default per-user installation directory. If you don't want to install, you can continue distributing the `win-unpacked` no-install package.

## GitHub CI Automated Packaging and Release Publishing

The repository supports automated desktop building and uploading to GitHub Releases via GitHub Actions:

- Workflow: `.github/workflows/desktop-release.yml`
- Trigger methods:
  - Automatically triggered after pushing a semantic version tag (e.g., `v3.2.12`)
  - Manually triggered from the Actions page with specified `release_tag`
- Artifacts:
  - Windows installer: Release attachment and local `apps/dsa-desktop/dist/` unified as `daily-stock-analysis-windows-installer-<tag>.exe`
  - Windows auto-update metadata: Release attachment additionally preserves `latest.yml` and `*.blockmap` for installed desktop version background download and update verification; regular users don't need to manually download these metadata. After download completion, when the user confirms "restart to install," the desktop client stops the built-in backend, backs up runtime files, and executes the installer in silent mode.
  - Windows no-install package: `daily-stock-analysis-windows-noinstall-<tag>.zip`
  - macOS Intel: `daily-stock-analysis-macos-x64-<tag>.dmg`
  - macOS Apple Silicon: `daily-stock-analysis-macos-arm64-<tag>.dmg`

Recommended release process:

1. Merge code to `main`
2. Auto-tag workflow generates version (or manually create tag)
3. `desktop-release` workflow automatically builds and attaches both platform installers to the corresponding GitHub Release

## Pre-Release Reproducible Verification (Desktop Update Pipeline)

The desktop auto-update pipeline depends on Windows NSIS build artifacts, `latest.yml`, and `*.blockmap` metadata. Current desktop CI does not cover the `desktop-release` packaged artifact publishable pipeline; before submitting, it's recommended to supplement with the following local verification:

Note: This checklist focuses on Windows NSIS installed version and `electron-updater` release metadata. Current Linux environments cannot directly produce Windows installers and updater metadata (`latest.yml` / `*.blockmap`); this pipeline needs to be verified on a Windows release executor or local Windows environment.

If the above verification cannot be completed in a non-Windows environment, the PR acceptance notes must clearly state the Windows release pipeline reviewer, review time window, and `desktop-release` artifact check results (release/tag and `daily-stock-analysis-windows-installer-<tag>.exe`, `latest.yml`, `*.blockmap` version consistency and downloadability).

1. First build Web static artifacts (desktop main window and settings page entry depend on these)

```bash
cd apps/dsa-web
npm ci
npm run lint
npm run build
```

2. Return to desktop, supplement dependencies, run preload unit tests, then execute Electron packaging

```bash
cd ../dsa-desktop
npm ci
npm test
npm run build
```

In the Windows release verification environment, you can additionally run:

```powershell
./scripts/verify-desktop-updater-artifacts.ps1 -ReleaseTag v$(node -p "require('./apps/dsa-desktop/package.json').version")
```

> When the current execution environment does not support generating Windows NSIS installers, the delivery notes must clearly state the platform limitation and require the designated Windows release pipeline reviewer to supplement this verification.

3. Check whether update metadata was produced

```bash
ls -1 dist | sort
ls -1 dist/*.yml dist/*.blockmap 2>/dev/null || true
```

4. Force align version and release attachments (can be verified on Windows environment or executor that can produce NSIS artifacts)

```bash
RELEASE_TAG="v$(node -p \"require('./package.json').version\")"
REPO="ZhuLinsen/daily_stock_analysis"

for f in dist/*latest.yml dist/*.blockmap dist/daily-stock-analysis-windows-installer-*.exe; do
  [ -f \"$f\" ] && echo \"[FOUND] $f\"
done

if [ -f dist/latest.yml ]; then
  echo \"---- latest.yml version fragment ----\"
  grep -E \"^version:|^files:|^sha512:\" dist/latest.yml
fi

echo \"---- Release manifest (manual verification) ----\"
echo \"Release Tag: $RELEASE_TAG\"
echo \"Release URL: https://github.com/$REPO/releases/tag/$RELEASE_TAG\"
echo \"Verify attachments include:\"
echo \"- daily-stock-analysis-windows-installer-*.exe\"
echo \"- latest.yml\"
echo \"- *.blockmap\"
echo \"And ensure latest.yml version matches tag semantic version, path/url matches installer attachment name\"
```

5a. Recommended "verifiable output" to record in PR description (Windows):

```bash
echo "release-tag=${RELEASE_TAG}"
echo "latest.yml version:"
grep -E "^version:" dist/latest.yml
echo "latest.yml files:"
sed -n '1,80p' dist/latest.yml
echo "packaging artifacts:"
ls -1 dist/*.yml dist/*.blockmap dist/*installer*.exe 2>/dev/null | sort
```

Windows release pipeline verification checklist (executed by release team/maintainer after PR):

- release/tag version matches `daily-stock-analysis-windows-installer-<tag>.exe`;
- `latest.yml`, `daily-stock-analysis-windows-installer-<tag>.exe`, `*.blockmap` appear in sync with the same tag and are downloadable;
- `latest.yml` `version` matches Release tag semantically (compared after removing `v` prefix), and `path` / `files.url` matches installer attachment name;
- If the above files are missing or `release-tag` doesn't match, flag as blocking and supplement the `desktop-release` packaging pipeline.

5. Windows/NSIS artifact and release attachment consistency should be manually verified in a Windows environment (can manually trigger the release process), and runtime file retention verified after upgrade:

   1. Before and after installation, record SHA256 of `.env`, `data/stock_analysis.db`, `data/stock_analysis.db-wal`, `data/stock_analysis.db-shm`, `logs/desktop.log` in the installation directory;
   2. Confirm that after the next desktop startup, the above files still exist and match pre-installation records;
   3. If inconsistent, check whether `.dsa-desktop-update-backup` in the user data directory was fully cleaned after application exit, and combine with latest logs for investigation.

Windows platform is recommended to use PowerShell:

```bash
Get-FileHash .env,data\\stock_analysis.db,data\\stock_analysis.db-wal,data\\stock_analysis.db-shm,logs\\desktop.log -Algorithm SHA256
```

Note: The application has stopped the built-in backend before "restart to install" in the Windows NSIS installed version, backed up the above runtime files alongside the installation directory, and executed the update installer in silent mode, to prevent the installation wizard from preemptively overwriting the still-running desktop process while reducing file loss risk during the update process; if recovery fails, the desktop client displays the update installation error and retains a manual download path for rollback handling. This fix only changes the Windows update installation pipeline and built-in backend process lifecycle handling, without affecting settings save semantics, model runtime cleanup strategy, or configuration migration behavior.

### Step-by-Step Packaging

1) Build React UI

```bash
cd apps/dsa-web
npm install
npm run build
```

2) Package Python backend per existing scripts (scripts have built-in AlphaSift dependency collection)

- Windows:

```bash
powershell -ExecutionPolicy Bypass -File scripts\build-backend.ps1
```

- macOS:

```bash
bash scripts/build-backend-macos.sh
```

This script runs `--collect-all alphasift` after installing dependencies and verifies that `alphasift.dsa_adapter` can be imported in the packaged artifacts, preventing step-by-step commands from missing built-in AlphaSift modules.

3) Package Electron desktop application

```bash
cd apps/dsa-desktop
npm install
npm run build
```

Packaged artifacts are located in `apps/dsa-desktop/dist/`. The Windows installer generates `daily-stock-analysis-windows-installer-<tag>.exe` with selectable installation directory in the wizard.

## Directory Structure

Windows installer mode: The installer supports only current user installation with administrator elevation disabled, allowing users to select installation directory in the wizard; the installer prevents selection of system-protected directories like `Program Files` and `Windows` at the installer level ("Next" button automatically disabled when selected). After installation, the application generates/reads `.env`, `data/stock_analysis.db` (including `data/stock_analysis.db-wal` / `data/stock_analysis.db-shm`), and `logs/desktop.log` alongside the installation directory. Please keep the default per-user installation location or select another user-writable directory.

`win-unpacked` no-install mode directory structure:

```
win-unpacked/
  Daily Stock Analysis.exe    <- Double-click to launch
  .env                        <- User configuration (auto-generated on first launch)
  data/
    stock_analysis.db         <- Database main file
    stock_analysis.db-wal     <- WAL log file (update backup/restore)
    stock_analysis.db-shm     <- WAL shared meta file (update backup/restore)
  logs/
    desktop.log               <- Runtime logs
  resources/
    .env.example              <- Configuration template
    backend/
      stock_analysis.exe      <- Backend service
```

## Configuration File Notes

- Windows desktop `.env` is placed in the same directory as the exe
- macOS packaged `.env`, `data/`, and `logs/` are placed in the Electron user data directory to avoid loss when replacing `.app`
- Auto-generated from `.env.example` on first launch
- When upgrading from an old version, if the old `.app` bundle's internal `.env`, `data/stock_analysis.db`, or log files are still accessible, the new version automatically migrates them to the user data directory when target files don't exist; existing target files are not overwritten
- Users need to edit `.env` to configure:
  - `GEMINI_API_KEY` or `OPENAI_API_KEY`: Required for AI analysis
  - `STOCK_LIST`: Watchlist (comma-separated)
  - Other optional configurations, see `.env.example`

### Configuration Backup / Restore `.env`

- Both WebUI and desktop can see "Export .env" and "Import .env" buttons from `System Settings -> Configuration Backup`
- WebUI non-desktop runtime needs admin authentication enabled and login completed; buttons are disabled when authentication is not enabled, API returns `403`
- "Export .env" exports the currently **saved** `.env` backup file; local drafts not yet saved on the page will not be exported
- "Import .env" reads key-value pairs from the backup file and merges them into the current configuration, triggering immediate configuration reload after import
- Import is "key-level override" rather than whole-file replacement: keys present in the backup file override current values, keys not present are kept unchanged
- If the current page has unsaved drafts, confirmation is prompted before import to avoid mixing local drafts with saved configuration
- When Web default `ADMIN_AUTH_ENABLED=false`, the settings page displays buttons as disabled and prompts to enable admin authentication first; desktop is unaffected by this configuration and can directly use configuration backup/restore capabilities.

> Recommendation: macOS users upgrading from old versions can still perform an "Export .env" before upgrading as insurance; if the old `.app` has been entirely replaced, old bundled files cannot be recovered from nothing and can only be restored via backup import.

### Settings Page Version Information

- "Desktop Version" in `System Settings -> Version Information` is provided by Electron main process's `app.getVersion()` and exposed to the frontend via preload bridge
- Development mode `npm run dev` and packaged mode `npm run build` / installer all reuse the same version injection pipeline, no longer maintaining an independent hardcoded version number in `preload.js`
- `README.md` continues to retain installation and runtime entry notes; these desktop runtime details are maintained in this dedicated document to avoid beginner documentation bloat

### LAN Access to Windows Desktop WebUI

- Desktop defaults to `WEBUI_HOST=127.0.0.1` allowing only local access, preventing unintended backend service exposure after installation
- To allow other devices on the same LAN to access, set `WEBUI_HOST=0.0.0.0` in the desktop `.env` or `System Settings -> WebUI Listen Address`, save and restart the desktop
- Desktop automatically selects an available port from `8000-8100` and passes it to the backend; commonly it's still `8000`, but if the port is occupied, you can see `Using port ...` and `Backend launch command=...` in `logs/desktop.log`
- Windows firewall or server security groups still need to allow the actual listening port; before external exposure, it's recommended to also enable `ADMIN_AUTH_ENABLED`
- Even when the backend binds to `0.0.0.0`, the desktop window itself still uses a locally accessible address for health checks and page loading

### Desktop Update Reminders

- After the main interface loads, the application checks GitHub Releases for the latest official version in the background and performs semantic version comparison with current `app.getVersion()`
- Windows NSIS installed version automatically downloads new versions via built-in GitHub update source; after download, a one-time reminder pops up, and after user confirmation, silently restarts and installs
- Auto-update silent installation reuses the current installation directory; if users selected a non-default or space-containing directory during installation, subsequent auto-updates still overwrite the same directory
- "Desktop Update" area in `System Settings -> Version Information` allows manual update checking; if update is downloaded, "restart to install" action is displayed
- Windows no-install package, development mode, and macOS DMG maintain the "reminder + jump to download page" compatibility path, not blocking desktop startup on network failure
- Version check failure, GitHub API timeout, update metadata missing, or download/installation exceptions are logged to `logs/desktop.log`, with error state displayed during manual checking on the settings page

## FAQ

### "Preparing backend..." displayed indefinitely after startup

1. Check `logs/desktop.log` for error messages
2. Confirm `.env` file exists and is configured correctly
3. Confirm ports 8000-8100 are not occupied; desktop automatically selects one available port without needing to manually change `WEBUI_PORT` via `.env`
4. If logs show Electron is waiting on a different port than the backend is actually listening on, prioritize upgrading to a version with the desktop port synchronization fix

### ModuleNotFoundError on backend startup

A module was missing during PyInstaller packaging; add `--hidden-import` in `scripts/build-backend.ps1`.

### Blank UI loading

Confirm `static/index.html` exists; if not, rebuild the React UI.

### macOS Configuration Migration After Upgrade

Old versions wrote runtime `.env`, database, and logs inside the `.app` bundle. New versions use the Electron user data directory, with a one-time migration when old `.app` bundle files are still accessible. The migration rule is "copy only when target doesn't exist," avoiding overwriting configurations already saved in the new version.

If the old `.app` has been entirely replaced, old bundled `.env` cannot be auto-recovered by the new version. In this case, use the `.env` exported before upgrading to manually import from `System Settings -> Configuration Backup`; after completing one migration or reconfiguration, subsequent versions continue using the user data directory without loss on `.app` replacement.

## Distribution to Users

Windows distribution now has two methods:

1. Installer: Distribute `apps/dsa-desktop/dist/daily-stock-analysis-windows-installer-<tag>.exe`; users can select their target directory during installation
2. No-install package: Package the entire `apps/dsa-desktop/dist/win-unpacked/` folder for users

Using the `win-unpacked` no-install package, users only need to:

1. Extract the folder
2. Edit `.env` to configure API Key and stock list
3. Double-click `Daily Stock Analysis.exe` to launch
