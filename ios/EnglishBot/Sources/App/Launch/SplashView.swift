import SwiftUI
import DesignSystem

public struct SplashView: View {
    @ObservedObject public var viewModel: AppBootstrapViewModel
    @State private var pulseScale: CGFloat = 1.0

    public init(viewModel: AppBootstrapViewModel) {
        self.viewModel = viewModel
    }

    public var body: some View {
        ZStack {
            Color.BotTheme.primary
                .ignoresSafeArea()

            VStack(spacing: 0) {
                Spacer()

                if #available(iOS 17, macOS 14, *) {
                    Image(systemName: "mic.fill")
                        .resizable()
                        .scaledToFit()
                        .frame(width: 80, height: 80)
                        .foregroundColor(.white)
                        .symbolEffect(.pulse, options: .repeating)
                } else {
                    Image(systemName: "mic.fill")
                        .resizable()
                        .scaledToFit()
                        .frame(width: 80, height: 80)
                        .foregroundColor(.white)
                        .scaleEffect(pulseScale)
                        .animation(.easeInOut(duration: 1.5).repeatForever(autoreverses: true), value: pulseScale)
                        .onAppear { pulseScale = 1.1 }
                }

                Spacer().frame(height: 24)

                Text("English Coach")
                    .font(Font.BotTheme.heading1)
                    .foregroundColor(.white)

                Spacer().frame(height: 40)

                ProgressView()
                    .tint(.white)

                Spacer().frame(height: 16)

                Text(viewModel.progressMessage)
                    .font(Font.BotTheme.bodySecondary)
                    .foregroundColor(.white.opacity(0.8))
                    .animation(.easeInOut, value: viewModel.progressMessage)

                Spacer()
            }
        }
        .transition(.opacity)
    }
}
