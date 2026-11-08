"""Reproduce the ShopPro cost estimate offline. Python 3.10+, standard library only.

Rates are the saved public USD prices in data/pricing-sources.json.
No cloud resources are created, and no credentials are required.
"""
import csv
import json
import math
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
A = json.loads((ROOT / 'data/assumptions.json').read_text())
S = json.loads((ROOT / 'data/pricing-sources.json').read_text())
D = lambda n: Decimal(str(n))
ZERO = D(0)

def rate(key):
    return D(S[key]['price'])

def money(value):
    return D(value).quantize(D('.01'), rounding=ROUND_HALF_UP)

def monthly_rate(key, term):
    return rate(key + '_' + term) / {'1y': D(12), '3y': D(36)}[term]

def estimate(year=1, mode='optimized', term='1y', ahb=False):
    """mode baseline: always-on PAYG; scheduled: schedules only; optimized: schedules + RI."""
    assert 1 <= year <= 3
    assert mode in ('baseline', 'scheduled', 'optimized')
    assert term in ('1y', '3y')
    n = year - 1
    load = (D(1)+D(A['traffic_growth'])) ** n
    data = (D(1)+D(A['data_growth'])) ** n
    H = D(A['hours_per_month'])
    peak_h = D(A['peak_hours'])
    off_h = D(A['off_peak_hours'])
    rows = []
    total_vm_hours = ZERO
    maximum_vms = 0
    def add(category, item, region, quantity, price_key, note='', unit_price=None):
        q = D(quantity)
        price = rate(price_key) if unit_price is None else D(unit_price)
        assert q >= 0 and price >= 0
        rows.append(dict(category=category, item=item, region=region,
                         quantity=str(q), rate_key=price_key, unit_price=str(price),
                         monthly_usd=str(money(q*price)), calculation=note))

    for i, region in enumerate(A['regions']):
        web = math.ceil(D(A['web_vms_per_region']) * load)
        peak = math.ceil(D(A['api_peak_vms'][i]) * load)
        off = math.ceil(D(A['api_off_peak_vms'][i]) * load)
        pay = A['payment_vms_per_region']  # retain 2 PCI-scope nodes, scale vertically only after measurement
        maximum_vms += web + peak + pay
        if mode == 'optimized':
            add('Operations', 'Web: reserved D4s v5 Linux', region, web,
                f'vm_{region}_{term}', f'{web} x term price / {12 if term=="1y" else 36}',
                monthly_rate(f'vm_{region}',term))
            add('Operations', 'API: reserved off-peak D4s v5 Linux', region, off,
                f'vm_{region}_{term}', 'Reserve only the continuously used floor', monthly_rate(f'vm_{region}',term))
            add('Operations', 'API: PAYG peak burst D4s v5 Linux', region, (peak-off)*peak_h,
                f'vm_{region}_payg', '(peak VMs - floor VMs) x 244 hours')
        else:
            add('Operations', 'Web: D4s v5 Linux', region, web*H, f'vm_{region}_payg', 'VM count x 730 hours')
            api_hours = peak*H if mode == 'baseline' else peak*peak_h + off*off_h
            add('Operations', 'API: D4s v5 Linux', region, api_hours, f'vm_{region}_payg',
                'All peak nodes x 730' if mode=='baseline' else 'Peak x 244 + floor x 486')
        api_hours = peak*H if mode == 'baseline' else peak*peak_h + off*off_h
        total_vm_hours += (web+pay)*H + api_hours
        # Windows PAYG includes compute + OS. The reservation discounts compute only.
        os_rate = rate(f'windows_{region}') - rate(f'vm_{region}_payg')
        if mode == 'optimized':
            add('Operations', 'Payment: reserved D4s v5 compute', region, pay,
                f'vm_{region}_{term}', '2 nodes per region; do not shut down payment capacity', monthly_rate(f'vm_{region}',term))
            add('Operations', 'Payment: Windows OS license', region, pay*H,
                f'windows_{region}', 'Windows PAYG - Linux/base compute; AHB only in separately labelled scenario',
                ZERO if ahb else os_rate)
        else:
            add('Operations', 'Payment: Windows D4s v5 license included', region, pay*H, f'windows_{region}')
        disks = web+peak+pay
        if i == 0: disks += A['batch_vms']+1
        add('Operations', '128 GiB E10 LRS OS disks', region, disks, f'disk_{region}', 'Retained even when VM is deallocated')
        add('Operations', 'Managed-disk transactions', region, disks*A['vm_disk_operations_per_vm']/10000,
            'disk_ops', '1 million billed operations per allocated disk; East US transaction meter used for equal-price regions')

        cores = A['sql_vcores_by_year'][n]
        copies = A['sql_compute_copies'][i]
        if mode == 'optimized':
            add('Operations', 'SQL Hyperscale Gen5 compute', region, cores*copies,
                f'sql_{region}_{term}', 'East US primary + 1 HA replica; 1 geo-secondary in each other region',
                monthly_rate(f'sql_{region}',term))
        else:
            add('Operations', 'SQL Hyperscale Gen5 compute', region, cores*copies*H,
                f'sql_{region}_payg', 'vCores x compute copies x 730')
        add('Operations', 'SQL Hyperscale allocated storage', region, D(A['sql_gb'])*data,
            f'sql_storage_{region}', 'One storage copy per regional database; HA shares primary storage')
        add('Operations', 'SQL geo-redundant PITR backup allowance', region, D(A['sql_gb'])*data,
            f'sql_backup_{region}', '5 TB incremental/billed backup storage per regional DB; budget assumption, not guaranteed retention capacity')
        ru = math.ceil(D(A['cosmos_ru_per_region'])*load/100)*100
        storage_gb = D(A['cosmos_gb'])*data
        assert ru >= storage_gb  # manual throughput floor >= 1 RU/s per stored GB
        add('Operations', 'Cosmos DB single-write manual throughput', region, D(ru)/100*H, 'cosmos_ru',
            '20,000 RU/s x 730 / 100 per region in year 1; no free tier')
        add('Operations', 'Cosmos DB data and index storage', region, storage_gb,
            'cosmos_storage', '10 TB is assumed to include indexes; billed in every region')
        add('Operations', 'Independent full logical backup set: Blob', region,
            D(A['blob_backup_gb_per_region'])*data, f'blob_{region}',
            'One 30 TB logical backup set per continent; East US/Europe GZRS, Southeast Asia GRS')
        add('Operations', 'Blob write operation budget', region,
            D(A['blob_operations_per_region'])*load/10000, 'blob_writes_'+region,
            'Exact regional Hot GZRS/GRS write meter')
        add('Operations', 'Blob read operation budget', region,
            D(A['blob_operations_per_region'])*load/10000, 'blob_reads', '10 million monthly operations per region')
        add('Operations', 'Standard regional load balancer', region, H, 'lb_hour', '1 LB with <=5 included rules')
        add('Operations', 'Load-balancer processed data', region, D(A['load_balancer_gb_per_region'])*load, 'lb_gb')
        add('Operations', 'NAT Gateway', region, H, 'nat_hour', '1 outbound gateway per region; production HA design must be validated')
        add('Operations', 'NAT processed data', region, D(A['nat_gb_per_region'])*load, 'nat_gb')
        add('Operations', 'Public IPs: LB + NAT', region, 2*H, 'public_ip')
        zone = 'apac' if region=='southeastasia' else 'na_eu'
        cdn_gb = D(A['cdn_gb_per_region'])*load
        assert cdn_gb <= 10000  # first-tier pricing remains valid throughout modeled three years
        add('Operations', 'Front Door Premium CDN egress', region, cdn_gb, 'fd_gb_'+zone)
        add('Operations', 'Front Door Premium requests', region, D(A['cdn_requests_per_region'])*load/10000, 'fd_requests_'+zone)
        add('Operations', 'Front Door edge-to-origin requests', region, D(A['edge_to_origin_gb_per_region'])*load, 'fd_origin_'+zone)

    batch_h = H if mode=='baseline' else D(A['batch_optimized_hours'])*load
    gpu_h = H if mode=='baseline' else D(A['gpu_optimized_hours'])*load
    wh_h = H if mode=='baseline' else D(A['warehouse_optimized_hours'])*load
    # Explicitly provision more nodes if a projected schedule ever exceeds a month.
    assert batch_h <= H and gpu_h <= H and wh_h <= H
    add('Operations', 'Scheduled batch: 2 Linux D8s v5', 'eastus', A['batch_vms']*batch_h, 'batch_payg')
    add('Operations', 'GPU training: NC4as T4 v3', 'eastus', gpu_h, 'gpu')
    add('Operations', 'Synapse dedicated SQL pool DW100c', 'eastus', wh_h, 'warehouse', 'Pause compute after batch/report window; storage remains billed')
    add('Operations', 'Synapse dedicated warehouse storage and snapshots', 'eastus', math.ceil(D(A['warehouse_tb'])*data*D('1.2')),
        'warehouse_storage', '15 TB data + 20% snapshot allowance, rounded up to whole TB')
    add('Operations', 'Synapse native geo-redundant DR backup', 'eastus', D(A['warehouse_tb'])*1000*data,
        'warehouse_geo_backup', 'Native automatic geo-backup is additional to the explicit cross-continent logical exports')
    add('Operations', 'Synapse pipeline data movement', 'eastus', 400*load, 'pipeline_copy', '100 hours x 4 DIUs per month')
    add('Operations', 'Synapse orchestration', 'eastus', 10*load, 'pipeline_runs', '10,000 activity runs / 1,000')
    add('Operations', 'Front Door Premium base / WAF', 'Global', 1, 'frontdoor_base', 'Managed WAF rules and Private Link feature included; no separate WAF fee')
    add('Operations', 'Customer-managed private endpoints', 'Global', 11*H, 'private_endpoint',
        '3 SQL + 3 Cosmos + 3 Blob + 1 Synapse + 1 Key Vault; distinct from Front Door managed Private Link feature')
    add('Operations', 'Private-endpoint inbound data', 'All regions', 3000*load, 'private_ingress', '3 TB aggregate across endpoints; distinct processing fee')
    add('Operations', 'Private-endpoint outbound data', 'All regions', 3000*load, 'private_egress', '3 TB aggregate across endpoints; distinct processing fee')
    add('Operations', 'Private DNS zones', 'Global', 5, 'private_dns_zone', '5 shared service zones; fewer than 10,000 record sets each')
    add('Operations', 'Private DNS queries', 'Global', 30*load, 'private_dns_query', '30 million queries in year 1')
    add('Operations', 'Public DNS zone', 'Global', 1, 'public_dns_zone')
    add('Operations', 'Public DNS queries', 'Global', 10*load, 'public_dns_query')
    # Initial seeds are in migration; only monthly changes are included here.
    add('Operations', 'Cosmos cross-continent replication', 'eastus -> Europe + Asia',
        2*D(A['cosmos_replication_gb_per_destination'])*load, 'intercontinental_na_eu', 'SQL active geo-replication bandwidth is included and not charged again')
    add('Operations', 'Independent Blob backup cross-continent delta copies', 'eastus -> Europe + Asia',
        2*D(A['blob_delta_gb_per_destination'])*data, 'intercontinental_na_eu', '3 TB changes sent to each other continent each month')
    add('Operations', 'Intra-region cross-zone network allowance', 'All regions', 1, 'cost_management',
        'No separate cross-zone bandwidth charge assumed; restore/failed-over workload is covered by contingency')
    # Additional geo-redundant storage replication bandwidth, conservatively reserved.
    add('Operations', 'Paired-region Blob geo-replication bandwidth allowance', 'All regions',
        3*D(A['blob_delta_gb_per_destination'])*data, 'intercontinental_na_eu',
        'Conservative $0.05/GB proxy for 3 x 3 TB GRS/GZRS deltas; actual within-continent rates may be lower')
    total_vm_hours += A['batch_vms']*batch_h + gpu_h
    maximum_vms += A['batch_vms']+1
    add('Management', 'Central Log Analytics ingestion', 'eastus', max(ZERO,D(A['logs_gb'])*load-D(A['logs_free_gb'])), 'logs',
        '400 GB in year 1, 5 GB free, <=31 days interactive retention; no extended retention assumed')
    add('Management', 'Billable metric-alert time series', 'eastus', A['alert_time_series']-A['free_alert_time_series'], 'alerts')
    add('Management', 'Defender for Servers Plan 1', 'All regions', total_vm_hours, 'defender', 'Billed on actual provisioned server-hours')
    add('Management', 'Defender for SQL', '3 logical SQL servers + Synapse', 4, 'defender_sql')
    add('Management', 'Key Vault standard operations', 'eastus', 300*load, 'vault_ops', '3 million standard operations / 10,000')
    add('Management', 'Key Vault automatic key rotations', 'eastus', 3, 'vault_rotate')
    add('Management', 'Azure Standard support', 'Subscription', 1, 'support')
    add('Management', 'Cost Management, budgets and tags', 'Subscription', 1, 'cost_management')
    operations = sum((D(x['monthly_usd']) for x in rows if x['category']=='Operations'),ZERO)
    management = sum((D(x['monthly_usd']) for x in rows if x['category']=='Management'),ZERO)
    return dict(year=year,mode=mode,term=term,ahb=ahb,rows=rows,
                operations=str(money(operations)),management=str(money(management)),
                monthly=str(money(operations+management)),maximum_vms=maximum_vms,
                vm_hours=str(total_vm_hours))

def migration():
    rows=[]
    def add(item,q,k,note='',unit_price=None):
        price=rate(k) if unit_price is None else D(unit_price)
        rows.append(dict(item=item,quantity=str(q),rate_key=k,unit_price=str(price),
                         one_time_usd=str(money(D(q)*price)),calculation=note))
    add('Azure Migrate discovery and assessment',1,'migrate','Assess applications and VMs; use the supported Server Migration workflow for app hosts')
    add('Initial 30 TB upload to Azure',30000,'ingress','SQL 5 TB + Cosmos 10 TB + warehouse 15 TB; source ISP/egress excluded')
    add('SQL replication / validation temporary Windows D8s v5 hosts',2*A['migration_hours'],'temp_windows_d8',
        'Two temporary 8-vCPU hosts x 14 days x 24 hours; existing SQL licenses on source/distributor assumed')
    add('Temporary 128 GiB OS disks',D(2)*D(14)/30,'disk_eastus','2 disks x $9.60/month x 14/30 month')
    add('Temporary migration data/snapshot staging: 30 TB for 14 days',D(30000)*14/30,'blob_eastus',
        'Conservative GZRS staging allowance; includes SQL snapshots and load files')
    add('Synapse pipelines self-hosted IR copy',336,'pipeline_selfhost','336 billed activity-hours; integration runtime hosts costed separately')
    add('Synapse pipelines Azure IR copy',1000,'pipeline_copy','1000 DIU-hours; independent from byte-ingress charge')
    add('Migration pipeline orchestration',10,'pipeline_runs','10,000 activity runs / 1000')
    add('Temporary VpnGw1AZ migration connection',336,'vpn','On-premises side assumed existing; actual throughput/partner gateway quoted separately')
    add('VPN public IPv4',336,'public_ip')
    add('Initial Cosmos secondary-region seeds',20000,'intercontinental_na_eu','10 TB to Europe + 10 TB to Asia; SQL geo-seed transfer is included')
    add('Initial independent Blob backup copies to other continents',60000,'intercontinental_na_eu','30 TB x 2 destinations')
    add('Initial GRS/GZRS paired-region replication allowance',90000,'intercontinental_na_eu',
        '30 TB in each of 3 accounts; conservatively budget $0.05/GB, including non-North-American origins')
    # Production destination services during migration are additional to steady-state month 1.
    scheduled=estimate(mode='scheduled')
    add('14-day parallel Azure destination / validation overlap',D(14)/30,'cost_management',
        '14/30 of scheduled PAYG monthly model, including management; conservative additional pre-production window',D(scheduled['monthly']))
    add('Migration engineering and cutover effort allowance',80,'cost_management',
        'Assumed 80 hours x $75/hour; planning allowance, not a vendor cloud price',D(75))
    total=sum((D(r['one_time_usd']) for r in rows),ZERO)
    return dict(rows=rows,total=str(money(total)),cloud_only=str(money(total-D(6000))))

def write_csv(path, rows):
    with path.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

def main():
    out=ROOT/'data'
    cases={m:estimate(mode=m) for m in ['baseline','scheduled','optimized']}
    cases['optimized_3y']=estimate(term='3y')
    cases['optimized_ahb_if_eligible']=estimate(ahb=True)
    mig=migration()
    projections=[]
    for year in range(1,4):
        b=estimate(year,'baseline');o=estimate(year)
        annual_b=money(D(b['monthly'])*12)
        annual_o=money(D(o['monthly'])*12)
        one=D(mig['total']) if year==1 else ZERO
        total=annual_o+one
        projections.append(dict(year=year,baseline_monthly=b['monthly'],optimized_monthly=o['monthly'],
                                baseline_annual=str(annual_b),optimized_annual=str(annual_o),
                                one_time_migration=str(one),planned_total=str(money(total)),
                                budget_with_15pct_contingency=str(money(total*D('1.15'))),
                                annual_recurring_savings=str(money(annual_b-annual_o)),
                                maximum_vms=o['maximum_vms']))
    for key,c in cases.items():write_csv(out/(key+'-monthly.csv'),c['rows'])
    write_csv(out/'migration.csv',mig['rows']);write_csv(out/'three-year-budget.csv',projections)
    results={'assumptions':A,'cases':{k:{kk:vv for kk,vv in c.items() if kk!='rows'} for k,c in cases.items()},
             'migration':{k:v for k,v in mig.items() if k!='rows'},'projections':projections}
    (out/'results.json').write_text(json.dumps(results,indent=2)+'\n')
    print(json.dumps(results,indent=2))

if __name__=='__main__':main()
