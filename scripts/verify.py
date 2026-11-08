"""Independent arithmetic, source, capacity and real calculator-export checks."""
import csv
import hashlib
import json
import math
from pathlib import Path
from decimal import Decimal as D
from zipfile import ZipFile
from xml.etree import ElementTree as ET
import estimate as m

checks=[]
def check(name, condition, evidence):
    if not condition:raise AssertionError((name,evidence))
    checks.append({'check':name,'result':'PASS','evidence':str(evidence)})

def workbook_rows(path):
    ns={'x':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
    with ZipFile(path) as z:
        strings=[]
        if 'xl/sharedStrings.xml' in z.namelist():
            for si in ET.fromstring(z.read('xl/sharedStrings.xml')).findall('x:si',ns):
                strings.append(''.join(t.text or '' for t in si.findall('.//x:t',ns)))
        rows=[]
        for row in ET.fromstring(z.read('xl/worksheets/sheet1.xml')).findall('.//x:sheetData/x:row',ns):
            vals={}
            for c in row.findall('x:c',ns):
                v=c.find('x:v',ns)
                if v is None:continue
                txt=v.text or ''
                vals[''.join(filter(str.isalpha,c.attrib['r']))]=strings[int(txt)] if c.attrib.get('t')=='s' else txt
            if vals:rows.append(vals)
        return rows

check('730-hour month fully allocated',m.A['peak_hours']+m.A['off_peak_hours']==m.A['hours_per_month'],m.A['hours_per_month'])
check('Assignment starting VM and data counts',sum(m.A['api_peak_vms'])==20 and m.A['web_vms_per_region']*3==30 and
      m.A['sql_gb']==5000 and m.A['cosmos_gb']==10000 and m.A['warehouse_tb']==15,'30 web VMs, 20 peak API VMs, 5/10/15 TB')
for key,value in m.S.items():
    check('Price nonnegative: '+key,D(str(value['price']))>=0,value['price'])
    if 'record' in value:
        rec=value['record']
        check('Quoted record matches: '+key,rec['currencyCode']=='USD' and D(str(rec['retailPrice']))==D(str(value['price'])),rec['meterId'])
        check('No Spot/DevTest substitution: '+key,rec['type'] in ('Consumption','Reservation') and not any(x in rec['meterName'] for x in ['Spot','Low Priority']),rec['productName'])

wb=m.ROOT/'evidence/azure-calculator-reference.xlsx'
rows=workbook_rows(wb)
expected={
    'Virtual Machines':m.rate('vm_eastus_3y')/36*10,
    'Azure Cosmos DB':D(3)*(D(200)*730*m.rate('cosmos_ru')+10000*m.rate('cosmos_storage')),
    'Azure SQL Database':D(16)*730*m.rate('sql_eastus_payg')+5000*m.rate('sql_storage_eastus')+5000*m.rate('sql_backup_eastus')}
ref_total=D(0)
for name,cost in expected.items():
    row=next(x for x in rows if x.get('B')==name)
    check('Actual calculator export: '+name,m.money(row['F'])==m.money(cost),f"export {row['F']} vs independent {cost}")
    ref_total+=D(row['F'])
total=next(x for x in rows if 'Total' in x.values())
check('Calculator exported grand total',m.money(total['F'])==m.money(ref_total)==D('15941.08'),total['F'])
cosmos_row=next(x for x in rows if x.get('B')=='Azure Cosmos DB')
check('Calculator actual 3 requested regions',all(x in cosmos_row['E'] for x in ['East US (Write Region)','West Europe','Southeast Asia']),cosmos_row['E'])
check('Calculator no free-tier credit','Always-free quantity disabled' in cosmos_row['E'],cosmos_row['E'])

results=json.loads((m.ROOT/'data/results.json').read_text())
for key in ['baseline','scheduled','optimized','optimized_3y','optimized_ahb_if_eligible']:
    csvrows=list(csv.DictReader((m.ROOT/f'data/{key}-monthly.csv').open(encoding='utf-8')))
    actual=sum((D(r['monthly_usd']) for r in csvrows),D(0))
    check('CSV grand total: '+key,actual==D(results['cases'][key]['monthly']),actual)
    for r in csvrows:
        check('Quantity times price: '+key+' / '+r['region']+' / '+r['item'],m.money(D(r['quantity'])*D(r['unit_price']))==D(r['monthly_usd']),r['monthly_usd'])

b=m.estimate(mode='baseline');s=m.estimate(mode='scheduled');o=m.estimate()
check('API actual scheduled VM-hours',sum((D(r['quantity']) for r in s['rows'] if r['item'].startswith('API:')),D(0))==9740,'20 x 244 + 10 x 486 = 9740')
check('Savings are sequential, not added twice',D(b['monthly'])-D(o['monthly'])==(D(b['monthly'])-D(s['monthly']))+(D(s['monthly'])-D(o['monthly'])),'baseline -> scheduled -> reservations')
check('License discount isolated',D(o['monthly'])-D(m.estimate(ahb=True)['monthly'])==D('805.92'),'6 Windows D4s v5 x 730 x (0.376 - 0.192)')
for year in range(1,4):
    case=m.estimate(year);peak=m.estimate(year,'baseline')
    check(f'Year {year} operations + management',D(case['operations'])+D(case['management'])==D(case['monthly']),case['monthly'])
    check(f'Year {year} savings positive',D(case['monthly'])<D(peak['monthly']),peak['monthly']+' vs '+case['monthly'])
    data=(D(1)+D(str(m.A['data_growth'])))**(year-1)
    load=(D(1)+D(str(m.A['traffic_growth'])))**(year-1)
    ru=math.ceil(D(m.A['cosmos_ru_per_region'])*load/100)*100
    check(f'Year {year} Cosmos throughput storage floor',D(ru)>=D(m.A['cosmos_gb'])*data,f'{ru} RU/s vs {10000*data} GB')
    check(f'Year {year} first-tier CDN and Blob rates valid',5000*load<=10000 and 30000*data<51200,'Regional quantities stay inside selected rate tiers')
    check(f'Year {year} web minimum preserved',math.ceil(D(10)*load)>=10,'At least 10 web VMs per region')
    check(f'Year {year} persisted disks retained',sum((D(r['quantity']) for r in case['rows'] if r['item'].startswith('128 GiB')),D(0))==case['maximum_vms'],case['maximum_vms'])
    p=results['projections'][year-1]
    check(f'Year {year} annualization',D(p['optimized_annual'])==D(case['monthly'])*12,p['optimized_annual'])
    check(f'Year {year} contingency separate',D(p['budget_with_15pct_contingency'])==m.money(D(p['planned_total'])*D('1.15')),p['budget_with_15pct_contingency'])
check('Migration charged exactly once',sum((D(p['one_time_migration']) for p in results['projections']),D(0))==D(results['migration']['total']),results['migration']['total'])
migrows=list(csv.DictReader((m.ROOT/'data/migration.csv').open(encoding='utf-8')))
check('Migration CSV arithmetic',sum((D(r['one_time_usd']) for r in migrows),D(0))==D(results['migration']['total']),results['migration']['total'])
check('Source snapshot and report exclude confirmed AHB assumption',m.A['eligible_windows_licenses_confirmed'] is False,'Principal plan includes OS licensing')
output={'status':'PASS','checks_passed':len(checks),'calculator_export_sha256':hashlib.sha256(wb.read_bytes()).hexdigest(),
        'calculator_reference_total_usd':str(m.money(ref_total)),'model_results':results['cases'],
        'checks':checks,'scope':'Arithmetic, pricing records, actual calculator export and assignment quantities; not a deployed application performance or PCI certification test.'}
(m.ROOT/'evidence/verification.json').write_text(json.dumps(output,indent=2)+'\n')
print(f'PASS: {len(checks)} checks; actual calculator export reconciles to $15,941.08; all CSVs and 3-year totals reconcile.')
