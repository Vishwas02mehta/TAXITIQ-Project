# TAXITIQ License Review

This document outlines options for licensing the TAXITIQ repository prior to public publication.

## 1. Open Source License Options

### MIT License
- **Description**: A highly permissive, lightweight license.
- **Permissions**: Anyone can use, modify, distribute, and sell the software without restrictions.
- **Conditions**: The original license and copyright notice must be included.
- **Best for**: Maximizing community adoption and simplicity.

### Apache-2.0 License
- **Description**: A permissive license similar to MIT but with explicit patent grants and trademark limitations.
- **Permissions**: Anyone can use, modify, and distribute the software.
- **Conditions**: Must include the copyright notice, a copy of the license, and clear attribution of changes made.
- **Best for**: Larger community-driven projects where trademark protections and patent safety are desired.

---

## 2. Corpus Redistribution Licensing Concerns
The repository indexes and references two primary documents in the `data/` subdirectory:
1. **Income-tax Act, 2025**
2. **Income-tax Rules, 2026**

These documents are public legislative statutory texts published by the Government of India. 
- **Copyright status**: Public domain/non-copyrightable legislative texts in India under Section 52(1)(q) of the Indian Copyright Act, 1957.
- **Recommendation**: Redirection links to official governmental portals can be provided to avoid storing large PDFs (such as the 72MB rules PDF) directly inside the Git repository, which keeps the repository lightweight and avoids any licensing redistribution disputes.

---

## 3. Decision
A final `LICENSE` file has not been initialized. It is recommended that the project author review these options and select either MIT or Apache-2.0 prior to push.
