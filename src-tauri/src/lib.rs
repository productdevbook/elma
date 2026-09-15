//! elma — an iPhone/iPad device manager.

mod bridge;

use bridge::{Bridge, BridgeError};
use serde_json::Value;
use tauri::{Manager, State};

struct AppState {
    bridge: Bridge,
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
                .bridge
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

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .setup(|app| {
            // In development the bridge runs from the repo; a packaged build
            // ships its own interpreter next to the binary.
            let python = std::env::var("ELMA_PYTHON")
                .unwrap_or_else(|_| "python3".to_string());
            let cwd = std::env::var("ELMA_BRIDGE_DIR")
                .map(std::path::PathBuf::from)
                .unwrap_or_else(|_| {
                    app.path()
                        .resource_dir()
                        .map(|d| d.join("python"))
                        .unwrap_or_else(|_| std::path::PathBuf::from("python"))
                });

            let bridge = Bridge::spawn(&python, &cwd)?;
            app.manage(AppState { bridge });
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            device_list,
            device_info,
            app_list,
            file_list,
            ios_signed_versions,
        ])
        .run(tauri::generate_context!())
        .expect("error while running elma");
}
