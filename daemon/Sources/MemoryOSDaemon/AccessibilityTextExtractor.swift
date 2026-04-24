import ApplicationServices
import AppKit
import Foundation

struct AccessibilityWindowSnapshot {
    let appName: String
    let windowTitle: String?
    let content: String
}

final class AccessibilityTextExtractor {
    private let blockedApps: Set<String>
    private let maxDepth = 10
    private let maxNodes = 700

    init(blockedApps: Set<String>) {
        self.blockedApps = blockedApps
    }

    var isTrusted: Bool {
        AXIsProcessTrusted()
    }

    func requestTrustPromptIfNeeded() {
        guard !AXIsProcessTrusted() else { return }
        let options = [
            kAXTrustedCheckOptionPrompt.takeUnretainedValue() as String: true
        ] as CFDictionary
        _ = AXIsProcessTrustedWithOptions(options)
    }

    func captureFrontmostWindow() -> AccessibilityWindowSnapshot? {
        guard let app = NSWorkspace.shared.frontmostApplication else { return nil }
        let appName = app.localizedName ?? app.bundleIdentifier ?? "unknown"
        guard !blockedApps.contains(appName) else { return nil }

        let axApp = AXUIElementCreateApplication(app.processIdentifier)
        guard let focusedWindow = copyElementAttribute(axApp, kAXFocusedWindowAttribute) else {
            return nil
        }

        let title = copyStringAttribute(focusedWindow, kAXTitleAttribute)
        var chunks: [String] = []
        var nodesVisited = 0
        extractText(from: focusedWindow, depth: 0, nodesVisited: &nodesVisited, into: &chunks)

        let content = TextDigest.normalized(chunks.joined(separator: "\n"))
        guard content.count >= 20 else { return nil }
        return AccessibilityWindowSnapshot(appName: appName, windowTitle: title, content: content)
    }

    private func extractText(
        from element: AXUIElement,
        depth: Int,
        nodesVisited: inout Int,
        into chunks: inout [String]
    ) {
        guard depth <= maxDepth, nodesVisited < maxNodes else { return }
        nodesVisited += 1

        if isSensitive(element) {
            return
        }

        for attribute in [
            kAXTitleAttribute,
            kAXValueAttribute,
            kAXDescriptionAttribute,
            kAXHelpAttribute
        ] {
            if let text = copyTextAttribute(element, attribute) {
                let normalized = TextDigest.normalized(text)
                if normalized.count > 1 {
                    chunks.append(normalized)
                }
            }
        }

        for attribute in [kAXVisibleChildrenAttribute, kAXChildrenAttribute] {
            guard let children = copyChildrenAttribute(element, attribute), !children.isEmpty else {
                continue
            }
            for child in children {
                extractText(
                    from: child,
                    depth: depth + 1,
                    nodesVisited: &nodesVisited,
                    into: &chunks
                )
            }
            if attribute == kAXVisibleChildrenAttribute {
                break
            }
        }
    }

    private func isSensitive(_ element: AXUIElement) -> Bool {
        let role = copyStringAttribute(element, kAXRoleAttribute) ?? ""
        let subrole = copyStringAttribute(element, kAXSubroleAttribute) ?? ""
        return role.localizedCaseInsensitiveContains("secure")
            || subrole.localizedCaseInsensitiveContains("secure")
            || role == "AXSecureTextField"
    }

    private func copyTextAttribute(_ element: AXUIElement, _ attribute: String) -> String? {
        var value: CFTypeRef?
        guard AXUIElementCopyAttributeValue(element, attribute as CFString, &value) == .success,
              let value else {
            return nil
        }

        if let string = value as? String {
            return string
        }
        if let attributed = value as? NSAttributedString {
            return attributed.string
        }
        if let number = value as? NSNumber {
            return number.stringValue
        }
        return nil
    }

    private func copyStringAttribute(_ element: AXUIElement, _ attribute: String) -> String? {
        copyTextAttribute(element, attribute)
    }

    private func copyElementAttribute(_ element: AXUIElement, _ attribute: String) -> AXUIElement? {
        var value: CFTypeRef?
        guard AXUIElementCopyAttributeValue(element, attribute as CFString, &value) == .success,
              let value else {
            return nil
        }
        return (value as! AXUIElement)
    }

    private func copyChildrenAttribute(_ element: AXUIElement, _ attribute: String) -> [AXUIElement]? {
        var value: CFTypeRef?
        guard AXUIElementCopyAttributeValue(element, attribute as CFString, &value) == .success,
              let value else {
            return nil
        }
        return value as? [AXUIElement]
    }
}
