import Foundation
import Glibc
import IMEKit

let env = ProcessInfo.processInfo.environment
let home = FileManager.default.homeDirectoryForCurrentUser.path
let data = (env["XDG_DATA_HOME"] ?? home + "/.local/share") + "/myime"
let config = (env["XDG_CONFIG_HOME"] ?? home + "/.config") + "/myime/preferences.json"
try FileManager.default.createDirectory(atPath: data, withIntermediateDirectories: true,
                                        attributes: [.posixPermissions: 0o700])
let replacement = data + "/system.sqlite"
let database = env["MYIME_SYSTEM_DATABASE"] ?? (FileManager.default.fileExists(atPath: replacement) ? replacement : "/usr/share/myime/system.sqlite")
guard let system = SQLiteStore(path: database), let user = UserStore(path: data + "/user.sqlite") else {
    fatalError("MyIME could not open the dictionary or learning database")
}
func prefs() -> EnginePrefs {
    guard let bytes = FileManager.default.contents(atPath: config),
          let result = try? JSONDecoder().decode(EnginePrefs.self, from: bytes) else { return EnginePrefs() }
    return result
}
if CommandLine.arguments.count > 1 {
    let args = Array(CommandLine.arguments.dropFirst())
    switch args {
    case ["defaults"]:
        print(String(decoding: try JSONEncoder().encode(EnginePrefs()), as: UTF8.self))
    case ["clear-learning"]: user.clearLearning()
    case ["validate"]: exit(system.integrityCheck() ? 0 : 1)
    default:
        guard args.count == 2 else { exit(2) }
        let url = URL(fileURLWithPath: args[1])
        if args[0] == "import" { print(user.importTSV(from: url)) }
        else if args[0] == "export" { try user.exportTSV(to: url) }
        else { exit(2) }
    }
    user.waitForPendingWrites()
    exit(0)
}

var engine = Engine(store: system, userStore: user)
var output = EngineOutput(preedit: "", candidates: [], hasMore: false, raw: "")
var raw = "", composed = ""
var syllables: [String] = []
var suggesting = false
@MainActor func clear() {
    raw = ""; composed = ""; syllables = []; suggesting = false
    output = EngineOutput(preedit: "", candidates: [], hasMore: false, raw: "")
}
while let line = readLine() {
    do {
        let req = try JSONSerialization.jsonObject(with: Data(line.utf8)) as? [String: Any] ?? [:]
        let pref = prefs()
        var commit = ""
        switch req["op"] as? String {
        case "reset":
            clear()
            engine = Engine(store: system, userStore: user)
        case "append", "back":
            if req["op"] as? String == "back" {
                if !raw.isEmpty { raw.removeLast() }
            } else { raw += req["text"] as? String ?? "" }
            suggesting = false
            output = engine.update(raw, prefs: pref)
            if !raw.isEmpty, let words = req["english"] as? [String], !words.isEmpty {
                var candidates = output.candidates
                let extra = words.prefix(2).enumerated().map { i, word in
                    Candidate(id: Int64.min / 2 + Int64(i), word: word, pinyinPath: [], score: 0, consumedLength: raw.count)
                }
                candidates.insert(contentsOf: extra, at: min(3, candidates.count))
                output = EngineOutput(preedit: output.preedit, candidates: Array(candidates.prefix(100)),
                                      hasMore: output.hasMore || candidates.count > 100, raw: raw)
            }
        case "literal":
            commit = composed + raw
            engine.breakPhraseLearningContext()
            clear()
        case "select":
            if let i = req["index"] as? Int, output.candidates.indices.contains(i) {
                let c = output.candidates[i]
                if suggesting {
                    commit = c.word
                    engine.commitLearning(word: c.word, pinyin: [])
                } else {
                    let result = engine.select(i, from: output)
                    if !c.pinyinPath.isEmpty { engine.commitLearning(word: c.word, pinyin: c.pinyinPath) }
                    composed += result.commitText
                    syllables += c.pinyinPath
                    raw = result.remainingRaw
                    if raw.isEmpty {
                        commit = composed
                        if c.pinyinPath.isEmpty { engine.breakPhraseLearningContext(); clear() }
                        else {
                            engine.commitUserPhrase(word: composed, pinyin: syllables)
                            suggesting = true
                            composed = ""; syllables = []
                        }
                    } else { output = engine.update(raw, prefs: pref) }
                }
                if suggesting {
                    let candidates = engine.suggestions(limit: max(36, pref.pageSize))
                    output = EngineOutput(preedit: "", candidates: candidates, hasMore: false, raw: "")
                    suggesting = !candidates.isEmpty
                }
            }
        default: break
        }
        func localize(_ value: String) -> String {
            pref.outputTraditional ? system.traditionalConverter.convert(value) : value
        }
        let response: [String: Any] = [
            "commit": localize(commit), "raw": raw, "preedit": localize(composed) + (output.preedit.isEmpty ? raw : output.preedit),
            "suggesting": suggesting, "pageSize": min(9, max(1, pref.pageSize)),
            "vertical": pref.orientation == .vertical,
            "words": output.candidates.map { candidate in
                let gloss = pref.showEnglishGloss ? candidate.displayGloss : nil
                return localize(candidate.word) + (gloss.map { " · " + $0 } ?? "")
            }
        ]
        print(String(decoding: try JSONSerialization.data(withJSONObject: response), as: UTF8.self))
    } catch { print("{}") }
    fflush(nil)
}
user.waitForPendingWrites()
