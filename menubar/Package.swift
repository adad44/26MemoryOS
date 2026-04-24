// swift-tools-version: 6.0

import PackageDescription

let package = Package(
    name: "MemoryOSMenuBar",
    platforms: [
        .macOS(.v13)
    ],
    products: [
        .executable(name: "memoryos-menubar", targets: ["MemoryOSMenuBar"])
    ],
    targets: [
        .executableTarget(
            name: "MemoryOSMenuBar",
            linkerSettings: [
                .linkedFramework("AppKit"),
                .linkedFramework("SwiftUI")
            ]
        )
    ]
)
