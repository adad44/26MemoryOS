import Foundation

struct MemoryOSConfig {
    let databasePath: String
    let pollIntervalSeconds: TimeInterval
    let maxFileCharacters: Int
    let watchedDirectories: [String]
    let allowedFileExtensions: Set<String>
    let blockedApps: Set<String>
    let ignoredHostFragments: [String]

    static func load() -> MemoryOSConfig {
        let home = FileManager.default.homeDirectoryForCurrentUser.path
        let dataDir = "\(home)/Library/Application Support/MemoryOS"
        try? FileManager.default.createDirectory(
            atPath: dataDir,
            withIntermediateDirectories: true
        )

        return MemoryOSConfig(
            databasePath: ProcessInfo.processInfo.environment["MEMORYOS_DB"]
                ?? "\(dataDir)/memoryos.db",
            pollIntervalSeconds: 8,
            maxFileCharacters: 2_000,
            watchedDirectories: [
                "\(home)/Documents",
                "\(home)/Desktop",
                "\(home)/Downloads"
            ],
            allowedFileExtensions: [
                "pdf", "md", "txt", "py", "js", "ts", "tsx", "jsx", "swift",
                "json", "yaml", "yml", "html", "css", "csv"
            ],
            blockedApps: [
                "1Password", "Keychain Access", "System Settings", "System Preferences"
            ],
            ignoredHostFragments: [
                "bank", "chase.com", "wellsfargo.com", "capitalone.com",
                "paypal.com", "venmo.com"
            ]
        )
    }
}
