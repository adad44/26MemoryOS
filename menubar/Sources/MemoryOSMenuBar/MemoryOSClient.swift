import AppKit
import Foundation

@MainActor
final class MemoryOSClient: ObservableObject {
    @Published var backendURL: String {
        didSet {
            UserDefaults.standard.set(backendURL, forKey: "backendURL")
        }
    }
    @Published var webURL: String {
        didSet {
            UserDefaults.standard.set(webURL, forKey: "webURL")
        }
    }
    @Published var apiKey: String {
        didSet {
            UserDefaults.standard.set(apiKey, forKey: "apiKey")
        }
    }
    @Published var state: BackendState = .checking
    @Published var stats: StatsResponse?
    @Published var isRefreshingIndex = false
    @Published var capturePaused = false

    private let session = URLSession.shared
    private let pauseFlagURL: URL

    init() {
        backendURL = UserDefaults.standard.string(forKey: "backendURL") ?? "http://127.0.0.1:8765"
        webURL = UserDefaults.standard.string(forKey: "webURL") ?? "http://127.0.0.1:5173"
        apiKey = UserDefaults.standard.string(forKey: "apiKey") ?? ""
        let supportURL = FileManager.default.homeDirectoryForCurrentUser
            .appendingPathComponent("Library/Application Support/MemoryOS", isDirectory: true)
        pauseFlagURL = supportURL.appendingPathComponent("capture.paused")
        capturePaused = FileManager.default.fileExists(atPath: pauseFlagURL.path)
    }

    func refresh() async {
        state = .checking
        do {
            let health: HealthResponse = try await request(path: "/health")
            guard health.ok else {
                state = .offline("Health check failed")
                return
            }
            stats = try await request(path: "/stats")
            state = .online
        } catch {
            state = .offline(error.localizedDescription)
        }
    }

    func refreshIndex() async {
        isRefreshingIndex = true
        defer { isRefreshingIndex = false }
        do {
            _ = try await request(
                path: "/refresh-index",
                method: "POST",
                body: ["backend": "tfidf"]
            ) as RefreshIndexResponse
            await refresh()
        } catch {
            state = .offline(error.localizedDescription)
        }
    }

    func openSearch() {
        open(urlString: webURL)
    }

    func openBackendDocs() {
        open(urlString: "\(backendURL)/docs")
    }

    func toggleCapturePaused() {
        do {
            try FileManager.default.createDirectory(
                at: pauseFlagURL.deletingLastPathComponent(),
                withIntermediateDirectories: true
            )
            if capturePaused {
                try? FileManager.default.removeItem(at: pauseFlagURL)
                capturePaused = false
            } else {
                try "paused\n".write(to: pauseFlagURL, atomically: true, encoding: .utf8)
                capturePaused = true
            }
        } catch {
            state = .offline(error.localizedDescription)
        }
    }

    private func open(urlString: String) {
        guard let url = URL(string: urlString) else { return }
        NSWorkspace.shared.open(url)
    }

    private func request<T: Decodable>(
        path: String,
        method: String = "GET",
        body: [String: String]? = nil
    ) async throws -> T {
        guard let url = URL(string: backendURL + path) else {
            throw URLError(.badURL)
        }
        var request = URLRequest(url: url)
        request.httpMethod = method
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        if !apiKey.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
            request.setValue(apiKey, forHTTPHeaderField: "X-MemoryOS-API-Key")
        }
        if let body {
            request.httpBody = try JSONEncoder().encode(body)
        }

        let (data, response) = try await session.data(for: request)
        guard let http = response as? HTTPURLResponse, (200..<300).contains(http.statusCode) else {
            throw URLError(.badServerResponse)
        }
        return try JSONDecoder().decode(T.self, from: data)
    }
}

private struct RefreshIndexResponse: Decodable {
    let indexedCount: Int
    let artifactPath: String

    enum CodingKeys: String, CodingKey {
        case indexedCount = "indexed_count"
        case artifactPath = "artifact_path"
    }
}
