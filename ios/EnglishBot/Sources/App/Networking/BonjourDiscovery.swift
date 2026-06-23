import Foundation

final class BonjourDiscovery: NSObject, NetServiceBrowserDelegate, NetServiceDelegate {
    private var browser: NetServiceBrowser?
    private var foundService: NetService?
    private var completion: ((URL?) -> Void)?
    private var timeoutTask: Task<Void, Never>?

    func discover(timeout: TimeInterval = 5.0) async -> URL? {
        await withCheckedContinuation { continuation in
            completion = { url in
                continuation.resume(returning: url)
            }

            let browser = NetServiceBrowser()
            self.browser = browser
            browser.delegate = self
            browser.searchForServices(ofType: "_englishbot._tcp.", inDomain: "local.")

            timeoutTask = Task { [weak self] in
                guard let self else { return }
                try? await Task.sleep(nanoseconds: UInt64(timeout * 1_000_000_000))
                guard !Task.isCancelled else { return }
                browser.stop()
                self.finish(with: nil)
            }
        }
    }

    func netServiceBrowser(_ browser: NetServiceBrowser, didFind service: NetService, moreComing: Bool) {
        guard completion != nil else { return }
        foundService = service
        service.delegate = self
        service.resolve(withTimeout: 3.0)
    }

    func netServiceDidResolveAddress(_ sender: NetService) {
        timeoutTask?.cancel()
        browser?.stop()

        if let hostName = sender.hostName {
            let trimmedHost = hostName.trimmingCharacters(in: CharacterSet(charactersIn: "."))
            finish(with: URL(string: "http://\(trimmedHost):\(sender.port)"))
        } else {
            finish(with: nil)
        }
    }

    func netService(_ sender: NetService, didNotResolve errorDict: [String : NSNumber]) {}

    private func finish(with url: URL?) {
        timeoutTask?.cancel()
        timeoutTask = nil
        browser?.stop()
        browser = nil
        foundService = nil

        let completion = self.completion
        self.completion = nil
        completion?(url)
    }
}
