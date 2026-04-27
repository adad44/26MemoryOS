import AppKit
import SwiftUI

struct MemoryOSLogo: View {
    var size: CGFloat = 24
    var artworkSize: CGFloat? = nil

    var body: some View {
        ZStack {
            Group {
                if let image = MemoryOSLogoImage.load() {
                    Image(nsImage: image)
                        .resizable()
                        .renderingMode(.template)
                        .scaledToFit()
                        .foregroundStyle(.primary)
                } else {
                    Image(systemName: "brain")
                        .resizable()
                        .scaledToFit()
                        .foregroundStyle(.primary)
                }
            }
            .frame(width: artworkSize ?? size, height: artworkSize ?? size)
        }
        .frame(width: size, height: size)
        .contentShape(Rectangle())
        .accessibilityLabel("MemoryOS")
    }
}

enum MemoryOSLogoImage {
    static func load() -> NSImage? {
        if let url = Bundle.main.url(forResource: "memoryos-menubar-logo", withExtension: "svg"),
           let image = NSImage(contentsOf: url) {
            image.isTemplate = true
            return image
        }

        let sourceURL = URL(fileURLWithPath: FileManager.default.currentDirectoryPath)
            .appendingPathComponent("menubar/Assets/memoryos-menubar-logo.svg")
        guard let image = NSImage(contentsOf: sourceURL) else {
            return nil
        }
        image.isTemplate = true
        return image
    }
}
