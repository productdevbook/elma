//! elma — an iPhone/iPad device manager.

mod bridge;

use bridge::{Bridge, BridgeError};
use serde_json::Value;
use std::sync::Arc;

use tauri::{Emitter, Manager, State};

/// The bridge is created inside the async runtime (tokio's process API needs a
/// reactor), so commands may run before it exists. They wait on this cell
/// rather than racing setup.
struct AppState {
    bridge: tokio::sync::OnceCell<Bridge>,
}

impl AppState {
    async fn bridge(&self) -> Result<&Bridge, BridgeError> {
        self.bridge.get().ok_or(BridgeError::Closed)
    }
}

/// Every command is a thin pass-through: the Python side owns the protocol
/// details, and keeping the mapping mechanical means adding a feature is a
/// one-line change on both ends.
macro_rules! forward {
    ($name:ident, $method:literal) => {
        #[tauri::command]
        async fn $name(
            state: State<'_, AppState>,
            params: Option<Value>,
        ) -> Result<Value, BridgeError> {
            state
                .bridge()
                .await?
                .call($method, params.unwrap_or(Value::Object(Default::default())))
                .await
        }
    };
}

forward!(device_list, "device.list");
forward!(device_info, "device.info");
forward!(app_list, "app.list");
forward!(file_list, "file.list");
forward!(ios_signed_versions, "ios.signedVersions");
forward!(app_icons, "app.icons");
forward!(file_pull, "file.pull");
forward!(backup_create, "backup.create");
forward!(backup_info, "backup.info");
forward!(backup_encryption, "backup.encryption");

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .setup(|app| {
            // Resolve the interpreter: an explicit override first (used in
            // development), then the runtime vendored into the bundle, then
            // whatever python3 is on PATH as a last resort.
            let resource_dir = app.path().resource_dir().ok();
            let bridge_dir = std::env::var("ELMA_BRIDGE_DIR")
                .map(std::path::PathBuf::from)
                .ok()
                .or_else(|| resource_dir.as_ref().map(|d| d.join("python")))
                .unwrap_or_else(|| std::path::PathBuf::from("python"));

            let python = std::env::var("ELMA_PYTHON").ok().unwrap_or_else(|| {
                let vendored = bridge_dir.join(".runtime/bin/python3");
                if vendored.is_file() {
                    vendored.to_string_lossy().into_owned()
                } else {
                    "python3".to_string()
                }
            });
            let cwd = bridge_dir;

            // Progress events from the bridge become webview events under
            // the same name, so the UI listens for e.g. "backup.progress".
            let handle = app.handle().clone();
            let sink: bridge::EventSink = Arc::new(move |name, data| {
                let _ = handle.emit(&name, data);
            });

            app.manage(AppState { bridge: tokio::sync::OnceCell::new() });

            // Spawning the bridge touches tokio's process API, which needs a
            // running reactor — setup() has none, so defer onto the runtime.
            let handle2 = app.handle().clone();
            tauri::async_runtime::spawn(async move {
                match Bridge::spawn(&python, &cwd, sink) {
                    Ok(b) => {
                        let state = handle2.state::<AppState>();
                        let _ = state.bridge.set(b);
                        let _ = handle2.emit("bridge.ready", ());
                    }
                    Err(e) => {
                        let _ = handle2.emit("bridge.failed", e.to_string());
                    }
                }
            });
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            device_list,
            device_info,
            app_list,
            file_list,
            ios_signed_versions,
            app_icons,
            file_pull,
            backup_create,
            backup_info,
            backup_encryption,
        ])
        .run(tauri::generate_context!())
        .expect("error while running elma");
}
