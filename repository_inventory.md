# TAXITIQ Project Repository Inventory

| Relative Path | File Type | Size (Bytes) | SHA-256 | Git Action | Reason |
| --- | --- | --- | --- | --- | --- |
| `01_parse_pdf.py` | source code | 5425 | `b17646e2...` | **TRACK** | Main numbered execution scripts must stay at root to preserve imports and paths |
| `02_chunker.py` | source code | 13132 | `decb21c3...` | **TRACK** | Main numbered execution scripts must stay at root to preserve imports and paths |
| `03_ingest.py` | source code | 37041 | `d0aa98ee...` | **TRACK** | Main numbered execution scripts must stay at root to preserve imports and paths |
| `04_search.py` | source code | 25489 | `0c0f0516...` | **TRACK** | Main numbered execution scripts must stay at root to preserve imports and paths |
| `05_reranker.py` | source code | 21856 | `b4027768...` | **TRACK** | Main numbered execution scripts must stay at root to preserve imports and paths |
| `06_context_builder.py` | source code | 15602 | `8098d883...` | **TRACK** | Main numbered execution scripts must stay at root to preserve imports and paths |
| `07_answer_engine.py` | source code | 17657 | `5510c910...` | **TRACK** | Main numbered execution scripts must stay at root to preserve imports and paths |
| `08_multi_llm_generator.py` | source code | 47861 | `17f7c956...` | **TRACK** | Main numbered execution scripts must stay at root to preserve imports and paths |
| `09_build_evaluation_dataset.py` | source code | 61755 | `9d7dd316...` | **TRACK** | Main numbered execution scripts must stay at root to preserve imports and paths |
| `10_evaluate_rag.py` | source code | 109227 | `b690a2bb...` | **TRACK** | Main numbered execution scripts must stay at root to preserve imports and paths |
| `11_statistical_analysis.py` | source code | 61921 | `eb67c572...` | **TRACK** | Main numbered execution scripts must stay at root to preserve imports and paths |
| `12_results_integrity_audit.py` | source code | 26318 | `bfa0c6f9...` | **TRACK** | Main numbered execution scripts must stay at root to preserve imports and paths |
| `13_generate_paper_artifacts.py` | source code | 72582 | `b9b564ab...` | **TRACK** | Main numbered execution scripts must stay at root to preserve imports and paths |
| `_analyze_jsons.py` | source code | 6633 | `716ae479...` | **TRACK** | Helper utilities must stay at root to preserve relative imports |
| `answer.json` | unknown | 8965 | `e5a948bc...` | **TRACK** | Standard project file |
| `answer_validator.py` | source code | 11223 | `13d2243f...` | **TRACK** | Helper utilities must stay at root to preserve relative imports |
| `assembled_context.json` | unknown | 8259 | `c368957b...` | **TRACK** | Standard project file |
| `assembled_context_debug.md` | unknown | 6414 | `20ddce4d...` | **TRACK** | Standard project file |
| `assessment_year_trace.json` | unknown | 2864 | `7f7c19ea...` | **TRACK** | Standard project file |
| `authoritative_paired_outcomes.csv` | paper artifact | 5026 | `a9384469...` | **TRACK** | CSV tables used in paper |
| `chroma_db/c03f8261-6601-4ec4-b0e1-1192e64240f9/data_level0.bin` | cache | 17350656 | `fcaf9f9f...` | **IGNORE** | Local database files are machine-specific caches |
| `chroma_db/c03f8261-6601-4ec4-b0e1-1192e64240f9/header.bin` | cache | 100 | `e02d6e50...` | **IGNORE** | Local database files are machine-specific caches |
| `chroma_db/c03f8261-6601-4ec4-b0e1-1192e64240f9/index_metadata.pickle` | cache | 344208 | `5fc2e278...` | **IGNORE** | Local database files are machine-specific caches |
| `chroma_db/c03f8261-6601-4ec4-b0e1-1192e64240f9/length.bin` | cache | 16384 | `a433faca...` | **IGNORE** | Local database files are machine-specific caches |
| `chroma_db/c03f8261-6601-4ec4-b0e1-1192e64240f9/link_lists.bin` | cache | 35560 | `4ea7d205...` | **IGNORE** | Local database files are machine-specific caches |
| `chroma_db/cb660bc4-21d0-49f6-89d4-caa951e917c6/data_level0.bin` | cache | 13008756 | `016d6d59...` | **IGNORE** | Local database files are machine-specific caches |
| `chroma_db/cb660bc4-21d0-49f6-89d4-caa951e917c6/header.bin` | cache | 100 | `daf6db59...` | **IGNORE** | Local database files are machine-specific caches |
| `chroma_db/cb660bc4-21d0-49f6-89d4-caa951e917c6/index_metadata.pickle` | cache | 258104 | `a564c7d2...` | **IGNORE** | Local database files are machine-specific caches |
| `chroma_db/cb660bc4-21d0-49f6-89d4-caa951e917c6/length.bin` | cache | 12284 | `823161da...` | **IGNORE** | Local database files are machine-specific caches |
| `chroma_db/cb660bc4-21d0-49f6-89d4-caa951e917c6/link_lists.bin` | cache | 26156 | `3c26ba6e...` | **IGNORE** | Local database files are machine-specific caches |
| `chroma_db/chroma.sqlite3` | cache | 25747456 | `5a4936c4...` | **IGNORE** | Local database files are machine-specific caches |
| `chunks.json` | unknown | 3741952 | `70731288...` | **TRACK** | Standard project file |
| `context_utils.py` | source code | 20654 | `5bddabd3...` | **TRACK** | Helper utilities must stay at root to preserve relative imports |
| `conversation_memory.py` | source code | 1176 | `40680cbb...` | **TRACK** | Helper utilities must stay at root to preserve relative imports |
| `data/Income-tax-Rules-2026_2026-06-22_03-37-12_06bfa6_en.pdf` | dataset | 72087635 | `2f862294...` | **IGNORE** | Ignore rule applies to rulebook due to large file size (>50MB), track Act PDF |
| `data/Income_Tax_Act_2025_as_amended_by_FA_Act_2026.pdf` | dataset | 3299341 | `d54a0ed6...` | **TRACK** | Ignore rule applies to rulebook due to large file size (>50MB), track Act PDF |
| `evaluation_classification_changes_v2.json` | result | 111463 | `a2e19ecc...` | **TRACK** | Immutable experimental result file |
| `evaluation_dataset.json` | result | 62501 | `05b26d2e...` | **TRACK** | Immutable experimental result file |
| `evaluation_dataset_audit.json` | unknown | 251164 | `1a292e4f...` | **TRACK** | Standard project file |
| `evaluation_dataset_audit.md` | unknown | 7130 | `d62575ac...` | **TRACK** | Standard project file |
| `evaluation_dataset_audit_pre_repair.json` | unknown | 247593 | `d69960be...` | **TRACK** | Standard project file |
| `evaluation_dataset_audit_pre_repair.md` | unknown | 8012 | `d3e126eb...` | **TRACK** | Standard project file |
| `evaluation_dataset_pre_repair.json` | unknown | 61176 | `0ffefa2a...` | **TRACK** | Standard project file |
| `evaluation_dataset_repair_log.json` | unknown | 1923 | `183e0839...` | **TRACK** | Standard project file |
| `evaluation_manifest.json` | unknown | 5997 | `ce1986b9...` | **TRACK** | Standard project file |
| `evaluation_manifest_pre_rescore.json` | unknown | 5997 | `ce1986b9...` | **TRACK** | Standard project file |
| `evaluation_rejected_candidates.json` | unknown | 2 | `4f53cda1...` | **TRACK** | Standard project file |
| `evaluation_repair_rejected_candidates.json` | unknown | 834 | `5fc6b969...` | **TRACK** | Standard project file |
| `evaluation_report.md` | unknown | 5699 | `df535a06...` | **TRACK** | Standard project file |
| `evaluation_report_pre_rescore.md` | unknown | 5699 | `df535a06...` | **TRACK** | Standard project file |
| `evaluation_report_rescored_v2.md` | unknown | 6532 | `9384c981...` | **TRACK** | Standard project file |
| `evaluation_results.json` | result | 1117079 | `48648ec1...` | **TRACK** | Immutable experimental result file |
| `evaluation_results_pre_rescore.json` | unknown | 1117079 | `48648ec1...` | **TRACK** | Standard project file |
| `evaluation_results_rescored_v2.json` | result | 1131870 | `90783596...` | **TRACK** | Immutable experimental result file |
| `evaluation_scoring_audit.json` | unknown | 86970 | `11f0698a...` | **TRACK** | Standard project file |
| `evaluation_scoring_manifest_v2.json` | result | 2267 | `5efc1aac...` | **TRACK** | Immutable experimental result file |
| `evaluation_summary.json` | unknown | 3421 | `77f7e3dc...` | **TRACK** | Standard project file |
| `evaluation_summary_pre_rescore.json` | unknown | 3421 | `77f7e3dc...` | **TRACK** | Standard project file |
| `evaluation_summary_rescored_v2.json` | result | 4125 | `740d72e9...` | **TRACK** | Immutable experimental result file |
| `evaluation_utils.py` | source code | 6466 | `f45a2d13...` | **TRACK** | Helper utilities must stay at root to preserve relative imports |
| `experiment_manifest.json` | unknown | 1710 | `f152ae35...` | **TRACK** | Standard project file |
| `figure_data_integrity.json` | unknown | 2079 | `38fd666e...` | **TRACK** | Standard project file |
| `grounding_failure_cases.json` | unknown | 2171 | `0ea27539...` | **TRACK** | Standard project file |
| `grounding_failure_cases.md` | unknown | 2272 | `f6343e6d...` | **TRACK** | Standard project file |
| `llm_client.py` | source code | 10648 | `9ca1ec89...` | **TRACK** | Helper utilities must stay at root to preserve relative imports |
| `logs/answer_engine.log` | logs | 13727 | `877c1ca3...` | **IGNORE** | Runtime execution logs contain local trace states |
| `logs/context_builder.log` | logs | 34845 | `d03135a7...` | **IGNORE** | Runtime execution logs contain local trace states |
| `logs/ingestion.log` | logs | 11054 | `b741b607...` | **IGNORE** | Runtime execution logs contain local trace states |
| `logs/multi_llm.log` | logs | 55308 | `3517f24a...` | **IGNORE** | Runtime execution logs contain local trace states |
| `logs/reranker.log` | logs | 56172 | `9fff3258...` | **IGNORE** | Runtime execution logs contain local trace states |
| `logs/search.log` | logs | 35227 | `f9098ab7...` | **IGNORE** | Runtime execution logs contain local trace states |
| `model_config.py` | source code | 2143 | `d2e441fb...` | **TRACK** | Helper utilities must stay at root to preserve relative imports |
| `model_performance_by_category.csv` | paper artifact | 1580 | `d8bfcff5...` | **TRACK** | CSV tables used in paper |
| `model_performance_by_category.json` | unknown | 18248 | `b55e9a72...` | **TRACK** | Standard project file |
| `model_performance_by_formulation.csv` | paper artifact | 631 | `45d9140f...` | **TRACK** | CSV tables used in paper |
| `model_performance_by_formulation.json` | unknown | 10220 | `014473d9...` | **TRACK** | Standard project file |
| `model_success_rate_comparison.png` | paper artifact | 89191 | `1eb3ec0a...` | **TRACK** | Evaluation visualization chart used in paper |
| `multi_llm_results.json` | unknown | 26482 | `5b8898c1...` | **TRACK** | Standard project file |
| `paper_abstract_draft.md` | paper artifact | 1656 | `819f54e9...` | **TRACK** | Repaired paper text files |
| `paper_artifact_manifest.json` | unknown | 635 | `0af72c95...` | **TRACK** | Standard project file |
| `paper_claims_registry.json` | result | 4636 | `88b21ba0...` | **TRACK** | Immutable experimental result file |
| `paper_conclusion.md` | paper artifact | 1317 | `a5bc3900...` | **TRACK** | Repaired paper text files |
| `paper_contributions.md` | paper artifact | 1628 | `c4365e4e...` | **TRACK** | Repaired paper text files |
| `paper_discussion.md` | paper artifact | 2225 | `6a5583ad...` | **TRACK** | Repaired paper text files |
| `paper_experimental_setup.md` | paper artifact | 1018 | `4ce11cb6...` | **TRACK** | Repaired paper text files |
| `paper_limitations.md` | paper artifact | 1292 | `155a6c3d...` | **TRACK** | Repaired paper text files |
| `paper_methodology.md` | paper artifact | 2590 | `a39350c6...` | **TRACK** | Repaired paper text files |
| `paper_numbers_registry.json` | result | 21928 | `68c4431f...` | **TRACK** | Immutable experimental result file |
| `paper_outline.md` | paper artifact | 1547 | `40740bd4...` | **TRACK** | Repaired paper text files |
| `paper_reproducibility_statement.md` | paper artifact | 936 | `0cbd1405...` | **TRACK** | Repaired paper text files |
| `paper_results.md` | paper artifact | 2718 | `77d1b8ae...` | **TRACK** | Repaired paper text files |
| `paper_table_category_analysis.csv` | paper artifact | 462 | `32b281c1...` | **TRACK** | CSV tables used in paper |
| `paper_table_failure_analysis.csv` | paper artifact | 300 | `fe928470...` | **TRACK** | CSV tables used in paper |
| `paper_table_formulation_analysis.csv` | paper artifact | 211 | `a70c6182...` | **TRACK** | CSV tables used in paper |
| `paper_table_generator_comparison.csv` | paper artifact | 339 | `802b0f9d...` | **TRACK** | CSV tables used in paper |
| `paper_table_integrity.json` | unknown | 871 | `d3b591da...` | **TRACK** | Standard project file |
| `paper_table_retrieval.csv` | paper artifact | 561 | `f02f974c...` | **TRACK** | CSV tables used in paper |
| `paper_table_statistical_significance.csv` | paper artifact | 604 | `f9d7b5b6...` | **TRACK** | CSV tables used in paper |
| `paper_threats_to_validity.md` | paper artifact | 1586 | `bb880fc9...` | **TRACK** | Repaired paper text files |
| `paper_title_candidates.md` | paper artifact | 1246 | `931fe424...` | **TRACK** | Repaired paper text files |
| `parsed_output.json` | unknown | 1860766 | `5715ac48...` | **TRACK** | Standard project file |
| `prompt_builder.py` | source code | 8155 | `36e23ee8...` | **TRACK** | Helper utilities must stay at root to preserve relative imports |
| `question_level_lineage.csv` | paper artifact | 5126 | `4636f7a2...` | **TRACK** | CSV tables used in paper |
| `repository_freeze_manifest.json` | unknown | 1219 | `29532733...` | **TRACK** | Standard project file |
| `repository_inventory.json` | unknown | 63442 | `2b995146...` | **TRACK** | Standard project file |
| `repository_inventory.md` | unknown | 15826 | `f83eace7...` | **TRACK** | Standard project file |
| `repository_migration_plan.json` | unknown | 766 | `13232889...` | **TRACK** | Standard project file |
| `repository_migration_plan.md` | unknown | 964 | `b5191191...` | **TRACK** | Standard project file |
| `reranked_results.json` | unknown | 180145 | `39df621c...` | **TRACK** | Standard project file |
| `reranker_utils.py` | source code | 10844 | `dae15a21...` | **TRACK** | Helper utilities must stay at root to preserve relative imports |
| `results_integrity_audit.json` | result | 2718 | `24849804...` | **TRACK** | Immutable experimental result file |
| `results_integrity_audit.md` | unknown | 1226 | `8065a1b4...` | **TRACK** | Standard project file |
| `retrieval_by_formulation.csv` | paper artifact | 561 | `f02f974c...` | **TRACK** | CSV tables used in paper |
| `retrieval_by_formulation.json` | unknown | 1739 | `1fea5d0c...` | **TRACK** | Standard project file |
| `retrieval_recall_at_k.png` | paper artifact | 116280 | `deb5f7b2...` | **TRACK** | Evaluation visualization chart used in paper |
| `scratch_audit.py` | source code | 35361 | `e26838b1...` | **TRACK** | Helper utilities must stay at root to preserve relative imports |
| `scratch_test_match.py` | source code | 1214 | `4b301fe5...` | **TRACK** | Helper utilities must stay at root to preserve relative imports |
| `search_results.json` | unknown | 186553 | `5ccc18ac...` | **TRACK** | Standard project file |
| `search_utils.py` | source code | 8012 | `f129ae9e...` | **TRACK** | Helper utilities must stay at root to preserve relative imports |
| `statistical_analysis_manifest.json` | result | 1835 | `2b166f88...` | **TRACK** | Immutable experimental result file |
| `statistical_analysis_report.md` | unknown | 8337 | `7d073308...` | **TRACK** | Standard project file |
| `success_rate_by_category.png` | paper artifact | 151206 | `b04a49f4...` | **TRACK** | Evaluation visualization chart used in paper |
| `success_rate_by_formulation.png` | paper artifact | 93626 | `26a2de11...` | **TRACK** | Evaluation visualization chart used in paper |
| `supported_refusal_analysis.json` | unknown | 1793 | `30796469...` | **TRACK** | Standard project file |
| `supported_refusal_analysis.md` | unknown | 812 | `efb97050...` | **TRACK** | Standard project file |
| `supported_refusal_comparison.png` | paper artifact | 99366 | `1d400524...` | **TRACK** | Evaluation visualization chart used in paper |
| `test_run.log` | unknown | 870778 | `4eda628e...` | **TRACK** | Standard project file |
| `threshold_sensitivity.png` | paper artifact | 102242 | `4889e668...` | **TRACK** | Evaluation visualization chart used in paper |
| `threshold_sensitivity_table.csv` | paper artifact | 212 | `6eed6014...` | **TRACK** | CSV tables used in paper |
