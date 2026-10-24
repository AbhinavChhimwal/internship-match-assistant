# Curated collection

`curated_records.json` is a hand-selected source ledger, reviewed from public employer/ATS listings on 2026-10-24. Each row holds company, title, original URL, concise paraphrase, required skills, work mode, location, and explicitly stated graduation years. `prepare_data.py` converts this local ledger to `jobs.csv`; it never accesses the network or extracts job text with an LLM.

Unknown fields stay null. In particular, the internship's year does **not** establish its graduation eligibility. Open-ended or ambiguous ranges remain unknown. Stated month windows remain in descriptions: the application filters by graduation year only, so testers must verify the full date, degree, enrollment and work-authorization requirements at the source. This is a shortlist, not a complete eligibility assessment.

Alternative requirements (Python **or** C++) are not flattened into a list requiring both. Optional stack technologies are not presented as missing mandatory skills. This deliberately leaves many coverage fields unavailable.

Remote listings do not imply worldwide eligibility. `compatible_locations` explicitly records supported places; remote jobs without verified geography stay excluded when remote-only is requested. Toboggan additionally restricts Canadian time zones; see source before applying. Older terms and passed deadlines are marked inactive. Other active flags indicate the public page appeared available at review, not a promise that applications remain open. Recheck manually every few days and edit the CSV; import and rebuild embeddings afterward. Do not rerun prepare_data.py over your own later curation.

The collection spans backend, frontend, data and ML, with many unknown graduation requirements. The resulting eligible subset is intentionally smaller. The evaluation profiles include varied skills and interests; zero-result and location-specific behavior have separate tests. Relevance labels were written before running rankings. They are project-author judgments, not independently collected classmate ratings.

Sources are cited per row in `source_url`; no automated scraping or live-feed importer is included.


## October 24 expansion

`jobs.csv` now contains 152 records: 52 initial listings plus 100 new source-linked records in `web_additions_2026-10-24.json`. The additional research used employer-published public Greenhouse data and an official Cargill listing. Qualification excerpts and locations were reviewed; there is no live importer or recurring scraper in the application. `web_sources_2026-10-24.json` records provenance and concise graduation-year evidence.

Descriptions distinguish technologies merely mentioned from required skills. Open-ended or ambiguous year requirements remain unknown. Twenty-seven of the new listings state specific graduation years. Dates within those years, degree levels and work authorization still need to be checked on the original listing.

The admin dashboard appends custom listings to this CSV and updates SQLite and embeddings. `prepare_data.py` now refuses to overwrite an expanded catalog, protecting web and admin additions. Unknown graduation eligibility remains excluded by default; a student can opt in explicitly in Profile, and every such card is labeled unverified.
