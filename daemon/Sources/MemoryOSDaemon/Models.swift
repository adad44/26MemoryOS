import Foundation

enum SourceType: String {
    case accessibility
    case file
    case browser
    case screenshot
}

struct CaptureRecord {
    let timestamp: Date
    let appName: String
    let windowTitle: String?
    let content: String
    let sourceType: SourceType
    let url: String?
    let filePath: String?
}

struct AppSession {
    let id: Int64
    let appName: String
    let startTime: Date
}
