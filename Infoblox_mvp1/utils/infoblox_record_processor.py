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
        },
        'alias_record': {
            'required': ['name', 'target_name', 'target_type', 'view'],
            'optional': ['comment', 'disable', 'use_ttl'],
            'output': 'alias_record.json'
        },
        'network_view': {
            'required': ['name'],
            'optional': ['comment'],
            'output': 'network_view.json'
        },
        'zone_rp': {
            'required': ['fqdn', 'view'],
            'optional': ['comment', 'rpz_policy', 'rpz_severity', 'rpz_type', 'rpz_priority', 
                        'ns_group', 'grid_primary', 'network_view', 'soa_default_ttl',
                        'soa_expire', 'soa_negative_ttl', 'soa_refresh', 'soa_retry'],
            'output': 'zone_rp.json'
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
            'alias_record': self._process_alias_record,
            'srv_record': self._process_srv_record,
            'txt_record': self._process_txt_record,
            'nios_zone': self._process_zone,
            'network_view': self._process_network_view,
            'zone_rp': self._process_zone_rp


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

        # Add comment if present (before extattrs)
        comment = self._get_field(row, ['comment', 'description'])
        if comment:
            record['comment'] = comment

        # Collect extensible attributes
        extattr_fields = ['Environment', 'Owner', 'Location', 'Department', 'Creator']
        for field in extattr_fields:
            value = self._get_field(row, [field, field.lower()])
            if value:
                extattrs[field] = value

        # Only add extattrs if there are any attributes, otherwise add empty dict
        if extattrs:
            record['extattrs'] = extattrs
        else:
            record['extattrs'] = {}  # Based on most of your examples
        
        # View should be last
        record['view'] = view

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
        
        # Add comment if present (before extattrs)
        comment = self._get_field(row, ['comment', 'description'])
        if comment:
            record['comment'] = comment

        # Collect extensible attributes
        extattr_fields = ['Environment', 'Owner', 'Location', 'Department', 'Creator']
        for field in extattr_fields:
            value = self._get_field(row, [field, field.lower()])
            if value:
                extattrs[field] = value

        # Only add extattrs if there are any attributes
        if extattrs:
            record['extattrs'] = extattrs
        
        # View should be last
        record['view'] = view

        # TTL is optional (not shown in your examples but supported)
        ttl = self._get_field(row, ['ttl'])
        if ttl:
            try:
                record['ttl'] = int(ttl)
            except ValueError:
                pass

        return record

    def _process_fixed_address(self, row: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """Process fixed address record"""
        record = {}
        extattrs = {}

        ipv4addr = self._get_field(row, ['ipv4addr', 'ip', 'ip_address', 'ipaddr'])
        mac = self._get_field(row, ['mac', 'mac_address'])
        
        if not ipv4addr:
            return None
        
        # Set required fields
        record['ipv4addr'] = ipv4addr
        
        # Handle MAC and match_client
        match_client = self._get_field(row, ['match_client'])
        if match_client:
            record['match_client'] = match_client.upper()
        elif mac and mac != '00:00:00:00:00:00':
            record['match_client'] = 'MAC_ADDRESS'
        else:
            record['match_client'] = 'RESERVED'
        
        record['mac'] = mac.upper() if mac else '00:00:00:00:00:00'
        
        # Network fields
        network = self._get_field(row, ['network', 'subnet'])
        if network:
            record['network'] = network
        
        network_view = self._get_field(row, ['network_view'])
        record['network_view'] = network_view if network_view else 'default'
        
        # Optional name and comment
        name = self._get_field(row, ['name', 'hostname'])
        if name:
            record['name'] = name
        
        comment = self._get_field(row, ['comment', 'description'])
        if comment:
            record['comment'] = comment
        
        # Boolean flags (default values)
        record['allow_telnet'] = False
        record['always_update_dns'] = False
        record['client_identifier_prepend_zero'] = False
        record['deny_bootp'] = False
        record['dhcp_client_identifier'] = ""
        record['disable'] = False
        record['disable_discovery'] = False
        record['discover_now_status'] = "NONE"
        record['enable_ddns'] = False
        record['enable_pxe_lease_time'] = False
        record['ignore_dhcp_option_list_request'] = False
        record['is_invalid_mac'] = False
        record['reserved_interface'] = None
        
        # Process DHCP options
        options = []
        dhcp_option_fields = {
            'domain-name-servers': 6,
            'domain-name': 15,
            'dhcp-lease-time': 51,
            'routers': 3,
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
        
        record['options'] = options
        
        # Use flags (defaults)
        record['use_bootfile'] = False
        record['use_bootserver'] = False
        record['use_cli_credentials'] = False
        record['use_ddns_domainname'] = False
        record['use_deny_bootp'] = False
        record['use_enable_ddns'] = False
        record['use_ignore_dhcp_option_list_request'] = False
        record['use_logic_filter_rules'] = False
        record['use_ms_options'] = False
        record['use_nextserver'] = False
        record['use_options'] = True if options else False
        record['use_pxe_lease_time'] = False
        record['use_snmp3_credential'] = False
        record['use_snmp_credential'] = False
        
        # Empty arrays
        record['logic_filter_rules'] = []
        record['ms_options'] = []
        
        # Extensible attributes
        extattr_fields = ['Environment', 'Owner', 'Location', 'Department', 'Creator']
        for field in extattr_fields:
            value = self._get_field(row, [field, field.lower()])
            if value:
                extattrs[field] = value
        
        record['extattrs'] = extattrs
        
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

        # Configure for DNS (default true for host records)
        configure_for_dns = self._get_field(row, ['configure_for_dns', 'dns'])
        if configure_for_dns:
            record['configure_for_dns'] = configure_for_dns.lower() in ['true', 'yes', '1']
        else:
            record['configure_for_dns'] = True  # Default to true

        # Process IPv4 addresses (can be semicolon-separated)
        ipv4addrs_str = self._get_field(row, ['ipv4addrs', 'ipv4', 'ipv4_addresses', 'ipv4addr'])
        if ipv4addrs_str:
            ipv4_list = [ip.strip() for ip in ipv4addrs_str.split(';') if ip.strip()]
            ipv4addrs = []
            for ip in ipv4_list:
                # Check if MAC address is provided with IP (format: ip|mac)
                if '|' in ip:
                    ip_parts = ip.split('|')
                    ipv4_obj = {'ipv4addr': ip_parts[0].strip()}
                    if len(ip_parts) > 1 and ip_parts[1].strip():
                        ipv4_obj['mac'] = ip_parts[1].strip().upper()
                else:
                    ipv4_obj = {'ipv4addr': ip}
                ipv4addrs.append(ipv4_obj)
            record['ipv4addrs'] = ipv4addrs

        # Process IPv6 addresses (can be semicolon-separated)
        ipv6addrs_str = self._get_field(row, ['ipv6addrs', 'ipv6', 'ipv6_addresses', 'ipv6addr'])
        if ipv6addrs_str:
            ipv6_list = [ip.strip() for ip in ipv6addrs_str.split(';') if ip.strip()]
            ipv6addrs = []
            for ip in ipv6_list:
                # Check if DUID is provided with IPv6 (format: ip|duid)
                if '|' in ip:
                    ip_parts = ip.split('|')
                    ipv6_obj = {'ipv6addr': ip_parts[0].strip()}
                    if len(ip_parts) > 1 and ip_parts[1].strip():
                        ipv6_obj['duid'] = ip_parts[1].strip()
                else:
                    ipv6_obj = {'ipv6addr': ip}
                ipv6addrs.append(ipv6_obj)
            record['ipv6addrs'] = ipv6addrs

        # Optional comment
        comment = self._get_field(row, ['comment', 'description'])
        if comment:
            record['comment'] = comment

        # TTL handling
        ttl = self._get_field(row, ['ttl'])
        if ttl:
            try:
                record['ttl'] = int(ttl)
            except ValueError:
                pass

        # Use TTL flag
        use_ttl = self._get_field(row, ['use_ttl'])
        if use_ttl:
            record['use_ttl'] = use_ttl.lower() in ['true', 'yes', '1']

        # Extensible attributes
        extattr_fields = ['Environment', 'Owner', 'Location', 'Department', 'Creator']
        for field in extattr_fields:
            value = self._get_field(row, [field, field.lower()])
            if value:
                extattrs[field] = value

        record['extattrs'] = extattrs if extattrs else {}
        
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

        # Collect extensible attributes first
        extattr_fields = ['Environment', 'Owner', 'Location', 'Department', 'Creator']
        for field in extattr_fields:
            value = self._get_field(row, [field, field.lower()])
            if value:
                extattrs[field] = value

        # Build record with proper field ordering
        if extattrs:
            record['extattrs'] = extattrs
        
        record['mail_exchanger'] = mail_exchanger
        record['name'] = name
        
        try:
            record['preference'] = int(preference)
        except ValueError:
            return None

        view = self._get_field(row, ['view', 'dns_view'])
        record['view'] = view if view else 'default'

        # TTL is optional and comes after view
        ttl = self._get_field(row, ['ttl'])
        if ttl:
            try:
                record['ttl'] = int(ttl)
            except ValueError:
                pass

        # Comment is not shown in your examples but keeping for compatibility
        comment = self._get_field(row, ['comment', 'description'])
        if comment:
            record['comment'] = comment

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

        # Extensible attributes
        extattr_fields = ['Environment', 'Owner', 'Location', 'Department', 'Creator']
        for field in extattr_fields:
            value = self._get_field(row, [field, field.lower()])
            if value:
                extattrs[field] = value

        record['extattrs'] = extattrs
        record['logic_filter_rules'] = []
        
        # Process members (semicolon-separated if multiple)
        members_str = self._get_field(row, ['members', 'member'])
        if members_str:
            member_list = [m.strip() for m in members_str.split(';') if m.strip()]
            record['members'] = [{'name': member} for member in member_list]
        else:
            record['members'] = []

        # Process DHCP options
        options = []
        dhcp_option_fields = {
            'domain-name-servers': 6,
            'domain-name': 15,
            'dhcp-lease-time': 51,
            'routers': 3,
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

        record['options'] = options if options else []
        record['use_logic_filter_rules'] = False
        
        # Process VLANs if needed (complex structure, usually empty)
        record['vlans'] = []

        return record

    def _process_ptr_record(self, row: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """Process PTR record"""
        record = {}
        extattrs = {}

        name = self._get_field(row, ['name', 'ptr_name', 'reverse_name'])
        ptrdname = self._get_field(row, ['ptrdname', 'hostname', 'target', 'fqdn'])

        if not all([name, ptrdname]):
            return None

        # Collect extensible attributes first
        extattr_fields = ['Environment', 'Owner', 'Location', 'Department', 'Creator']
        for field in extattr_fields:
            value = self._get_field(row, [field, field.lower()])
            if value:
                extattrs[field] = value

        # Build record with proper field ordering
        # If there are extattrs, they come first
        if extattrs:
            record['extattrs'] = extattrs
        else:
            record['extattrs'] = {}

        # IP addresses (always include both, even if empty)
        ipv4addr = self._get_field(row, ['ipv4addr', 'ipv4', 'ip', 'ip_address'])
        record['ipv4addr'] = ipv4addr if ipv4addr else ''

        ipv6addr = self._get_field(row, ['ipv6addr', 'ipv6', 'ipv6_address'])
        record['ipv6addr'] = ipv6addr if ipv6addr else ''

        # TTL (optional, comes before name/ptrdname in some cases)
        ttl = self._get_field(row, ['ttl'])
        if ttl:
            try:
                record['ttl'] = int(ttl)
            except ValueError:
                pass

        record['name'] = name
        record['ptrdname'] = ptrdname

        view = self._get_field(row, ['view', 'dns_view'])
        record['view'] = view if view else 'default'

        # Comment (optional, comes after view)
        comment = self._get_field(row, ['comment', 'description'])
        if comment:
            record['comment'] = comment

        return record


    def _process_network_range(self, row: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """Process network range record"""
        record = {}
        extattrs = {}

        network = self._get_field(row, ['network', 'cidr', 'subnet'])
        start_addr = self._get_field(row, ['start_addr', 'start', 'start_address'])
        end_addr = self._get_field(row, ['end_addr', 'end', 'end_address'])

        if not all([network, start_addr, end_addr]):
            return None

        # Build record with proper field ordering
        comment = self._get_field(row, ['comment', 'description'])
        if comment:
            record['comment'] = comment

        # Disable flag (default false)
        disable = self._get_field(row, ['disable', 'disabled'])
        record['disable'] = disable.lower() in ['true', 'yes', '1'] if disable else False

        record['end_addr'] = end_addr

        # Extensible attributes
        extattr_fields = ['Environment', 'Owner', 'Location', 'Department', 'Creator']
        for field in extattr_fields:
            value = self._get_field(row, [field, field.lower()])
            if value:
                extattrs[field] = value

        record['extattrs'] = extattrs if extattrs else {}

        # Optional name field
        name = self._get_field(row, ['name', 'range_name'])
        if name:
            record['name'] = name

        # Member configuration
        member_name = self._get_field(row, ['member', 'member_name'])
        member_ip = self._get_field(row, ['member_ip', 'member_ipv4addr'])
        
        if member_name and member_ip:
            record['member'] = {
                '_struct': 'dhcpmember',
                'ipv4addr': member_ip,
                'ipv6addr': None,
                'name': member_name
            }

        record['network'] = network
        
        network_view = self._get_field(row, ['network_view'])
        record['network_view'] = network_view if network_view else 'default'

        # Process DHCP options
        options = []
        dhcp_option_fields = {
            'dhcp-lease-time': 51,
            'domain-name-servers': 6,
            'domain-name': 15,
            'routers': 3,
            'broadcast-address': 28
        }

        for option_name, option_num in dhcp_option_fields.items():
            value = self._get_field(row, [option_name, option_name.replace('-', '_')])
            if value:
                # Check if option should be used (default false for ranges)
                use_option = self._get_field(row, [f'use_{option_name.replace("-", "_")}'])
                use_flag = use_option.lower() in ['true', 'yes', '1'] if use_option else False
                
                options.append({
                    'name': option_name,
                    'num': option_num,
                    'use_option': use_flag,
                    'value': value,
                    'vendor_class': 'DHCP'
                })

        record['options'] = options if options else [
            {
                'name': 'dhcp-lease-time',
                'num': 51,
                'use_option': False,
                'value': '43200',
                'vendor_class': 'DHCP'
            }
        ]

        # Server association type
        server_association_type = self._get_field(row, ['server_association_type', 'association_type'])
        if server_association_type:
            record['server_association_type'] = server_association_type.upper()
        elif member_name:
            record['server_association_type'] = 'MEMBER'
        else:
            record['server_association_type'] = 'NONE'

        record['start_addr'] = start_addr

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

        # Collect extensible attributes first
        extattr_fields = ['Environment', 'Owner', 'Location', 'Department', 'Creator']
        for field in extattr_fields:
            value = self._get_field(row, [field, field.lower()])
            if value:
                extattrs[field] = value

        # Build record with proper field ordering
        if extattrs:
            record['extattrs'] = extattrs
        else:
            record['extattrs'] = {}  # Always include extattrs based on your examples

        record['name'] = name
        
        try:
            record['port'] = int(port)
            record['priority'] = int(priority)
        except ValueError:
            return None

        record['target'] = target
        record['view'] = view
        
        try:
            record['weight'] = int(weight)
        except ValueError:
            return None

        # Comment comes last
        comment = self._get_field(row, ['comment', 'description'])
        if comment:
            record['comment'] = comment

        # TTL is optional (not shown in your examples but keeping for compatibility)
        ttl = self._get_field(row, ['ttl'])
        if ttl:
            try:
                record['ttl'] = int(ttl)
            except ValueError:
                pass

        return record

    def _process_txt_record(self, row: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """Process TXT record"""
        record = {}
        extattrs = {}

        name = self._get_field(row, ['name', 'hostname'])
        text = self._get_field(row, ['text', 'value', 'txt', 'data'])

        if not all([name, text]):
            return None

        # Collect extensible attributes first
        extattr_fields = ['Environment', 'Owner', 'Location', 'Department', 'Creator']
        for field in extattr_fields:
            value = self._get_field(row, [field, field.lower()])
            if value:
                extattrs[field] = value

        # Build record with flexible field ordering
        # Check if comment exists to determine field order
        comment = self._get_field(row, ['comment', 'description'])
        
        if comment and extattrs:
            # Comment first, then extattrs (like record 1)
            record['comment'] = comment
            record['extattrs'] = extattrs
        elif comment and not extattrs:
            # Comment with empty extattrs (like record 2)
            record['comment'] = comment
            record['extattrs'] = {}
        elif extattrs:
            # Extattrs only (like record 4)
            record['extattrs'] = extattrs
        else:
            # No comment or extattrs (like record 3 and 5)
            record['extattrs'] = {}

        record['name'] = name
        record['text'] = text
        
        view = self._get_field(row, ['view', 'dns_view'])
        record['view'] = view if view else 'default'

        # TTL is optional (not shown in most of your examples)
        ttl = self._get_field(row, ['ttl'])
        if ttl:
            try:
                record['ttl'] = int(ttl)
            except ValueError:
                pass

        return record

    def _process_zone(self, row: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """Process zone record"""
        record = {}
        extattrs = {}

        fqdn = self._get_field(row, ['fqdn', 'zone', 'domain'])
        if not fqdn:
            return None

        # Comment comes first if present
        comment = self._get_field(row, ['comment', 'description'])
        if comment:
            record['comment'] = comment

        # Collect extensible attributes
        extattr_fields = ['Environment', 'Owner', 'Location', 'Department', 'Creator']
        for field in extattr_fields:
            value = self._get_field(row, [field, field.lower()])
            if value:
                extattrs[field] = value

        # Add extattrs (always present in your examples)
        if extattrs:
            record['extattrs'] = extattrs
        else:
            record['extattrs'] = {}

        record['fqdn'] = fqdn

        # Always include these as empty arrays
        record['grid_primary'] = []
        record['grid_secondaries'] = []

        # View
        view = self._get_field(row, ['view', 'dns_view'])
        record['view'] = view if view else 'default'

        # Zone format - determine based on FQDN if not specified
        zone_format = self._get_field(row, ['zone_format', 'format', 'type'])
        if zone_format:
            record['zone_format'] = zone_format.upper()
        else:
            # Auto-detect zone format based on FQDN
            if 'in-addr.arpa' in fqdn.lower() or '/' in fqdn:
                record['zone_format'] = 'IPV4'
            elif 'ip6.arpa' in fqdn.lower() or '::' in fqdn:
                record['zone_format'] = 'IPV6'
            else:
                record['zone_format'] = 'FORWARD'

        # Optional NS group
        ns_group = self._get_field(row, ['ns_group', 'nameserver_group'])
        if ns_group:
            record['ns_group'] = ns_group

        return record

    def _process_alias_record(self, row: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """Process alias record"""
        record = {}
        
        name = self._get_field(row, ['name', 'alias_name', 'hostname'])
        target_name = self._get_field(row, ['target_name', 'target', 'destination'])
        target_type = self._get_field(row, ['target_type', 'type', 'record_type'])
        view = self._get_field(row, ['view', 'dns_view'])
        
        if not all([name, target_name, target_type, view]):
            return None
        
        # Set required fields
        record['disable'] = False
        record['extattrs'] = {}
        record['name'] = name
        record['target_name'] = target_name
        record['target_type'] = target_type.upper()  # Ensure uppercase (A, AAAA, MX, TXT)
        record['use_ttl'] = False
        record['view'] = view
        
        # Optional comment (placed between name and target_name in your JSON)
        comment = self._get_field(row, ['comment', 'description'])
        if comment:
            # Reorder to match your JSON structure
            record = {
                'disable': False,
                'extattrs': {},
                'name': name,
                'comment': comment,
                'target_name': target_name,
                'target_type': target_type.upper(),
                'use_ttl': False,
                'view': view
            }
        
        return record

    def _process_network_view(self, row: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """Process network view record"""
        record = {}
        extattrs = {}
        
        name = self._get_field(row, ['name', 'network_view', 'view_name'])
        if not name:
            return None
        
        # Extensible attributes
        extattr_fields = ['Environment', 'Owner', 'Location', 'Department', 'Creator']
        for field in extattr_fields:
            value = self._get_field(row, [field, field.lower()])
            if value:
                extattrs[field] = value
        
        # Always include extattrs (even if empty)
        record['extattrs'] = extattrs
        record['name'] = name
        
        # Optional comment
        comment = self._get_field(row, ['comment', 'description'])
        if comment:
            record['comment'] = comment
        
        return record

    def _process_zone_rp(self, row: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """Process Response Policy Zone (RPZ) record"""
        record = {}
        extattrs = {}
        
        fqdn = self._get_field(row, ['fqdn', 'zone', 'domain', 'display_domain'])
        view = self._get_field(row, ['view', 'dns_view'])
        
        if not all([fqdn, view]):
            return None
        
        # Boolean flags (defaults)
        record['disable'] = False
        record['display_domain'] = fqdn
        
        # Extensible attributes
        extattr_fields = ['Environment', 'Owner', 'Location', 'Department', 'Creator']
        for field in extattr_fields:
            value = self._get_field(row, [field, field.lower()])
            if value:
                extattrs[field] = value
        
        record['extattrs'] = extattrs if extattrs else {}
        
        # External primaries and secondaries (usually empty)
        record['external_primaries'] = []
        record['external_secondaries'] = []
        
        # FireEye integration (usually null)
        record['fireeye_rule_mapping'] = None
        
        record['fqdn'] = fqdn
        
        # Grid primary configuration
        grid_primary_name = self._get_field(row, ['grid_primary', 'primary_server'])
        if grid_primary_name:
            stealth = self._get_field(row, ['stealth'])
            record['grid_primary'] = [{
                'name': grid_primary_name,
                'stealth': stealth.lower() in ['true', 'yes', '1'] if stealth else False
            }]
        else:
            record['grid_primary'] = []
        
        record['grid_secondaries'] = []
        
        # RPZ specific settings
        record['locked'] = False
        record['log_rpz'] = True
        record['member_soa_mnames'] = []
        
        # Member SOA serials
        if grid_primary_name:
            serial = self._get_field(row, ['soa_serial_number', 'serial'])
            record['member_soa_serials'] = [{
                'grid_primary': grid_primary_name,
                'serial': int(serial) if serial else 1
            }]
        else:
            record['member_soa_serials'] = []
        
        # Network view
        network_view = self._get_field(row, ['network_view'])
        record['network_view'] = network_view if network_view else 'default'
        
        # NS group (optional)
        ns_group = self._get_field(row, ['ns_group', 'nameserver_group'])
        if ns_group:
            record['ns_group'] = ns_group
        
        record['parent'] = ''
        record['primary_type'] = 'Grid'
        
        # RPZ drop IP rule settings
        record['rpz_drop_ip_rule_enabled'] = False
        record['rpz_drop_ip_rule_min_prefix_length_ipv4'] = 29
        record['rpz_drop_ip_rule_min_prefix_length_ipv6'] = 112
        
        # RPZ last updated time (will be set by system)
        record['rpz_last_updated_time'] = 0
        
        # RPZ policy settings
        rpz_policy = self._get_field(row, ['rpz_policy', 'policy'])
        record['rpz_policy'] = rpz_policy.upper() if rpz_policy else 'GIVEN'
        
        # RPZ priority
        rpz_priority = self._get_field(row, ['rpz_priority', 'priority'])
        record['rpz_priority'] = int(rpz_priority) if rpz_priority else 0
        record['rpz_priority_end'] = 999
        
        # RPZ severity
        rpz_severity = self._get_field(row, ['rpz_severity', 'severity'])
        if rpz_severity:
            record['rpz_severity'] = rpz_severity.upper()
        else:
            record['rpz_severity'] = 'INFORMATIONAL'
        
        # RPZ type
        rpz_type = self._get_field(row, ['rpz_type', 'type'])
        record['rpz_type'] = rpz_type.upper() if rpz_type else 'LOCAL'
        
        # SOA settings
        soa_default_ttl = self._get_field(row, ['soa_default_ttl', 'default_ttl'])
        record['soa_default_ttl'] = int(soa_default_ttl) if soa_default_ttl else 7201
        
        soa_expire = self._get_field(row, ['soa_expire', 'expire'])
        record['soa_expire'] = int(soa_expire) if soa_expire else 2419201
        
        soa_negative_ttl = self._get_field(row, ['soa_negative_ttl', 'negative_ttl'])
        record['soa_negative_ttl'] = int(soa_negative_ttl) if soa_negative_ttl else 901
        
        soa_refresh = self._get_field(row, ['soa_refresh', 'refresh'])
        record['soa_refresh'] = int(soa_refresh) if soa_refresh else 10801
        
        soa_retry = self._get_field(row, ['soa_retry', 'retry'])
        record['soa_retry'] = int(soa_retry) if soa_retry else 3601
        
        soa_serial = self._get_field(row, ['soa_serial_number', 'serial'])
        record['soa_serial_number'] = int(soa_serial) if soa_serial else 1
        
        # Use flags
        record['use_external_primary'] = False
        record['use_grid_zone_timer'] = False
        record['use_log_rpz'] = False
        record['use_record_name_policy'] = False
        record['use_rpz_drop_ip_rule'] = False
        record['use_soa_email'] = False
        
        record['view'] = view
        
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
