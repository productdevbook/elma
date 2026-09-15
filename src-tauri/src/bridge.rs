//! Talks to the Python bridge process.
//!
//! The bridge is spawned once and kept alive: it holds the open lockdown
//! connection, so a per-request process would pay the handshake every time.
//! Requests are matched to responses by id, which lets calls overlap.

use std::collections::HashMap;
use std::process::Stdio;
use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::Arc;

use serde::{Deserialize, Serialize};
use serde_json::Value;
use tokio::io::{AsyncBufReadExt, AsyncWriteExt, BufReader};
use tokio::process::{Child, ChildStdin, Command};
use tokio::sync::{oneshot, Mutex};

#[derive(Debug, thiserror::Error)]
pub enum BridgeError {
    #[error("bridge process failed to start: {0}")]
    Spawn(#[from] std::io::Error),
    #[error("bridge process is gone")]
    Closed,
    #[error("{kind}: {message}")]
    Device { kind: String, message: String },
}

impl Serialize for BridgeError {
    fn serialize<S: serde::Serializer>(&self, s: S) -> Result<S::Ok, S::Error> {
        use serde::ser::SerializeMap;
        let mut m = s.serialize_map(Some(2))?;
        match self {
            BridgeError::Device { kind, message } => {
                m.serialize_entry("kind", kind)?;
                m.serialize_entry("message", message)?;
            }
            other => {
                m.serialize_entry("kind", "bridge")?;
                m.serialize_entry("message", &other.to_string())?;
            }
        }
        m.end()
    }
}

#[derive(Deserialize)]
struct Response {
    id: Option<u64>,
    ok: Option<bool>,
    result: Option<Value>,
    error: Option<ResponseError>,
    event: Option<String>,
    data: Option<Value>,
}

#[derive(Deserialize)]
struct ResponseError {
    kind: String,
    message: String,
}

type Pending = Arc<Mutex<HashMap<u64, oneshot::Sender<Result<Value, BridgeError>>>>>;

/// Called for every `{"event": ...}` line the bridge emits. Used to forward
/// progress out to the webview; the bridge itself stays UI-agnostic.
pub type EventSink = Arc<dyn Fn(String, Value) + Send + Sync>;

pub struct Bridge {
    stdin: Mutex<ChildStdin>,
    pending: Pending,
    next_id: AtomicU64,
    last_error: Arc<Mutex<Option<String>>>,
    _child: Child,
}

impl Bridge {
    /// Spawns the bridge and starts the reader task that fans responses
    /// back out to whoever is waiting on each id.
    pub fn spawn(
        python: &str,
        cwd: &std::path::Path,
        on_event: EventSink,
    ) -> Result<Self, BridgeError> {
        let mut child = Command::new(python)
            .arg("-m")
            .arg("elma_bridge")
            .current_dir(cwd)
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .stderr(Stdio::piped())
            .kill_on_drop(true)
            .spawn()?;

        let stdin = child.stdin.take().ok_or(BridgeError::Closed)?;
        let stdout = child.stdout.take().ok_or(BridgeError::Closed)?;
        let stderr = child.stderr.take().ok_or(BridgeError::Closed)?;

        // A bridge that dies on import (missing dependency, wrong interpreter)
        // would otherwise just look like a hang. Keep the tail of stderr so the
        // failure can be shown instead of an empty window.
        let last_error: Arc<Mutex<Option<String>>> = Arc::new(Mutex::new(None));
        let err_slot = last_error.clone();
        tokio::spawn(async move {
            let mut lines = BufReader::new(stderr).lines();
            let mut tail: Vec<String> = Vec::new();
            while let Ok(Some(line)) = lines.next_line().await {
                eprintln!("[bridge] {line}");
                tail.push(line);
                if tail.len() > 20 {
                    tail.remove(0);
                }
                *err_slot.lock().await = Some(tail.join("\n"));
            }
        });
        let pending: Pending = Arc::new(Mutex::new(HashMap::new()));

        let reader_pending = pending.clone();
        tokio::spawn(async move {
            let mut lines = BufReader::new(stdout).lines();
            while let Ok(Some(line)) = lines.next_line().await {
                let Ok(resp) = serde_json::from_str::<Response>(&line) else {
                    continue;
                };
                // Events carry no id; hand them to the sink instead.
                if let Some(name) = resp.event {
                    on_event(name, resp.data.unwrap_or(Value::Null));
                    continue;
                }
                let Some(id) = resp.id else { continue };
                let Some(tx) = reader_pending.lock().await.remove(&id) else {
                    continue;
                };
                let outcome = if resp.ok.unwrap_or(false) {
                    Ok(resp.result.unwrap_or(Value::Null))
                } else {
                    let e = resp.error.unwrap_or(ResponseError {
                        kind: "unknown".into(),
                        message: "no error detail".into(),
                    });
                    Err(BridgeError::Device { kind: e.kind, message: e.message })
                };
                let _ = tx.send(outcome);
            }
            // stdout closed: nothing more will arrive, so release the waiters.
            let mut map = reader_pending.lock().await;
            for (_, tx) in map.drain() {
                let _ = tx.send(Err(BridgeError::Closed));
            }
        });

        Ok(Self {
            stdin: Mutex::new(stdin),
            pending,
            next_id: AtomicU64::new(1),
            last_error,
            _child: child,
        })
    }

    pub async fn call(&self, method: &str, params: Value) -> Result<Value, BridgeError> {
        let id = self.next_id.fetch_add(1, Ordering::Relaxed);
        let (tx, rx) = oneshot::channel();
        self.pending.lock().await.insert(id, tx);

        let payload = serde_json::json!({ "id": id, "method": method, "params": params });
        let mut line = serde_json::to_string(&payload).map_err(|_| BridgeError::Closed)?;
        line.push('\n');

        {
            let mut stdin = self.stdin.lock().await;
            stdin.write_all(line.as_bytes()).await?;
            stdin.flush().await?;
        }

        match rx.await {
            Ok(outcome) => outcome,
            Err(_) => {
                // The bridge went away mid-call; its stderr says why.
                let detail = self.last_error.lock().await.clone();
                Err(match detail {
                    Some(d) => BridgeError::Device {
                        kind: "bridge_crashed".into(),
                        message: d,
                    },
                    None => BridgeError::Closed,
                })
            }
        }
    }
}
