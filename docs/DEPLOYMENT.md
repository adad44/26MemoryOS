# Deployment

MemoryOS is local-first. The intended deployment runs all services on the user's Mac.

For a first local run, use the one-command installer from the repository root:

```sh
scripts/install_memoryos.sh
```

The installer copies app files to `~/Library/Application Support/MemoryOS/app`, creates the Python environment, builds the web UI and native apps, installs/starts Ollama, pulls `mistral` when needed, registers launch agents, and opens the web UI.

## Local Services

After install:

```text
Backend: http://127.0.0.1:8765
Web UI:  http://127.0.0.1:5173
```

For debugging only, run services directly from a checkout.

Backend debug server:

```sh
scripts/run_backend.sh
```

Web UI dev server:

```sh
cd web
npm install
npm run dev
```

Daemon debug run:

```sh
scripts/build_daemon.sh
daemon/.build/memoryos-daemon
```

Menu bar app debug run:

```sh
scripts/build_menubar.sh
open menubar/dist/MemoryOS.app
```

## Login Startup

Normal login startup is handled by `scripts/install_memoryos.sh`. To manage individual launch agents:

Install backend:

```sh
scripts/install_backend_launch_agent.sh
```

Install web UI:

```sh
scripts/install_web_launch_agent.sh
```

Install daemon:

```sh
scripts/install_daemon_launch_agent.sh
```

Install scheduler:

```sh
scripts/install_scheduler_launch_agent.sh
```

Install menu bar app:

```sh
scripts/install_menubar_launch_agent.sh
```

Uninstall:

```sh
scripts/uninstall_backend_launch_agent.sh
scripts/uninstall_web_launch_agent.sh
scripts/uninstall_daemon_launch_agent.sh
scripts/uninstall_scheduler_launch_agent.sh
scripts/uninstall_menubar_launch_agent.sh
```

## Installed App Path

Launch agents should run from:

```text
~/Library/Application Support/MemoryOS/app
```

Running launch agents directly from `~/Downloads` can be blocked by macOS privacy controls. The installer copies files into the app support path before registering launch agents.

## Ollama And Phase 7

The installer starts Ollama through Homebrew and pulls `mistral` unless `--skip-model-pull` or `--skip-ollama` is used. The Phase 7 scheduler runs every 6 hours through `com.memoryos.scheduler`.

Check scheduler status:

```sh
launchctl print gui/$(id -u)/com.memoryos.scheduler
```

## Optional API Key

```sh
MEMORYOS_API_KEY="dev-secret" scripts/run_backend.sh
```

Then set the same key in the web UI and menu bar settings.

## Web Hosting

The web UI can be deployed as a static Vite app, but it still talks to the local backend.

Build:

```sh
cd web
npm run build
```

Output:

```text
web/dist/
```

Set `VITE_API_URL` if the backend URL differs:

```sh
VITE_API_URL=http://127.0.0.1:8765 npm run build
```

## Distribution Notes

For local development, the unsigned app bundle is enough. For broader distribution:

- Add a proper Xcode project or package workflow.
- Sign the menu bar app.
- Notarize the app bundle.
- Provide a permissions onboarding flow for Accessibility and Screen Recording.
