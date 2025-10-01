# Quick Start Guide - Infoblox Record Processor

## 🚀 Process Records in 3 Steps

### Step 1: Prepare Your CSV File

Copy a template from `add/templates/` and fill in your data:

```bash
cp add/templates/a_record.csv my_servers.csv
# Edit my_servers.csv with your server data
```

Or create your own CSV with headers matching the template format.

### Step 2: Process CSV to JSON

**Single file:**
```bash
python infoblox_record_processor.py my_servers.csv --grid-host production-grid
```

**All templates at once:**
```bash
python process_all_records.py --grid-host production-grid
```

### Step 3: Run Ansible Playbook

```bash
ansible-playbook add/playbooks/nios_a_record.yml -e grid_host=production-grid
```

That's it! Your records are now in Infoblox.

## 📁 File Locations

### Inputs (CSV Templates)
```
add/templates/
├── a_record.csv          # A records
├── aaaa_record.csv       # AAAA records
├── cname_record.csv      # CNAME records
├── host_record.csv       # Host records
└── ...
```

### Outputs (Generated JSON)
```
add/prod_changes/{grid_host}/
├── a_record.json
├── cname_record.json
└── ...
```

### Playbooks
```
add/playbooks/
├── nios_a_record.yml
├── nios_cname_record.yml
└── ...
```

## 📝 CSV Format Examples

### ✨ Column Order is Flexible!

**Important:** You can arrange columns in any order - the processor maps by column name, not position!

```csv
# All of these work:
name,ipv4addr,view,comment
comment,view,ipv4addr,name
Owner,name,view,ipv4addr,Environment
```

### A Record
```csv
name,ipv4addr,view,comment,Environment,Owner
web01.corp.com,10.1.1.10,production,Web Server,prod,webteam
```

### CNAME Record
```csv
name,canonical,view,comment,ttl
www.corp.com,web01.corp.com,production,Website alias,3600
```

### Host Record (Multiple IPs)
```csv
name,view,ipv4addrs,comment,configure_for_dns
mail.corp.com,production,10.1.1.50;10.1.1.51,Mail server,true
```

Note: Use semicolons (`;`) to separate multiple IP addresses.

## 🔧 Common Commands

### Process specific record type
```bash
python infoblox_record_processor.py servers.csv --grid-host grid01 --record-type a_record
```

### Process all templates for multiple grids
```bash
for grid in grid01 grid02 grid03; do
    python process_all_records.py --grid-host $grid
done
```

### Run multiple playbooks
```bash
ansible-playbook add/playbooks/nios_a_record.yml -e grid_host=grid01
ansible-playbook add/playbooks/nios_cname_record.yml -e grid_host=grid01
ansible-playbook add/playbooks/nios_host_record.yml -e grid_host=grid01
```

## ✅ Verification

### Check generated JSON
```bash
cat add/prod_changes/grid01/a_record.json
```

### View processing summary
```bash
python process_all_records.py --grid-host grid01
# Shows success/fail count for each template
```

## 🔍 Troubleshooting

### CSV not processing?
1. Check file exists: `ls -la myfile.csv`
2. Verify headers match template
3. Try specifying record type: `--record-type a_record`

### Record type not detected?
Ensure filename contains keyword: `a_record`, `cname_record`, etc.

### Missing required fields?
Check template for required vs optional fields. Required fields vary by type:
- **A Record:** `name`, `ipv4addr`, `view`
- **CNAME:** `name`, `canonical`, `view`
- **Host:** `name`, `view`

### Excel files not working?
```bash
pip install pandas openpyxl
```

## 📊 Supported Record Types

| Type | Required Fields | Key Features |
|------|----------------|--------------|
| A | name, ipv4addr, view | IPv4 DNS records |
| AAAA | name, ipv6addr, view | IPv6 DNS records |
| CNAME | name, canonical, view | Aliases |
| Host | name, view | Multiple IPs, DNS/DHCP |
| MX | name, mail_exchanger, preference | Mail routing |
| PTR | name, ptrdname | Reverse DNS |
| TXT | name, text | SPF, DKIM, etc. |
| SRV | name, port, target, priority, weight, view | Service discovery |
| Network | network | DHCP networks |
| Range | network, start_addr, end_addr | DHCP pools |
| Zone | fqdn | DNS zones |
| Fixed | ipv4addr, mac | Reserved IPs |

## 💡 Tips

1. **Start Small** - Test with 2-3 records first
2. **Use Templates** - Copy from `add/templates/`
3. **Check JSON** - Review generated files before running playbooks
4. **Extensible Attributes** - Add custom columns (Environment, Owner, etc.)
5. **Comments** - Include descriptive comments for documentation
6. **Backup** - Keep original CSV files

## 📚 More Information

See [README.md](README.md) for complete documentation including:
- Detailed field descriptions
- Advanced usage examples
- Error handling
- Integration with CI/CD
- Custom column mapping

## 🆘 Need Help?

1. Check error message carefully
2. Review sample templates in `add/templates/`
3. Verify required fields for your record type
4. Test with template files first
5. Check [README.md](README.md) for detailed docs
