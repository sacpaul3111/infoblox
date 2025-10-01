# GitLab CI Pipeline User Guide

## Overview

The enhanced GitLab CI pipeline allows you to deploy Infoblox DNS/DHCP records directly through the GitLab web interface by simply pasting CSV data.

## 🚀 Quick Start

### 1. Open GitLab Pipeline

Navigate to: **CI/CD → Pipelines → Run Pipeline**

### 2. Configure Variables

You'll see three dropdown fields and one large text field:

#### A. Select Environment (Grid)
```
Options:
- cabgridmgr  (CAB Grid Manager)
- etsl        (ETSL Grid)
- nhq         (NHQ Grid Manager)
- enterprise  (Enterprise Grid Manager)
```

#### B. Select Record Type
```
Options:
- a_record          (IPv4 DNS A records)
- aaaa_record       (IPv6 DNS AAAA records)
- cname_record      (CNAME aliases)
- host_record       (Host records - DNS/DHCP)
- mx_record         (Mail exchanger records)
- ptr_record        (Reverse DNS PTR records)
- txt_record        (TXT records - SPF, DKIM)
- srv_record        (Service discovery records)
- network           (DHCP network objects)
- network_range     (DHCP address ranges)
- fixed_address     (DHCP fixed/reserved IPs)
- nios_zone         (DNS zones)
```

#### C. Select Operation
```
Options:
- add     (Create/update records - default)
- delete  (Remove records)
```

#### D. Paste CSV Data (Large Text Field)
Paste your CSV data with headers and records.

### 3. Run Pipeline

Click **"Run Pipeline"** button

### 4. Monitor Progress

Watch the pipeline stages execute:
1. ✅ File Processing - Validates and converts CSV to JSON
2. ✅ Pre-Implementation - Network tests and validation
3. ✅ Validation Checkpoint - Ready for deployment
4. 🔵 Deploy - **Manual trigger required**
5. ✅ Post-Implementation - Cleanup

### 5. Deploy (Manual Step)

Once validation passes, click **"Play"** button on the Deploy stage to execute the changes.

## 📝 CSV Format Examples

### A Record
```csv
name,ipv4addr,view,comment,Environment,Owner
webserver1.amfam.com,192.168.1.10,production,Web server,prod,teamA
dbserver1.amfam.com,192.168.1.11,production,Database server,prod,teamB
appserver1.amfam.com,192.168.1.12,production,Application server,prod,teamA
```

### CNAME Record
```csv
name,canonical,view,comment
www.amfam.com,webserver1.amfam.com,production,Website alias
mail.amfam.com,mailserver1.amfam.com,production,Mail server alias
```

### Host Record (Multiple IPs)
```csv
name,view,ipv4addrs,comment,configure_for_dns
mailserver1.amfam.com,production,192.168.1.50;192.168.1.51,Mail server cluster,true
```
**Note:** Use semicolon (`;`) to separate multiple IP addresses

### MX Record
```csv
name,mail_exchanger,preference,view,comment
amfam.com,mail1.amfam.com,10,production,Primary mail server
amfam.com,mail2.amfam.com,20,production,Secondary mail server
```

### Network
```csv
network,network_view,comment,routers,domain-name-servers,domain-name
192.168.1.0/24,default,Production network,192.168.1.1,192.168.1.10;192.168.1.11,amfam.com
```

### Fixed Address
```csv
name,ipv4addr,mac,network,comment
printer1,192.168.1.100,00:11:22:33:44:55,192.168.1.0/24,Office printer
```

### TXT Record
```csv
name,text,view,comment
amfam.com,v=spf1 include:_spf.amfam.com ~all,production,SPF record
```

### PTR Record
```csv
name,ptrdname,view,ipv4addr,comment
10.1.168.192.in-addr.arpa,webserver1.amfam.com,production,192.168.1.10,Web server reverse DNS
```

### SRV Record
```csv
name,port,target,priority,weight,view,comment
_ldap._tcp.amfam.com,389,ldapserver1.amfam.com,10,60,production,Primary LDAP
```

### DNS Zone
```csv
fqdn,view,comment,zone_format
production.amfam.com,production,Production zone,FORWARD
```

## 🎯 Important Features

### 1. Flexible Column Order
**You can arrange columns in ANY order!**

These all work:
```csv
# Standard order
name,ipv4addr,view,comment

# Reverse order
comment,view,ipv4addr,name

# Mixed order
Owner,name,view,ipv4addr,Environment
```

### 2. Case Insensitive Headers
```csv
Name,IPV4ADDR,View    # Works
name,ipv4addr,view    # Works
NAME,IPV4ADDR,VIEW    # Works
```

### 3. Column Name Aliases
Multiple names map to same field:
- **IP:** `ipv4addr`, `ip`, `ip_address`, `ipaddr`
- **Name:** `name`, `hostname`, `fqdn`
- **View:** `view`, `dns_view`
- **Comment:** `comment`, `description`

### 4. Optional Fields
Missing optional columns are handled gracefully. Only include what you need.

### 5. Extensible Attributes
Unknown columns automatically become extensible attributes:
- Environment
- Owner
- Location
- Department
- Creator

## 📏 Input Limits

- **Maximum Size:** 5000 characters
- **Estimated Capacity:**
  - Simple format: ~200 records
  - With comments: ~100 records
  - Complex format: ~50 records

## 🔍 Pipeline Stages Explained

### Stage 1: File Processing (Automatic)
- Validates CSV format
- Checks character limits
- Converts CSV to JSON
- Generates file for deployment
- **Artifacts:** JSON files stored for 1 hour

### Stage 2: Pre-Implementation (Automatic)
- Tests grid connectivity
- Validates JSON format
- Verifies record count
- Checks playbook existence

### Stage 3: Validation Checkpoint (Automatic)
- Summary of what will be deployed
- Final checkpoint before deployment
- **Pipeline pauses here**

### Stage 4: Deploy (MANUAL)
- **Requires manual trigger**
- Executes Ansible playbook
- Creates/updates/deletes records in Infoblox
- **Click "Play" button to proceed**

### Stage 5: Post-Implementation (Automatic)
- Cleanup operations
- Summary report
- Success confirmation

## ⚠️ Troubleshooting

### CSV Validation Failed
**Problem:** "ERROR: CSV_DATA is empty!"

**Solution:**
- Ensure you pasted data in the CSV_DATA field
- Include header row
- Check for at least one data row

### Character Limit Exceeded
**Problem:** "ERROR: Input exceeds character limit!"

**Solution:**
- Split into multiple pipeline runs
- Remove optional columns (comments, extra attributes)
- Use shorter hostnames
- Current: 5000 characters max

### Invalid CSV Format
**Problem:** "Could not parse row"

**Solution:**
- Check required fields for your record type
- Verify comma separation
- Ensure no missing required columns
- See templates in `add/templates/` directory

### Playbook Not Found
**Problem:** "ERROR: Playbook not found"

**Solution:**
- Verify RECORD_TYPE matches available options
- Check playbook exists in `add/playbooks/nios_${RECORD_TYPE}.yml`

### Grid Unreachable
**Problem:** "Grid manager is unreachable"

**Solution:**
- Verify environment selection
- Check network connectivity
- Confirm grid is online
- Contact network team

## 💡 Tips & Best Practices

### 1. Start Small
Test with 2-3 records first to validate format

### 2. Use Templates
Copy from `add/templates/` directory for correct format

### 3. Validate Locally First
```bash
python infoblox_record_processor.py your_file.csv --grid-host test --record-type a_record
```

### 4. Include Headers
Always include the header row in your CSV data

### 5. Check Required Fields
Each record type has different required fields:
- **A Record:** name, ipv4addr, view
- **CNAME:** name, canonical, view
- **Host:** name, view
- **MX:** name, mail_exchanger, preference

### 6. Use Comments
Add descriptive comments for easier troubleshooting

### 7. Test Environment First
Use test/dev grids before production

### 8. Manual Deployment Step
Deployment requires manual trigger - this is by design for safety

### 9. Review Validation Output
Check validation stage logs before deploying

### 10. Keep CSV Backup
Save your CSV data locally for records

## 📊 Record Type Requirements

| Record Type | Required Fields | Key Optional Fields |
|------------|-----------------|---------------------|
| A Record | name, ipv4addr, view | comment, ttl |
| AAAA Record | name, ipv6addr, view | comment, ttl |
| CNAME | name, canonical, view | comment, ttl |
| Host | name, view | ipv4addrs, ipv6addrs, comment |
| MX | name, mail_exchanger, preference | view, comment, ttl |
| PTR | name, ptrdname | view, ipv4addr, comment |
| TXT | name, text | view, comment, ttl |
| SRV | name, port, target, priority, weight, view | comment |
| Network | network | network_view, comment, options |
| Range | network, start_addr, end_addr | name, comment |
| Fixed | ipv4addr, mac | name, network, comment |
| Zone | fqdn | view, comment, zone_format |

## 🔐 Security Notes

1. **Credentials** are stored as GitLab CI/CD variables (secured)
2. **Manual deployment** prevents accidental changes
3. **Validation stage** catches errors before deployment
4. **Audit trail** in GitLab pipeline history
5. **JSON artifacts** expire after 1 hour

## 📞 Support

### Common Issues
- CSV format errors → Check templates
- Character limit → Split into batches
- Grid unreachable → Verify environment
- Missing fields → Review requirements

### Need Help?
1. Check pipeline logs for detailed errors
2. Review templates in `add/templates/`
3. Consult [README.md](README.md) for complete docs
4. Test locally with `infoblox_record_processor.py`

## 🎓 Examples

### Example 1: Add 3 A Records
```
Environment: cabgridmgr
Record Type: a_record
Operation: add
CSV Data:
name,ipv4addr,view,comment
web01.amfam.com,10.1.1.10,production,Web Server 1
web02.amfam.com,10.1.1.11,production,Web Server 2
web03.amfam.com,10.1.1.12,production,Web Server 3
```

### Example 2: Add CNAME Aliases
```
Environment: enterprise
Record Type: cname_record
Operation: add
CSV Data:
name,canonical,view,comment,ttl
www.amfam.com,web01.amfam.com,production,Primary website,3600
mail.amfam.com,mailserver1.amfam.com,production,Email service,7200
```

### Example 3: Create DNS Zone
```
Environment: nhq
Record Type: nios_zone
Operation: add
CSV Data:
fqdn,view,comment,zone_format
newapp.amfam.com,production,New application zone,FORWARD
```

## 📈 Workflow Summary

```
1. Open GitLab → CI/CD → Pipelines → Run Pipeline
2. Select Environment (Grid)
3. Select Record Type
4. Select Operation (add/delete)
5. Paste CSV Data
6. Click "Run Pipeline"
7. Wait for Validation ✅
8. Review validation output
9. Click "Play" on Deploy stage 🔵
10. Wait for completion ✅
11. Verify records in Infoblox
```

## ✅ Success Indicators

- **File Processing:** "PROCESSING COMPLETE"
- **Validation:** "PRE-IMPLEMENTATION VALIDATION COMPLETE"
- **Deployment:** "DEPLOYMENT SUCCESSFUL"
- **Post-Implementation:** "Deployment complete"

## 🚦 Pipeline Status Colors

- 🔵 **Blue (Manual)** - Waiting for manual trigger
- 🟡 **Yellow (Running)** - Stage in progress
- ✅ **Green (Passed)** - Stage completed successfully
- ❌ **Red (Failed)** - Stage failed, check logs

---

**Remember:** Always review validation logs before clicking deploy!
