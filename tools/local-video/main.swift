import Foundation
import CryptoKit
import AppKit
import Darwin

// Swift owns intake, provenance, edit decisions, cache and verification.
// FFmpeg/ffprobe are invoked directly, without a shell, for media processing.
struct Failure: Error, CustomStringConvertible { let description: String; init(_ s: String) { description = s } }
let fm = FileManager.default
func require(_ condition: Bool, _ message: String) throws { if !condition { throw Failure(message) } }
func read(_ url: URL) throws -> [String: Any] {
    guard let obj = try JSONSerialization.jsonObject(with: Data(contentsOf: url)) as? [String: Any] else { throw Failure("Expected JSON object: \(url.path)") }; return obj
}
func write(_ obj: Any, _ url: URL) throws {
    try fm.createDirectory(at: url.deletingLastPathComponent(), withIntermediateDirectories: true)
    try JSONSerialization.data(withJSONObject: obj, options: [.prettyPrinted, .sortedKeys, .withoutEscapingSlashes]).write(to: url, options: .atomic)
}
func sha(_ url: URL) throws -> String {
    let handle = try FileHandle(forReadingFrom: url); defer { try? handle.close() }
    var hash = SHA256()
    while let bytes = try handle.read(upToCount: 1_048_576), !bytes.isEmpty { hash.update(data: bytes) }
    return hash.finalize().map { String(format: "%02x", $0) }.joined()
}
func digest(_ text: String) -> String { SHA256.hash(data: Data(text.utf8)).map { String(format: "%02x", $0) }.joined() }
func tool(_ name: String) throws -> URL {
    let paths = (ProcessInfo.processInfo.environment["PATH"] ?? "").components(separatedBy: ":") + ["/opt/homebrew/bin", "/usr/local/bin", "/usr/bin"]
    for path in paths where !path.isEmpty { let url = URL(fileURLWithPath: path).appendingPathComponent(name); if fm.isExecutableFile(atPath: url.path) { return url } }
    throw Failure("Missing \(name). Install FFmpeg: brew install ffmpeg")
}
@discardableResult func run(_ name: String, _ args: [String]) throws -> Data {
    let p = Process(); p.executableURL = try tool(name); p.arguments = args
    // A file for stderr avoids pipe-buffer deadlocks on long encodes.
    let log = fm.temporaryDirectory.appendingPathComponent("muse-\(UUID().uuidString).log")
    fm.createFile(atPath: log.path, contents: nil)
    let err = try FileHandle(forWritingTo: log); defer { try? err.close(); try? fm.removeItem(at: log) }
    let out = Pipe(); p.standardOutput = out; p.standardError = err
    try p.run(); let data = out.fileHandleForReading.readDataToEndOfFile(); p.waitUntilExit()
    if p.terminationStatus != 0 { throw Failure("\(name) failed (\(p.terminationStatus)): \(String(data: (try? Data(contentsOf: log)) ?? Data(), encoding: .utf8) ?? "")") }
    return data
}
struct Media {
    let duration: Double; let width: Int; let height: Int; let audio: Bool; let videoCodec: String; let audioCodec: String
    init(_ url: URL) throws {
        let bytes = try run("ffprobe", ["-v", "error", "-show_format", "-show_streams", "-of", "json", url.path])
        let data = try JSONSerialization.jsonObject(with: bytes) as? [String: Any] ?? [:]
        let streams = data["streams"] as? [[String: Any]] ?? []
        guard let video = streams.first(where: { $0["codec_type"] as? String == "video" }) else { throw Failure("No video stream: \(url.path)") }
        let format = data["format"] as? [String: Any] ?? [:]
        duration = Double(format["duration"] as? String ?? "0") ?? 0
        width = video["width"] as? Int ?? 0; height = video["height"] as? Int ?? 0
        audio = streams.contains { $0["codec_type"] as? String == "audio" }
        videoCodec = video["codec_name"] as? String ?? ""
        audioCodec = streams.first { $0["codec_type"] as? String == "audio" }?["codec_name"] as? String ?? ""
        try require(duration.isFinite && duration > 0 && width > 0 && height > 0, "Invalid media: \(url.path)")
    }
}
struct Project {
    let root: URL; let definition: [String: Any]; let shots: [[String: Any]]
    init(_ path: String) throws {
        root = URL(fileURLWithPath: path).standardizedFileURL
        definition = try read(root.appendingPathComponent("project.json"))
        let sequences = root.appendingPathComponent("sequences")
        let files = try fm.contentsOfDirectory(at: sequences, includingPropertiesForKeys: nil).filter { $0.pathExtension == "json" }.sorted { $0.lastPathComponent < $1.lastPathComponent }
        var found: [[String: Any]] = []
        for file in files { found += try read(file)["shots"] as? [[String: Any]] ?? [] }
        // Explicit order wins; legacy projects retain sequence-file/array order.
        if found.allSatisfy({ $0["order"] is Int }) { found.sort { ($0["order"] as! Int) < ($1["order"] as! Int) } }
        let ids = found.compactMap { $0["shotId"] as? String }
        try require(!found.isEmpty && ids.count == found.count && Set(ids).count == ids.count, "Missing/duplicate shot IDs")
        for id in ids { try require(id.range(of: "^[A-Za-z0-9_-]+$", options: .regularExpression) != nil, "Unsafe shot ID: \(id)") }
        shots = found
    }
    func path(_ p: String) throws -> URL {
        let result = root.appendingPathComponent(p).standardizedFileURL.resolvingSymlinksInPath()
        try require(result.path.hasPrefix(root.resolvingSymlinksInPath().path + "/"), "Path escapes project: \(p)")
        return result
    }
    func prompt(_ id: String) throws -> String { try sha(path("prompts/\(id).txt")) }
    func manifest() throws -> [String: Any] {
        let url = try path("manifest.json")
        return fm.fileExists(atPath: url.path) ? try read(url) : ["version": 1, "clips": [], "redoRequests": []]
    }
    func selected(_ manifest: [String: Any], _ id: String) -> [String: Any]? {
        (manifest["clips"] as? [[String: Any]] ?? []).last { $0["shotId"] as? String == id && $0["selected"] as? Bool == true }
    }
}
func ingest(_ project: Project, _ input: String, _ shot: String?, _ expectedPrompt: String?) throws {
    var manifest = try project.manifest(); var clips = manifest["clips"] as? [[String: Any]] ?? []
    let url = URL(fileURLWithPath: input).standardizedFileURL
    var isDir: ObjCBool = false
    try require(fm.fileExists(atPath: url.path, isDirectory: &isDir), "Input does not exist: \(input)")
    let files = isDir.boolValue ? try fm.contentsOfDirectory(at: url, includingPropertiesForKeys: nil).filter { ["mp4", "mov", "m4v"].contains($0.pathExtension.lowercased()) } : [url]
    var mappings: [(URL, String)] = []
    for file in files.sorted(by: { $0.lastPathComponent < $1.lastPathComponent }) {
        let matches = project.shots.compactMap { $0["shotId"] as? String }.filter { id in
            file.deletingPathExtension().lastPathComponent.range(of: "(^|[^A-Za-z0-9])\(NSRegularExpression.escapedPattern(for: id))([^A-Za-z0-9]|$)", options: .regularExpression) != nil
        }
        if !isDir.boolValue, let id = shot { mappings.append((file, id)) }
        else if matches.count == 1 { mappings.append((file, matches[0])) }
        else { throw Failure("Cannot map \(file.lastPathComponent) unambiguously. Import it with --shot sNN.") }
    }
    try require(!mappings.isEmpty, "No video files to import")
    try require(Set(mappings.map { $0.1 }).count == mappings.count, "Multiple takes for one shot in directory; select each explicitly with --shot")
    // Preflight the whole batch before selecting any takes.
    var pending: [[String: Any]] = []
    for (file, id) in mappings {
        try require(project.shots.contains { $0["shotId"] as? String == id }, "Unknown shot: \(id)")
        let hash = try sha(file); let promptHash = try project.prompt(id)
        if let expectedPrompt { try require(expectedPrompt == promptHash, "Generation prompt differs from current prompt for \(id)") }
        let media = try Media(file)
        let rel = "clips/raw/\(id)-\(hash).mp4"; let dest = try project.path(rel)
        try fm.createDirectory(at: dest.deletingLastPathComponent(), withIntermediateDirectories: true)
        if !fm.fileExists(atPath: dest.path) { try fm.copyItem(at: file, to: dest) }
        try require(try sha(dest) == hash, "Copy checksum failed for \(id)")
        pending.append(["shotId": id, "file": rel, "sha256": hash, "promptSha256": promptHash,
                        "promptProvenance": expectedPrompt == nil ? "operator-mapped-to-current-packet" : "generation-hash-verified",
                        "durationSec": media.duration, "width": media.width, "height": media.height,
                        "sourceName": file.lastPathComponent, "status": "generated", "selected": true,
                        "importedAt": ISO8601DateFormatter().string(from: Date())])
    }
    for take in pending {
        let id = take["shotId"] as! String
        if let old = project.selected(["clips": clips], id), old["sha256"] as? String == take["sha256"] as? String, old["promptSha256"] as? String == take["promptSha256"] as? String, old["status"] as? String != "redo" { print("Unchanged \(id), skipped"); continue }
        for i in clips.indices where clips[i]["shotId"] as? String == id { clips[i]["selected"] = false }
        clips.append(take); print("Imported \(id): \(take["durationSec"]!) seconds")
    }
    manifest["clips"] = clips; try write(manifest, project.path("manifest.json"))
}
func cards(_ project: Project) throws {
    for shot in project.shots where shot["kind"] as? String == "title" {
        guard let id = shot["shotId"] as? String, let title = shot["titleText"] as? String else { throw Failure("Invalid title card") }
        let width = 1280, height = 720
        guard let bitmap = NSBitmapImageRep(bitmapDataPlanes: nil, pixelsWide: width, pixelsHigh: height, bitsPerSample: 8, samplesPerPixel: 4, hasAlpha: true, isPlanar: false, colorSpaceName: .deviceRGB, bytesPerRow: 0, bitsPerPixel: 0), let context = NSGraphicsContext(bitmapImageRep: bitmap) else { throw Failure("Cannot create title canvas") }
        NSGraphicsContext.saveGraphicsState(); NSGraphicsContext.current = context
        NSColor.black.setFill(); NSRect(x: 0, y: 0, width: width, height: height).fill()
        let paragraph = NSMutableParagraphStyle(); paragraph.alignment = .center
        var fontSize: CGFloat = 80
        let safeWidth = CGFloat(width - 160)
        while fontSize > 20 && (title as NSString).size(withAttributes: [.font: NSFont(name: "TimesNewRomanPS-BoldMT", size: fontSize) ?? NSFont.boldSystemFont(ofSize: fontSize)]).width > safeWidth { fontSize -= 2 }
        let attributes: [NSAttributedString.Key: Any] = [.font: NSFont(name: "TimesNewRomanPS-BoldMT", size: fontSize) ?? NSFont.boldSystemFont(ofSize: fontSize), .foregroundColor: NSColor(calibratedRed: 0.78, green: 0.10, blue: 0.08, alpha: 1), .paragraphStyle: paragraph]
        (title as NSString).draw(in: NSRect(x: 80, y: CGFloat(height)/2 - fontSize/2, width: safeWidth, height: fontSize*1.5), withAttributes: attributes)
        NSGraphicsContext.restoreGraphicsState()
        guard let png = bitmap.representation(using: .png, properties: [:]) else { throw Failure("Cannot encode title") }
        let work = try project.path("work/cards"); try fm.createDirectory(at: work, withIntermediateDirectories: true)
        let still = work.appendingPathComponent(id + ".png"), video = work.appendingPathComponent(id + ".mp4")
        try png.write(to: still)
        let duration = shot["sourceDurationSec"] as? Double ?? 5
        try run("ffmpeg", ["-v", "error", "-nostdin", "-y", "-loop", "1", "-framerate", "24", "-i", still.path, "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-t", String(duration), "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p", "-c:a", "aac", "-movflags", "+faststart", video.path])
        try ingest(project, video.path, id, project.prompt(id))
    }
    try status(project)
}

func status(_ project: Project) throws {
    let manifest = try project.manifest(); var queue: [[String: Any]] = []; var localPending: [String] = []
    for shot in project.shots {
        let id = shot["shotId"] as! String
        var state = "missing"
        if let take = project.selected(manifest, id) {
            if take["status"] as? String == "redo" { state = "redo" }
            else if take["promptSha256"] as? String != (try project.prompt(id)) { state = "stale-prompt" }
            else if let file = take["file"] as? String, fm.fileExists(atPath: try project.path(file).path), try sha(project.path(file)) == take["sha256"] as? String { state = take["status"] as? String ?? "generated" }
            else { state = "missing-or-corrupt" }
        }
        print("\(id): \(state)")
        if ["missing", "redo", "stale-prompt", "missing-or-corrupt"].contains(state) {
            if shot["kind"] as? String == "title" { localPending.append(id) }
            else { queue.append(["shotId": id, "reason": state, "promptSha256": try project.prompt(id)]) }
        }
    }
    try write(["pending": queue, "nextBatch": Array(queue.prefix(6)), "localPending": localPending, "complete": queue.isEmpty && localPending.isEmpty], project.path("generation-queue.json"))
}
func redo(_ project: Project, _ id: String, _ reason: String) throws {
    try require(project.shots.contains { $0["shotId"] as? String == id }, "Unknown shot: \(id)")
    try require(!reason.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty, "A concrete redo reason is required")
    var manifest = try project.manifest(); var clips = manifest["clips"] as? [[String: Any]] ?? []
    for i in clips.indices where clips[i]["shotId"] as? String == id && clips[i]["selected"] as? Bool == true { clips[i]["status"] = "redo" }
    var requests = manifest["redoRequests"] as? [[String: Any]] ?? []
    requests.append(["shotId": id, "reason": reason, "at": ISO8601DateFormatter().string(from: Date()), "promptSha256": try project.prompt(id)])
    manifest["clips"] = clips; manifest["redoRequests"] = requests
    try write(manifest, project.path("manifest.json")); try status(project)
}
func assemble(_ project: Project) throws {
    let manifest = try project.manifest()
    let editURL = try project.path("edit.json")
    let edit = fm.fileExists(atPath: editURL.path) ? try read(editURL) : [:]
    let cuts = edit["shots"] as? [[String: Any]] ?? project.shots.map { ["shotId": $0["shotId"]!, "inSec": 0.0, "durationSec": $0["durationSec"] ?? 10.0] }
    let width = edit["width"] as? Int ?? 1280; let height = edit["height"] as? Int ?? 720; let fps = edit["fps"] as? Int ?? 24
    try require(width > 0 && height > 0 && width % 2 == 0 && height % 2 == 0 && fps > 0 && fps <= 120 && !cuts.isEmpty, "Invalid render settings")
    let work = try project.path("work/render-\(UUID().uuidString)"); try fm.createDirectory(at: work, withIntermediateDirectories: true)
    defer { try? fm.removeItem(at: work) }
    let cache = try project.path("work/cache"); try fm.createDirectory(at: cache, withIntermediateDirectories: true)
    var normalized: [URL] = []; var entries: [[String: Any]] = []; var cursor = 0.0
    for cut in cuts {
        guard let id = cut["shotId"] as? String, let take = project.selected(manifest, id), let rel = take["file"] as? String else { throw Failure("Missing selected clip: \(cut["shotId"] ?? "?")") }
        try require(take["status"] as? String != "redo", "\(id) needs a redo")
        try require(take["promptSha256"] as? String == (try project.prompt(id)), "\(id) has a stale prompt")
        let source = try project.path(rel); let hash = try sha(source)
        try require(hash == take["sha256"] as? String, "Checksum changed: \(id)")
        let media = try Media(source)
        let start = cut["inSec"] as? Double ?? 0; let duration = cut["durationSec"] as? Double ?? 3
        try require(start.isFinite && duration.isFinite && start >= 0 && duration > 0 && start + duration <= media.duration + 0.02, "Trim outside source duration: \(id)")
        try require(abs(duration * Double(fps) - (duration * Double(fps)).rounded()) < 0.001, "Trim duration must align to a frame at \(fps) fps: \(id)")
        try require((cut["transitionIn"] as? String ?? "cut") == "cut", "Only hard cuts are supported; unsupported transition in \(id)")
        let key = digest("v2|\(hash)|\(start)|\(duration)|\(width)|\(height)|\(fps)")
        let output = cache.appendingPathComponent("\(key).mp4")
        if !fm.fileExists(atPath: output.path) {
            let temp = work.appendingPathComponent("\(key).mp4")
            var args = ["-v", "error", "-nostdin", "-y", "-ss", String(start), "-i", source.path]
            if !media.audio { args += ["-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo"] }
            args += ["-map", "0:v:0", "-map", media.audio ? "0:a:0" : "1:a:0", "-t", String(duration),
                     "-vf", "scale=\(width):\(height):force_original_aspect_ratio=decrease,pad=\(width):\(height):(ow-iw)/2:(oh-ih)/2,setsar=1,fps=\(fps),setpts=PTS-STARTPTS",
                     "-af", "aresample=48000,apad,atrim=duration=\(duration),asetpts=PTS-STARTPTS", "-ac", "2",
                     "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
                     "-video_track_timescale", "24000", "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", temp.path]
            print("Normalize \(id) [\(start), \(start+duration))")
            try run("ffmpeg", args); try fm.moveItem(at: temp, to: output)
        } else { print("Cached \(id)") }
        normalized.append(output)
        entries.append(["shotId": id, "sourceFile": rel, "sourceSha256": hash, "promptSha256": take["promptSha256"]!, "sourceInSec": start, "sourceOutSec": start + duration, "startSec": cursor, "endSec": cursor + duration, "transitionIn": "cut"])
        cursor += duration
    }
    let concat = work.appendingPathComponent("concat.txt")
    // Cache filenames are hex; escape the directory too for project paths containing apostrophes.
    let list = normalized.map { "file '\($0.path.replacingOccurrences(of: "'", with: "'\\''"))'" }.joined(separator: "\n")
    try Data(list.utf8).write(to: concat)
    let video = work.appendingPathComponent("video.mp4")
    // Normalize once, then concatenate video by stream copy. Re-encode audio once
    // to eliminate per-segment AAC priming gaps and keep the final timeline exact.
    try run("ffmpeg", ["-v", "error", "-nostdin", "-y", "-f", "concat", "-safe", "0", "-i", concat.path, "-t", String(cursor), "-c:v", "copy", "-c:a", "aac", "-af", "aresample=async=1:first_pts=0", "-b:a", "160k", "-movflags", "+faststart", video.path])
    let result = try Media(video)
    try require(abs(result.duration - cursor) <= 0.12 && result.videoCodec == "h264" && result.audioCodec == "aac", "Final media does not match edit")
    try run("ffmpeg", ["-v", "error", "-nostdin", "-y", "-ss", String(min(cursor / 2, 2)), "-i", video.path, "-frames:v", "1", work.appendingPathComponent("poster.jpg").path])
    let final = try project.path("final"); try fm.createDirectory(at: final, withIntermediateDirectories: true)
    let order = entries.map { $0["shotId"]! }
    let outManifest: [String: Any] = ["slug": project.definition["slug"]!, "title": project.definition["title"]!, "file": "video.mp4", "sha256": try sha(video), "durationSec": result.duration, "timelineDurationSec": cursor, "resolution": "\(width)x\(height)", "fps": fps, "shotOrder": order, "reviewState": "unreviewed", "audioStems": [], "renderer": "Swift + FFmpeg; H.264/AAC; hard cuts", "createdAt": ISO8601DateFormatter().string(from: Date())]
    try write(["shotOrder": order, "entries": entries, "totalSec": cursor], work.appendingPathComponent("edl.json"))
    try write(outManifest, work.appendingPathComponent("final-manifest.json"))
    // Keep the previous deliverable recoverable before replacing it.
    if fm.fileExists(atPath: final.appendingPathComponent("video.mp4").path) {
        let archive = try project.path("work/final-history/\(UUID().uuidString)"); try fm.createDirectory(at: archive, withIntermediateDirectories: true)
        for name in ["video.mp4", "poster.jpg", "edl.json", "final-manifest.json"] where fm.fileExists(atPath: final.appendingPathComponent(name).path) { try fm.copyItem(at: final.appendingPathComponent(name), to: archive.appendingPathComponent(name)) }
    }
    for name in ["video.mp4", "poster.jpg", "edl.json", "final-manifest.json"] { try Data(contentsOf: work.appendingPathComponent(name)).write(to: final.appendingPathComponent(name), options: .atomic) }
    print("Saved \(final.appendingPathComponent("video.mp4").path): \(result.duration)s; visual review pending")
    try verify(project)
}
func verify(_ project: Project) throws {
    let manifest = try read(project.path("final/final-manifest.json")); let edl = try read(project.path("final/edl.json"))
    let video = try project.path("final/video.mp4"); let media = try Media(video)
    try require(try sha(video) == manifest["sha256"] as? String, "Final SHA256 mismatch")
    guard let expected = edl["totalSec"] as? Double, let entries = edl["entries"] as? [[String: Any]], let order = edl["shotOrder"] as? [String] else { throw Failure("Invalid EDL") }
    try require(!entries.isEmpty && order == entries.compactMap { $0["shotId"] as? String } && order == manifest["shotOrder"] as? [String], "EDL shot order mismatch")
    var cursor = 0.0
    for entry in entries {
        guard let start = entry["startSec"] as? Double, let end = entry["endSec"] as? Double else { throw Failure("Missing EDL timing") }
        try require(abs(start - cursor) < 0.001 && end > start, "EDL gap/overlap")
        guard let id = entry["shotId"] as? String else { throw Failure("Missing EDL shot") }
        try require(entry["promptSha256"] as? String == (try project.prompt(id)), "Final uses stale prompt: \(id)")
        cursor = end
    }
    try require(abs(cursor - expected) < 0.001 && abs(media.duration - expected) < 0.12 && abs(media.duration - (manifest["durationSec"] as? Double ?? -1)) < 0.01, "Final duration mismatch")
    try require(media.videoCodec == "h264" && media.audioCodec == "aac" && "\(media.width)x\(media.height)" == manifest["resolution"] as? String, "Final codecs/resolution mismatch")
    print("VERIFIED: checksum, EDL, duration, H.264/AAC, resolution. Review: \(manifest["reviewState"] ?? "unreviewed")")
}

func main() throws {
    let args = Array(CommandLine.arguments.dropFirst())
    guard args.count >= 2 else { print("""
    Usage: scripts/local-video.sh <command> <project-directory> [options]
      import PROJECT INPUT [--shot sNN] [--prompt-sha256 HASH]
      status PROJECT                         report missing/stale/redo queue (max 6)
      cards PROJECT                          render local title cards (no AI credits)
      assemble PROJECT                       use edit.json; cache normalized takes
      verify PROJECT                         validate saved media/EDL/checksum
      redo PROJECT --shot sNN --reason TEXT   preserve take and queue replacement
    """); return }
    let project = try Project(args[1]); let lock = try project.path(".local-video.lock")
    let fd = open(lock.path, O_CREAT | O_RDWR, S_IRUSR | S_IWUSR)
    try require(fd >= 0, "Cannot open project lock"); defer { close(fd) }
    try require(flock(fd, LOCK_EX | LOCK_NB) == 0, "Another local video operation is running for this project")
    defer { flock(fd, LOCK_UN) }
    func option(_ name: String) -> String? { guard let i = args.firstIndex(of: name), i+1 < args.count else { return nil }; return args[i+1] }
    switch args[0] {
    case "import": try require(args.count >= 3, "Missing input file/directory"); try ingest(project, args[2], option("--shot"), option("--prompt-sha256")); try status(project)
    case "status": try status(project)
    case "cards": try cards(project)
    case "redo-file":
        try require(args.count >= 3, "Missing redo request JSON")
        let request = try read(URL(fileURLWithPath: args[2]))
        try require(request["project"] as? String == project.definition["slug"] as? String, "Redo request belongs to a different project")
        guard let id = request["shotId"] as? String, let reason = request["reason"] as? String else { throw Failure("Invalid redo request") }
        try redo(project, id, reason)
    case "assemble": try assemble(project)
    case "verify": try verify(project)
    case "redo": guard let id = option("--shot"), let reason = option("--reason") else { throw Failure("redo needs --shot and --reason") }; try redo(project, id, reason)
    default: throw Failure("Unknown command: \(args[0])")
    }
}
do { try main() } catch { fputs("ERROR: \(error)\n", stderr); exit(1) }
