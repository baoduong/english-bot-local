import Foundation
import AVFoundation

public class AudioRecorder: NSObject, ObservableObject, AVAudioRecorderDelegate {
    private var audioRecorder: AVAudioRecorder?
    @Published public var isRecording = false
    
    public override init() {
        super.init()
    }

    public enum AudioRecorderError: Error {
        case permissionDenied
        case recordingFailed(Error)
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
        let permission = audioSession.recordPermission
        switch permission {
        case .denied, .undetermined:
            throw AudioRecorderError.permissionDenied
        case .granted:
            break
        @unknown default:
            break
        }
        let semaphore = DispatchSemaphore(value: 0)
        var activationError: Error?

        Task {
            do {
                try await AudioSessionCoordinator.shared.activate(for: .record)
            } catch {
                activationError = error
            }

            semaphore.signal()
        }

        semaphore.wait()

        if let activationError {
            throw activationError
        }
        #endif
        
        let documentPath = FileManager.default.temporaryDirectory
        let url = documentPath.appendingPathComponent("\(UUID().uuidString).m4a")
        
        let settings: [String: Any] = [
            AVFormatIDKey: Int(kAudioFormatMPEG4AAC),
            AVSampleRateKey: 44100,
            AVNumberOfChannelsKey: 1,
            AVEncoderAudioQualityKey: AVAudioQuality.high.rawValue
        ]
        
        do {
            audioRecorder = try AVAudioRecorder(url: url, settings: settings)
            audioRecorder?.delegate = self
            guard audioRecorder?.record() == true else {
                throw AudioRecorderError.recordingFailed(NSError(domain: "AudioRecorder", code: -1, userInfo: [NSLocalizedDescriptionKey: "Failed to start recording"]))
            }
        } catch let error as AudioRecorderError {
            throw error
        } catch {
            throw AudioRecorderError.recordingFailed(error)
        }

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
        Task {
            try? await AudioSessionCoordinator.shared.deactivate()
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
