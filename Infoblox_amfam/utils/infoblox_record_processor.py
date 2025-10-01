
#!/usr/bin/env python3
"""
Enhanced Infoblox Record Processor
Processes CSV files for all Infoblox record types and generates JSON for Ansible playbooks
"""

import json
import re
import sys
import csv
import argparse
from pathlib import Path
from typing import List, Dict, Any, Optional

# Optional Excel support
try:
    import pandas as pd
    EXCEL_SUPPORT = True
except ImportError:
    EXCEL_SUPPORT = False


class InfobloxRecordProcessor:
    """Process CSV/Excel files for various Infoblox record types"""

    # Map filename patterns to record types and output filenames
    RECORD_TYPE_MAP = {
        'a_record': {
            'required': ['name', 'ipv4addr', 'view'],
            'optional': ['comment', 'ttl'],
            'output': 'a_record.json'
        },
        'aaaa_record': {
            'required': ['name', 'ipv6addr', 'view'],
            'optional': ['comment', 'ttl'],
            'output': 'aaaa_record.json'
        },
        'cname_record': {
            'required': ['name', 'canonical', 'view'],
            'optional': ['comment', 'ttl'],
            'output': 'cname_record.json'
        },
        'fixed_address': {
            'required': ['ipv4addr', 'mac'],
            'optional': ['name', 'network', 'network_view', 'comment', 'options'],
            'output': 'fixed_address.json'
        },
        'host_record': {
            'required': ['name', 'view'],
            'optional': ['comment', 'configure_for_dns', 'ipv4addrs', 'ipv6addrs'],
            'output': 'host_record.json'
        },
        'mx_record': {
            'required': ['name', 'mail_exchanger', 'preference'],
            'optional': ['view', 'comment', 'ttl'],
            'output': 'mx_record.json'
        },
        'network': {
            'required': ['network'],
            'optional': ['network_view', 'comment', 'options', 'members'],
            'output': 'network.json'
        },
        'ptr_record': {
            'required': ['name', 'ptrdname'],
            'optional': ['view', 'ipv4addr', 'ipv6addr', 'comment', 'ttl'],
            'output': 'ptr_record.json'
        },
        'network_range': {
            'required': ['network', 'start_addr', 'end_addr'],
            'optional': ['name', 'network_view', 'comment', 'disable', 'server_association_type', 'member'],
            'output': 'network_range.json'
        },
        'srv_record': {
            'required': ['name', 'port', 'target', 'priority', 'weight', 'view'],
            'optional': ['comment', 'ttl'],
            'output': 'srv_record.json'
        },
        'txt_record': {
            'required': ['name', 'text'],
            'optional': ['view', 'comment', 'ttl'],
            'output': 'txt_record.json'
        },
        'nios_zone': {
            'required': ['fqdn'],
            'optional': ['view', 'comment', 'zone_format', 'ns_group', 'grid_primary', 'grid_secondaries'],
            'output': 'nios_zone.json'
        }
    }

    def __init__(self, record_type: str):
        self.record_type = record_type
        if record_type not in self.RECORD_TYPE_MAP:
            raise ValueError(f"Unsupported record type: {record_type}")

        self.config = self.RECORD_TYPE_MAP[record_type]
        self.required_fields = self.config['required']
        self.optional_fields = self.config['optional']

    @staticmethod
    def detect_record_type(filename: str) -> Optional[str]:
        """Detect record type from filename"""
        filename_lower = Path(filename).stem.lower()

        # Sort by length descending to match longer patterns first (aaaa_record before a_record)
        record_types = sorted(InfobloxRecordProcessor.RECORD_TYPE_MAP.keys(),
                            key=len, reverse=True)

        for record_type in record_types:
            if record_type in filename_lower:
                return record_type

        return None

    def process_file(self, input_file: str, grid_host: str, output_dir: str = 'prod_changes') -> bool:
        """Process input file and generate JSON output"""
        try:
            input_path = Path(input_file)

            if not input_path.exists():
                print(f"Error: Input file '{input_file}' not found")
                return False

            # Create output directory structure
            output_path = Path(output_dir) / grid_host
            output_path.mkdir(parents=True, exist_ok=True)

            output_file = output_path / self.config['output']

            records = []
            file_ext = input_path.suffix.lower()

            if file_ext == '.csv':
                records = self._process_csv_file(input_path)
            elif file_ext in ['.xlsx', '.xls'] and EXCEL_SUPPORT:
                records = self._process_excel_file(input_path)
            elif file_ext in ['.xlsx', '.xls'] and not EXCEL_SUPPORT:
                print("Error: Excel support not available. Install pandas with: pip install pandas openpyxl")
                return False
            else:
                print(f"Error: Unsupported file format: {file_ext}")
                return False

            # Write JSON output
            with open(output_file, 'w') as f:
                json.dump(records, f, indent=4)

            print(f"Successfully processed {len(records)} {self.record_type} records")
            print(f"Output: {output_file}")
            return True

        except Exception as e:
            print(f"Error processing file: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _process_csv_file(self, file_path: Path) -> List[Dict[str, Any]]:
        """Process CSV file"""
        records = []

        with open(file_path, 'r', newline='', encoding='utf-8') as csvfile:
            # Try to detect delimiter
            sample = csvfile.read(1024)
            csvfile.seek(0)
            try:
                sniffer = csv.Sniffer()
                delimiter = sniffer.sniff(sample).delimiter
            except:
                delimiter = ','

            reader = csv.DictReader(csvfile, delimiter=delimiter)

            for row_num, row in enumerate(reader, 2):
                try:
                    record = self._process_row(row)
                    if record:
                        records.append(record)
                    elif any(row.values()):  # Skip empty rows
                        print(f"Warning: Could not parse row {row_num}: {row}")
                except Exception as e:
                    print(f"Warning: Error processing row {row_num}: {e}")

        return records

    def _process_excel_file(self, file_path: Path) -> List[Dict[str, Any]]:
        """Process Excel file using pandas"""
        if not EXCEL_SUPPORT:
            raise ImportError("Excel support requires pandas and openpyxl")

        records = []

        try:
            df = pd.read_excel(file_path, engine='openpyxl')

            for index, row in df.iterrows():
                try:
                    # Convert pandas Series to dict, handling NaN values
                    row_dict = {}
                    for col, value in row.items():
                        if pd.notna(value):
                            row_dict[col] = str(value).strip()

                    record = self._process_row(row_dict)
                    if record:
                        records.append(record)
                    elif any(row_dict.values()):
                        print(f"Warning: Could not parse Excel row {index + 2}: {row_dict}")
                except Exception as e:
                    print(f"Warning: Error processing Excel row {index + 2}: {e}")

        except Exception as e:
            print(f"Error reading Excel file: {e}")
            raise

        return records

    def _process_row(self, row: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """Process a single row based on record type"""

        # Route to specific processor based on record type
        processors = {
            'a_record': self._process_a_record,
            'aaaa_record': self._process_aaaa_record,
            'cname_record': self._process_cname_record,
            'fixed_address': self._process_fixed_address,
            'host_record': self._process_host_record,
            'mx_record': self._process_mx_record,
            'network': self._process_network,
            'ptr_record': self._process_ptr_record,
            'network_range': self._process_network_range,
            'srv_record': self._process_srv_record,
            'txt_record': self._process_txt_record,
            'nios_zone': self._process_zone
        }

        processor = processors.get(self.record_type)
        if processor:
            return processor(row)

        return None

    def _process_a_record(self, row: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """Process A record"""
        record = {}
        extattrs = {}

        # Map column names
        name = self._get_field(row, ['name', 'hostname', 'fqdn'])
        ipv4addr = self._get_field(row, ['ipv4addr', 'ip', 'ip_address', 'ipv4', 'ipaddr'])
        view = self._get_field(row, ['view', 'dns_view'])

        if not all([name, ipv4addr, view]):
            return None

        record['name'] = name
        record['ipv4addr'] = ipv4addr
        record['view'] = view

        # Optional fields
        comment = self._get_field(row, ['comment', 'description'])
        if comment:
            record['comment'] = comment

        # Collect extensible attributes
        extattr_fields = ['Environment', 'Owner', 'Location', 'Department', 'Creator']
        for field in extattr_fields:
            value = self._get_field(row, [field, field.lower()])
            if value:
                extattrs[field] = value

        record['extattrs'] = extattrs
        return record

    def _process_aaaa_record(self, row: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """Process AAAA record"""
        record = {}
        extattrs = {}

        name = self._get_field(row, ['name', 'hostname', 'fqdn'])
        ipv6addr = self._get_field(row, ['ipv6addr', 'ipv6', 'ipv6_address'])
        view = self._get_field(row, ['view', 'dns_view'])

        if not all([name, ipv6addr, view]):
            return None

        record['name'] = name
        record['ipv6addr'] = ipv6addr
        record['view'] = view

        comment = self._get_field(row, ['comment', 'description'])
        if comment:
            record['comment'] = comment

        # Extensible attributes
        extattr_fields = ['Environment', 'Owner', 'Location', 'Department', 'Creator']
        for field in extattr_fields:
            value = self._get_field(row, [field, field.lower()])
            if value:
                extattrs[field] = value

        record['extattrs'] = extattrs
        return record

    def _process_cname_record(self, row: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """Process CNAME record"""
        record = {}
        extattrs = {}

        name = self._get_field(row, ['name', 'hostname', 'alias'])
        canonical = self._get_field(row, ['canonical', 'target', 'cname'])
        view = self._get_field(row, ['view', 'dns_view'])

        if not all([name, canonical, view]):
            return None

        record['name'] = name
        record['canonical'] = canonical
        record['view'] = view

        comment = self._get_field(row, ['comment', 'description'])
        if comment:
            record['comment'] = comment

        ttl = self._get_field(row, ['ttl'])
        if ttl:
            try:
                record['ttl'] = int(ttl)
            except ValueError:
                pass

        # Extensible attributes
        extattr_fields = ['Environment', 'Owner', 'Location', 'Department', 'Creator']
        for field in extattr_fields:
            value = self._get_field(row, [field, field.lower()])
            if value:
                extattrs[field] = value

        record['extattrs'] = extattrs
        return record

    def _process_fixed_address(self, row: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """Process fixed address record"""
        record = {}

        ipv4addr = self._get_field(row, ['ipv4addr', 'ip', 'ip_address', 'ipaddr'])
        mac = self._get_field(row, ['mac', 'mac_address'])

        if not all([ipv4addr, mac]):
            return None

        record['ipv4addr'] = ipv4addr
        record['mac'] = mac.upper()

        name = self._get_field(row, ['name', 'hostname'])
        if name:
            record['name'] = name

        network = self._get_field(row, ['network'])
        if network:
            record['network'] = network

        network_view = self._get_field(row, ['network_view'])
        record['network_view'] = network_view if network_view else 'default'

        comment = self._get_field(row, ['comment', 'description'])
        if comment:
            record['comment'] = comment

        # Process DHCP options
        options = []
        dhcp_option_fields = {
            'routers': 3,
            'domain-name-servers': 6,
            'domain-name': 15
        }

        for option_name, option_num in dhcp_option_fields.items():
            value = self._get_field(row, [option_name, option_name.replace('-', '_')])
            if value:
                options.append({
                    'name': option_name,
                    'num': option_num,
                    'use_option': True,
                    'value': value,
                    'vendor_class': 'DHCP'
                })

        if options:
            record['options'] = options

        return record

    def _process_host_record(self, row: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """Process host record"""
        record = {}
        extattrs = {}

        name = self._get_field(row, ['name', 'hostname', 'fqdn'])
        view = self._get_field(row, ['view', 'dns_view'])

        if not all([name, view]):
            return None

        record['name'] = name
        record['view'] = view

        comment = self._get_field(row, ['comment', 'description'])
        if comment:
            record['comment'] = comment

        configure_for_dns = self._get_field(row, ['configure_for_dns'])
        if configure_for_dns:
            record['configure_for_dns'] = configure_for_dns.lower() in ['true', 'yes', '1']

        # Process IPv4 addresses (can be semicolon-separated)
        ipv4addrs_str = self._get_field(row, ['ipv4addrs', 'ipv4', 'ipv4_addresses'])
        if ipv4addrs_str:
            ipv4_list = [ip.strip() for ip in ipv4addrs_str.split(';') if ip.strip()]
            record['ipv4addrs'] = [{'ipv4addr': ip} for ip in ipv4_list]

        # Process IPv6 addresses (can be semicolon-separated)
        ipv6addrs_str = self._get_field(row, ['ipv6addrs', 'ipv6', 'ipv6_addresses'])
        if ipv6addrs_str:
            ipv6_list = [ip.strip() for ip in ipv6addrs_str.split(';') if ip.strip()]
            record['ipv6addrs'] = [{'ipv6addr': ip} for ip in ipv6_list]

        # Extensible attributes
        extattr_fields = ['Environment', 'Owner', 'Location', 'Department', 'Creator']
        for field in extattr_fields:
            value = self._get_field(row, [field, field.lower()])
            if value:
                extattrs[field] = value

        record['extattrs'] = extattrs
        return record

    def _process_mx_record(self, row: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """Process MX record"""
        record = {}
        extattrs = {}

        name = self._get_field(row, ['name', 'domain'])
        mail_exchanger = self._get_field(row, ['mail_exchanger', 'mx', 'mail_server'])
        preference = self._get_field(row, ['preference', 'priority'])

        if not all([name, mail_exchanger, preference]):
            return None

        record['name'] = name
        record['mail_exchanger'] = mail_exchanger
        try:
            record['preference'] = int(preference)
        except ValueError:
            return None

        view = self._get_field(row, ['view', 'dns_view'])
        record['view'] = view if view else 'default'

        comment = self._get_field(row, ['comment', 'description'])
        if comment:
            record['comment'] = comment

        ttl = self._get_field(row, ['ttl'])
        if ttl:
            try:
                record['ttl'] = int(ttl)
            except ValueError:
                pass

        # Extensible attributes
        extattr_fields = ['Environment', 'Owner', 'Location', 'Department', 'Creator']
        for field in extattr_fields:
            value = self._get_field(row, [field, field.lower()])
            if value:
                extattrs[field] = value

        if extattrs:
            record['extattrs'] = extattrs

        return record

    def _process_network(self, row: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """Process network record"""
        record = {}
        extattrs = {}

        network = self._get_field(row, ['network', 'cidr', 'subnet'])
        if not network:
            return None

        record['network'] = network

        network_view = self._get_field(row, ['network_view'])
        record['network_view'] = network_view if network_view else 'default'

        comment = self._get_field(row, ['comment', 'description'])
        if comment:
            record['comment'] = comment

        # Process DHCP options
        options = []
        dhcp_option_fields = {
            'routers': 3,
            'domain-name-servers': 6,
            'domain-name': 15,
            'dhcp-lease-time': 51,
            'broadcast-address': 28
        }

        for option_name, option_num in dhcp_option_fields.items():
            value = self._get_field(row, [option_name, option_name.replace('-', '_')])
            if value:
                options.append({
                    'name': option_name,
                    'num': option_num,
                    'use_option': True,
                    'value': value,
                    'vendor_class': 'DHCP'
                })

        if options:
            record['options'] = options

        # Extensible attributes
        extattr_fields = ['Environment', 'Owner', 'Location', 'Department', 'Creator']
        for field in extattr_fields:
            value = self._get_field(row, [field, field.lower()])
            if value:
                extattrs[field] = value

        record['extattrs'] = extattrs
        record['logic_filter_rules'] = []
        record['use_logic_filter_rules'] = False
        record['members'] = []
        record['vlans'] = []

        return record

    def _process_ptr_record(self, row: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """Process PTR record"""
        record = {}
        extattrs = {}

        name = self._get_field(row, ['name', 'ptr_name'])
        ptrdname = self._get_field(row, ['ptrdname', 'hostname', 'target'])

        if not all([name, ptrdname]):
            return None

        record['name'] = name
        record['ptrdname'] = ptrdname

        view = self._get_field(row, ['view', 'dns_view'])
        record['view'] = view if view else 'default'

        ipv4addr = self._get_field(row, ['ipv4addr', 'ipv4', 'ip'])
        if ipv4addr:
            record['ipv4addr'] = ipv4addr
        else:
            record['ipv4addr'] = ''

        ipv6addr = self._get_field(row, ['ipv6addr', 'ipv6'])
        if ipv6addr:
            record['ipv6addr'] = ipv6addr
        else:
            record['ipv6addr'] = ''

        comment = self._get_field(row, ['comment', 'description'])
        if comment:
            record['comment'] = comment

        ttl = self._get_field(row, ['ttl'])
        if ttl:
            try:
                record['ttl'] = int(ttl)
            except ValueError:
                pass

        # Extensible attributes
        extattr_fields = ['Environment', 'Owner', 'Location', 'Department', 'Creator']
        for field in extattr_fields:
            value = self._get_field(row, [field, field.lower()])
            if value:
                extattrs[field] = value

        record['extattrs'] = extattrs
        return record

    def _process_network_range(self, row: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """Process network range record"""
        record = {}
        extattrs = {}

        network = self._get_field(row, ['network', 'cidr'])
        start_addr = self._get_field(row, ['start_addr', 'start', 'start_address'])
        end_addr = self._get_field(row, ['end_addr', 'end', 'end_address'])

        if not all([network, start_addr, end_addr]):
            return None

        record['network'] = network
        record['start_addr'] = start_addr
        record['end_addr'] = end_addr

        name = self._get_field(row, ['name'])
        if name:
            record['name'] = name

        network_view = self._get_field(row, ['network_view'])
        if network_view:
            record['network_view'] = network_view

        comment = self._get_field(row, ['comment', 'description'])
        if comment:
            record['comment'] = comment

        disable = self._get_field(row, ['disable'])
        if disable:
            record['disable'] = disable.lower() in ['true', 'yes', '1']

        server_association_type = self._get_field(row, ['server_association_type'])
        if server_association_type:
            record['server_association_type'] = server_association_type

        member = self._get_field(row, ['member'])
        if member:
            record['member'] = {'name': member}

        # Extensible attributes
        extattr_fields = ['Environment', 'Owner', 'Location', 'Department', 'Creator']
        for field in extattr_fields:
            value = self._get_field(row, [field, field.lower()])
            if value:
                extattrs[field] = value

        if extattrs:
            record['extattrs'] = extattrs

        return record

    def _process_srv_record(self, row: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """Process SRV record"""
        record = {}
        extattrs = {}

        name = self._get_field(row, ['name', 'service'])
        port = self._get_field(row, ['port'])
        target = self._get_field(row, ['target', 'hostname'])
        priority = self._get_field(row, ['priority'])
        weight = self._get_field(row, ['weight'])
        view = self._get_field(row, ['view', 'dns_view'])

        if not all([name, port, target, priority, weight, view]):
            return None

        record['name'] = name
        try:
            record['port'] = int(port)
            record['priority'] = int(priority)
            record['weight'] = int(weight)
        except ValueError:
            return None

        record['target'] = target
        record['view'] = view

        comment = self._get_field(row, ['comment', 'description'])
        if comment:
            record['comment'] = comment

        # Extensible attributes
        extattr_fields = ['Environment', 'Owner', 'Location', 'Department', 'Creator']
        for field in extattr_fields:
            value = self._get_field(row, [field, field.lower()])
            if value:
                extattrs[field] = value

        if extattrs:
            record['extattrs'] = extattrs

        return record

    def _process_txt_record(self, row: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """Process TXT record"""
        record = {}
        extattrs = {}

        name = self._get_field(row, ['name', 'hostname'])
        text = self._get_field(row, ['text', 'value', 'txt'])

        if not all([name, text]):
            return None

        record['name'] = name
        record['text'] = text

        view = self._get_field(row, ['view', 'dns_view'])
        record['view'] = view if view else 'default'

        comment = self._get_field(row, ['comment', 'description'])
        if comment:
            record['comment'] = comment

        ttl = self._get_field(row, ['ttl'])
        if ttl:
            try:
                record['ttl'] = int(ttl)
            except ValueError:
                pass

        # Extensible attributes
        extattr_fields = ['Environment', 'Owner', 'Location', 'Department', 'Creator']
        for field in extattr_fields:
            value = self._get_field(row, [field, field.lower()])
            if value:
                extattrs[field] = value

        if extattrs:
            record['extattrs'] = extattrs

        return record

    def _process_zone(self, row: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """Process zone record"""
        record = {}
        extattrs = {}

        fqdn = self._get_field(row, ['fqdn', 'zone', 'domain'])
        if not fqdn:
            return None

        record['fqdn'] = fqdn

        view = self._get_field(row, ['view', 'dns_view'])
        record['view'] = view if view else 'default'

        comment = self._get_field(row, ['comment', 'description'])
        if comment:
            record['comment'] = comment

        zone_format = self._get_field(row, ['zone_format', 'format'])
        record['zone_format'] = zone_format if zone_format else 'FORWARD'

        ns_group = self._get_field(row, ['ns_group'])
        if ns_group:
            record['ns_group'] = ns_group

        grid_primary = self._get_field(row, ['grid_primary', 'primary'])
        if grid_primary:
            record['grid_primary'] = [{'name': grid_primary}]
        else:
            record['grid_primary'] = []

        record['grid_secondaries'] = []

        # Extensible attributes
        extattr_fields = ['Environment', 'Owner', 'Location', 'Department', 'Creator']
        for field in extattr_fields:
            value = self._get_field(row, [field, field.lower()])
            if value:
                extattrs[field] = value

        if extattrs:
            record['extattrs'] = extattrs

        return record

    def _get_field(self, row: Dict[str, str], field_names: List[str]) -> Optional[str]:
        """Get field value from row trying multiple possible field names"""
        for field_name in field_names:
            for key, value in row.items():
                if key.lower() == field_name.lower():
                    if value and str(value).strip():
                        return str(value).strip()
        return None


def main():
    """Command line interface"""
    parser = argparse.ArgumentParser(
        description='Process Infoblox records from CSV/Excel to JSON',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Process A records
  python utils/infoblox_record_processor.py templates/a_record.csv --grid-host grid01

  # Process all template files
  python utils/infoblox_record_processor.py templates/*.csv --grid-host grid01

  # Auto-detect record type from filename
  python utils/infoblox_record_processor.py my_a_records.csv --grid-host grid01
        '''
    )

    parser.add_argument('input_file', help='Input CSV or Excel file')
    parser.add_argument('--grid-host', required=True, help='Grid host identifier')
    parser.add_argument('--output-dir', default='prod_changes', help='Output directory (default: prod_changes)')
    parser.add_argument('--record-type', help='Record type (auto-detected from filename if not specified)')

    args = parser.parse_args()

    # Detect record type if not specified
    record_type = args.record_type
    if not record_type:
        record_type = InfobloxRecordProcessor.detect_record_type(args.input_file)
        if not record_type:
            print(f"Error: Could not detect record type from filename: {args.input_file}")
            print(f"Please specify --record-type")
            print(f"Supported types: {', '.join(InfobloxRecordProcessor.RECORD_TYPE_MAP.keys())}")
            sys.exit(1)
        print(f"Detected record type: {record_type}")

    try:
        processor = InfobloxRecordProcessor(record_type)
        success = processor.process_file(args.input_file, args.grid_host, args.output_dir)
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
