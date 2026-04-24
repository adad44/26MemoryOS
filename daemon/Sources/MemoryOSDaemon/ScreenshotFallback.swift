import Foundation

final class ScreenshotFallback {
    func noteUnavailable(for appName: String) {
        fputs(
            "No accessibility text for \(appName). Screenshot OCR fallback is queued for the signed app target.\n",
            stderr
        )
    }
}
