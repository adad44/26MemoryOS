import CoreServices
import Foundation
import PDFKit

final class FileCaptureWatcher {
    private let config: MemoryOSConfig
    private let database: Database
    private var stream: FSEventStreamRef?
    private var recentlyCaptured: [String: Date] = [:]

    init(config: MemoryOSConfig, database: Database) {
        self.config = config
        self.database = database
    }

    func start() {
        var context = FSEventStreamContext(
            version: 0,
            info: Unmanaged.passUnretained(self).toOpaque(),
            retain: nil,
            release: nil,
            copyDescription: nil
        )

        let callback: FSEventStreamCallback = { _, info, count, eventPaths, _, _ in
            guard let info else { return }
            let watcher = Unmanaged<FileCaptureWatcher>.fromOpaque(info).takeUnretainedValue()
            let paths = unsafeBitCast(eventPaths, to: NSArray.self) as? [String] ?? []
            for index in 0..<min(count, paths.count) {
                watcher.handleChangedPath(paths[index])
            }
        }

        stream = FSEventStreamCreate(
            kCFAllocatorDefault,
            callback,
            &context,
            config.watchedDirectories as CFArray,
            FSEventStreamEventId(kFSEventStreamEventIdSinceNow),
            2.0,
            UInt32(kFSEventStreamCreateFlagFileEvents | kFSEventStreamCreateFlagUseCFTypes)
        )

        guard let stream else {
            fputs("Could not start FSEvents stream.\n", stderr)
            return
        }

        FSEventStreamScheduleWithRunLoop(stream, CFRunLoopGetMain(), CFRunLoopMode.defaultMode.rawValue)
        FSEventStreamStart(stream)
    }

    func stop() {
        guard let stream else { return }
        FSEventStreamStop(stream)
        FSEventStreamInvalidate(stream)
        FSEventStreamRelease(stream)
        self.stream = nil
    }

    private func handleChangedPath(_ path: String) {
        guard !FileManager.default.fileExists(atPath: config.pauseFlagPath) else {
            return
        }
        let url = URL(fileURLWithPath: path)
        guard shouldCapture(url) else { return }

        let now = Date()
        if let last = recentlyCaptured[path], now.timeIntervalSince(last) < 10 {
            return
        }
        recentlyCaptured[path] = now

        guard let content = readContent(from: url), content.count >= config.minCaptureCharacters else { return }
        database.insertCapture(CaptureRecord(
            timestamp: now,
            appName: "File System",
            windowTitle: url.lastPathComponent,
            content: content,
            sourceType: .file,
            url: nil,
            filePath: path
        ))
    }

    private func shouldCapture(_ url: URL) -> Bool {
        let filename = url.lastPathComponent
        guard !filename.hasPrefix(".") else { return false }
        guard !config.excludedPathFragments.contains(where: { url.path.contains($0) }) else {
            return false
        }

        var isDirectory: ObjCBool = false
        guard FileManager.default.fileExists(atPath: url.path, isDirectory: &isDirectory),
              !isDirectory.boolValue else {
            return false
        }

        let ext = url.pathExtension.lowercased()
        return config.allowedFileExtensions.contains(ext)
    }

    private func readContent(from url: URL) -> String? {
        if url.pathExtension.lowercased() == "pdf" {
            return readPDF(url)
        }

        guard let data = try? Data(contentsOf: url, options: [.mappedIfSafe]),
              !data.contains(0),
              let text = String(data: data.prefix(256_000), encoding: .utf8)
                ?? String(data: data.prefix(256_000), encoding: .ascii) else {
            return nil
        }

        return String(TextDigest.normalized(text).prefix(config.maxFileCharacters))
    }

    private func readPDF(_ url: URL) -> String? {
        guard let document = PDFDocument(url: url) else { return nil }
        var chunks: [String] = []
        for index in 0..<min(document.pageCount, 5) {
            if let text = document.page(at: index)?.string {
                chunks.append(text)
            }
        }
        return String(TextDigest.normalized(chunks.joined(separator: "\n")).prefix(config.maxFileCharacters))
    }
}
