# Architecture

## Components
- **GUI (Tkinter):** controls, i18n, table, progress, logs
- **Shredder core:** overwrite strategies, verification, renaming, deletion
- **Reporting:** CSV/JSON writer

## Classes
- `App`: GUI, i18n, event handling
- `Shredder`: core logic, `wipe_file(path, method, verify, renames)` → `ReportRow`
- `ReportRow`: structured result

## Flow (File)
1. Open file `r+b`  
2. For each pass: overwrite in chunks, flush+fsync  
3. Optional verify for fixed patterns  
4. Optional renames  
5. Delete file

## Flow (Folder)
Recursive: wipe files first, then remove empty folders.

## i18n
Full EN/DE localization for all UI elements, combobox labels, dialogs.
