import AVFoundation

actor AudioSessionCoordinator {
    static let shared = AudioSessionCoordinator()

    enum Purpose {
        case record
        case playback
        case recordAndPlayback
    }

    private var activeCount = 0
    private var currentPurpose: Purpose?

    func activate(for purpose: Purpose) throws {
        #if os(iOS)
        let session = AVAudioSession.sharedInstance()
        let category: AVAudioSession.Category

        switch purpose {
        case .record, .recordAndPlayback:
            category = .playAndRecord
        case .playback:
            category = .playback
        }

        try session.setCategory(
            category,
            mode: .default,
            options: purpose == .recordAndPlayback ? [.defaultToSpeaker] : []
        )
        try session.setActive(true)
        activeCount += 1
        currentPurpose = purpose
        #else
        activeCount += 1
        currentPurpose = purpose
        #endif
    }

    func deactivate() throws {
        activeCount -= 1

        if activeCount <= 0 {
            activeCount = 0
            #if os(iOS)
            try AVAudioSession.sharedInstance().setActive(false, options: .notifyOthersOnDeactivation)
            #endif
            currentPurpose = nil
        }
    }
}
