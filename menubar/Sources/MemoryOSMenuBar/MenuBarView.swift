import AppKit
import SwiftUI

struct MenuBarView: View {
    @EnvironmentObject private var client: MemoryOSClient
    @State private var showingSettings = false

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            header
            Divider()
            stats
            actions
            if showingSettings {
                Divider()
                settings
            }
            Divider()
            footer
        }
        .padding(14)
        .frame(width: 300)
    }

    private var header: some View {
        HStack(spacing: 10) {
            Image(systemName: "brain.head.profile")
                .font(.title2)
                .foregroundStyle(.primary)
            VStack(alignment: .leading, spacing: 2) {
                Text("MemoryOS")
                    .font(.headline)
                HStack(spacing: 6) {
                    Circle()
                        .fill(statusColor)
                        .frame(width: 8, height: 8)
                    Text(client.state.label)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            }
            Spacer()
            Button {
                Task { await client.refresh() }
            } label: {
                Image(systemName: "arrow.clockwise")
            }
            .buttonStyle(.borderless)
            .help("Refresh status")
        }
    }

    private var stats: some View {
        VStack(alignment: .leading, spacing: 8) {
            statRow("Captures", value: "\(client.stats?.totalCaptures ?? 0)")
            statRow("Index", value: client.stats?.indexedAvailable == true ? "Ready" : "Missing")
            statRow("Capture", value: client.capturePaused ? "Paused" : "Active")
            statRow("Latest", value: formattedLatest)
        }
    }

    private var actions: some View {
        VStack(spacing: 8) {
            Button {
                client.openSearch()
            } label: {
                actionLabel("Open Search", systemImage: "magnifyingglass")
            }
            Button {
                client.toggleCapturePaused()
            } label: {
                actionLabel(client.capturePaused ? "Resume Capture" : "Pause Capture", systemImage: client.capturePaused ? "play.fill" : "pause.fill")
            }
            Button {
                Task { await client.refreshIndex() }
            } label: {
                actionLabel(client.isRefreshingIndex ? "Refreshing Index" : "Refresh Index", systemImage: "externaldrive")
            }
            .disabled(client.isRefreshingIndex)
            Button {
                client.openBackendDocs()
            } label: {
                actionLabel("Backend API", systemImage: "curlybraces")
            }
            Button {
                showingSettings.toggle()
            } label: {
                actionLabel(showingSettings ? "Hide Settings" : "Settings", systemImage: "gearshape")
            }
        }
        .buttonStyle(.plain)
    }

    private var settings: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("Backend URL")
                .font(.caption)
                .foregroundStyle(.secondary)
            TextField("Backend URL", text: $client.backendURL)
                .textFieldStyle(.roundedBorder)
            Text("Web URL")
                .font(.caption)
                .foregroundStyle(.secondary)
            TextField("Web URL", text: $client.webURL)
                .textFieldStyle(.roundedBorder)
            Text("API Key")
                .font(.caption)
                .foregroundStyle(.secondary)
            SecureField("Optional", text: $client.apiKey)
                .textFieldStyle(.roundedBorder)
        }
    }

    private var footer: some View {
        HStack {
            Button("Quit") {
                NSApplication.shared.terminate(nil)
            }
            .buttonStyle(.borderless)
            Spacer()
            Text("Local only")
                .font(.caption)
                .foregroundStyle(.secondary)
        }
    }

    private func statRow(_ label: String, value: String) -> some View {
        HStack {
            Text(label)
                .foregroundStyle(.secondary)
            Spacer()
            Text(value)
                .fontWeight(.medium)
                .lineLimit(1)
                .truncationMode(.middle)
        }
        .font(.callout)
    }

    private func actionLabel(_ title: String, systemImage: String) -> some View {
        HStack {
            Image(systemName: systemImage)
                .frame(width: 18)
            Text(title)
            Spacer()
        }
        .padding(.horizontal, 10)
        .padding(.vertical, 8)
        .background(Color(nsColor: .controlBackgroundColor))
        .clipShape(RoundedRectangle(cornerRadius: 6))
    }

    private var formattedLatest: String {
        guard let latest = client.stats?.latestCaptureAt else {
            return "None"
        }
        let formatter = ISO8601DateFormatter()
        guard let date = formatter.date(from: latest) else {
            return latest
        }
        return date.formatted(date: .abbreviated, time: .shortened)
    }

    private var statusColor: Color {
        switch client.state {
        case .checking:
            return .orange
        case .online:
            return .green
        case .offline:
            return .red
        }
    }
}
