import Foundation
import AVFoundation

public class AudioRecorder: NSObject, ObservableObject, AVAudioRecorderDelegate {
    private var audioRecorder: AVAudioRecorder?
    @Published public var isRecording = false
    
    public override init() {
        super.init()
    }
    
    public func requestPermission() async -> Bool {
        #if os(iOS)
        return await withCheckedContinuation { continuation in
            AVAudioSession.sharedInstance().requestRecordPermission { granted in
                continuation.resume(returning: granted)
            }
        }
        #else
        return true
        #endif
    }
    
    public func startRecording() throws -> URL {
        #if os(iOS)
        let audioSession = AVAudioSession.sharedInstance()
        try audioSession.setCategory(.playAndRecord, mode: .default, options: .defaultToSpeaker)
        try audioSession.setActive(true)
        #endif
        
        let documentPath = FileManager.default.temporaryDirectory
        let url = documentPath.appendingPathComponent("\(UUID().uuidString).m4a")
        
        let settings: [String: Any] = [
            AVFormatIDKey: Int(kAudioFormatMPEG4AAC),
            AVSampleRateKey: 44100,
            AVNumberOfChannelsKey: 1,
            AVEncoderAudioQualityKey: AVAudioQuality.high.rawValue
        ]
        
        audioRecorder = try AVAudioRecorder(url: url, settings: settings)
        audioRecorder?.delegate = self
        audioRecorder?.record()
        
        DispatchQueue.main.async {
            self.isRecording = true
        }
        
        return url
    }
    
    public func stopRecording() -> URL? {
        guard let recorder = audioRecorder else { return nil }
        let url = recorder.url
        recorder.stop()
        
        #if os(iOS)
        do {
            let audioSession = AVAudioSession.sharedInstance()
            try audioSession.setActive(false)
        } catch {
            print("Failed to deactivate audio session")
        }
        #endif
        
        DispatchQueue.main.async {
            self.isRecording = false
        }
        
        return url
    }
    
    public func audioRecorderDidFinishRecording(_ recorder: AVAudioRecorder, successfully flag: Bool) {
        if !flag {
            _ = stopRecording()
        }
    }
}
