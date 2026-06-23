import XCTest
@testable import App

final class AudioPlayerTests: XCTestCase {
    func test_clearCacheStopsPlayer() {
        let player = AudioPlayer()

        player.isPlaying = true

        player.clearCache()

        XCTAssertFalse(player.isPlaying)
    }
}
