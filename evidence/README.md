# Azure Pricing Calculator evidence

Captured from the actual Azure calculator on November 7, 2026. These are browser-page screenshots and the unchanged browser-exported workbook. No cloud services were provisioned.

| Evidence | What it proves |
| --- | --- |
| [Web VM PAYG configuration](calculator-web-payg.png) | 10 East US D4s v5 Linux VMs, 730 hours, $0.192/hour = $1,401.60/month |
| [One-year web reservation](calculator-web-reserved-1y.png) | Same compute: $865/month, monthly payment |
| [Three-year web reservation](calculator-web-reserved-3y.png) | Same compute: $553.61/month, monthly payment |
| [Cosmos three-region throughput](calculator-cosmos-three-regions.png) | East US, West Europe, Southeast Asia; 20,000 RU/s each; $3,504 total throughput |
| [SQL compute and HA](calculator-sql-payg-ha.png) | 8-vCore primary and one HA replica, PAYG compute |
| [SQL storage and RA-GRS backup](calculator-sql-storage-backup.png) | 5 TB storage at $0.25/GB-month; 5 TB backup at $0.20/GB-month |
| [Reference estimate total](calculator-reference-export.png) | $15,941.08/month; $0 upfront; USD; selected components only |
| [Original Excel export](azure-calculator-reference.xlsx) | Exact underlying descriptions, selected regions, individual amounts and reference total |
| [Model verification](verification.json) | Calculator export reconciled to saved rates; financial and capacity checks |

The workbook contains only three **reference cases**: the 3-year web VM case ($553.61), Cosmos throughput plus three 10 TB storage copies ($11,004), and East US SQL primary/HA/storage/backup ($4,383.47). It deliberately has a different scope from the full multi-region model in the report. The PAYG and one-year web comparison values are in the separate screenshots. The workbook timestamp is UTC, so its November 8 timestamp corresponds to the evening of November 7 Eastern.
