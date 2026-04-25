# Phase 5 Mac Menu Bar App

Phase 5 adds a SwiftUI menu bar app and launch-agent packaging for login startup.

## Install

Normal users should run:

```sh
scripts/install_memoryos.sh
```

That builds the daemon and menu bar app, copies MemoryOS into `~/Library/Application Support/MemoryOS/app`, and registers launch agents.

## Build For Debugging

Build the daemon:

```sh
scripts/build_daemon.sh
```

Build the menu bar app bundle:

```sh
scripts/build_menubar.sh
```

Output:

```text
menubar/dist/MemoryOS.app
```

## Run For Debugging

Start the backend and web UI first, unless you already used the installer:

```sh
scripts/run_backend.sh
cd web && npm run dev
```

Open the menu bar app:

```sh
open menubar/dist/MemoryOS.app
```

## Menu Bar Controls

- Backend status.
- Capture count.
- Index readiness.
- Latest capture timestamp.
- Capture active/paused state.
- Setup panel for macOS permissions.
- Accessibility status and shortcut to the Accessibility privacy pane.
- Full Disk Access review shortcut for file capture.
- Screen Recording fallback status and request action.
- Open Search.
- Pause/Resume Capture.
- Refresh Index.
- Open backend API docs.
- Backend URL, web URL, and API key settings.
- Quit.

## Permission Onboarding

The menu bar app now includes a SwiftUI setup panel for local macOS permissions:

- Accessibility is required for `AXUIElement` active-window text capture. The setup panel checks `AXIsProcessTrusted()`, can trigger the macOS prompt, and opens the Accessibility privacy pane.
- Full Disk Access is recommended for broader file capture. macOS does not provide a public API to grant this automatically, so the setup panel opens the Full Disk Access privacy pane and performs a best-effort protected-folder read check.
- Screen Recording is listed as fallback-only. The current daemon does not use screenshot OCR for normal capture, but the setup panel can request/open the Screen Recording pane for future fallback work.

## Pause Capture

The menu bar app toggles:

```text
~/Library/Application Support/MemoryOS/capture.paused
```

The Swift daemon checks this flag before saving Accessibility and file captures. When the flag exists, capture is paused. Removing it resumes capture.

## Launch Agents

The one-command installer handles all launch agents. Individual commands are available for debugging.

Install daemon launch at login:

```sh
scripts/install_daemon_launch_agent.sh
```

Install backend launch at login:

```sh
scripts/install_backend_launch_agent.sh
```

Install web UI launch at login:

```sh
scripts/install_web_launch_agent.sh
```

Install scheduler launch at login:

```sh
scripts/install_scheduler_launch_agent.sh
```

Uninstall daemon launch agent:

```sh
scripts/uninstall_daemon_launch_agent.sh
```

Uninstall backend launch agent:

```sh
scripts/uninstall_backend_launch_agent.sh
```

Uninstall web UI launch agent:

```sh
scripts/uninstall_web_launch_agent.sh
```

Uninstall scheduler launch agent:

```sh
scripts/uninstall_scheduler_launch_agent.sh
```

Install menu bar launch at login:

```sh
scripts/install_menubar_launch_agent.sh
```

Uninstall menu bar launch agent:

```sh
scripts/uninstall_menubar_launch_agent.sh
```

The plist files are written to:

```text
~/Library/LaunchAgents/com.memoryos.daemon.plist
~/Library/LaunchAgents/com.memoryos.backend.plist
~/Library/LaunchAgents/com.memoryos.web.plist
~/Library/LaunchAgents/com.memoryos.scheduler.plist
~/Library/LaunchAgents/com.memoryos.menubar.plist
```

## Notes

The menu bar app is packaged with `LSUIElement=true`, so it runs as a menu bar utility instead of a normal Dock app.

The local Swift Package Manager manifest path is present for future Xcode/SPM workflows, but `scripts/build_menubar.sh` uses direct `swiftc` compilation because the local Command Line Tools SwiftPM manifest linker is unreliable on this machine.
