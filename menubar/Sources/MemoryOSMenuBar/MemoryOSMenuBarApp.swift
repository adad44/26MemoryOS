import AppKit
import SwiftUI

@main
struct MemoryOSMenuBarApp: App {
    @NSApplicationDelegateAdaptor(MemoryOSAppDelegate.self) private var appDelegate

    var body: some Scene {
        Settings {
            EmptyView()
        }
    }
}

@MainActor
final class MemoryOSAppDelegate: NSObject, NSApplicationDelegate, NSMenuDelegate {
    private let client = MemoryOSClient()
    private var statusItem: NSStatusItem?
    private let menu = NSMenu()
    private var hostingView: NSView?

    func applicationDidFinishLaunching(_ notification: Notification) {
        configureStatusItem()
        configureMenu()
        Task { await client.refresh() }
    }

    private func configureStatusItem() {
        let item = NSStatusBar.system.statusItem(withLength: NSStatusItem.squareLength)
        statusItem = item
        item.menu = menu

        guard let button = item.button else {
            return
        }
        button.image = makeStatusImage()
        button.imagePosition = .imageOnly
        button.imageScaling = .scaleProportionallyDown
        button.toolTip = "MemoryOS"
    }

    private func configureMenu() {
        menu.delegate = self
        menu.removeAllItems()

        let view = MenuBarView()
            .environmentObject(client)
        let host = NSHostingView(rootView: view)
        host.frame = NSRect(x: 0, y: 0, width: 320, height: 430)
        hostingView = host

        let item = NSMenuItem()
        item.view = host
        menu.addItem(item)
    }

    func menuWillOpen(_ menu: NSMenu) {
        Task { await client.refresh() }
        client.refreshPermissions()
    }

    private func makeStatusImage() -> NSImage? {
        guard let image = MemoryOSLogoImage.load() else {
            return nil
        }
        image.size = NSSize(width: 17, height: 17)
        image.isTemplate = true
        return image
    }
}
