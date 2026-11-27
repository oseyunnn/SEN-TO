# SEN'TO Evidence & Attribution Audit Report

Automated structural, attribution, and source-reliability audit across all 24 curated Markdown profiles in `data/senator_records/`.

## 1. Executive Summary

- **Senators audited:** 24
- **Claim-to-source matrix rows:** 1406
- **Evidence status breakdown:** `{"VERIFIED": 202, "CORROBORATED": 247, "REPORTED": 494, "DISPUTED": 7, "ALLEGED": 6, "UNVERIFIED": 7, "UNAVAILABLE": 1}`
- **Source reliability breakdown:** `{"official_government": 485, "credible_news_or_factcheck": 456, "secondary_or_other": 361, "research_organization": 96}`
- **Attribution checks:** `{"PRIMARY_SUBJECT": 1346, "JOINT_OR_SHARED_SURNAME": 19, "CONTEXTUAL_OR_IMPLICIT": 33}`
- **URLs shared across multiple senators:** 29

## 2. Per-Senator Summary

| Senator | File | Claims | Verified | Sources | Official (.gov.ph) | Invalid/Missing URLs | Missing Pub Dates | Attribution Flags |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| Alan Peter Cayetano | `Alan_Cayetano.md` | 110 | 18 | 183 | 26 | 0 | 11 | 0 |
| Paolo Benigno Aquino IV | `Bam_Aquino.md` | 28 | 0 | 63 | 33 | 0 | 4 | 0 |
| Christopher Lawrence “Bong” Go | `Bong_Go.md` | 41 | 1 | 61 | 3 | 0 | 2 | 0 |
| Camille Villar | `Camille_Villar.md` | 57 | 6 | 75 | 6 | 0 | 0 | 0 |
| Francis “Chiz” Escudero | `Chiz_Escudero.md` | 31 | 26 | 31 | 27 | 0 | 0 | 0 |
| Erwin Tulfo | `Erwin_Tulfo.md` | 26 | 0 | 61 | 5 | 0 | 2 | 0 |
| Imee Marcos | `Imee_Marcos.md` | 37 | 3 | 68 | 29 | 0 | 2 | 0 |
| Jinggoy Ejercito Estrada | `Jinggoy_Estrada.md` | 41 | 4 | 73 | 25 | 0 | 0 | 0 |
| Joel Villanueva | `Joel_Villanueva.md` | 36 | 6 | 36 | 15 | 0 | 0 | 0 |
| Joseph Victor Ejercito | `JV_Ejercito.md` | 27 | 2 | 59 | 27 | 0 | 10 | 0 |
| Francis Pangilinan | `Kiko_Pangilinan.md` | 36 | 6 | 36 | 14 | 0 | 0 | 0 |
| Manuel “Lito” Lapid | `Lito_Lapid.md` | 33 | 21 | 33 | 24 | 0 | 0 | 0 |
| Loren Legarda | `Loren_Legarda.md` | 29 | 0 | 73 | 16 | 0 | 4 | 0 |
| Mark Villar | `Mark_Villar.md` | 32 | 0 | 82 | 31 | 0 | 0 | 0 |
| Juan Miguel “Migz” Zubiri | `Migz_Zubiri.md` | 42 | 6 | 44 | 29 | 0 | 14 | 0 |
| Pia Cayetano | `Pia_Cayetano.md` | 29 | 9 | 30 | 13 | 0 | 0 | 0 |
| Panfilo “Ping” Lacson | `Ping_Lacson.md` | 87 | 6 | 100 | 8 | 0 | 0 | 0 |
| Raffy Tulfo | `Raffy_Tulfo.md` | 37 | 10 | 41 | 21 | 0 | 11 | 0 |
| Risa Hontiveros | `Risa_Hontiveros.md` | 28 | 4 | 62 | 27 | 0 | 3 | 0 |
| Robinhood Padilla | `Robin_Padilla.md` | 39 | 14 | 39 | 22 | 0 | 2 | 0 |
| Rodante Marcoleta | `Rodante_Marcoleta.md` | 36 | 8 | 43 | 17 | 0 | 13 | 0 |
| Ronald dela Rosa | `Ronald_Dela_Rosa.md` | 32 | 25 | 32 | 25 | 0 | 0 | 0 |
| Vicente Sotto III | `Tito_Sotto.md` | 36 | 9 | 36 | 9 | 0 | 9 | 0 |
| Win Gatchalian | `Win_Gatchalian.md` | 34 | 18 | 37 | 33 | 0 | 3 | 0 |

## 3. Potential Attribution Flags (Shared Surnames / Namesakes)

Found **0** claim-source rows where a shared-surname peer's given name appears without the file senator's given name:

- None detected.

## 4. Shared URLs Across Multiple Senators (Top 20)

- `https://tribune.net.ph/2025/10/29/all-senators-file-2025-salns-villar-remains-richest-escudero-posts-lowest-net-worth` → alan-peter-cayetano, francis-chiz-escudero, francis-pangilinan, joel-villanueva, juan-miguel-migz-zubiri, manuel-lito-lapid, pia-cayetano, raffy-tulfo, rodante-marcoleta, ronald-dela-rosa, vicente-sotto-iii, win-gatchalian
- `https://web.senate.gov.ph/` → imee-marcos, jinggoy-ejercito-estrada, joseph-victor-ejercito, loren-legarda, mark-villar, panfilo-ping-lacson, paolo-benigno-aquino-iv, risa-hontiveros
- `https://www.philstar.com/` → camille-villar, christopher-lawrence-bong-go, erwin-tulfo, imee-marcos, jinggoy-ejercito-estrada, joseph-victor-ejercito, loren-legarda, mark-villar, panfilo-ping-lacson, paolo-benigno-aquino-iv, risa-hontiveros
- `https://www.gmanetwork.com/news/` → erwin-tulfo, jinggoy-ejercito-estrada, joseph-victor-ejercito, mark-villar, paolo-benigno-aquino-iv, risa-hontiveros
- `https://web.senate.gov.ph/lis/` → joseph-victor-ejercito, paolo-benigno-aquino-iv
- `https://bataswatch.ph/` → erwin-tulfo, joseph-victor-ejercito, mark-villar, paolo-benigno-aquino-iv, risa-hontiveros
- `https://www.pna.gov.ph/` → christopher-lawrence-bong-go, erwin-tulfo, imee-marcos, jinggoy-ejercito-estrada, mark-villar, paolo-benigno-aquino-iv
- `https://saln.bettergov.ph/` → christopher-lawrence-bong-go, erwin-tulfo, jinggoy-ejercito-estrada, joseph-victor-ejercito, mark-villar, panfilo-ping-lacson, paolo-benigno-aquino-iv
- `https://www.pep.ph/` → panfilo-ping-lacson, paolo-benigno-aquino-iv
- `https://verafiles.org/` → camille-villar, christopher-lawrence-bong-go, erwin-tulfo
- `https://www.rappler.com/` → christopher-lawrence-bong-go, erwin-tulfo, imee-marcos, panfilo-ping-lacson
- `https://senate.ph/` → christopher-lawrence-bong-go, erwin-tulfo, jinggoy-ejercito-estrada
- `https://www.senate.gov.ph/` → camille-villar, christopher-lawrence-bong-go, joseph-victor-ejercito, panfilo-ping-lacson
- `https://news.tv5.com.ph/` → camille-villar, christopher-lawrence-bong-go, imee-marcos, mark-villar
- `https://www.philstar.com/headlines/2026/04/10/2519995/who-scored-perfect-senate-attendance-data-puts-focus-batos-31-absences` → camille-villar, christopher-lawrence-bong-go, jinggoy-ejercito-estrada, panfilo-ping-lacson, risa-hontiveros
- `https://www.dbm.gov.ph/wp-content/uploads/AboutDBM/2026-Government-Directory.pdf` → francis-chiz-escudero, francis-pangilinan, joel-villanueva, juan-miguel-migz-zubiri, manuel-lito-lapid, pia-cayetano, raffy-tulfo, rodante-marcoleta, ronald-dela-rosa, vicente-sotto-iii, win-gatchalian
- `https://legacy.senate.gov.ph/The%20Senators%27%20Directory_v04.pdf` → francis-chiz-escudero, joel-villanueva, juan-miguel-migz-zubiri, manuel-lito-lapid, pia-cayetano, raffy-tulfo, ronald-dela-rosa, win-gatchalian
- `https://legacy.senate.gov.ph/lisdata/4843644382%21.pdf` → francis-chiz-escudero, francis-pangilinan, joel-villanueva, juan-miguel-migz-zubiri, manuel-lito-lapid, raffy-tulfo, rodante-marcoleta, ronald-dela-rosa, vicente-sotto-iii, win-gatchalian
- `https://www.inquirer.net/` → erwin-tulfo, imee-marcos, joseph-victor-ejercito, mark-villar
- `https://www.abs-cbn.com/` → erwin-tulfo, imee-marcos, jinggoy-ejercito-estrada, mark-villar, panfilo-ping-lacson

## 5. Full Matrix

The complete machine-readable claim-to-source validation matrix is saved at `data/audit_matrix.json`.
