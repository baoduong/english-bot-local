import Foundation
import AVFoundation

public class AudioPlayer: ObservableObject {
    private var player: AVPlayer?
    private var observerToken: NSObjectProtocol?
    @Published public var isPlaying = false
    private var cache: [URL: URL] = [:]
    private let cacheDir: URL = FileManager.default.temporaryDirectory.appendingPathComponent("audio_cache")

    public init() {
        try? FileManager.default.createDirectory(at: cacheDir, withIntermediateDirectories: true)
    }

    public func play(url: URL) {
        removeObserver()

        #if os(iOS)
        let semaphore = DispatchSemaphore(value: 0)

        Task {
            try? await AudioSessionCoordinator.shared.activate(for: .playback)
            semaphore.signal()
        }

        semaphore.wait()
        #endif

        if let localFile = cache[url] {
            playLocal(localFile)
            return
        }

        let task = URLSession.shared.downloadTask(with: url) { [weak self] tempURL, _, error in
            guard let self = self, let tempURL = tempURL, error == nil else {
                DispatchQueue.main.async { self?.playRemote(url) }
                return
            }
            let dest = self.cacheDir.appendingPathComponent(UUID().uuidString + ".mp3")
            try? FileManager.default.moveItem(at: tempURL, to: dest)
            DispatchQueue.main.async {
                self.cache[url] = dest
                self.playLocal(dest)
            }
        }
        task.resume()
    }

    public func clearCache() {
        for localFile in cache.values {
            try? FileManager.default.removeItem(at: localFile)
        }
        cache.removeAll()
    }

    public func stop() {
        player?.pause()
        isPlaying = false
        removeObserver()

        #if os(iOS)
        Task {
            try? await AudioSessionCoordinator.shared.deactivate()
        }
        #endif
    }

    private func playLocal(_ fileURL: URL) {
        let playerItem = AVPlayerItem(url: fileURL)
        player = AVPlayer(playerItem: playerItem)
        observerToken = NotificationCenter.default.addObserver(
            forName: .AVPlayerItemDidPlayToEndTime,
            object: playerItem,
            queue: .main
        ) { [weak self] _ in
            self?.playerDidFinishPlaying()
        }
        player?.play()
        isPlaying = true
    }

    private func playRemote(_ url: URL) {
        let playerItem = AVPlayerItem(url: url)
        player = AVPlayer(playerItem: playerItem)
        observerToken = NotificationCenter.default.addObserver(
            forName: .AVPlayerItemDidPlayToEndTime,
            object: playerItem,
            queue: .main
        ) { [weak self] _ in
            self?.playerDidFinishPlaying()
        }
        player?.play()
        isPlaying = true
    }

    private func removeObserver() {
        if let token = observerToken {
            NotificationCenter.default.removeObserver(token)
            observerToken = nil
        }
    }

    private func playerDidFinishPlaying() {
        isPlaying = false
        removeObserver()

        #if os(iOS)
        Task {
            try? await AudioSessionCoordinator.shared.deactivate()
        }
        #endif
    }

    deinit {
        removeObserver()
    }
}
