# CST8913 Lab 09: ShopPro cloud cost estimate

Chukwudubem Chukwurah | November 7, 2026

**[Read the complete report](REPORT.md)** containing all three required deliverables:

1. [Cost estimate report](REPORT.md#1-cost-estimate-report): one-time migration, monthly operations and management.
2. [Cost optimization strategy](REPORT.md#2-cost-optimization-strategy): scheduling, right-sizing, reservations, conditional Hybrid Benefit and cost allocation.
3. [Future growth and budget plan](REPORT.md#3-future-growth-and-budget-plan): three-year quantities, costs, contingency and sensitivity.

| Metric | USD |
| --- | ---: |
| One-time migration, including 14-day overlap and $6,000 effort allowance | $36,249.78 |
| Always-on PAYG monthly baseline, year 1 | $45,858.80 |
| Recommended monthly total, year 1 | $38,884.98 |
| Modeled recurring annual saving, year 1 | $83,685.84 |
| Three-year planned total including migration once | $1,817,012.22 |
| Three-year budget with 15% contingency | $2,089,564.05 |

Prices are public Azure USD estimates checked November 7, 2026. The main plan includes Windows licensing and does not assume unconfirmed Hybrid Benefit rights. No cloud infrastructure was deployed for this estimation lab.

## Supporting files

- [Assignment requirement check](REQUIREMENTS.md)
- [Calculator screenshots and original export](evidence/README.md)
- [Inputs](data/assumptions.json) and [exact price records](data/pricing-sources.json)
- [Detailed recommended monthly costs](data/optimized-monthly.csv), [migration costs](data/migration.csv), [three-year budget](data/three-year-budget.csv)
- [Verification evidence](evidence/verification.json)

Reproduce the model with Python 3.10+; no packages, cloud login or paid resources are needed:

```text
python scripts/estimate.py
python scripts/verify.py
python scripts/build_report.py
```

The calculator workbook validates selected components and totals $15,941.08/month. It is labelled separately from the complete multi-region ShopPro model. The full report explains all exclusions and conservative allowances.
