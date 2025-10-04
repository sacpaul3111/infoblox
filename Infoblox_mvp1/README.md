# Infoblox DNS/DHCP Automation

Automated Infoblox NIOS record management using Ansible playbooks with CSV/Excel input processing.

## Overview

This project automates the creation and management of Infoblox DNS and DHCP records through:
- **CSV/Excel Templates** - Simple input format for bulk operations
- **Python Processor** - Converts CSV to JSON with intelligent field mapping
- **Ansible Playbooks** - Executes changes against Infoblox grid

## Supported Record Types

| Record Type | Description | Template File |
|------------|-------------|---------------|
| A Record | IPv4 DNS address records | `a_record.csv` |
| AAAA Record | IPv6 DNS address records | `aaaa_record.csv` |
| CNAME Record | Canonical name aliases | `cname_record.csv` |
| Fixed Address | DHCP fixed/reserved IP addresses | `fixed_address.csv` |
| Host Record | Combined DNS/DHCP host records | `host_record.csv` |
| MX Record | Mail exchanger records | `mx_record.csv` |
| Network | DHCP network objects | `network.csv` |
| PTR Record | Reverse DNS pointer records | `ptr_record.csv` |
| Network Range | DHCP address ranges/pools | `network_range.csv` |
| SRV Record | Service locator records | `srv_record.csv` |
| TXT Record | Text/SPF/DKIM records | `txt_record.csv` |
| DNS Zone | Forward/reverse DNS zones | `nios_zone.csv` |

## Quick Start

### 1. Prepare Your CSV File

Use the templates in `add/templates/` as examples:

```csv
name,ipv4addr,view,comment,Environment,Owner
webserver1.example.com,192.168.1.10,production,Web server,prod,teamA
dbserver1.example.com,192.168.1.11,production,Database server,prod,teamB
```

### 2. Process CSV to JSON

**Single file:**
```bash
python infoblox_record_processor.py add/templates/a_record.csv --grid-host grid01
```

**All templates:**
```bash
python process_all_records.py --grid-host grid01
```

### 3. Run Ansible Playbook

```bash
ansible-playbook add/playbooks/nios_a_record.yml -e grid_host=grid01
```

## Detailed Usage

### Processing Records

The `infoblox_record_processor.py` script converts CSV/Excel files to JSON format required by Ansible playbooks.

#### Command Line Options

```bash
python infoblox_record_processor.py <input_file> --grid-host <host> [options]

Required:
  input_file              CSV or Excel file to process
  --grid-host HOST        Grid host identifier (creates subdirectory)

Optional:
  --output-dir DIR        Output directory (default: add/prod_changes)
  --record-type TYPE      Record type (auto-detected from filename)
```

#### Examples

```bash
# Process A records
python infoblox_record_processor.py my_servers.csv --grid-host production-grid

# Process from Excel file
python infoblox_record_processor.py datacenter_hosts.xlsx --grid-host dc01

# Specify record type manually
python infoblox_record_processor.py records.csv --grid-host grid01 --record-type a_record

# Custom output directory
python infoblox_record_processor.py data.csv --grid-host grid01 --output-dir custom/path
```

### Batch Processing

Process all CSV templates at once:

```bash
python process_all_records.py --grid-host grid01
```

This will:
1. Scan `add/templates/` for all CSV files
2. Auto-detect record type from filename
3. Generate JSON files in `add/prod_changes/grid01/`
4. Display processing summary

### Running Playbooks

After generating JSON files, execute the appropriate Ansible playbook:

```bash
# A Records
ansible-playbook add/playbooks/nios_a_record.yml -e grid_host=grid01

# CNAME Records
ansible-playbook add/playbooks/nios_cname_record.yml -e grid_host=grid01

# Networks
ansible-playbook add/playbooks/nios_network.yml -e grid_host=grid01 -e batch_size=10
```

## CSV Template Format

### Important: Column Order is Flexible! 🎯

**You can arrange columns in ANY order** - the processor intelligently maps fields by name, not position.

```csv
# These all work equally well:
name,ipv4addr,view,comment
comment,view,ipv4addr,name
view,comment,name,ipv4addr
```

The processor also supports:
- ✅ **Case insensitive headers** - `Name`, `name`, `NAME` all work
- ✅ **Multiple column name aliases** - `ipv4addr`, `ip`, `ip_address` all map correctly
- ✅ **Optional fields** - Missing columns are handled gracefully
- ✅ **Extra custom fields** - Unknown columns become extensible attributes

### Common Fields

All record types support these extensible attributes:
- `Environment` - Environment designation (prod, test, dev)
- `Owner` - Team or owner name
- `Location` - Physical location
- `Department` - Department/organization
- `Creator` - Record creator

### A Record Example

```csv
name,ipv4addr,view,comment,Environment,Owner,Location,Department
webserver1.example.com,192.168.1.10,production,Web server,prod,teamA,DataCenter1,IT
```

**Required:** `name`, `ipv4addr`, `view`
**Optional:** `comment`, `ttl`, extensible attributes

### Host Record Example

```csv
name,view,ipv4addrs,ipv6addrs,comment,configure_for_dns,Environment,Owner
mailserver1.example.com,production,192.168.1.50;192.168.1.51,,Mail server,true,prod,teamB
```

**Multiple IPs:** Separate with semicolon (`;`)
**Required:** `name`, `view`
**Optional:** `ipv4addrs`, `ipv6addrs`, `comment`, `configure_for_dns`

### Network Example

```csv
network,network_view,comment,routers,domain-name-servers,domain-name,Environment,Owner
192.168.1.0/24,default,Production network,192.168.1.1,192.168.1.10;192.168.1.11,example.com,prod,network-team
```

**DHCP Options:** Automatically converted to Infoblox format
**Required:** `network`
**Optional:** `network_view`, `comment`, DHCP options (routers, domain-name-servers, etc.)

### Fixed Address Example

```csv
name,ipv4addr,mac,network,network_view,comment,routers,domain-name-servers
printer1,192.168.1.100,00:11:22:33:44:55,192.168.1.0/24,default,Office printer,192.168.1.1,8.8.8.8
```

**Required:** `ipv4addr`, `mac`
**Optional:** `name`, `network`, `network_view`, `comment`, DHCP options

## Output Structure

Generated JSON files are stored in:
```
add/prod_changes/{grid_host}/{record_type}.json
```

Example:
```
add/prod_changes/
├── grid01/
│   ├── a_record.json
│   ├── cname_record.json
│   ├── host_record.json
│   └── network.json
└── grid02/
    └── a_record.json
```

## JSON Output Format

### A Record
```json
[
    {
        "name": "webserver1.example.com",
        "ipv4addr": "192.168.1.10",
        "view": "production",
        "comment": "Web server",
        "extattrs": {
            "Environment": "prod",
            "Owner": "teamA",
            "Location": "DataCenter1",
            "Department": "IT"
        }
    }
]
```

### Host Record
```json
[
    {
        "name": "mailserver1.example.com",
        "view": "production",
        "comment": "Mail server with multiple IPs",
        "configure_for_dns": true,
        "ipv4addrs": [
            {"ipv4addr": "192.168.1.50"},
            {"ipv4addr": "192.168.1.51"}
        ],
        "extattrs": {
            "Environment": "prod",
            "Owner": "teamB"
        }
    }
]
```

## Project Structure

```
.
├── README.md                           # This file
├── infoblox_record_processor.py        # Main CSV/Excel processor
├── process_all_records.py              # Batch processor
├── file_processor.py                   # Legacy A record processor
├── process_records.py                  # Legacy wrapper
│
├── add/
│   ├── playbooks/                      # Ansible playbooks
│   │   ├── nios_a_record.yml
│   │   ├── nios_aaaa_record.yml
│   │   ├── nios_cname_record.yml
│   │   ├── nios_fixed_address.yml
│   │   ├── nios_host_record.yml
│   │   ├── nios_mx_record.yml
│   │   ├── nios_network.yml
│   │   ├── nios_ptr_record.yml
│   │   ├── nios_range.yml
│   │   ├── nios_srv_record.yml
│   │   ├── nios_txt_record.yml
│   │   └── nios_zone.yml
│   │
│   ├── templates/                      # CSV templates
│   │   ├── a_record.csv
│   │   ├── aaaa_record.csv
│   │   ├── cname_record.csv
│   │   ├── fixed_address.csv
│   │   ├── host_record.csv
│   │   ├── mx_record.csv
│   │   ├── network.csv
│   │   ├── ptr_record.csv
│   │   ├── network_range.csv
│   │   ├── srv_record.csv
│   │   ├── txt_record.csv
│   │   └── nios_zone.csv
│   │
│   └── prod_changes/                   # Generated JSON outputs
│       └── {grid_host}/
│           ├── a_record.json
│           ├── cname_record.json
│           └── ...
│
├── pre_check.py                        # Pre-change validation
└── post_check.py                       # Post-change verification
```

## Features

### Intelligent Field Mapping

The processor automatically maps various column names to standard fields:

- **Name:** `name`, `hostname`, `fqdn`, `server_name`
- **IPv4:** `ipv4addr`, `ip`, `ip_address`, `ipv4`, `ipaddr`
- **IPv6:** `ipv6addr`, `ipv6`, `ipv6_address`
- **View:** `view`, `dns_view`
- **Comment:** `comment`, `description`

### Extensible Attributes

Custom fields not matching standard names are automatically added as extensible attributes (extattrs). Common attributes:
- Environment
- Owner
- Location
- Department
- Creator

### DHCP Options Support

Network and Fixed Address records support DHCP options:
- `routers`
- `domain-name-servers`
- `domain-name`
- `dhcp-lease-time`
- `broadcast-address`

Options are automatically formatted for Infoblox API.

### Multi-Value Fields

Some fields support multiple values separated by semicolon (`;`):
- Host record IP addresses: `192.168.1.50;192.168.1.51`
- DNS servers: `8.8.8.8;8.8.4.4`

## Prerequisites

### Python Requirements

```bash
# Required
python 3.6+

# Optional (for Excel support)
pip install pandas openpyxl
```

### Ansible Requirements

```bash
# Install Infoblox collection
ansible-galaxy collection install infoblox.nios_modules

# Configure provider in your playbook vars
clean_provider:
  host: <infoblox_host>
  username: <username>
  password: <password>
```

## Error Handling

The processor validates:
- Required fields presence
- IP address format (IPv4/IPv6)
- Data type conversions (integers for ports, priorities, etc.)
- File existence and permissions

Warnings are displayed for:
- Missing optional fields
- Rows that cannot be parsed
- Unsupported DHCP options

## Workflow Example

### Complete Workflow: Adding A Records

1. **Create CSV file** (`my_servers.csv`):
```csv
name,ipv4addr,view,comment,Environment,Owner
web01.corp.com,10.1.1.10,production,Web Server 1,prod,webteam
web02.corp.com,10.1.1.11,production,Web Server 2,prod,webteam
db01.corp.com,10.1.1.20,production,Database Server,prod,dbteam
```

2. **Process to JSON**:
```bash
python infoblox_record_processor.py my_servers.csv --grid-host prod-grid
# Output: add/prod_changes/prod-grid/a_record.json
```

3. **Review JSON** (optional):
```bash
cat add/prod_changes/prod-grid/a_record.json
```

4. **Run Ansible playbook**:
```bash
ansible-playbook add/playbooks/nios_a_record.yml -e grid_host=prod-grid
```

5. **Verify** (optional):
```bash
python post_check.py --grid-host prod-grid
```

## Tips & Best Practices

1. **Use Templates** - Start with provided templates in `add/templates/`
2. **Test First** - Process a small CSV first to verify format
3. **Backup** - Keep original CSV files for reference
4. **Validate** - Review generated JSON before running playbooks
5. **Batch Size** - For large datasets, use `batch_size` parameter in playbooks
6. **Extensible Attributes** - Use consistent naming across all records
7. **Comments** - Include descriptive comments for troubleshooting
8. **Grid Host** - Use meaningful grid_host names (environment-location)

## Troubleshooting

### CSV Not Processing

```bash
# Check file exists
ls -la my_file.csv

# Verify CSV format
head my_file.csv

# Try manual record type
python infoblox_record_processor.py my_file.csv --grid-host test --record-type a_record
```

### Record Type Not Detected

Ensure filename contains record type keyword:
- `a_record` for A records
- `cname_record` for CNAME records
- etc.

Or specify manually with `--record-type`

### Missing Fields Error

Check CSV headers match template. Required fields vary by record type (see template examples).

### Excel Files Not Working

Install pandas and openpyxl:
```bash
pip install pandas openpyxl
```

## Advanced Usage

### Custom Column Names

The processor intelligently maps column variations:
```csv
# These all map to 'name' field
hostname,fqdn,server_name,name
```

### Processing Multiple Grids

```bash
# Process for multiple grids
for grid in grid01 grid02 grid03; do
    python process_all_records.py --grid-host $grid
done
```

### Integration with CI/CD

```bash
#!/bin/bash
# Example CI/CD pipeline script

GRID_HOST="prod-grid"

# Process CSV files
python process_all_records.py --grid-host $GRID_HOST || exit 1

# Run playbooks
ansible-playbook add/playbooks/nios_a_record.yml -e grid_host=$GRID_HOST || exit 1
ansible-playbook add/playbooks/nios_cname_record.yml -e grid_host=$GRID_HOST || exit 1

# Verify changes
python post_check.py --grid-host $GRID_HOST
```

## Contributing

When adding new record types:
1. Add record type to `RECORD_TYPE_MAP` in `infoblox_record_processor.py`
2. Create processor method `_process_{record_type}`
3. Create CSV template in `add/templates/`
4. Create Ansible playbook in `add/playbooks/`
5. Update this README

## Support

For issues or questions:
- Check error messages carefully
- Review sample templates
- Verify required fields for record type
- Test with small dataset first

## License

Internal use only - American Family Insurance
