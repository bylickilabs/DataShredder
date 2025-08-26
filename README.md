# Data Shredder

|<img width="1280" height="640" alt="shredder" src="https://github.com/user-attachments/assets/782d1f8f-6eb8-4c36-8002-cf4f3f67fa2d" />|
|---|

**Secure deletion of files and folders** (Windows / Linux / macOS) using **multi-pass overwrite** strategies.  
Light Tkinter GUI, full **EN/DE language toggle**, **CSV/JSON reports**, robust error handling.

---

## Highlights
- **Wipe Methods:** Zero (1x), Random (1x), **DoD 5220.22‑M (3x)**, **NIST SP 800‑88 (1x random)**, **Gutmann (35x)**
- **Recursive folder shredding**, **symlink skip** (removes link only)
- **Rename-before-delete** (configurable), **verification** for fixed patterns (0x00/0xFF)
- **Progress bar**, **ETA**, **cancel button**, **live log**
- **Export** results as **CSV/JSON** (path, method, size, passes, rename, verification, duration, result)

> ⚠️ **SSDs**: Due to wear-leveling/TRIM, secure deletion cannot be guaranteed.
  - Use **full-disk encryption** and **vendor secure erase** for high-security requirements.

---

## Quickstart
```bash
python app.py
```
1. Add files/folders → 2. Select method → 3. Start → 4. Export report

---

## Scope
- GUI: Light-only, DE/EN toggle, clear status messages
- Core: Chunk-based overwrites (default: 8 MB) with fsync flush per pass
- Verification: Byte-by-byte for fixed patterns; random cannot be verified
- Rename: Multiple random renames before delete (optional)
- Reports: CSV/JSON with all relevant fields for compliance

---

## Risks
- SSDs and modern filesystems abstract sectors → no hard guarantee of data erasure
- Locked files or insufficient privileges can block operations (see **Troubleshooting**)

---

## License
[LICENSE](LICENSE)
- ©Thorsten Bylicki | ©BYLICKILABS
