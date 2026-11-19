// swift-tools-version: 6.0
import PackageDescription
let package = Package(name: "MyIMELinux", dependencies: [.package(path: "IMEKit")],
    targets: [.executableTarget(name: "MyIMEHost", dependencies: ["IMEKit"])])
