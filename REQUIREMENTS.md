# Lab 09 requirements review

Source: the live CST8913 Brightspace Lab 09 assignment, checked November 7, 2026. Due and availability end: **November 7, 2026, 11:59 PM Eastern**. Six points. No separate rubric or attachment was displayed; this checklist maps every published requirement instead of inventing grading categories.

| Published requirement | Where it is addressed | Review |
| --- | --- | --- |
| Global ShopPro migration across North America, Europe and Asia-Pacific | Report 1.1: three named Azure regions and copy counts | Covered |
| 10 front-end VMs per region; HA, load balancing and CDN | 30 web VMs; zoned scale sets, three regional LBs, Front Door Premium | Covered |
| 50 microservices across 20 VMs; autoscale | Report 1.1 and 1.4; 20 total peak API hosts, 10 off-peak, 244/486 hours | Covered |
| Secure payment VMs, encryption in transit/at rest, PCI scope | Six isolated Windows payment hosts; report 1.5 controls and compliance responsibility | Covered |
| 5 TB SQL, 10 TB NoSQL, 15 TB warehouse | Three regional SQL/Cosmos copies; Synapse primary, snapshots, geo-backup and exports | Covered |
| Dedicated GPU-enabled VMs and scheduled batch jobs | NC4as T4 v3 and two D8s v5 workers; 200/220-hour optimized schedule | Covered |
| Redundant backup/DR and geo-storage across all regions | Live data replicas, native backups and explicit logical export sets in all three continents | Covered |
| Uptime/performance/security monitoring, budgeting/cost allocation | Report 1.5 and monthly management CSV rows; Monitor, Defender, Vault, support, tags and budgets | Covered |
| Use a cloud provider pricing calculator | Original Azure calculator workbook and screenshots; exact component reconciliation in verify.py | Covered |
| One-time migration cost: transfer, DB replication and temporary resources | Report 1.3 and migration.csv, including 14-day overlap and initial regional seeds | Covered |
| Monthly VMs, databases, LB, storage/network across regions | Report 1.4; every region and priced quantity in monthly CSVs | Covered |
| Peak/off-peak scaling | Report 1.4/2.1; separately costed PAYG burst and reserved minimum floor | Covered |
| Management cost including monitoring/logging/security/cost tools | Separate report 1.5 subtotal and Management CSV category | Covered |
| Reservations versus PAYG; database and critical-app savings | Report 2.2; regional VM rates, 32 SQL vCores and critical compute comparison | Covered |
| Autoscale and right-sizing savings | Report 2.1/2.3; actual modeled schedules and a conditional batch size comparison | Covered |
| Discounts, hybrid benefits and multi-year commitments | Report 2.2/2.3; one-/three-year rates and applied conditional Windows Hybrid Benefit scenario; eligibility is unconfirmed and excluded from main budget | Covered |
| Three-year growth and future optimization | Report 3; 20% demand / 30% data growth, exact rounded quantities, budget, contingency and sensitivity | Covered |
| Cost Estimate Report deliverable | REPORT.md section 1 | Covered |
| Cost Optimization Strategy deliverable | REPORT.md section 2 | Covered |
| Future Growth and Budget Plan deliverable | REPORT.md section 3 and three-year-budget.csv | Covered |
| All reports/submission on GitHub | Public school-account repository; README links to all deliverables | Verify public repository before Brightspace submission |

The estimate distinguishes quoted unit rates from workload assumptions and explicitly labelled allowances. It does not claim actual application deployment, performance, failover, PCI certification or license eligibility. Arithmetic and calculator checks are recorded in [verification.json](evidence/verification.json).
