// swift-tools-version: 6.1

import PackageDescription

let package = Package(
    name: "MemoryOSDaemon",
    platforms: [
        .macOS(.v13)
    ],
    products: [
        .executable(name: "memoryos-daemon", targets: ["MemoryOSDaemon"])
    ],
    targets: [
        .systemLibrary(
            name: "CSQLite",
            path: "Sources/CSQLite",
            pkgConfig: "sqlite3"
        ),
        .executableTarget(
            name: "MemoryOSDaemon",
            dependencies: ["CSQLite"],
            linkerSettings: [
                .linkedLibrary("sqlite3")
            ]
        )
    ]
)
