import AppKit
import Foundation

final class AppSessionTracker {
    private let database: Database
    private var currentSession: AppSession?
    private var observers: [NSObjectProtocol] = []

    init(database: Database) {
        self.database = database
    }

    func start() {
        if let appName = NSWorkspace.shared.frontmostApplication?.localizedName {
            currentSession = database.startSession(appName: appName, at: Date())
        }

        let center = NSWorkspace.shared.notificationCenter
        observers.append(center.addObserver(
            forName: NSWorkspace.didActivateApplicationNotification,
            object: nil,
            queue: .main
        ) { [weak self] notification in
            guard let self else { return }
            let app = notification.userInfo?[NSWorkspace.applicationUserInfoKey] as? NSRunningApplication
            self.switchTo(appName: app?.localizedName ?? app?.bundleIdentifier ?? "unknown")
        })

        observers.append(center.addObserver(
            forName: NSWorkspace.screensDidSleepNotification,
            object: nil,
            queue: .main
        ) { [weak self] _ in
            self?.closeCurrentSession()
        })
    }

    func stop() {
        closeCurrentSession()
        let center = NSWorkspace.shared.notificationCenter
        observers.forEach { center.removeObserver($0) }
        observers.removeAll()
    }

    private func switchTo(appName: String) {
        closeCurrentSession()
        currentSession = database.startSession(appName: appName, at: Date())
    }

    private func closeCurrentSession() {
        if let currentSession {
            database.endSession(currentSession, at: Date())
        }
        currentSession = nil
    }
}
