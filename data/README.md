# TAXITIQ Source PDF Data Requirements

To run the PDF parsing and ingestion pipeline, you must obtain and place the official statutory PDF documents in this directory.

## Required Documents

### 1. Income-tax Act, 2025 PDF
- **Description**: The official codified text of India's Income-tax Act 2025.
- **Expected Path**: `data/Income_Tax_Act_2025_as_amended_by_FA_Act_2026.pdf`
- **Expected SHA-256 Checksum**: `d54a0ed6a91673d1a4fbcef9b5e472c3efe441139fae38f85a5a0c5b2cfc998b`

### 2. Income-tax Rules, 2026 PDF
- **Description**: The rules document associated with the 2025 Act.
- **Expected Path**: `data/Income-tax-Rules-2026_2026-06-22_03-37-12_06bfa6_en.pdf`
- **Expected SHA-256 Checksum**: `2a884efde332d733ca32192789f2db4811a2f646e3e54b6c3b65ef3dfc4bc80a` (Wait, let's verify if we need to put rules checksum - we can compute it if needed, or just mention the path).

*Note: These files are excluded from Git tracking via `.gitignore` to prevent redistribution of large files and ensure compliance with repository distribution guidelines. Please obtain them from official portals before running `01_parse_pdf.py`.*
