/// ViewHostingTestSupport.swift
/// Foundation for state-dependent ViewInspector tests (T4, T5, T7).
///
/// ## Usage Example
///
/// ```swift
/// func testProgressMessageUpdates() async throws {
///     let vm = MyViewModel()
///     let view = MyView(viewModel: vm)
///     ViewHosting.host(view: view)
///     defer { ViewHosting.expel() }
///
///     // Trigger state change
///     await MainActor.run { vm.message = "Updated" }
///
///     // Inspect after update
///     try await Task.sleep(nanoseconds: 50_000_000) // 50ms for SwiftUI to update
///     let inspected = try view.inspect()
///     // ... assertions on inspected view
/// }
/// ```
///
/// For ObservableObject-driven views, use `inspectAfterPublishedChange`:
/// ```swift
/// try await inspectAfterPublishedChange(vm, timeout: 1.0) {
///     let text = try $0.find(text: "Updated")
///     XCTAssertNotNil(text)
/// }
/// ```

import XCTest
import SwiftUI
import ViewInspector
@testable import App

// MARK: - Inspection Publisher Pattern

/// Inspection helper for state-dependent ViewInspector tests.
/// Follows the ViewInspector "hosting + inspection" pattern for @Published-driven views.
///
/// Usage: Add `let inspection = Inspection<Self>()` to your View,
/// call `inspection.visit(self, #line)` in `.onReceive(inspection.notice)`,
/// then use `inspectView` helper in tests.
public struct Inspection<V> {
    public let notice = PassthroughSubject<UInt, Never>()
    public var callbacks: [UInt: (V) -> Void] = [:]

    public init() {}

    public mutating func visit(_ view: V, _ line: UInt) {
        if let callback = callbacks.removeValue(forKey: line) {
            callback(view)
        }
    }
}

// MARK: - Combine import for PassthroughSubject

import Combine

// MARK: - Test Helpers

/// Host a view, wait for a state change, then inspect it.
/// - Parameters:
///   - view: The SwiftUI view to host and inspect.
///   - timeout: Max wait time in seconds (default 1.0).
///   - stateChange: Async closure that triggers the state change.
///   - inspection: Closure that receives the hosted view for inspection.
@MainActor
public func inspectAfterStateChange<V: View & Inspectable>(
    _ view: V,
    timeout: TimeInterval = 1.0,
    stateChange: @escaping () async -> Void,
    inspection: @escaping (V) throws -> Void
) async throws {
    ViewHosting.host(view: view)
    defer { ViewHosting.expel() }

    await stateChange()

    // Allow SwiftUI to process the state change
    try await Task.sleep(nanoseconds: 100_000_000) // 100ms

    try inspection(view)
}

/// Host a view and inspect it immediately (for static/initial state tests).
@MainActor
public func inspectView<V: View & Inspectable>(
    _ view: V,
    timeout: TimeInterval = 1.0,
    inspection: @escaping (V) throws -> Void
) async throws {
    ViewHosting.host(view: view)
    defer { ViewHosting.expel() }

    // Allow initial render
    try await Task.sleep(nanoseconds: 50_000_000) // 50ms

    try inspection(view)
}

/// Wait for an @ObservedObject's @Published property to update, then inspect.
/// - Parameters:
///   - observable: The ObservableObject to observe.
///   - view: The view to inspect after the update.
///   - timeout: Max wait time in seconds.
///   - trigger: Closure that triggers the @Published change.
///   - inspection: Closure that receives the view for inspection.
@MainActor
public func inspectAfterPublishedChange<O: ObservableObject, V: View & Inspectable>(
    _ observable: O,
    view: V,
    timeout: TimeInterval = 1.0,
    trigger: @escaping () async -> Void,
    inspection: @escaping (V) throws -> Void
) async throws {
    ViewHosting.host(view: view)
    defer { ViewHosting.expel() }

    await trigger()

    // Allow SwiftUI to propagate the @Published change
    try await Task.sleep(nanoseconds: 100_000_000) // 100ms

    try inspection(view)
}
