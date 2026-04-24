import Foundation

struct HealthResponse: Decodable {
    let ok: Bool
    let apiKeyEnabled: Bool

    enum CodingKeys: String, CodingKey {
        case ok
        case apiKeyEnabled = "api_key_enabled"
    }
}

struct StatsResponse: Decodable {
    let totalCaptures: Int
    let indexedAvailable: Bool
    let latestCaptureAt: String?

    enum CodingKeys: String, CodingKey {
        case totalCaptures = "total_captures"
        case indexedAvailable = "indexed_available"
        case latestCaptureAt = "latest_capture_at"
    }
}

enum BackendState: Equatable {
    case checking
    case online
    case offline(String)

    var label: String {
        switch self {
        case .checking:
            return "Checking"
        case .online:
            return "Online"
        case .offline:
            return "Offline"
        }
    }
}
