# Shared test fixtures (messy-data edge cases)

- `messy_unsupported.bin` — binary bytes; parse as `application/octet-stream` → empty extract (no OCR claim).
- `messy_empty_pdf.pdf` — minimal/degenerate PDF; extract may be empty without failing the worker path.

See `docs/documentation/ai.md` § Messy-data pipeline.
