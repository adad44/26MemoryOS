import CSQLite
import Foundation

private let SQLITE_TRANSIENT = unsafeBitCast(-1, to: sqlite3_destructor_type.self)

final class Database {
    private var db: OpaquePointer?
    private let queue = DispatchQueue(label: "memoryos.database")

    init(path: String) throws {
        if sqlite3_open(path, &db) != SQLITE_OK {
            throw DatabaseError.open(message: lastError)
        }
        try migrate()
    }

    deinit {
        sqlite3_close(db)
    }

    func insertCapture(_ capture: CaptureRecord) {
        queue.sync {
            let sql = """
            INSERT INTO captures
            (timestamp, app_name, window_title, content, source_type, url, file_path)
            VALUES (?, ?, ?, ?, ?, ?, ?);
            """
            withStatement(sql) { statement in
                bindDate(capture.timestamp, to: 1, in: statement)
                bindText(capture.appName, to: 2, in: statement)
                bindText(capture.windowTitle, to: 3, in: statement)
                bindText(capture.content, to: 4, in: statement)
                bindText(capture.sourceType.rawValue, to: 5, in: statement)
                bindText(capture.url, to: 6, in: statement)
                bindText(capture.filePath, to: 7, in: statement)
                step(statement)
            }
        }
    }

    func startSession(appName: String, at startTime: Date) -> AppSession? {
        queue.sync {
            let sql = "INSERT INTO sessions (app_name, start_time) VALUES (?, ?);"
            var result: AppSession?
            withStatement(sql) { statement in
                bindText(appName, to: 1, in: statement)
                bindDate(startTime, to: 2, in: statement)
                if step(statement) {
                    result = AppSession(
                        id: sqlite3_last_insert_rowid(db),
                        appName: appName,
                        startTime: startTime
                    )
                }
            }
            return result
        }
    }

    func endSession(_ session: AppSession, at endTime: Date) {
        queue.sync {
            let duration = max(0, Int(endTime.timeIntervalSince(session.startTime)))
            let sql = "UPDATE sessions SET end_time = ?, duration_s = ? WHERE id = ?;"
            withStatement(sql) { statement in
                bindDate(endTime, to: 1, in: statement)
                sqlite3_bind_int(statement, 2, Int32(duration))
                sqlite3_bind_int64(statement, 3, session.id)
                step(statement)
            }
        }
    }

    func captureCountsByApp(limit: Int = 20) -> [(String, Int)] {
        queue.sync {
            let sql = """
            SELECT app_name, COUNT(*) FROM captures
            GROUP BY app_name
            ORDER BY 2 DESC
            LIMIT ?;
            """
            var rows: [(String, Int)] = []
            withStatement(sql) { statement in
                sqlite3_bind_int(statement, 1, Int32(limit))
                while sqlite3_step(statement) == SQLITE_ROW {
                    let appName = sqlite3_column_text(statement, 0).map { String(cString: $0) } ?? "unknown"
                    let count = Int(sqlite3_column_int(statement, 1))
                    rows.append((appName, count))
                }
            }
            return rows
        }
    }

    private func migrate() throws {
        let schema = """
        PRAGMA journal_mode = WAL;
        CREATE TABLE IF NOT EXISTS captures (
          id           INTEGER PRIMARY KEY,
          timestamp    DATETIME NOT NULL,
          app_name     TEXT NOT NULL,
          window_title TEXT,
          content      TEXT NOT NULL,
          source_type  TEXT NOT NULL,
          url          TEXT,
          file_path    TEXT,
          is_noise     INTEGER DEFAULT NULL,
          embedding    BLOB
        );

        CREATE TABLE IF NOT EXISTS sessions (
          id          INTEGER PRIMARY KEY,
          app_name    TEXT NOT NULL,
          start_time  DATETIME NOT NULL,
          end_time    DATETIME,
          duration_s  INTEGER
        );

        CREATE INDEX IF NOT EXISTS idx_captures_timestamp ON captures(timestamp);
        CREATE INDEX IF NOT EXISTS idx_captures_app ON captures(app_name);
        CREATE INDEX IF NOT EXISTS idx_sessions_app ON sessions(app_name);
        """

        var error: UnsafeMutablePointer<CChar>?
        if sqlite3_exec(db, schema, nil, nil, &error) != SQLITE_OK {
            let message = error.map { String(cString: $0) } ?? lastError
            sqlite3_free(error)
            throw DatabaseError.migration(message: message)
        }
    }

    private func withStatement(_ sql: String, _ body: (OpaquePointer?) -> Void) {
        var statement: OpaquePointer?
        if sqlite3_prepare_v2(db, sql, -1, &statement, nil) != SQLITE_OK {
            fputs("SQLite prepare failed: \(lastError)\n", stderr)
            return
        }
        defer { sqlite3_finalize(statement) }
        body(statement)
    }

    @discardableResult
    private func step(_ statement: OpaquePointer?) -> Bool {
        let result = sqlite3_step(statement)
        if result != SQLITE_DONE && result != SQLITE_ROW {
            fputs("SQLite step failed: \(lastError)\n", stderr)
            return false
        }
        return true
    }

    private func bindDate(_ date: Date, to index: Int32, in statement: OpaquePointer?) {
        bindText(Self.dateFormatter.string(from: date), to: index, in: statement)
    }

    private func bindText(_ value: String?, to index: Int32, in statement: OpaquePointer?) {
        guard let value else {
            sqlite3_bind_null(statement, index)
            return
        }
        sqlite3_bind_text(statement, index, value, -1, SQLITE_TRANSIENT)
    }

    private var lastError: String {
        db.flatMap { sqlite3_errmsg($0).map { String(cString: $0) } } ?? "unknown SQLite error"
    }

    private static let dateFormatter: ISO8601DateFormatter = {
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        return formatter
    }()
}

enum DatabaseError: Error, CustomStringConvertible {
    case open(message: String)
    case migration(message: String)

    var description: String {
        switch self {
        case .open(let message): "Could not open SQLite database: \(message)"
        case .migration(let message): "Could not migrate SQLite database: \(message)"
        }
    }
}
