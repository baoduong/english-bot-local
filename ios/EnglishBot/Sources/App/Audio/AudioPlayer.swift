import Foundation
import AVFoundation

public class AudioPlayer: ObservableObject {
    private var player: AVPlayer?
    @Published public var isPlaying = false
    
    public init() {}
    
    public func play(url: URL) {
        #if os(iOS)
        do {
            let audioSession = AVAudioSession.sharedInstance()
            try audioSession.setCategory(.playAndRecord, mode: .default, options: .defaultToSpeaker)
            try audioSession.setActive(true)
        } catch {
            print("Failed to set up audio session for playback")
        }
        #endif
        
        let playerItem = AVPlayerItem(url: url)
        player = AVPlayer(playerItem: playerItem)
        
        NotificationCenter.default.addObserver(self, selector: #selector(playerDidFinishPlaying), name: .AVPlayerItemDidPlayToEndTime, object: playerItem)
        
        player?.play()
        isPlaying = true
    }
    
    public func stop() {
        player?.pause()
        isPlaying = false
    }
    
    @objc private func playerDidFinishPlaying(sender: Notification) {
        DispatchQueue.main.async {
            self.isPlaying = false
        }
    }
}
