# Phase 5 Mac Menu Bar App

Phase 5 adds a SwiftUI menu bar app and launch-agent packaging for login startup.

## Build

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

## Run

Start the backend and web UI first:

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
- Open Search.
- Pause/Resume Capture.
- Refresh Index.
- Open backend API docs.
- Backend URL, web URL, and API key settings.
- Quit.

## Pause Capture

The menu bar app toggles:

```text
~/Library/Application Support/MemoryOS/capture.paused
```

The Swift daemon checks this flag before saving Accessibility and file captures. When the flag exists, capture is paused. Removing it resumes capture.

## Launch Agents

Install daemon launch at login:

```sh
scripts/install_daemon_launch_agent.sh
```

Uninstall daemon launch agent:

```sh
scripts/uninstall_daemon_launch_agent.sh
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
~/Library/LaunchAgents/com.memoryos.menubar.plist
```

## Notes

The menu bar app is packaged with `LSUIElement=true`, so it runs as a menu bar utility instead of a normal Dock app.

The local Swift Package Manager manifest path is present for future Xcode/SPM workflows, but `scripts/build_menubar.sh` uses direct `swiftc` compilation because the local Command Line Tools SwiftPM manifest linker is unreliable on this machine.
