import Foundation
import AVFoundation
import AppKit
let output = CommandLine.arguments[1]
for file in CommandLine.arguments.dropFirst(2) {
 let url = URL(fileURLWithPath: file)
 let asset = AVURLAsset(url: url)
 let duration = CMTimeGetSeconds(asset.duration)
 let stem = url.deletingPathExtension().lastPathComponent.replacingOccurrences(of: "WhatsApp Video 2026-09-29 at ", with: "")
 let generator = AVAssetImageGenerator(asset: asset)
 generator.appliesPreferredTrackTransform = true
 generator.maximumSize = CGSize(width: 1100, height: 1100)
 generator.requestedTimeToleranceBefore = .zero
 generator.requestedTimeToleranceAfter = .zero
 print("\(stem) duration=\(duration) audio_tracks=\(asset.tracks(withMediaType: .audio).count)")
 for (idx, fraction) in [0.02,0.20,0.40,0.60,0.80,0.96].enumerated() {
  do {
   let time = CMTime(seconds: duration*fraction, preferredTimescale: 600)
   let cg = try generator.copyCGImage(at: time, actualTime: nil)
   let image = NSBitmapImageRep(cgImage: cg)
   let data = image.representation(using: .jpeg, properties: [.compressionFactor: 0.85])!
   try data.write(to: URL(fileURLWithPath: "\(output)/\(stem)_\(idx).jpg"))
  } catch { print("ERROR \(stem) \(idx): \(error)") }
 }
}
