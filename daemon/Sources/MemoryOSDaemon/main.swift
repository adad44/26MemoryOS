import Foundation

let config = MemoryOSConfig.load()

do {
    let database = try Database(path: config.databasePath)

    if CommandLine.arguments.contains("--stats") {
        let rows = database.captureCountsByApp()
        if rows.isEmpty {
            print("No captures yet.")
        } else {
            for (app, count) in rows {
                print("\(app): \(count)")
            }
        }
        exit(0)
    }

    print("MemoryOS daemon starting")
    print("Database: \(config.databasePath)")
    print("Watching: \(config.watchedDirectories.joined(separator: ", "))")

    let extractor = AccessibilityTextExtractor(blockedApps: config.blockedApps)
    extractor.requestTrustPromptIfNeeded()

    let sessions = AppSessionTracker(database: database)
    let windowPoller = WindowCapturePoller(
        config: config,
        database: database,
        extractor: extractor
    )
    let fileWatcher = FileCaptureWatcher(config: config, database: database)

    sessions.start()
    windowPoller.start()
    fileWatcher.start()

    signal(SIGINT) { _ in
        print("\nMemoryOS daemon stopping")
        CFRunLoopStop(CFRunLoopGetMain())
    }

    RunLoop.main.run()

    fileWatcher.stop()
    windowPoller.stop()
    sessions.stop()
} catch {
    fputs("\(error)\n", stderr)
    exit(1)
}
