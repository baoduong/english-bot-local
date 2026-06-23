// swift-tools-version: 5.9
// The swift-tools-version declares the minimum version of Swift required to build this package.

import PackageDescription

let package = Package(
    name: "EnglishBot",
    platforms: [
        .iOS(.v16), .macOS(.v13)
    ],
    products: [
        // Products define the executables and libraries a package produces, making them visible to other packages.
        .library(
            name: "DesignSystem",
            targets: ["DesignSystem"]),
        .library(
            name: "App",
            targets: ["App"]),
    ],
    dependencies: [
        .package(url: "https://github.com/nalexn/ViewInspector", .upToNextMajor(from: "0.10.0")),
    ],
    targets: [
        // Targets are the basic building blocks of a package, defining a module or a test suite.
        // Targets can depend on other targets in this package and products from dependencies.
        .target(
            name: "DesignSystem",
            path: "Sources/DesignSystem"
        ),
        .target(
            name: "App",
            dependencies: ["DesignSystem"],
            path: "Sources/App"
        ),
        .testTarget(
            name: "AppTests",
            dependencies: [
                "App",
                .product(name: "ViewInspector", package: "ViewInspector"),
            ],
            path: "Tests/AppTests"
        ),
    ]
)
