import Foundation

final class WindowCapturePoller {
    private let config: MemoryOSConfig
    private let database: Database
    private let extractor: AccessibilityTextExtractor
    private var timer: Timer?
    private var lastDigest: String?

    init(config: MemoryOSConfig, database: Database, extractor: AccessibilityTextExtractor) {
        self.config = config
        self.database = database
        self.extractor = extractor
    }

    func start() {
        timer = Timer.scheduledTimer(withTimeInterval: config.pollIntervalSeconds, repeats: true) { [weak self] _ in
            self?.poll()
        }
        timer?.tolerance = 1.5
        poll()
    }

    func stop() {
        timer?.invalidate()
        timer = nil
    }

    private func poll() {
        guard extractor.isTrusted else {
            fputs("MemoryOS is waiting for Accessibility permission.\n", stderr)
            return
        }
        guard let snapshot = extractor.captureFrontmostWindow() else { return }

        let digest = TextDigest.stable([
            snapshot.appName,
            snapshot.windowTitle ?? "",
            snapshot.content
        ].joined(separator: "|"))

        guard digest != lastDigest else { return }
        lastDigest = digest

        database.insertCapture(CaptureRecord(
            timestamp: Date(),
            appName: snapshot.appName,
            windowTitle: snapshot.windowTitle,
            content: snapshot.content,
            sourceType: .accessibility,
            url: nil,
            filePath: nil
        ))
    }
}
