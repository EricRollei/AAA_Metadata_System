# AAA_Metadata_System — temporary fixes (2026-11-03)

Applied during a ComfyUI startup-log cleanup. These are stopgaps; fold proper fixes into the planned update.

## Applied

1. **`TEMPLATE_` files were imported as nodes** (`__init__.py`, node loop)
   - `nodes/TEMPLATE_Multi_LoRA_Loader_Platform.py` failed every launch: `name 'REQUIRES_CLIP' is not defined`.
   - Temp fix: loop now skips files starting with `TEMPLATE_`.
   - Proper fix: move templates out of `nodes/` (e.g. `templates/`), or make the template importable.

2. **JS extension was installed twice** (`__init__.py`, `install_web_extensions()`)
   - The package sets `WEB_DIRECTORY = "./web"` (served by ComfyUI) AND copied `web/*.js` into
     `ComfyUI/web/extensions/MetadataSystem/` on every start — two copies of `lora_gallery_extension.js`.
   - Temp fix: copy gated behind `INSTALL_LEGACY_WEB_COPY = False`; the old copied folder was moved to
     `custom_nodes/.disabled/_legacy_web_ext_MetadataSystem`.
   - Proper fix: delete `install_web_extensions()` entirely; rely on `WEB_DIRECTORY`.

3. **Wrong import path in `web/lora_gallery_extension.js`**
   - `import { app } from "../scripts/app.js"` resolves to `/extensions/scripts/app.js` (404).
     Extensions are served at `/extensions/<pack>/file.js`, so it must be `../../scripts/app.js`.
   - Temp fix: path corrected.

## Still open (not touched)

4. **Package `__init__` runs twice at startup** — every "Loaded node module: …" line appears twice in the log.
   Likely cause: ComfyUI loads the pack under its full-path module name, while other packs
   (`Eric-image-classification`, `Eric_Krea2/_trigger_words.py`, `eric_semantic_search`) do
   `from AAA_Metadata_System import MetadataService`; if that import happens before the
   `sys.modules['AAA_Metadata_System']` alias is set, Python imports a second copy.
   Fix idea: in consumers, resolve via `sys.modules` first / lazy-import inside functions; or have the
   pack's import guard check for an already-loaded instance.
5. `metadata.db` lives inside the package folder — consider moving to `ComfyUI/user/` so updates/reinstalls don't touch it.
6. `lora_gallery_extension.js` uses the legacy `app` import; plan migration to the current frontend extension API.
