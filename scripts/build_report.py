"""Render the three requested deliverables from the checked cost model."""
import csv
import json
from collections import defaultdict
from decimal import Decimal as D
from pathlib import Path
import estimate as m

R=m.ROOT
results=json.loads((R/'data/results.json').read_text())
cases=results['cases']
f=lambda x:f'${D(str(x)):,.2f}'
def table(headers,rows):
    return '| '+' | '.join(headers)+' |\n| '+' | '.join(['---']*len(headers))+' |\n'+''.join('| '+' | '.join(str(x).replace('|','/') for x in row)+' |\n' for row in rows)
def sumrows(case,predicate):
    return sum((D(x['monthly_usd']) for x in m.estimate(mode=case)['rows'] if predicate(x)),D(0))

b=D(cases['baseline']['monthly']);o=D(cases['optimized']['monthly']);s=D(cases['scheduled']['monthly'])
mig=D(results['migration']['total']);save=b-o
recurring=sum((D(p['optimized_annual']) for p in results['projections']),D(0))
total=sum((D(p['planned_total']) for p in results['projections']),D(0))
budget=sum((D(p['budget_with_15pct_contingency']) for p in results['projections']),D(0))
three_savings=sum((D(p['annual_recurring_savings']) for p in results['projections']),D(0))

intro=f'''# Lab 09: Cloud Cost Estimation for Enterprise Application Migration

**CST8913 Cloud Migration | Chukwudubem Chukwurah | November 7, 2026**

## Recommendation

ShopPro International should use Azure across East US, West Europe and Southeast Asia, keep its required 30 web VMs, and reserve only continuously used compute. Schedule API burst capacity, GPU training, batch workers and warehouse compute around actual demand. The year-one recurring estimate is **{f(o)} per month**, compared with **{f(b)}** for the same architecture running at peak capacity on pay-as-you-go pricing. The modeled reduction is **{f(save)} per month ({save/b*100:.1f}%)**, or **{f(save*12)} annually**.

The one-time migration budget is **{f(mig)}**, including a 14-day parallel destination environment and an explicit $6,000 engineering allowance. The three-year planned total, including migration once, is **{f(total)}**; a 15% contingency increases the requested budget to **{f(budget)}**. These are estimates for the stated workload assumptions, not a measured production bill or a cloud deployment.

This report contains the three requested deliverables: the cost estimate, cost optimization strategy, and future growth/budget plan. Brightspace displayed the instructions and a six-point score allocation, but no separate grading rubric or attachment. [Requirement-by-requirement review](REQUIREMENTS.md).

## 1. Cost estimate report

### 1.1 Scope, assumptions and service selection

The assignment supplies VM counts and data sizes but no utilization, VM sizes, request rate, traffic, retention policy or license inventory. The following are explicit planning assumptions. Values can be changed in [assumptions.json](data/assumptions.json) and recalculated with the supplied script.

'''
assumptions=[
('Currency and time','USD retail prices checked November 7, 2026; 730 hours/month; 12 comparable months/year. Capacity convention: 1 TB = 1,000 GB. VM memory/disk GiB labels retain the vendor SKU units. No CAD conversion, taxes, negotiated agreement, student credits or Dev/Test discount.'),
('Regions','North America: East US; Europe: West Europe; Asia-Pacific: Southeast Asia. East US is the primary write/management region. Data-residency approval is a prerequisite to cross-continent copies.'),
('Web front end','10 Linux D4s v5 VMs per region: 30 total, each 4 vCPUs / 16 GiB. VM scale sets distribute instances across availability zones; a regional Standard Load Balancer and global Front Door Premium provide health-based routing/CDN.'),
('API / microservices','All 50 microservices run on container hosts in VM scale sets, distributed across 20 peak D4s v5 VMs: 8 / 6 / 6 by region. This is 20 globally, not 20 per region. No separate AKS control plane is assumed.'),
('Peak and off-peak','244 peak hours/month and 486 off-peak hours. Off-peak API floor: 4 / 3 / 3 VMs. The required 10 web VMs per region stay running; they are not reduced for savings.'),
('Payment processing','2 Windows D4s v5 VMs per region: 6 total, isolated from web hosts. Windows licenses are included in the principal budget. No cardholder data is written to diagnostic logs.'),
('Primary SQL database','Azure SQL Database Hyperscale, Standard-series Gen5, 8 vCores: East US primary + one paid in-region HA replica; one 8-vCore geo-secondary in Europe and Asia. Four compute copies / 32 vCores, three 5 TB regional storage copies. Local HA is not claimed to be zone-redundant.'),
('Analytics NoSQL database','Cosmos DB for NoSQL, General Purpose, single-write, manual 20,000 RU/s per region and 10,000 GB per region, including indexes. All three regional compute and storage copies are billed. Free tier, analytical storage and dedicated gateway are off.'),
('Warehouse and ML','Synapse dedicated SQL pool DW100c; 15 TB data plus 20% snapshot allowance, rounded up to 18 billed TB in year 1; native geo-backup included separately. One NC4as T4 v3 GPU VM; two Linux D8s v5 batch VMs.'),
('Disks','59 peak VM OS disks, 128 GiB Standard SSD E10 LRS, including deallocated burst/batch/GPU nodes. One million disk operations/disk/month. Durable application data is in the managed data services, not OS disks.'),
('Network demand','5,000 GB CDN egress and 10 million Front Door requests per region/month; 100 GB edge-to-origin traffic/region. 2,000 GB/LB and 1,000 GB/NAT per region. Cosmos: 1,000 GB monthly changed data to each secondary; independent backups: 3,000 GB changes to each other continent.'),
('Private connectivity','11 customer private endpoints: 3 SQL, 3 Cosmos, 3 Blob, 1 Synapse, 1 Key Vault. 3 TB inbound + 3 TB outbound total endpoint traffic; 5 shared private DNS zones, 30 million private queries, 1 public zone and 10 million public queries.'),
('Backups and DR','5 TB of billable SQL PITR backup storage per regional DB. Cosmos uses two included periodic backup copies. Each continent also stores one current 30 TB logical export set in Blob: GZRS in East US/West Europe and GRS in Southeast Asia. This is one retained full set per region, not 30 TB of daily history.'),
('Monitoring and security','400 GB/month centralized Log Analytics ingestion, 5 GB free, no extended interactive retention beyond the included period; 30 monitored metric time series with 10 free; Defender for Servers P1, Defender for 3 SQL logical servers plus Synapse, Key Vault and Standard support.'),
('Growth and uncertainty','Traffic/compute demand +20% annually; stored data and backup deltas +30%. Price levels held constant in the central forecast. 15% contingency is separate from priced consumption; a price-increase stress case is shown below.')]

report=intro+table(['Area','Assumption / reason'],assumptions)
report+='''
Hyperscale supports the 5 TB database without forcing it into a smaller single-database storage limit. Its HA replica shares primary page storage, while a geo-secondary has its own storage copy; the model therefore charges four compute copies but three storage copies. Active geo-replication SQL transfer is included by Azure, so it is not charged again as general bandwidth. Cosmos replication transfer is separately billable and is included. [SQL replicas](https://learn.microsoft.com/en-us/azure/azure-sql/database/service-tier-hyperscale-replicas), [SQL pricing](https://azure.microsoft.com/en-us/pricing/details/azure-sql-database/single/), [Cosmos bandwidth](https://learn.microsoft.com/en-us/azure/cosmos-db/network-bandwidth).

### 1.2 Pricing calculator and reproducibility

I used the [Azure Pricing Calculator](https://azure.microsoft.com/en-us/pricing/calculator/) to check actual configured reference cases and exported its workbook. [Microsoft documents](https://learn.microsoft.com/en-us/azure/cost-management-billing/costs/pricing-calculator) that calculator unit prices come from the Retail Prices API. The complete multi-region estimate is an explicit quantity-times-rate model using saved public API meter records and official pricing tables. The calculator workbook is a **component validation estimate**, not the complete ShopPro total: it contains only the three reference components below.

'''
report+=table(['Reference configuration','Calculator monthly result','Independent calculation'],[
('East US web: 10 D4s v5 Linux, PAYG','$1,401.60','10 x 730 x $0.192'),
('Same web VMs, 1-year reservation, monthly payment','$865.00','10 x $1,038 / 12'),
('Same web VMs, 3-year reservation, monthly payment','$553.61','10 x $1,993 / 36'),
('Cosmos: 20,000 RU/s + 10 TB in each of 3 regions','$11,004.00','3 x (200 x 730 x $0.008 + 10,000 x $0.25)'),
('East US SQL: 8-vCore primary + 1 HA, 5 TB storage, 5 TB RA-GRS backup, PAYG','$4,383.47','16 x 730 x $0.18266 + 5,000 x $0.25 + 5,000 x $0.20')])
report+='''
The final exported reference workbook totals **$15,941.08/month**: the 3-year web case + Cosmos + East US SQL. The earlier PAYG and 1-year web results are recorded in separate screenshots. [Original calculator export](evidence/azure-calculator-reference.xlsx), [calculator screenshots](evidence/README.md), [saved unit-price records](data/pricing-sources.json).

The selected Hyperscale calculator storage meter is $0.25/GB-month in East US and $0.301724 in each of the other two regions. The API contains other similarly named Hyperscale storage meters; this report uses the meter matching the calculator configuration, rather than substituting a cheaper unrelated meter. It does not add the API's separate I/O meter because this selected Hyperscale configuration does not bill IOPS separately.

Reservation records contain the **full commitment price for the term**, even where the API unit field says “1 Hour.” They are divided by 12 or 36 months, never multiplied by 730. Windows VM reservations cover base compute; the Windows license component remains payable unless Hybrid Benefit eligibility is verified. No reservation and savings-plan discounts are stacked.

To reproduce without cloud access:

```text
python scripts/estimate.py
python scripts/verify.py
python scripts/build_report.py
```

The CSVs list every quantity, rate key, calculation and monthly amount. USD line items are rounded to cents before addition, so totals reconcile to the displayed rows. The calculator can differ by a cent when it rounds an aggregated, unrounded subtotal.

### 1.3 One-time migration costs

Use Azure Migrate to discover and assess the application servers. For the assumed SQL Server source, perform compatibility checks and use supported SQL transactional replication / push subscription for continuous synchronization into Hyperscale. Synapse pipelines with self-hosted and Azure integration runtimes copy the NoSQL and warehouse datasets. These are Azure migration/data-integration services; the estimate does not rely on retired DMS classic SQL scenarios or its old free-period claim. [SQL migration guide](https://learn.microsoft.com/en-us/data-migration/sql-server/database/guide), [migration tooling options](https://techcommunity.microsoft.com/blog/modernizationbestpracticesblog/microsoft-options-to-migrate-sql-server-databases/4521637), [DMS classic retirement](https://azure.microsoft.com/en-ca/updates?id=retirement-azure-database-migration-service-classic-sql-server-scenarios-deprecation).

The planning window is 14 days / 336 hours. At an assumed effective 250 Mbps, uploading 30 TB takes about 267 hours, leaving around 69 hours for retries and synchronization. This requires validating source I/O, change rate, network capacity and compatibility before committing to the window. The temporary Windows hosts are assumed to run the existing licensed SQL distributor/validation tooling; new SQL licenses, if required, need a separate quote. The source remains authoritative until reconciliation and cutover succeed.

'''
report+=table(['One-time component','Amount (USD)','Quantity / explanation'],[(x['item'],f(x['one_time_usd']),x['calculation'] or f"{x['quantity']} x {x['unit_price']}") for x in m.migration()['rows']])
report+=f'''
**Total migration budget: {f(mig)}.** Of this, {f(results['migration']['cloud_only'])} is cloud consumption, parallel operation and migration infrastructure; $6,000 is the separately assumed engineering cost. Full source ISP/on-premises operation, payment-processor transaction fees, application redevelopment, external PCI assessment and taxes are outside this estimate. They are not assumed to cost zero.

The 14-day overlap line is 14/30 of the scheduled PAYG destination environment ({f(s)}/month), charged **before** the first 12 steady-state months. Destination SQL compute, replicas, storage, monitoring and replication during that window are therefore covered without another duplicate target-compute charge. Initial Cosmos seeds and cross-continent backup exports are additional one-time transfer. SQL active geo-seeding transfer is included by Azure.

Initial paired-region GRS/GZRS transfer is an explicit conservative planning allowance: 90,000 GB at a blended $0.05/GB, not a retrieved storage replication meter. Its recurring counterpart is 9,000 GB/month at that proxy rate. The generic within-continent bandwidth table would be $0.02/GB for North America/Europe and $0.08/GB for Asia; the selected blend is above the equal-volume weighted mean. Confirm the actual storage replication meter before procurement. This allowance is clearly separated from the exact regional storage and transaction prices.

### 1.4 Monthly operations: always-on baseline versus recommended plan

'''
# Group identically named services together without hiding detailed regional CSVs.
groups=[
('Web compute',lambda x:x['item'].startswith('Web:')),
('API compute',lambda x:x['item'].startswith('API:')),
('Payment compute and Windows',lambda x:x['item'].startswith('Payment:')),
('VM OS disks and transactions',lambda x:x['item'].startswith('128 GiB') or x['item']=='Managed-disk transactions'),
('SQL compute',lambda x:x['item']=='SQL Hyperscale Gen5 compute'),
('SQL regional storage',lambda x:x['item']=='SQL Hyperscale allocated storage'),
('SQL geo-redundant PITR',lambda x:x['item']=='SQL geo-redundant PITR backup allowance'),
('Cosmos regional throughput and storage',lambda x:x['item'].startswith('Cosmos DB')),
('Independent Blob backups and operations',lambda x:x['item'].startswith('Independent full') or x['item'].startswith('Blob ')),
('GPU and batch compute',lambda x:x['item'].startswith('GPU training') or x['item'].startswith('Scheduled batch')),
('Synapse compute, data, snapshots, native DR and pipelines',lambda x:x['item'].startswith('Synapse')),
('CDN / WAF / Front Door traffic and requests',lambda x:x['item'].startswith('Front Door')),
('Regional LB, NAT and public IP',lambda x:x['item'].startswith(('Standard regional','Load-balancer','NAT ','Public IPs'))),
('Private endpoints and DNS',lambda x:x['item'].startswith(('Customer-managed','Private-','Private DNS','Public DNS'))),
('Cross-region deltas and paired-region allowance',lambda x:x['item'].startswith(('Cosmos cross','Independent Blob backup cross','Paired-region','Intra-region')))]
report+=table(['Operations component','Baseline PAYG / month','Recommended / month'],[(name,f(sumrows('baseline',pred)),f(sumrows('optimized',pred))) for name,pred in groups])
report+=f'''
**Operations subtotal:** baseline **{f(cases['baseline']['operations'])}**, recommended **{f(cases['optimized']['operations'])}**. [Full baseline CSV](data/baseline-monthly.csv), [recommended CSV](data/optimized-monthly.csv).

For example, API billing falls from **14,600 VM-hours** to **9,740 VM-hours**: `(8+6+6) x 244 + (4+3+3) x 486`. Reserve the ten continuously used API hosts and buy only the ten incremental hosts for peak hours. Keep health checks, minimum replicas and demand-based autoscale alarms; scale before predictable peaks and scale out on measured CPU, latency or queue depth. Disk charges remain for all retained nodes. A VM must be **deallocated**, not merely shut down inside its OS, to stop PAYG compute charges.

Front Door is priced as one Premium profile plus 15 TB/month edge-to-client delivery, requests and edge-to-origin request traffic, using the distinct North America/Europe and Asia-Pacific tariff zones. Azure-origin-to-Front-Door transfer is not charged a second time as general Internet egress. WAF is included with Premium; separately created SQL/Cosmos/Blob private endpoints still have their own cost. [Front Door pricing](https://azure.microsoft.com/en-us/pricing/details/frontdoor/), [bandwidth pricing](https://azure.microsoft.com/en-us/pricing/details/bandwidth/).

### 1.5 Monthly management and security

'''
mg=defaultdict(lambda:[D(0),D(0)])
for i,case in enumerate(['baseline','optimized']):
    for row in m.estimate(mode=case)['rows']:
        if row['category']=='Management':mg[row['item']][i]+=D(row['monthly_usd'])
report+=table(['Management component','Baseline / month','Recommended / month'],[(name,f(v[0]),f(v[1])) for name,v in mg.items()])
report+=f'''
**Management subtotal:** baseline **{f(cases['baseline']['management'])}**, recommended **{f(cases['optimized']['management'])}**. Including operations, the respective recurring totals are **{f(b)}** and **{f(o)}**.

Payment VMs belong in separate restricted subnets with NSGs, private data-service endpoints, managed identities, least privilege, OS patching, disk/storage encryption and TLS 1.2 or higher. Keep keys in Key Vault, enable audit trails, redact sensitive fields before logging, and route web traffic through the managed WAF. Defender and monitoring are priced above; native NSGs, RBAC, Azure Policy checks, tagging and Cost Management have no additional consumption fee in this assumed Azure-only setup. Existing identity/on-premises licensing is excluded.

These controls support a PCI DSS design; an Azure VM is not automatically a PCI-compliant payment system. ShopPro still needs a scoped cardholder-data environment, evidence, vulnerability scans and its required compliance assessment. Consider tokenizing card data with an approved payment processor to reduce scope. No compliance certification or production test is claimed by this estimate.

Use tags `Application=ShopPro`, `Environment`, `Region`, `Owner`, `CostCenter` and `DataClassification`. Apply a tag policy, daily cost-anomaly review, and subscription/resource-group budget alerts at 50%, 80% and 100%. Budgets alert; they do not automatically stop production resources. Review reservation utilization and unattached disks weekly. [Cost Management pricing](https://azure.microsoft.com/en-us/pricing/details/cost-management/), [Standard support](https://azure.microsoft.com/en-us/support/plans/standard/).

### 1.6 Recovery and validation before production

Distribute web/API/payment nodes across zones, keep the East US SQL HA replica, and maintain the two paid SQL geo-secondaries and three-region Cosmos account. GRS/GZRS alone replicates to a paired region; it does **not** create copies in all three continents. The explicit cross-continent Blob export sets meet that separate coverage requirement, alongside live SQL/Cosmos regional data copies. Synapse native geo-backup is also included.

Set initial planning targets of under-five-minute SQL/Cosmos regional RPO and four-hour RTO, and 24-hour RPO for warehouse/export recovery. These are business targets to test, not provider guarantees. Run restore and controlled failover drills, verify counts/checksums and financial totals, measure replication lag, validate reconnect/retry behavior, and keep an approved rollback plan. The SQL backup size and 20% Synapse snapshot allowance must be resized if measured daily churn exceeds them. No paid standby GPU/warehouse compute is included in secondary regions; restore-and-resume costs and short outage-related bursts come from contingency.

## 2. Cost optimization strategy

### 2.1 Avoid double-counted savings

'''
report+=table(['Step','Recurring monthly cost','Incremental monthly saving'],[
('Peak-sized, always-on PAYG baseline',f(b),'Starting point'),
('API scale-in + batch/GPU shutdown + warehouse pause; PAYG retained',f(s),f(b-s)),
('Then reserve steady VM and SQL compute for one year',f(o),f(s-o)),
('Total recommended reduction',f(o),f(save))])
report+='''
The reservation step is applied **after** scheduling, so savings are not calculated twice against the original peak footprint. Storage, network, backups and Windows OS licensing are not multiplied by a compute reservation discount.

### 2.2 Reserved versus pay-as-you-go compute

'''
reserve_rows=[]
for reg in m.A['regions']:
    reserve_rows.append((f'D4s v5 Linux, {reg}, one VM',f(m.rate('vm_'+reg+'_payg')*730),f(m.monthly_rate('vm_'+reg,'1y')),f(m.monthly_rate('vm_'+reg,'3y'))))
sqlpay=sum(m.rate('sql_'+reg+'_payg')*8*copies*730 for reg,copies in zip(m.A['regions'],[2,1,1]))
sql1=sum(m.monthly_rate('sql_'+reg,'1y')*8*copies for reg,copies in zip(m.A['regions'],[2,1,1]))
sql3=sum(m.monthly_rate('sql_'+reg,'3y')*8*copies for reg,copies in zip(m.A['regions'],[2,1,1]))
reserve_rows.append(('SQL Hyperscale: all 32 vCores, compute only',f(sqlpay),f(sql1),f(sql3)))
report+=table(['Workload','PAYG / month','1-year / month','3-year / month'],reserve_rows)
critical=lambda x:x['item'].startswith(('Web:','Payment:')) and x['item']!='Payment: Windows OS license'
critical_base=sumrows('baseline',lambda x:x['item'].startswith(('Web:','Payment:')))-D('805.92')
critical_opt=sumrows('optimized',critical)
report+=f'''
For the critical web and payment **base compute**, the comparable PAYG amount is {f(critical_base)}/month versus {f(critical_opt)} with one-year reservations: **{f(critical_base-critical_opt)}/month saved**, with the Windows OS line unchanged. SQL compute saves **{f(sqlpay-sql1)}/month** with one-year reservations; database storage and backups remain fully charged. Rounding can produce a one-cent difference from the sum of regional rounded CSV lines.

Using three-year reservations for the same scheduled VM/SQL footprint would reduce the year-one recurring total to **{f(cases['optimized_3y']['monthly'])}**, another **{f(o-D(cases['optimized_3y']['monthly']))}/month** below the one-year plan. This is a commitment comparison, not a promise of future rates. A three-year East US D4s v5 reservation breaks even against 730-hour PAYG at approximately {(m.rate('vm_eastus_3y')/36)/(m.rate('vm_eastus_payg')*730)*100:.1f}% utilization; a one-year reservation needs {(m.rate('vm_eastus_1y')/12)/(m.rate('vm_eastus_payg')*730)*100:.1f}%.

Start with one-year commitments after a utilization measurement period and renew/re-size annually. Consider three years only for verified stable demand and approved financing. Monthly reservation payment is assumed, so there is no initial cash payment in the model, but the term remains a contractual commitment. Do not reserve burst, GPU or pausable warehouse capacity simply because a headline discount is larger.

### 2.3 Hybrid Benefit and right-sizing

If ShopPro can prove sufficient eligible Windows Server licenses with active Software Assurance or qualifying subscription rights, applying Hybrid Benefit to the six payment VMs removes the modeled **$805.92/month** OS component. The one-year optimized total would then be **{f(cases['optimized_ahb_if_eligible']['monthly'])}**, saving another **$9,671.04/year**, before any existing license/assurance cost. Six 4-vCPU VMs require at least 48 qualifying core licenses because the minimum is eight per VM. Eligibility is unconfirmed, so these savings are **not included** in the principal budget. No Hybrid Benefit saving is assigned to new Hyperscale databases. [Windows eligibility](https://learn.microsoft.com/en-us/windows-server/get-started/azure-hybrid-benefit), [Hyperscale licensing](https://learn.microsoft.com/en-us/azure/azure-sql/database/service-tiers-sql-database-vcore).

Right-size after observing p95 CPU, memory, disk latency and request latency under representative load. For example, if both batch jobs fit D4s v5 rather than D8s v5 **without increasing the 220-hour run window**, the compute cost would fall from $168.96 to $84.48/month, a further $84.48/month. This is a measurable candidate, not booked savings. Preserve the assignment's 10 web hosts per region. Keep reserved capacity at the steady floor and retain at least two healthy service instances for availability during scale-in.

GPU shutdown from 730 to 200 hours saves $278.78/month in compute. Batch scheduling from 730 to 220 hours saves $391.68/month. Pausing DW100c from 730 to 220 hours saves $770.10/month while warehouse storage, snapshots and geo-backup continue to be charged. Together with the API schedule, these feed the first savings step above; they must not be added again to the final total.

Tune Cosmos partition keys, indexes and queries before increasing RU/s. At 10 TB, the 1 RU/s-per-GB manual throughput floor is 10,000 RU/s per region, so a 400-RU/s budget would be invalid. The chosen 20,000 RU/s remains above the storage floor through all three projected years. Autoscale has a different minimum/max and unit price, so the report does not automatically treat it as cheaper than manual throughput. [Cosmos capacity limits](https://learn.microsoft.com/en-us/azure/cosmos-db/concepts-limits).

Use caching/compression and lifecycle policies only after verifying correctness, freshness and restore requirements. Do not archive the active SQL/Cosmos working sets or remove replicas to manufacture savings. Consider newer VM generations, container consolidation and serverless execution for intermittent, non-payment microservices after profiling. Reprice the full compute, cold-start, request, storage and networking bill before adopting them; no unverified future technology discount is booked.

## 3. Future growth and budget plan

### 3.1 Three-year demand model

'''
projection_demands=[]
for year in range(1,4):
    t=((D(1)+D(str(m.A['traffic_growth'])))**(year-1));g=(D(1)+D(str(m.A['data_growth'])))**(year-1)
    web=[__import__('math').ceil(10*t)]*3
    api=[__import__('math').ceil(D(x)*t) for x in [8,6,6]]
    off=[__import__('math').ceil(D(x)*t) for x in [4,3,3]]
    projection_demands.append((year,' / '.join(map(str,web)),' / '.join(map(str,api)),' / '.join(map(str,off)),m.A['sql_vcores_by_year'][year-1],f'{5*g:.2f} / {10*g:.2f} / {15*g:.2f}',results['projections'][year-1]['maximum_vms']))
report+=table(['Year','Web VMs by region','Peak API VMs','Off-peak API VMs','SQL vCores / copy','SQL / Cosmos / warehouse logical TB','Peak total VMs'],projection_demands)
report+='''
Each year uses the stated growth factors on the underlying quantities, not a blanket percentage added to last year's bill. Round VMs up to whole instances. SQL goes from 8 to 10 to 12 vCores per compute copy; the fixed six payment VMs remain until measurements justify another size/count. GPU, batch and warehouse scheduled hours grow with demand; data, backup storage and backup deltas grow by 30%. The stored warehouse snapshot allowance is rounded to whole TB. Every regional data copy grows too.

### 3.2 Annual budget

'''
report+=table(['Year','Baseline recurring / year','Recommended recurring / year','One-time migration','Planned total','Budget incl. 15% contingency'],[(p['year'],f(p['baseline_annual']),f(p['optimized_annual']),f(p['one_time_migration']),f(p['planned_total']),f(p['budget_with_15pct_contingency'])) for p in results['projections']])
report+=f'''
Across three years, recommended recurring consumption is **{f(recurring)}**. Including migration once gives **{f(total)}**, versus **{f(total+three_savings)}** for the growing always-on baseline with the same migration budget. Modeled recurring savings total **{f(three_savings)}**. The all-in budget request including contingency is **{f(budget)}**. [Projection CSV](data/three-year-budget.csv).

Year 1: assess and pilot, validate sizing and recovery, then commit the measured steady compute floor. Use schedules and demand alarms immediately; check costs daily during migration and weekly after stabilization.

Year 2: renew reservations at the updated regional footprint, test the 10-vCore SQL size, and review retention/index growth. Trial serverless execution only for the most intermittent non-payment services and compare their measured total cost to the current VM allocation.

Year 3: validate 12-vCore SQL and the larger data sets, evaluate newer VM generations and whether some microservices can share fewer hosts while preserving the required web cluster and service redundancy. Buy another long commitment only when measured load and the application roadmap justify it. Recheck data residency and recovery times as export volumes grow.

### 3.3 Sensitivity and constraints

'''
stress=[]
for p in results['projections']:
    year=p['year'];annual=D(p['optimized_annual']);factor=D('1.05')**(year-1)
    stress.append((year,f(p['optimized_monthly']),f(D(p['optimized_monthly'])*factor),f(annual*(factor-1))))
report+=table(['Year','Central monthly estimate','Monthly with 5% annual price increase','Added annual cost'],stress)
report+='''
The price stress is separate from usage growth and from the central budget; do not add both it and the full contingency as two mandatory charges. A 25% increase in retained backup/data size would directly increase the corresponding storage and replication lines by about 25%, subject to tier thresholds. At the modeled three-year volumes, CDN traffic stays below 10 TB per regional zone and Blob data below 51.2 TB per regional account, so the selected first-tier rates remain applicable. The warehouse's 20% snapshot and SQL's 5 TB backup allowances may need more than proportional growth if data churn increases.

This is a planning estimate, not a production sizing or availability guarantee. Before purchase, validate the application/SQL compatibility, PCI scope, license entitlements, vCPU/GPU quotas, observed throughput and backup sizes, as well as regional product availability and exact current prices. Reprice support for a mission-critical enterprise SLA: the priced $100 Standard plan is a baseline allowance, not a claim that it satisfies every ShopPro support objective. External audits, source-side costs, long-term archival retention, a full active-active payment design and ongoing engineering salaries need separate business budgets.

## References and evidence

All prices were checked November 7, 2026. The primary source for each exact retail rate, meter ID, region, product, unit, tier and effective date is preserved in [pricing-sources.json](data/pricing-sources.json). Quantity assumptions are separate from quoted prices. Key references are linked at their point of use; other service pricing references are:

- [Azure Virtual Machines](https://azure.microsoft.com/en-us/pricing/details/virtual-machines/linux/)
- [Azure SQL Database](https://azure.microsoft.com/en-us/pricing/details/azure-sql-database/single/)
- [Cosmos DB provisioned throughput](https://azure.microsoft.com/en-us/pricing/details/cosmos-db/standard-provisioned/)
- [Blob storage](https://azure.microsoft.com/en-us/pricing/details/storage/blobs/)
- [Synapse Analytics and pipelines](https://azure.microsoft.com/en-us/pricing/details/synapse-analytics/)
- [Synapse backups and storage rounding](https://learn.microsoft.com/en-us/azure/synapse-analytics/sql-data-warehouse/backup-and-restore)
- [Azure Monitor](https://azure.microsoft.com/en-us/pricing/details/monitor/)
- [Microsoft Defender for Cloud](https://azure.microsoft.com/en-us/pricing/details/defender-for-cloud/)
- [Private Link](https://azure.microsoft.com/en-us/pricing/details/private-link/)
- [Key Vault](https://azure.microsoft.com/en-us/pricing/details/key-vault/)
- [Azure Migrate](https://azure.microsoft.com/en-us/pricing/details/azure-migrate/)
- [Verification results](evidence/verification.json)

AI assistance was used to research pricing, develop the reproducible model and draft this report under my direction. Workload assumptions, eligibility conditions and estimate limitations are disclosed for review.
'''
(R/'REPORT.md').write_text(report,encoding='utf-8')
readme=f'''# CST8913 Lab 09: ShopPro cloud cost estimate

Chukwudubem Chukwurah | November 7, 2026

**[Read the complete report](REPORT.md)** containing all three required deliverables:

1. [Cost estimate report](REPORT.md#1-cost-estimate-report): one-time migration, monthly operations and management.
2. [Cost optimization strategy](REPORT.md#2-cost-optimization-strategy): scheduling, right-sizing, reservations, conditional Hybrid Benefit and cost allocation.
3. [Future growth and budget plan](REPORT.md#3-future-growth-and-budget-plan): three-year quantities, costs, contingency and sensitivity.

| Metric | USD |
| --- | ---: |
| One-time migration, including 14-day overlap and $6,000 effort allowance | {f(mig)} |
| Always-on PAYG monthly baseline, year 1 | {f(b)} |
| Recommended monthly total, year 1 | {f(o)} |
| Modeled recurring annual saving, year 1 | {f(save*12)} |
| Three-year planned total including migration once | {f(total)} |
| Three-year budget with 15% contingency | {f(budget)} |

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
'''
(R/'README.md').write_text(readme,encoding='utf-8')
print('Rendered REPORT.md and README.md from current model results')
