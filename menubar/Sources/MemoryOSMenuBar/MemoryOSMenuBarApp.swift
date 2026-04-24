import SwiftUI

@main
struct MemoryOSMenuBarApp: App {
    @StateObject private var client = MemoryOSClient()

    var body: some Scene {
        MenuBarExtra {
            MenuBarView()
                .environmentObject(client)
                .task {
                    await client.refresh()
                }
        } label: {
            Label("MemoryOS", systemImage: iconName)
        }
        .menuBarExtraStyle(.window)
    }

    private var iconName: String {
        switch client.state {
        case .online:
            return "brain.head.profile"
        case .checking:
            return "arrow.triangle.2.circlepath"
        case .offline:
            return "exclamationmark.triangle"
        }
    }
}
