# Deployment

MemoryOS is local-first. The intended development deployment runs all services on the user's Mac.

For a first local run, use the end-to-end [Quickstart](QUICKSTART.md).

## Local Services

Backend:

```sh
scripts/run_backend.sh
```

Web UI:

```sh
cd web
npm install
npm run dev
```

Daemon:

```sh
scripts/build_daemon.sh
daemon/.build/memoryos-daemon
```

Menu bar app:

```sh
scripts/build_menubar.sh
open menubar/dist/MemoryOS.app
```

## Login Startup

Install daemon:

```sh
scripts/install_daemon_launch_agent.sh
```

Install backend:

```sh
scripts/install_backend_launch_agent.sh
```

Install menu bar app:

```sh
scripts/install_menubar_launch_agent.sh
```

Uninstall:

```sh
scripts/uninstall_daemon_launch_agent.sh
scripts/uninstall_backend_launch_agent.sh
scripts/uninstall_menubar_launch_agent.sh
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
