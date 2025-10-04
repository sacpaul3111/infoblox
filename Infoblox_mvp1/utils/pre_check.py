#!/usr/bin/env python3
"""
Pre-check script for validating Infoblox records before deployment.
"""

import json
import re
import os
import subprocess
import sys
import yaml
from ipaddress import ip_address, IPv6Address
import requests
import urllib3

# Disable SSL warnings for self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Infoblox connection details
INFOBLOX_SERVER = "cabgridmgr.amfam.com"
WAPI_VERSION = "2.13.4"
HTTP_TIMEOUT = 999999
MAX_RESULTS = 1000
VALIDATE_CERTS = False

# Since credentials are encrypted with Ansible Vault, we need to get them from environment variables
# These should be set in the GitLab CI pipeline
INFOBLOX_USERNAME = os.environ.get("infoblox_username")
INFOBLOX_PASSWORD = os.environ.get("infoblox_password")

if not INFOBLOX_USERNAME or not INFOBLOX_PASSWORD:
    print("Error: Infoblox credentials not found in environment variables.")
    print("Please set the environment variables infoblox_username and infoblox_password.")
    print("These can be set in GitLab CI variables section or in the job directly.")
    sys.exit(1)

# API URL base
BASE_URL = f"https://{INFOBLOX_SERVER}/wapi/v{WAPI_VERSION}"

def authenticate():
    """Test authentication to Infoblox."""
    try:
        response = requests.get(
            f"{BASE_URL}/grid",
            auth=(INFOBLOX_USERNAME, INFOBLOX_PASSWORD),
            verify=VALIDATE_CERTS,
            timeout=HTTP_TIMEOUT
        )
        if response.status_code == 200:
            print("✓ Successfully authenticated to Infoblox.")
            return True
        else:
            print(f"✗ Authentication to Infoblox failed with status code: {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Connection to Infoblox failed: {str(e)}")
        return False

def read_json_file(file_path):
    """Read and parse a JSON file."""
    try:
        with open(file_path, 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        print(f"✗ File not found: {file_path}")
        return []
    except json.JSONDecodeError:
        print(f"✗ Invalid JSON in file: {file_path}")
        return []
    except Exception as e:
        print(f"✗ Error reading file {file_path}: {str(e)}")
        return []

def validate_ipv4_format(ip_str):
    """Validate if string is a proper IPv4 address."""
    ip_pattern = r'^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'
    return bool(re.match(ip_pattern, ip_str))

def validate_ipv6_format(ip_str):
    """Validate if string is a proper IPv6 address."""
    try:
        IPv6Address(ip_str)
        return True
    except ValueError:
        return False

def check_existing_a_record(name, view):
    """Check if an A record already exists in Infoblox."""
    try:
        response = requests.get(
            f"{BASE_URL}/record:a",
            params={"name": name, "view": view},
            auth=(INFOBLOX_USERNAME, INFOBLOX_PASSWORD),
            verify=VALIDATE_CERTS,
            timeout=HTTP_TIMEOUT
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"✗ Error checking A record {name}: {response.status_code}")
            return []
    except Exception as e:
        print(f"✗ Error checking A record {name}: {str(e)}")
        return []

def check_existing_aaaa_record(name, view):
    """Check if an AAAA record already exists in Infoblox."""
    try:
        response = requests.get(
            f"{BASE_URL}/record:aaaa",
            params={"name": name, "view": view},
            auth=(INFOBLOX_USERNAME, INFOBLOX_PASSWORD),
            verify=VALIDATE_CERTS,
            timeout=HTTP_TIMEOUT
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"✗ Error checking AAAA record {name}: {response.status_code}")
            return []
    except Exception as e:
        print(f"✗ Error checking AAAA record {name}: {str(e)}")
        return []

def check_ipv4_conflict(ipv4addr, view):
    """Check if an IPv4 is already used by another record in Infoblox."""
    try:
        response = requests.get(
            f"{BASE_URL}/record:a",
            params={"ipv4addr": ipv4addr, "view": view},
            auth=(INFOBLOX_USERNAME, INFOBLOX_PASSWORD),
            verify=VALIDATE_CERTS,
            timeout=HTTP_TIMEOUT
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"✗ Error checking IP {ipv4addr}: {response.status_code}")
            return []
    except Exception as e:
        print(f"✗ Error checking IP {ipv4addr}: {str(e)}")
        return []

def check_ipv6_conflict(ipv6addr, view):
    """Check if an IPv6 is already used by another record in Infoblox."""
    try:
        response = requests.get(
            f"{BASE_URL}/record:aaaa",
            params={"ipv6addr": ipv6addr, "view": view},
            auth=(INFOBLOX_USERNAME, INFOBLOX_PASSWORD),
            verify=VALIDATE_CERTS,
            timeout=HTTP_TIMEOUT
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"✗ Error checking IPv6 {ipv6addr}: {response.status_code}")
            return []
    except Exception as e:
        print(f"✗ Error checking IPv6 {ipv6addr}: {str(e)}")
        return []

def extract_parent_domain(domain):
    """Extract the parent domain from a FQDN."""
    parts = domain.split('.')
    if len(parts) > 1:
        return '.'.join(parts[1:])
    return domain

def check_zone_exists(domain, view):
    """Check if a DNS zone exists in Infoblox."""
    try:
        response = requests.get(
            f"{BASE_URL}/zone_auth",
            params={"fqdn": domain, "view": view},
            auth=(INFOBLOX_USERNAME, INFOBLOX_PASSWORD),
            verify=VALIDATE_CERTS,
            timeout=HTTP_TIMEOUT
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"✗ Error checking zone {domain}: {response.status_code}")
            return []
    except Exception as e:
        print(f"✗ Error checking zone {domain}: {str(e)}")
        return []

def perform_dns_lookup(domain):
    """Perform a DNS lookup for a domain."""
    try:
        result = subprocess.run(['nslookup', domain], 
                               capture_output=True, 
                               text=True, 
                               check=False)
        return {
            'rc': result.returncode,
            'stdout': result.stdout,
            'stderr': result.stderr
        }
    except Exception as e:
        print(f"✗ Error performing DNS lookup for {domain}: {str(e)}")
        return {'rc': -1, 'stdout': '', 'stderr': str(e)}

def validate_a_records():
    """Validate A records from JSON file.
    """
    print("\n--- A Record Validation ---")

    a_record_file = "../prod_changes/cabgridmgr.amfam.com/a_record.json"
    
    # Read A record data from JSON file
    try:
        with open(a_record_file, 'r') as file:
            a_records = json.load(file)
            
            # If the content is not a list, convert it to a list with one item
            if not isinstance(a_records, list):
                a_records = [a_records]
                
            print(f"Found {len(a_records)} A records to validate.")
    except Exception as e:
        print(f"Error reading file {a_record_file}: {str(e)}")
        return False
    
    # Now continue with validation since we have records to check
    validation_failed = False
    invalid_ips = []
    ip_conflicts = []
    failed_domains = []
    missing_required_fields = [] 
    
    # Check for required fields based on playbook
    for record in a_records:
        # Check required fields that the playbook uses
        required_fields = ["name", "ipv4addr", "view"]
        missing_fields = [field for field in required_fields if field not in record or record[field] is None]
        if missing_fields:
            missing_required_fields.append(f"{record.get('name', 'Unknown record')}: missing {', '.join(missing_fields)}")
            validation_failed = True
            continue
    
    # Display missing required fields
    for missing in missing_required_fields:
        print(f"ERROR: Missing required fields - {missing}")
    
    # Validate IP address format
    for record in a_records:
        if "ipv4addr" in record and record["ipv4addr"]:
            if not validate_ipv4_format(record.get('ipv4addr', '')):
                invalid_ips.append(f"{record['name']}: {record['ipv4addr']}")
                validation_failed = True
    
    # Display invalid IP addresses
    for invalid_ip in invalid_ips:
        print(f"ERROR: Invalid IP address format - {invalid_ip}")
    
    # Check for existing A records in Infoblox
    for record in a_records:
        if "name" in record and "view" in record:
            existing_records = check_existing_a_record(record['name'], record['view'])
            if existing_records:
                print(f"Record '{record['name']}' already exists in Infoblox with IP {existing_records[0]['ipv4addr']}")
    
    # Check for IP conflicts with other records
    for record in a_records:
        if "ipv4addr" in record and "view" in record:
            conflict_records = check_ipv4_conflict(record['ipv4addr'], record['view'])
            if conflict_records:
                # Filter out the current record from conflict list
                conflicts = [r for r in conflict_records if r['name'] != record['name']]
                if conflicts:
                    conflict_names = [r['name'] for r in conflicts]
                    ip_conflicts.append({'ip': record['ipv4addr'], 'conflicts_with': conflict_names})
    
    # Display IP conflicts
    for conflict in ip_conflicts:
        print(f"WARNING: IP address '{conflict['ip']}' is already used by: {', '.join(conflict['conflicts_with'])}")
    
    # Check for DNS zone existence in Infoblox
    parent_domains = {}
    for record in a_records:
        if "name" in record and "view" in record:
            domain = extract_parent_domain(record['name'])
            if domain not in parent_domains:
                parent_domains[domain] = record['view']
    
    for domain, view in parent_domains.items():
        zone_exists = check_zone_exists(domain, view)
        if not zone_exists:
            print(f"ERROR: Parent domain '{domain}' does not exist in Infoblox")
            validation_failed = True
            failed_domains.append(domain)
    
    # Perform DNS lookup for each A record
    for record in a_records:
        if "name" in record:
            dns_result = perform_dns_lookup(record['name'])
            if dns_result['rc'] == 0:
                print(f"WARNING: DNS record '{record['name']}' already exists in DNS with result: {dns_result['stdout']}")
    
    # Validate optional fields that playbook accepts
    for record in a_records:
        # Check comment field (optional but should be string if present)
        if "comment" in record and record["comment"] is not None:
            if not isinstance(record["comment"], str):
                print(f"WARNING: Comment for record '{record['name']}' should be a string")
        
        # Check extattrs field (optional but should be dict if present)
        if "extattrs" in record and record["extattrs"] is not None:
            if not isinstance(record["extattrs"], dict):
                print(f"WARNING: Extended attributes for record '{record['name']}' should be a dictionary")
    
    # Display validation summary
    print("\nA Record Validation Summary:")
    print(f"Total records checked: {len(a_records)}")
    print(f"Records with missing required fields: {len(missing_required_fields)}")
    print(f"Invalid IP formats: {len(invalid_ips)}")
    print(f"IP conflicts: {len(ip_conflicts)}")
    print(f"Missing parent domains: {len(failed_domains)}")
    if failed_domains:
        print(f"Failed records: {', '.join(failed_domains)}")
    
    return not validation_failed and not invalid_ips and not missing_required_fields

def validate_aaaa_records():
    """Validate AAAA records from JSON file.
    This function assumes the file exists and has content.
    """
    print("\n--- AAAA Record Validation ---")
    
    aaaa_record_file = "../prod_changes/cabgridmgr.amfam.com/aaaa_record.json"
    
    # Read AAAA record data from JSON file
    try:
        with open(aaaa_record_file, 'r') as file:
            aaaa_records = json.load(file)
            
            # If the content is not a list, convert it to a list with one item
            if not isinstance(aaaa_records, list):
                aaaa_records = [aaaa_records]
                
            print(f"Found {len(aaaa_records)} AAAA records to validate.")
    except Exception as e:
        print(f"Error reading file {aaaa_record_file}: {str(e)}")
        return False
    
    # Now continue with validation since we have records to check
    validation_failed = False
    invalid_ips = []
    ip_conflicts = []
    failed_domains = []
    missing_required_fields = []  # Added this for required field validation
    
    # Check for required fields based on playbook
    for record in aaaa_records:
        # Check required fields that the playbook uses
        required_fields = ["name", "ipv6addr", "view"]
        missing_fields = [field for field in required_fields if field not in record or record[field] is None]
        if missing_fields:
            missing_required_fields.append(f"{record.get('name', 'Unknown record')}: missing {', '.join(missing_fields)}")
            validation_failed = True
            continue
    
    # Display missing required fields
    for missing in missing_required_fields:
        print(f"ERROR: Missing required fields - {missing}")
    
    # Validate IPv6 address format
    for record in aaaa_records:
        if "ipv6addr" in record and record["ipv6addr"]:
            if not validate_ipv6_format(record.get('ipv6addr', '')):
                invalid_ips.append(f"{record['name']}: {record['ipv6addr']}")
                validation_failed = True
    
    # Display invalid IP addresses
    for invalid_ip in invalid_ips:
        print(f"ERROR: Invalid IPv6 address format - {invalid_ip}")
    
    # Check for existing AAAA records in Infoblox
    for record in aaaa_records:
        if "name" in record and "view" in record:
            existing_records = check_existing_aaaa_record(record['name'], record['view'])
            if existing_records:
                print(f"Record '{record['name']}' already exists in Infoblox with IPv6 {existing_records[0]['ipv6addr']}")
    
    # Check for IP conflicts with other records
    for record in aaaa_records:
        if "ipv6addr" in record and "view" in record:
            conflict_records = check_ipv6_conflict(record['ipv6addr'], record['view'])
            if conflict_records:
                # Filter out the current record from conflict list
                conflicts = [r for r in conflict_records if r['name'] != record['name']]
                if conflicts:
                    conflict_names = [r['name'] for r in conflicts]
                    ip_conflicts.append({'ip': record['ipv6addr'], 'conflicts_with': conflict_names})
    
    # Display IP conflicts
    for conflict in ip_conflicts:
        print(f"WARNING: IPv6 address '{conflict['ip']}' is already used by: {', '.join(conflict['conflicts_with'])}")
    
    # Check for DNS zone existence in Infoblox
    parent_domains = {}
    for record in aaaa_records:
        if "name" in record and "view" in record:
            domain = extract_parent_domain(record['name'])
            if domain not in parent_domains:
                parent_domains[domain] = record['view']
    
    for domain, view in parent_domains.items():
        zone_exists = check_zone_exists(domain, view)
        if not zone_exists:
            print(f"ERROR: Parent domain '{domain}' does not exist in Infoblox")
            validation_failed = True
            failed_domains.append(domain)
    
    # Perform DNS lookup for each AAAA record
    for record in aaaa_records:
        if "name" in record:
            dns_result = perform_dns_lookup(record['name'])
            if dns_result['rc'] == 0:
                print(f"WARNING: DNS record '{record['name']}' already exists in DNS with result: {dns_result['stdout']}")
    
    # Validate optional fields that playbook accepts
    for record in aaaa_records:
        # Check comment field (optional but should be string if present)
        if "comment" in record and record["comment"] is not None:
            if not isinstance(record["comment"], str):
                print(f"WARNING: Comment for record '{record['name']}' should be a string")
        
        # Check extattrs field (optional but should be dict if present)
        if "extattrs" in record and record["extattrs"] is not None:
            if not isinstance(record["extattrs"], dict):
                print(f"WARNING: Extended attributes for record '{record['name']}' should be a dictionary")
    
    # Display validation summary
    print("\nAAAA Record Validation Summary:")
    print(f"Total records checked: {len(aaaa_records)}")
    print(f"Records with missing required fields: {len(missing_required_fields)}")
    print(f"Invalid IPv6 formats: {len(invalid_ips)}")
    print(f"IPv6 conflicts: {len(ip_conflicts)}")
    print(f"Missing parent domains: {len(failed_domains)}")
    if failed_domains:
        print(f"Failed records: {', '.join(failed_domains)}")
    
    return not validation_failed and not invalid_ips and not missing_required_fields

def check_existing_alias_record(name, view):
    """Check if an Alias record already exists in Infoblox."""
    try:
        response = requests.get(
            f"{BASE_URL}/record:alias",
            params={"name": name, "view": view},
            auth=(INFOBLOX_USERNAME, INFOBLOX_PASSWORD),
            verify=VALIDATE_CERTS,
            timeout=HTTP_TIMEOUT
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"✗ Error checking Alias record {name}: {response.status_code}")
            return []
    except Exception as e:
        print(f"✗ Error checking Alias record {name}: {str(e)}")
        return []

def check_target_record_exists(target_name, target_type, view):
    """Check if the target record exists in Infoblox."""
    # Map of endpoint URLs for different record types
    record_type_endpoints = {
        "A": "record:a",
        "AAAA": "record:aaaa",
        "CNAME": "record:cname",
        "MX": "record:mx",
        "TXT": "record:txt",
        "PTR": "record:ptr",
        "SRV": "record:srv",
        "NS": "record:ns"
    }
    
    # If target type is not in our map, return False
    if target_type not in record_type_endpoints:
        print(f"✗ Unsupported target type: {target_type}")
        return False
    
    endpoint = record_type_endpoints[target_type]
    
    try:
        response = requests.get(
            f"{BASE_URL}/{endpoint}",
            params={"name": target_name, "view": view},
            auth=(INFOBLOX_USERNAME, INFOBLOX_PASSWORD),
            verify=VALIDATE_CERTS,
            timeout=HTTP_TIMEOUT
        )
        
        if response.status_code == 200:
            return len(response.json()) > 0
        else:
            print(f"✗ Error checking target record {target_name} of type {target_type}: {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Error checking target record {target_name} of type {target_type}: {str(e)}")
        return False

def validate_alias_records():
    """Validate Alias records from JSON file.
    This function assumes the file exists and has content.
    """
    print("\n--- Alias Record Validation ---")
    
    alias_record_file = "playbooks/add/cabgridmgr.amfam.com/alias_record.json"
    
    # Read Alias record data from JSON file
    try:
        with open(alias_record_file, 'r') as file:
            alias_records = json.load(file)
            
            # If the content is not a list, convert it to a list with one item
            if not isinstance(alias_records, list):
                alias_records = [alias_records]
                
            print(f"Found {len(alias_records)} Alias records to validate.")
    except Exception as e:
        print(f"Error reading file {alias_record_file}: {str(e)}")
        return False
    
    # Now continue with validation since we have records to check
    validation_failed = False
    missing_required_fields = []
    invalid_target_types = []
    missing_target_records = []
    failed_domains = []
    
    valid_target_types = ["A", "AAAA", "CNAME", "MX", "TXT", "PTR", "SRV", "NS"]
    
    # Check for required fields based on what the playbook uses
    for record in alias_records:
        # Check required fields - based on the playbook, it needs at minimum name and view
        # The playbook sends the entire record object, so we need to validate all fields
        required_fields = ["name", "view"]
        missing_fields = [field for field in required_fields if field not in record or record[field] is None]
        if missing_fields:
            missing_required_fields.append(f"{record.get('name', 'Unknown record')}: missing {', '.join(missing_fields)}")
            validation_failed = True
            continue
        
        # Check if alias record has target fields (target_name and target_type are typical for alias records)
        if "target_name" in record and "target_type" in record:
            # Validate target_type if present
            if record["target_type"] not in valid_target_types:
                invalid_target_types.append(f"{record['name']}: {record['target_type']}")
                validation_failed = True
        else:
            # Warn if typical alias fields are missing
            print(f"WARNING: Alias record '{record.get('name', 'Unknown')}' may be missing target_name or target_type fields")
    
    # Display missing required fields
    for missing in missing_required_fields:
        print(f"ERROR: Missing required fields - {missing}")
    
    # Display invalid target types
    for invalid in invalid_target_types:
        print(f"ERROR: Invalid target type - {invalid}")
    
    # Check for existing Alias records in Infoblox
    for record in alias_records:
        if "name" not in record or "view" not in record:
            continue  # Skip if required fields are missing
            
        existing_records = check_existing_alias_record(record['name'], record['view'])
        if existing_records:
            print(f"Record '{record['name']}' already exists in Infoblox")
            if "target_name" in existing_records[0]:
                print(f"  Current target: {existing_records[0]['target_name']}")
            if "target_type" in existing_records[0]:
                print(f"  Current target type: {existing_records[0]['target_type']}")
    
    # Check if target records exist (only if target_name and target_type are present)
    for record in alias_records:
        if all(key in record for key in ["target_name", "target_type", "view"]):
            if not check_target_record_exists(record['target_name'], record['target_type'], record['view']):
                missing_target_records.append(f"{record['name']}: Target {record['target_name']} of type {record['target_type']}")
                print(f"WARNING: Target record '{record['target_name']}' of type {record['target_type']} does not exist")
    
    # Check for DNS zone existence in Infoblox
    parent_domains = {}
    for record in alias_records:
        if "name" not in record or "view" not in record:
            continue  # Skip if required fields are missing
            
        domain = extract_parent_domain(record['name'])
        if domain not in parent_domains:
            parent_domains[domain] = record['view']
    
    for domain, view in parent_domains.items():
        zone_exists = check_zone_exists(domain, view)
        if not zone_exists:
            print(f"ERROR: Parent domain '{domain}' does not exist in Infoblox")
            validation_failed = True
            failed_domains.append(domain)
    
    # Perform DNS lookup for each Alias record
    for record in alias_records:
        if "name" not in record:
            continue  # Skip if required fields are missing
            
        dns_result = perform_dns_lookup(record['name'])
        if dns_result['rc'] == 0:
            print(f"WARNING: DNS record '{record['name']}' already exists in DNS with result: {dns_result['stdout']}")
    
    # Validate any additional fields that might be in the alias record
    for record in alias_records:
        # List all fields in the record for information
        all_fields = list(record.keys())
        print(f"INFO: Alias record '{record.get('name', 'Unknown')}' contains fields: {', '.join(all_fields)}")
        
        # Validate common optional fields
        if "comment" in record and record["comment"] is not None:
            if not isinstance(record["comment"], str):
                print(f"WARNING: Comment for record '{record['name']}' should be a string")
        
        if "extattrs" in record and record["extattrs"] is not None:
            if not isinstance(record["extattrs"], dict):
                print(f"WARNING: Extended attributes for record '{record['name']}' should be a dictionary")
    
    # Display validation summary
    print("\nAlias Record Validation Summary:")
    print(f"Total records checked: {len(alias_records)}")
    print(f"Records with missing required fields: {len(missing_required_fields)}")
    print(f"Records with invalid target types: {len(invalid_target_types)}")
    print(f"Records with missing target records: {len(missing_target_records)}")
    print(f"Missing parent domains: {len(failed_domains)}")
    if failed_domains:
        print(f"Failed records: {', '.join(failed_domains)}")
    
    return not validation_failed and not missing_required_fields and not invalid_target_types

def check_existing_cname_record(name, view):
    """Check if a CNAME record already exists in Infoblox."""
    try:
        response = requests.get(
            f"{BASE_URL}/record:cname",
            params={"name": name, "view": view},
            auth=(INFOBLOX_USERNAME, INFOBLOX_PASSWORD),
            verify=VALIDATE_CERTS,
            timeout=HTTP_TIMEOUT
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"✗ Error checking CNAME record {name}: {response.status_code}")
            return []
    except Exception as e:
        print(f"✗ Error checking CNAME record {name}: {str(e)}")
        return []

def check_canonical_exists(canonical, view):
    """Check if the canonical name exists in Infoblox."""
    try:
        # Try to resolve the canonical name - could be any record type
        # First check A records
        a_response = requests.get(
            f"{BASE_URL}/record:a",
            params={"name": canonical, "view": view},
            auth=(INFOBLOX_USERNAME, INFOBLOX_PASSWORD),
            verify=VALIDATE_CERTS,
            timeout=HTTP_TIMEOUT
        )
        
        if a_response.status_code == 200 and len(a_response.json()) > 0:
            return True
        
        # Check AAAA records
        aaaa_response = requests.get(
            f"{BASE_URL}/record:aaaa",
            params={"name": canonical, "view": view},
            auth=(INFOBLOX_USERNAME, INFOBLOX_PASSWORD),
            verify=VALIDATE_CERTS,
            timeout=HTTP_TIMEOUT
        )
        
        if aaaa_response.status_code == 200 and len(aaaa_response.json()) > 0:
            return True
        
        # Check CNAME records
        cname_response = requests.get(
            f"{BASE_URL}/record:cname",
            params={"name": canonical, "view": view},
            auth=(INFOBLOX_USERNAME, INFOBLOX_PASSWORD),
            verify=VALIDATE_CERTS,
            timeout=HTTP_TIMEOUT
        )
        
        if cname_response.status_code == 200 and len(cname_response.json()) > 0:
            return True
        
        return False
    except Exception as e:
        print(f"✗ Error checking canonical name {canonical}: {str(e)}")
        return False

def validate_cname_records():
    """Validate CNAME records from JSON file.
    """
    print("\n--- CNAME Record Validation ---")
    
    cname_record_file = "../prod_changes/cabgridmgr.amfam.com/cname_record.json"
    
    # Read CNAME record data from JSON file
    try:
        with open(cname_record_file, 'r') as file:
            cname_records = json.load(file)
            
            # If the content is not a list, convert it to a list with one item
            if not isinstance(cname_records, list):
                cname_records = [cname_records]
                
            print(f"Found {len(cname_records)} CNAME records to validate.")
    except Exception as e:
        print(f"Error reading file {cname_record_file}: {str(e)}")
        return False
    
    # Now continue with validation since we have records to check
    validation_failed = False
    missing_required_fields = []
    missing_canonical_records = []
    failed_domains = []
    existing_name_conflicts = []
    invalid_ttls = []
    existing_cname_conflicts = []  # Added to track existing CNAME records
    
    # Check for required fields based on playbook
    for record in cname_records:
        # Check required fields that the playbook uses
        required_fields = ["name", "canonical", "view"]
        missing_fields = [field for field in required_fields if field not in record or record[field] is None]
        if missing_fields:
            missing_required_fields.append(f"{record.get('name', 'Unknown record')}: missing {', '.join(missing_fields)}")
            validation_failed = True
            continue
    
    # Display missing required fields
    for missing in missing_required_fields:
        print(f"ERROR: Missing required fields - {missing}")
    
    # Validate TTL if specified
    for record in cname_records:
        if "ttl" in record and record["ttl"] is not None:
            try:
                ttl = int(record["ttl"])
                if ttl < 0 or ttl > 2147483647:
                    invalid_ttls.append(f"{record['name']}: TTL {ttl} (must be 0-2147483647)")
                    validation_failed = True
            except (ValueError, TypeError):
                invalid_ttls.append(f"{record['name']}: TTL '{record['ttl']}' is not a valid integer")
                validation_failed = True
    
    # Display invalid TTL values
    for invalid in invalid_ttls:
        print(f"ERROR: Invalid TTL value - {invalid}")
    
    # Check for existing CNAME records in Infoblox
    for record in cname_records:
        if "name" not in record or "view" not in record:
            continue  # Skip if required fields are missing
            
        existing_records = check_existing_cname_record(record['name'], record['view'])
        if existing_records:
            # This is an error condition since the playbook will fail
            existing_cname_conflicts.append(f"{record['name']} in view {record['view']}")
            print(f"ERROR: CNAME record '{record['name']}' already exists in Infoblox view '{record['view']}'")
            print(f"       Existing canonical: {existing_records[0].get('canonical', 'Unknown')}")
            print(f"       New canonical: {record.get('canonical', 'Unknown')}")
            validation_failed = True
    
    # Check if the name already exists as another record type
    for record in cname_records:
        if "name" not in record or "view" not in record:
            continue  # Skip if required fields are missing
        
        # Only check for other record types if CNAME doesn't already exist
        if f"{record['name']} in view {record['view']}" in existing_cname_conflicts:
            continue  # Already reported as CNAME conflict
        
        # Check A records
        a_records = check_existing_a_record(record['name'], record['view'])
        if a_records:
            existing_name_conflicts.append(f"{record['name']}: A record")
            print(f"ERROR: '{record['name']}' already exists as an A record. CNAME and other record types cannot coexist for the same name.")
            validation_failed = True
            continue
        
        # Check AAAA records
        aaaa_records = check_existing_aaaa_record(record['name'], record['view'])
        if aaaa_records:
            existing_name_conflicts.append(f"{record['name']}: AAAA record")
            print(f"ERROR: '{record['name']}' already exists as an AAAA record. CNAME and other record types cannot coexist for the same name.")
            validation_failed = True
            continue
    
    # Check if canonical name exists
    for record in cname_records:
        if "canonical" not in record or "view" not in record:
            continue
            
        if not check_canonical_exists(record['canonical'], record['view']):
            missing_canonical_records.append(f"{record['name']}: Canonical {record['canonical']}")
            print(f"WARNING: Canonical name '{record['canonical']}' does not resolve to any record")
    
    # Check for DNS zone existence in Infoblox
    parent_domains = {}
    for record in cname_records:
        if "name" not in record or "view" not in record:
            continue
            
        domain = extract_parent_domain(record['name'])
        if domain not in parent_domains:
            parent_domains[domain] = record['view']
    
    for domain, view in parent_domains.items():
        zone_exists = check_zone_exists(domain, view)
        if not zone_exists:
            print(f"ERROR: Parent domain '{domain}' does not exist in Infoblox")
            validation_failed = True
            failed_domains.append(domain)
    
    # Perform DNS lookup for each CNAME record
    for record in cname_records:
        if "name" not in record:
            continue
            
        dns_result = perform_dns_lookup(record['name'])
        if dns_result['rc'] == 0:
            print(f"WARNING: DNS record '{record['name']}' already exists in DNS with result: {dns_result['stdout']}")
    
    # Validate optional fields that playbook accepts
    for record in cname_records:
        # Check comment field (optional but should be string if present)
        if "comment" in record and record["comment"] is not None:
            if not isinstance(record["comment"], str):
                print(f"WARNING: Comment for record '{record['name']}' should be a string")
        
        # Check extattrs field (optional but should be dict if present)
        if "extattrs" in record and record["extattrs"] is not None:
            if not isinstance(record["extattrs"], dict):
                print(f"WARNING: Extended attributes for record '{record['name']}' should be a dictionary")
        
        # Check canonical name format
        if "canonical" in record and record["canonical"]:
            canonical = record["canonical"]
            if not canonical.endswith('.'):
                print(f"INFO: Canonical name '{canonical}' for record '{record['name']}' should be fully qualified (end with a dot)")
    
    # Display validation summary
    print("\nCNAME Record Validation Summary:")
    print(f"Total records checked: {len(cname_records)}")
    print(f"Records with missing required fields: {len(missing_required_fields)}")
    print(f"Records with existing CNAME conflicts: {len(existing_cname_conflicts)}")
    print(f"Records with name conflicts: {len(existing_name_conflicts)}")
    print(f"Records with non-resolving canonical names: {len(missing_canonical_records)}")
    print(f"Records with invalid TTL values: {len(invalid_ttls)}")
    print(f"Missing parent domains: {len(failed_domains)}")
    if failed_domains:
        print(f"Failed records: {', '.join(failed_domains)}")
    
    return not validation_failed and not missing_required_fields and not existing_name_conflicts and not invalid_ttls and not existing_cname_conflicts

def check_existing_fixed_address(ipv4addr, network_view):
    """Check if a fixed address already exists in Infoblox."""
    try:
        response = requests.get(
            f"{BASE_URL}/fixedaddress",
            params={"ipv4addr": ipv4addr, "network_view": network_view},
            auth=(INFOBLOX_USERNAME, INFOBLOX_PASSWORD),
            verify=VALIDATE_CERTS,
            timeout=HTTP_TIMEOUT
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"✗ Error checking fixed address {ipv4addr}: {response.status_code}")
            return []
    except Exception as e:
        print(f"✗ Error checking fixed address {ipv4addr}: {str(e)}")
        return []

def check_existing_mac_address(mac, network_view):
    """Check if a MAC address is already being used in a fixed address."""
    try:
        response = requests.get(
            f"{BASE_URL}/fixedaddress",
            params={"mac": mac, "network_view": network_view},
            auth=(INFOBLOX_USERNAME, INFOBLOX_PASSWORD),
            verify=VALIDATE_CERTS,
            timeout=HTTP_TIMEOUT
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"✗ Error checking MAC address {mac}: {response.status_code}")
            return []
    except Exception as e:
        print(f"✗ Error checking MAC address {mac}: {str(e)}")
        return []

def check_network_exists(network, network_view):
    """Check if a network exists in Infoblox."""
    try:
        response = requests.get(
            f"{BASE_URL}/network",
            params={"network": network, "network_view": network_view},
            auth=(INFOBLOX_USERNAME, INFOBLOX_PASSWORD),
            verify=VALIDATE_CERTS,
            timeout=HTTP_TIMEOUT
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"✗ Error checking network {network}: {response.status_code}")
            return []
    except Exception as e:
        print(f"✗ Error checking network {network}: {str(e)}")
        return []

def validate_mac_format(mac_str):
    """Validate if string is a proper MAC address."""
    mac_pattern = r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$'
    return bool(re.match(mac_pattern, mac_str)) or mac_str == "00:00:00:00:00:00"  # Allow all-zero MAC for RESERVED

def validate_fixed_addresses():
    """Validate fixed addresses from JSON file."""
    print("\n--- Fixed Address Validation ---")
    
    fixed_address_file = "../prod_changes/cabgridmgr.amfam.com/fixed_address.json"
    
    # Read fixed address data from JSON file
    try:
        with open(fixed_address_file, 'r') as file:
            fixed_addresses = json.load(file)
            
            # If the content is not a list, convert it to a list with one item
            if not isinstance(fixed_addresses, list):
                fixed_addresses = [fixed_addresses]
                
            print(f"Found {len(fixed_addresses)} fixed addresses to validate.")
    except Exception as e:
        print(f"Error reading file {fixed_address_file}: {str(e)}")
        return False
    
    # Define supported DHCP options based on playbook
    supported_dhcp_options = [
        "subnet-mask", "time-offset", "routers", "time-servers", "name-servers",
        "domain-name-servers", "log-servers", "cookie-servers", "lpr-servers",
        "impress-servers", "resource-location-servers", "boot-size", "merit-dump",
        "domain-name", "swap-server", "root-path", "extensions-path", "ip-forwarding",
        "non-local-source-routing", "policy-filter", "max-dgram-reassembly",
        "default-ip-ttl", "path-mtu-aging-timeout", "path-mtu-plateau-table",
        "interface-mtu", "all-subnets-local", "broadcast-address", "perform-mask-discovery",
        "mask-supplier", "router-discovery", "router-solicitation-address",
        "static-routes", "trailer-encapsulation", "arp-cache-timeout",
        "ieee802-3-encapsulation", "default-tcp-ttl", "tcp-keepalive-interval",
        "tcp-keepalive-garbage", "nis-domain", "nis-servers", "ntp-servers",
        "vendor-encapsulated-options", "netbios-name-servers", "netbios-dd-server",
        "netbios-node-type", "netbios-scope", "font-servers", "x-display-manager",
        "dhcp-option-overload", "dhcp-server-identifier", "dhcp-message",
        "dhcp-max-message-size", "vendor-class-identifier", "nwip-domain-name",
        "nisplus-domain-name", "nisplus-severs", "tftp-server-name", "boot-file-name",
        "mobile-ip-home-agent", "smtp-server", "pop-server", "nntp-server",
        "www.-server", "finger-server", "irc-server", "streettalk-server",
        "streettalk-directory-assistance-server", "user-class", "slp-directory-agent",
        "slp-service-scope", "nds-server", "nds-tree-name", "nds-context",
        "bcms-controller-names", "bcms-controller-address", "client-system",
        "client-ndi", "uuid-guid", "uap-servers", "geoconf-civic", "pcode", "tcode",
        "netinfo-server-address", "netinfo-server-tag", "v4-captive-portal+",
        "auto-config", "name-server-search", "subnet-selection", "domain-search",
        "vivco-suboptions", "vivso-suboptions", "pana-agent", "v4-lost",
        "capwap-ac-v4", "sip-ua-cs-domains", "rdnss-selection", "v4-portparams",
        "v4-captive-portal-old+", "option-6rd", "v4-access-domain", "dhcp-lease-time"
    ]
    
    # Now continue with validation since we have records to check
    validation_failed = False
    invalid_ips = []
    invalid_macs = []
    missing_networks = []
    ip_conflicts = []
    mac_conflicts = []
    missing_required_fields = []
    unsupported_dhcp_options = []
    mac_address_records = []
    
    # Separate MAC_ADDRESS type records as playbook only processes these
    for record in fixed_addresses:
        if record.get("match_client") == "MAC_ADDRESS":
            mac_address_records.append(record)
    
    print(f"Found {len(mac_address_records)} MAC_ADDRESS type fixed addresses to validate.")
    
    # Check for required fields based on playbook
    for record in mac_address_records:
        # Check required fields for MAC_ADDRESS type based on playbook
        required_fields = ["ipv4addr", "mac", "network"]
        missing_fields = [field for field in required_fields if field not in record or record[field] is None]
        if missing_fields:
            missing_required_fields.append(f"{record.get('name', record.get('ipv4addr', 'Unknown'))}: missing {', '.join(missing_fields)}")
            validation_failed = True
            continue
        
        # The playbook uses name with default('default_name')
        if "name" not in record:
            print(f"INFO: Fixed address {record['ipv4addr']} has no name, will use 'default_name'")
    
    # Display missing required fields
    for missing in missing_required_fields:
        print(f"ERROR: Missing required fields - {missing}")
    
    # Validate IP address format
    for record in mac_address_records:
        if "ipv4addr" not in record:
            continue
        if not validate_ipv4_format(record["ipv4addr"]):
            invalid_ips.append(f"{record.get('name', record.get('ipv4addr', 'Unknown'))}: {record['ipv4addr']}")
            validation_failed = True
    
    # Display invalid IP addresses
    for invalid_ip in invalid_ips:
        print(f"ERROR: Invalid IP address format - {invalid_ip}")
    
    # Validate MAC address format for MAC_ADDRESS type
    for record in mac_address_records:
        if "mac" not in record:
            continue
        if not validate_mac_format(record["mac"]):
            invalid_macs.append(f"{record.get('name', record.get('ipv4addr', 'Unknown'))}: {record['mac']}")
            validation_failed = True
    
    # Display invalid MAC addresses
    for invalid_mac in invalid_macs:
        print(f"ERROR: Invalid MAC address format - {invalid_mac}")
    
    # Validate DHCP options if present
    for record in mac_address_records:
        if "options" in record and record["options"]:
            if not isinstance(record["options"], list):
                print(f"ERROR: DHCP options for {record.get('name', record['ipv4addr'])} should be a list")
                validation_failed = True
                continue
            
            for option in record["options"]:
                if not isinstance(option, dict):
                    print(f"ERROR: DHCP option in {record.get('name', record['ipv4addr'])} should be a dictionary")
                    validation_failed = True
                    continue
                
                if "name" not in option:
                    print(f"ERROR: DHCP option in {record.get('name', record['ipv4addr'])} missing 'name' field")
                    validation_failed = True
                    continue
                
                # Check if option is in supported list
                if option["name"] not in supported_dhcp_options:
                    unsupported_dhcp_options.append(f"{record.get('name', record['ipv4addr'])}: {option['name']}")
                    print(f"WARNING: DHCP option '{option['name']}' for {record.get('name', record['ipv4addr'])} is not in supported options list")
    
    # Check for existing fixed addresses
    for record in mac_address_records:
        if "ipv4addr" not in record:
            continue
            
        network_view = record.get("network_view", "default")  # Playbook uses default('default')
        existing_records = check_existing_fixed_address(record["ipv4addr"], network_view)
        if existing_records:
            current_mac = record.get("mac", "N/A")
            existing_mac = existing_records[0].get("mac", "N/A")
            print(f"Fixed address '{record['ipv4addr']}' already exists in Infoblox with MAC {existing_mac}")
            
            # If the existing record has a different MAC, flag it as a conflict
            if current_mac != "N/A" and existing_mac != "N/A" and current_mac != existing_mac:
                ip_conflicts.append(f"{record['ipv4addr']}: existing MAC {existing_mac}, new MAC {current_mac}")
                print(f"WARNING: IP address {record['ipv4addr']} is already assigned to MAC {existing_mac}")
    
    # Check for MAC address conflicts
    for record in mac_address_records:
        if "mac" not in record:
            continue
            
        network_view = record.get("network_view", "default")
        existing_records = check_existing_mac_address(record["mac"], network_view)
        conflicts = [r for r in existing_records if r["ipv4addr"] != record["ipv4addr"]]
        
        if conflicts:
            conflict_ips = [r["ipv4addr"] for r in conflicts]
            mac_conflicts.append(f"{record['mac']}: conflicts with {', '.join(conflict_ips)}")
            print(f"WARNING: MAC address {record['mac']} is already used by: {', '.join(conflict_ips)}")
    
    # Check for network existence
    for record in mac_address_records:
        if "network" not in record:
            continue
            
        network_view = record.get("network_view", "default")
        if not check_network_exists(record["network"], network_view):
            missing_networks.append(f"{record.get('name', record.get('ipv4addr', 'Unknown'))}: Network {record['network']}")
            print(f"ERROR: Network {record['network']} does not exist in view {network_view}")
            validation_failed = True
    
    # Check if IP is within the specified network
    for record in mac_address_records:
        if "ipv4addr" not in record or "network" not in record:
            continue
            
        try:
            # Extract network and prefix length
            network_parts = record["network"].split('/')
            if len(network_parts) != 2:
                print(f"ERROR: Invalid network format - {record['network']}")
                validation_failed = True
                continue
                
            network_ip = network_parts[0]
            prefix_length = int(network_parts[1])
            
            # Convert to integer representations for comparison
            ip_int = int.from_bytes(ip_address(record["ipv4addr"]).packed, byteorder='big')
            network_int = int.from_bytes(ip_address(network_ip).packed, byteorder='big')
            
            # Calculate subnet mask
            mask = (2 ** 32 - 1) - (2 ** (32 - prefix_length) - 1)
            
            # Check if IP is within network
            if (ip_int & mask) != (network_int & mask):
                print(f"ERROR: IP {record['ipv4addr']} is not within network {record['network']}")
                validation_failed = True
        except Exception as e:
            print(f"ERROR: Could not validate if IP {record['ipv4addr']} is within network {record['network']}: {str(e)}")
            validation_failed = True
    
    # Display validation summary
    print("\nFixed Address Validation Summary:")
    print(f"Total records checked: {len(fixed_addresses)}")
    print(f"MAC_ADDRESS type records: {len(mac_address_records)}")
    print(f"Records with missing required fields: {len(missing_required_fields)}")
    print(f"Invalid IP formats: {len(invalid_ips)}")
    print(f"Invalid MAC formats: {len(invalid_macs)}")
    print(f"IP conflicts: {len(ip_conflicts)}")
    print(f"MAC conflicts: {len(mac_conflicts)}")
    print(f"Missing networks: {len(missing_networks)}")
    print(f"Records with unsupported DHCP options: {len(set([opt.split(':')[0] for opt in unsupported_dhcp_options]))}")
    
    if len(fixed_addresses) > len(mac_address_records):
        print(f"INFO: {len(fixed_addresses) - len(mac_address_records)} non-MAC_ADDRESS type records will be skipped by the playbook")
    
    return not validation_failed

def check_existing_host_record(name, view):
    """Check if a host record already exists in Infoblox."""
    try:
        response = requests.get(
            f"{BASE_URL}/record:host",
            params={"name": name, "view": view},
            auth=(INFOBLOX_USERNAME, INFOBLOX_PASSWORD),
            verify=VALIDATE_CERTS,
            timeout=HTTP_TIMEOUT
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"✗ Error checking host record {name}: {response.status_code}")
            return []
    except Exception as e:
        print(f"✗ Error checking host record {name}: {str(e)}")
        return []

def check_ip_conflict(ip, is_ipv6, view):
    """Check if an IP is already used by another record in Infoblox."""
    try:
        # Check for conflicts in host records
        host_params = {"view": view}
        if is_ipv6:
            endpoint = "ipv6addr"
            host_params["ipv6addr"] = ip
        else:
            endpoint = "ipv4addr"
            host_params["ipv4addr"] = ip
        
        response = requests.get(
            f"{BASE_URL}/record:host",
            params=host_params,
            auth=(INFOBLOX_USERNAME, INFOBLOX_PASSWORD),
            verify=VALIDATE_CERTS,
            timeout=HTTP_TIMEOUT
        )
        
        if response.status_code == 200:
            host_results = response.json()
        else:
            print(f"✗ Error checking IP {ip} in hosts: {response.status_code}")
            host_results = []
        
        # Check for conflicts in A/AAAA records
        record_params = {"view": view}
        if is_ipv6:
            record_type = "record:aaaa"
            record_params["ipv6addr"] = ip
        else:
            record_type = "record:a"
            record_params["ipv4addr"] = ip
        
        record_response = requests.get(
            f"{BASE_URL}/{record_type}",
            params=record_params,
            auth=(INFOBLOX_USERNAME, INFOBLOX_PASSWORD),
            verify=VALIDATE_CERTS,
            timeout=HTTP_TIMEOUT
        )
        
        if record_response.status_code == 200:
            record_results = record_response.json()
        else:
            print(f"✗ Error checking IP {ip} in {record_type}: {record_response.status_code}")
            record_results = []
        
        return host_results + record_results
    except Exception as e:
        print(f"✗ Error checking IP {ip}: {str(e)}")
        return []

def check_alias_conflicts(aliases, view):
    """Check if aliases conflict with existing records."""
    conflicts = []
    for alias in aliases:
        # Check for existing A records
        a_records = check_existing_a_record(alias, view)
        if a_records:
            conflicts.append(f"{alias}: A record")
            continue
        
        # Check for existing AAAA records
        aaaa_records = check_existing_aaaa_record(alias, view)
        if aaaa_records:
            conflicts.append(f"{alias}: AAAA record")
            continue
        
        # Check for existing CNAME records
        cname_records = check_existing_cname_record(alias, view)
        if cname_records:
            conflicts.append(f"{alias}: CNAME record")
            continue
        
        # Check for existing host records
        host_records = check_existing_host_record(alias, view)
        if host_records:
            conflicts.append(f"{alias}: Host record")
            continue
    
    return conflicts

def validate_host_records():
    """Validate host records from JSON file."""
    print("\n--- Host Record Validation ---")
    
    host_record_file = "../prod_changes/cabgridmgr.amfam.com/host_record.json"
    
    # Read host record data from JSON file
    try:
        with open(host_record_file, 'r') as file:
            host_records = json.load(file)
            
            # If the content is not a list, convert it to a list with one item
            if not isinstance(host_records, list):
                host_records = [host_records]
            
            # Filter out any null entries
            host_records = [record for record in host_records if record is not None]
                
            print(f"Found {len(host_records)} host records to validate.")
    except Exception as e:
        print(f"Error reading file {host_record_file}: {str(e)}")
        return False
    
    # Now continue with validation since we have records to check
    validation_failed = False
    missing_required_fields = []
    invalid_ipv4s = []
    invalid_ipv6s = []
    invalid_macs = []
    ip_conflicts = []
    alias_conflicts = []
    failed_domains = []
    
    # Check for required fields
    for record in host_records:
        # Check required fields
        if not all(key in record for key in ["name", "view"]):
            missing_fields = [field for field in ["name", "view"] if field not in record]
            missing_required_fields.append(f"{record.get('name', 'Unknown record')}: missing {', '.join(missing_fields)}")
            validation_failed = True
            continue
        
        # Check if record has at least one IP address (IPv4 or IPv6)
        if not ("ipv4addrs" in record or "ipv6addrs" in record):
            missing_required_fields.append(f"{record['name']}: missing IP address (either ipv4addrs or ipv6addrs)")
            validation_failed = True
            continue
        
        # Check IPv4 addresses if present
        if "ipv4addrs" in record and record["ipv4addrs"]:
            for ipv4_item in record["ipv4addrs"]:
                if "ipv4addr" not in ipv4_item:
                    missing_required_fields.append(f"{record['name']}: ipv4addrs item missing ipv4addr field")
                    validation_failed = True
                    continue
                
                # Validate IPv4 format
                if not validate_ipv4_format(ipv4_item["ipv4addr"]):
                    invalid_ipv4s.append(f"{record['name']}: {ipv4_item['ipv4addr']}")
                    validation_failed = True
                
                # Validate MAC address if configure_for_dhcp is true
                if ipv4_item.get("configure_for_dhcp", False) and "mac" in ipv4_item:
                    if not validate_mac_format(ipv4_item["mac"]):
                        invalid_macs.append(f"{record['name']}: {ipv4_item['mac']}")
                        validation_failed = True
        
        # Check IPv6 addresses if present
        if "ipv6addrs" in record and record["ipv6addrs"]:
            for ipv6_item in record["ipv6addrs"]:
                if "ipv6addr" not in ipv6_item:
                    missing_required_fields.append(f"{record['name']}: ipv6addrs item missing ipv6addr field")
                    validation_failed = True
                    continue
                
                # Validate IPv6 format
                if not validate_ipv6_format(ipv6_item["ipv6addr"]):
                    invalid_ipv6s.append(f"{record['name']}: {ipv6_item['ipv6addr']}")
                    validation_failed = True
    
    # Display missing required fields
    for missing in missing_required_fields:
        print(f"ERROR: Missing required fields - {missing}")
    
    # Display invalid IP addresses
    for invalid_ip in invalid_ipv4s:
        print(f"ERROR: Invalid IPv4 address format - {invalid_ip}")
    
    for invalid_ip in invalid_ipv6s:
        print(f"ERROR: Invalid IPv6 address format - {invalid_ip}")
    
    # Display invalid MAC addresses
    for invalid_mac in invalid_macs:
        print(f"ERROR: Invalid MAC address format - {invalid_mac}")
    
    # Check for existing host records
    for record in host_records:
        if "name" not in record or "view" not in record:
            continue
            
        existing_records = check_existing_host_record(record["name"], record["view"])
        if existing_records:
            print(f"Record '{record['name']}' already exists in Infoblox")
    
    # Check for IP conflicts
    for record in host_records:
        if "view" not in record:
            continue
            
        # Check IPv4 addresses
        if "ipv4addrs" in record and record["ipv4addrs"]:
            for ipv4_item in record["ipv4addrs"]:
                if "ipv4addr" not in ipv4_item:
                    continue
                    
                conflict_records = check_ip_conflict(ipv4_item["ipv4addr"], False, record["view"])
                # Filter out the current record from conflict list
                conflicts = [r for r in conflict_records if r.get("name") != record.get("name")]
                
                if conflicts:
                    conflict_names = [r.get("name", "Unknown") for r in conflicts]
                    ip_conflicts.append(f"{record['name']}: {ipv4_item['ipv4addr']} conflicts with {', '.join(conflict_names)}")
                    print(f"WARNING: IP address {ipv4_item['ipv4addr']} is already used by: {', '.join(conflict_names)}")
        
        # Check IPv6 addresses
        if "ipv6addrs" in record and record["ipv6addrs"]:
            for ipv6_item in record["ipv6addrs"]:
                if "ipv6addr" not in ipv6_item:
                    continue
                    
                conflict_records = check_ip_conflict(ipv6_item["ipv6addr"], True, record["view"])
                # Filter out the current record from conflict list
                conflicts = [r for r in conflict_records if r.get("name") != record.get("name")]
                
                if conflicts:
                    conflict_names = [r.get("name", "Unknown") for r in conflicts]
                    ip_conflicts.append(f"{record['name']}: {ipv6_item['ipv6addr']} conflicts with {', '.join(conflict_names)}")
                    print(f"WARNING: IPv6 address {ipv6_item['ipv6addr']} is already used by: {', '.join(conflict_names)}")
    
    # Check for alias conflicts
    for record in host_records:
        if "aliases" in record and record["aliases"] and "view" in record:
            conflicts = check_alias_conflicts(record["aliases"], record["view"])
            if conflicts:
                for conflict in conflicts:
                    alias_conflicts.append(f"{record['name']}: {conflict}")
                    print(f"ERROR: Alias conflict - {conflict}")
                validation_failed = True
    
    # Check for DNS zone existence in Infoblox
    parent_domains = {}
    for record in host_records:
        if "name" not in record or "view" not in record:
            continue
            
        domain = extract_parent_domain(record["name"])
        if domain not in parent_domains:
            parent_domains[domain] = record["view"]
    
    for domain, view in parent_domains.items():
        zone_exists = check_zone_exists(domain, view)
        if not zone_exists:
            print(f"ERROR: Parent domain '{domain}' does not exist in Infoblox")
            validation_failed = True
            failed_domains.append(domain)
    
    # Validate nextserver if specified
    for record in host_records:
        if record.get("use_nextserver", False) and "nextserver" in record:
            # Check if nextserver resolves to a valid IP
            dns_result = perform_dns_lookup(record["nextserver"])
            if dns_result["rc"] != 0:
                print(f"WARNING: Next server '{record['nextserver']}' does not resolve in DNS")
    
    # Perform DNS lookup for each host record
    for record in host_records:
        if "name" not in record:
            continue
            
        dns_result = perform_dns_lookup(record["name"])
        if dns_result["rc"] == 0:
            print(f"WARNING: DNS record '{record['name']}' already exists in DNS with result: {dns_result['stdout']}")
    
    # Display validation summary
    print("\nHost Record Validation Summary:")
    print(f"Total records checked: {len(host_records)}")
    print(f"Records with missing required fields: {len(missing_required_fields)}")
    print(f"Invalid IPv4 formats: {len(invalid_ipv4s)}")
    print(f"Invalid IPv6 formats: {len(invalid_ipv6s)}")
    print(f"Invalid MAC formats: {len(invalid_macs)}")
    print(f"IP conflicts: {len(ip_conflicts)}")
    print(f"Alias conflicts: {len(alias_conflicts)}")
    print(f"Missing parent domains: {len(failed_domains)}")
    if failed_domains:
        print(f"Failed domains: {', '.join(failed_domains)}")
    
    return not validation_failed

def check_existing_mx_record(name, view):
    """Check if an MX record already exists in Infoblox."""
    try:
        response = requests.get(
            f"{BASE_URL}/record:mx",
            params={"name": name, "view": view},
            auth=(INFOBLOX_USERNAME, INFOBLOX_PASSWORD),
            verify=VALIDATE_CERTS,
            timeout=HTTP_TIMEOUT
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"✗ Error checking MX record {name}: {response.status_code}")
            return []
    except Exception as e:
        print(f"✗ Error checking MX record {name}: {str(e)}")
        return []

def check_mail_exchanger_exists(mail_exchanger, view):
    """Check if the mail exchanger exists in Infoblox."""
    try:
        # Check A records
        a_response = requests.get(
            f"{BASE_URL}/record:a",
            params={"name": mail_exchanger, "view": view},
            auth=(INFOBLOX_USERNAME, INFOBLOX_PASSWORD),
            verify=VALIDATE_CERTS,
            timeout=HTTP_TIMEOUT
        )
        
        if a_response.status_code == 200 and len(a_response.json()) > 0:
            return True
        
        # Check AAAA records
        aaaa_response = requests.get(
            f"{BASE_URL}/record:aaaa",
            params={"name": mail_exchanger, "view": view},
            auth=(INFOBLOX_USERNAME, INFOBLOX_PASSWORD),
            verify=VALIDATE_CERTS,
            timeout=HTTP_TIMEOUT
        )
        
        if aaaa_response.status_code == 200 and len(aaaa_response.json()) > 0:
            return True
        
        # Check CNAME records
        cname_response = requests.get(
            f"{BASE_URL}/record:cname",
            params={"name": mail_exchanger, "view": view},
            auth=(INFOBLOX_USERNAME, INFOBLOX_PASSWORD),
            verify=VALIDATE_CERTS,
            timeout=HTTP_TIMEOUT
        )
        
        if cname_response.status_code == 200 and len(cname_response.json()) > 0:
            return True
        
        # Check host records
        host_response = requests.get(
            f"{BASE_URL}/record:host",
            params={"name": mail_exchanger, "view": view},
            auth=(INFOBLOX_USERNAME, INFOBLOX_PASSWORD),
            verify=VALIDATE_CERTS,
            timeout=HTTP_TIMEOUT
        )
        
        if host_response.status_code == 200 and len(host_response.json()) > 0:
            return True
        
        return False
    except Exception as e:
        print(f"✗ Error checking mail exchanger {mail_exchanger}: {str(e)}")
        return False

def validate_mx_records():
    """Validate MX records from JSON file."""
    print("\n--- MX Record Validation ---")
    
    mx_record_file = "../prod_changes/cabgridmgr.amfam.com/mx_record.json"
    
    # Read MX record data from JSON file
    try:
        with open(mx_record_file, 'r') as file:
            mx_records = json.load(file)
            
            # If the content is not a list, convert it to a list with one item
            if not isinstance(mx_records, list):
                mx_records = [mx_records]
                
            print(f"Found {len(mx_records)} MX records to validate.")
    except Exception as e:
        print(f"Error reading file {mx_record_file}: {str(e)}")
        return False
    
    # Now continue with validation since we have records to check
    validation_failed = False
    missing_required_fields = []
    invalid_preferences = []
    missing_mail_exchangers = []
    failed_domains = []
    invalid_ttls = []
    
    # Check for required fields and validate preference values
    for record in mx_records:
        # Check required fields
        if not all(key in record for key in ["name", "mail_exchanger", "preference", "view"]):
            missing_fields = [field for field in ["name", "mail_exchanger", "preference", "view"] if field not in record]
            missing_required_fields.append(f"{record.get('name', 'Unknown record')}: missing {', '.join(missing_fields)}")
            validation_failed = True
            continue
        
        # Validate preference value
        try:
            preference = int(record["preference"])
            if preference < 0 or preference > 65535:
                invalid_preferences.append(f"{record['name']}: preference {preference} (must be 0-65535)")
                validation_failed = True
        except (ValueError, TypeError):
            invalid_preferences.append(f"{record['name']}: preference '{record['preference']}' is not a valid integer")
            validation_failed = True
        
        # Validate TTL if specified
        if "ttl" in record and record["ttl"] is not None:
            try:
                ttl = int(record["ttl"])
                if ttl < 0 or ttl > 2147483647:  # Max TTL value
                    invalid_ttls.append(f"{record['name']}: TTL {ttl} (must be 0-2147483647)")
                    validation_failed = True
            except (ValueError, TypeError):
                invalid_ttls.append(f"{record['name']}: TTL '{record['ttl']}' is not a valid integer")
                validation_failed = True
    
    # Display missing required fields
    for missing in missing_required_fields:
        print(f"ERROR: Missing required fields - {missing}")
    
    # Display invalid preference values
    for invalid in invalid_preferences:
        print(f"ERROR: Invalid preference value - {invalid}")
    
    # Display invalid TTL values
    for invalid in invalid_ttls:
        print(f"ERROR: Invalid TTL value - {invalid}")
    
    # Check for existing MX records in Infoblox
    for record in mx_records:
        if "name" not in record or "view" not in record:
            continue 
            
        existing_records = check_existing_mx_record(record['name'], record['view'])
        if existing_records:
            # Check if an MX record with the same preference already exists
            existing_prefs = [(r['mail_exchanger'], r['preference']) for r in existing_records]
            new_pref = record.get('preference')
            new_mx = record.get('mail_exchanger')
            
            # Check for exact match
            if (new_mx, new_pref) in existing_prefs:
                print(f"Record '{record['name']}' already exists in Infoblox with mail exchanger {new_mx} and preference {new_pref}")
            else:
                # Check for conflicts (same name, different preference/mail exchanger)
                print(f"MX record '{record['name']}' already exists in Infoblox with different configuration:")
                for mx, pref in existing_prefs:
                    print(f"  Existing: {mx} (preference: {pref})")
                print(f"  New: {new_mx} (preference: {new_pref})")
    
    # Check if mail exchangers exist
    for record in mx_records:
        if not all(key in record for key in ["mail_exchanger", "view"]):
            continue 
            
        if not check_mail_exchanger_exists(record['mail_exchanger'], record['view']):
            missing_mail_exchangers.append(f"{record['name']}: Mail exchanger {record['mail_exchanger']}")
            print(f"WARNING: Mail exchanger '{record['mail_exchanger']}' does not resolve to any record")
    
    # Check for DNS zone existence in Infoblox
    parent_domains = {}
    for record in mx_records:
        if "name" not in record or "view" not in record:
            continue 
            
        domain = extract_parent_domain(record['name'])
        if domain not in parent_domains:
            parent_domains[domain] = record['view']
    
    for domain, view in parent_domains.items():
        zone_exists = check_zone_exists(domain, view)
        if not zone_exists:
            print(f"ERROR: Parent domain '{domain}' does not exist in Infoblox")
            validation_failed = True
            failed_domains.append(domain)
    
    # Perform DNS lookup for each MX record
    for record in mx_records:
        if "name" not in record:
            continue
            
        dns_result = perform_dns_lookup(record['name'])
        if dns_result['rc'] == 0:
            print(f"WARNING: DNS record '{record['name']}' already exists in DNS with result: {dns_result['stdout']}")
    
    # Validate mail exchanger naming conventions
    for record in mx_records:
        if "mail_exchanger" not in record:
            continue
            
        mail_exchanger = record['mail_exchanger']
        
        # Check if mail exchanger ends with a dot 
        if not mail_exchanger.endswith('.'):
            print(f"INFO: Mail exchanger '{mail_exchanger}' for record '{record['name']}' should be fully qualified (end with a dot)")
        
        # Check for common naming patterns
        if not any(pattern in mail_exchanger.lower() for pattern in ['mail', 'mx', 'smtp']):
            print(f"INFO: Mail exchanger '{mail_exchanger}' for record '{record['name']}' does not follow common naming conventions")
    
    # Check for duplicate preferences within the same domain
    domain_preferences = {}
    for record in mx_records:
        if not all(key in record for key in ["name", "preference"]):
            continue
            
        domain = record['name']
        preference = record['preference']
        
        if domain not in domain_preferences:
            domain_preferences[domain] = []
        domain_preferences[domain].append((preference, record['mail_exchanger']))
    
    for domain, prefs in domain_preferences.items():
        pref_values = [p[0] for p in prefs]
        if len(pref_values) != len(set(pref_values)):
            duplicates = []
            seen = set()
            for pref, mx in prefs:
                if pref in seen:
                    duplicates.append(f"preference {pref} ({mx})")
                seen.add(pref)
            print(f"WARNING: Domain '{domain}' has duplicate preferences: {', '.join(duplicates)}")
    
    # Display validation summary
    print("\nMX Record Validation Summary:")
    print(f"Total records checked: {len(mx_records)}")
    print(f"Records with missing required fields: {len(missing_required_fields)}")
    print(f"Records with invalid preference values: {len(invalid_preferences)}")
    print(f"Records with invalid TTL values: {len(invalid_ttls)}")
    print(f"Records with non-resolving mail exchangers: {len(missing_mail_exchangers)}")
    print(f"Missing parent domains: {len(failed_domains)}")
    if failed_domains:
        print(f"Failed domains: {', '.join(failed_domains)}")
    
    return not validation_failed

def check_existing_naptr_record(name, view):
    """Check if a NAPTR record already exists in Infoblox."""
    try:
        response = requests.get(
            f"{BASE_URL}/record:naptr",
            params={"name": name, "view": view},
            auth=(INFOBLOX_USERNAME, INFOBLOX_PASSWORD),
            verify=VALIDATE_CERTS,
            timeout=HTTP_TIMEOUT
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"✗ Error checking NAPTR record {name}: {response.status_code}")
            return []
    except Exception as e:
        print(f"✗ Error checking NAPTR record {name}: {str(e)}")
        return []

def validate_naptr_flags(flags):
    """Validate NAPTR flags field."""
    valid_flags = ["", "U", "S", "A", "P", "AS", "SA", "AP", "PA", "SP", "PS", "AU", "UA", "SU", "US", "PU", "UP"]
    return flags in valid_flags

def validate_naptr_regexp(regexp, flags):
    """Validate NAPTR regexp field based on flags."""
    
    if not regexp:
        return True 

    if not isinstance(regexp, str):
        return False
    
    # Check for common NAPTR regexp patterns
    if regexp.startswith('!') and regexp.count('!') >= 2:
        return True  # Typical NAPTR regexp format
    
    # For non-standard formats, just check if it's a string
    return True

def validate_naptr_replacement(replacement, flags):
    """Validate NAPTR replacement field based on flags."""
    
    if not replacement:
        return False 
    
    if replacement == ".":
        return True 
    
    if len(replacement) > 253:
        return False
    
    # Should end with a dot for FQDN
    if not replacement.endswith('.'):
        return False
    
    return True

def validate_naptr_records():
    """Validate NAPTR records from JSON file."""
    print("\n--- NAPTR Record Validation ---")
    
    naptr_record_file = "playbooks/add/cabgridmgr.amfam.com/naptr_record.json"
    
    # Read NAPTR record data from JSON file
    try:
        with open(naptr_record_file, 'r') as file:
            naptr_records = json.load(file)
            
            if not isinstance(naptr_records, list):
                naptr_records = [naptr_records]
                
            print(f"Found {len(naptr_records)} NAPTR records to validate.")
    except Exception as e:
        print(f"Error reading file {naptr_record_file}: {str(e)}")
        return False
    
    # Now continue with validation since we have records to check
    validation_failed = False
    missing_required_fields = []
    invalid_orders = []
    invalid_preferences = []
    invalid_flags = []
    invalid_regexps = []
    invalid_replacements = []
    invalid_ttls = []
    failed_domains = []
    
    # Check for required fields and validate values
    for record in naptr_records:
        # Check required fields
        if not all(key in record for key in ["name", "view"]):
            missing_fields = [field for field in ["name", "view"] if field not in record]
            missing_required_fields.append(f"{record.get('name', 'Unknown record')}: missing {', '.join(missing_fields)}")
            validation_failed = True
            continue
        
        # Validate order value
        if "order" in record:
            try:
                order = int(record["order"])
                if order < 0 or order > 65535:
                    invalid_orders.append(f"{record['name']}: order {order} (must be 0-65535)")
                    validation_failed = True
            except (ValueError, TypeError):
                invalid_orders.append(f"{record['name']}: order '{record['order']}' is not a valid integer")
                validation_failed = True
        
        # Validate preference value
        if "preference" in record:
            try:
                preference = int(record["preference"])
                if preference < 0 or preference > 65535:
                    invalid_preferences.append(f"{record['name']}: preference {preference} (must be 0-65535)")
                    validation_failed = True
            except (ValueError, TypeError):
                invalid_preferences.append(f"{record['name']}: preference '{record['preference']}' is not a valid integer")
                validation_failed = True
        
        # Validate flags
        if "flags" in record:
            if not validate_naptr_flags(record["flags"]):
                invalid_flags.append(f"{record['name']}: flags '{record['flags']}' (should be combination of U, S, A, P or empty)")
                validation_failed = True
        
        # Validate regexp
        if "regexp" in record:
            flags = record.get("flags", "")
            if not validate_naptr_regexp(record["regexp"], flags):
                invalid_regexps.append(f"{record['name']}: invalid regexp '{record['regexp']}'")
                validation_failed = True
        
        # Validate replacement
        if "replacement" in record:
            flags = record.get("flags", "")
            if not validate_naptr_replacement(record["replacement"], flags):
                invalid_replacements.append(f"{record['name']}: invalid replacement '{record['replacement']}'")
                validation_failed = True
        
        # Validate TTL if specified
        if "ttl" in record and record["ttl"] is not None:
            try:
                ttl = int(record["ttl"])
                if ttl < 0 or ttl > 2147483647:
                    invalid_ttls.append(f"{record['name']}: TTL {ttl} (must be 0-2147483647)")
                    validation_failed = True
            except (ValueError, TypeError):
                invalid_ttls.append(f"{record['name']}: TTL '{record['ttl']}' is not a valid integer")
                validation_failed = True
    
    # Display validation errors
    for missing in missing_required_fields:
        print(f"ERROR: Missing required fields - {missing}")
    
    for invalid in invalid_orders:
        print(f"ERROR: Invalid order value - {invalid}")
    
    for invalid in invalid_preferences:
        print(f"ERROR: Invalid preference value - {invalid}")
    
    for invalid in invalid_flags:
        print(f"ERROR: Invalid flags - {invalid}")
    
    for invalid in invalid_regexps:
        print(f"ERROR: Invalid regexp - {invalid}")
    
    for invalid in invalid_replacements:
        print(f"ERROR: Invalid replacement - {invalid}")
    
    for invalid in invalid_ttls:
        print(f"ERROR: Invalid TTL value - {invalid}")
    
    # Check for existing NAPTR records in Infoblox
    for record in naptr_records:
        if "name" not in record or "view" not in record:
            continue
            
        existing_records = check_existing_naptr_record(record['name'], record['view'])
        if existing_records:
            existing_configs = [(r.get('order'), r.get('preference'), r.get('services')) for r in existing_records]
            new_order = record.get('order')
            new_pref = record.get('preference')
            new_services = record.get('services')
            
            # Check for exact match
            if (new_order, new_pref, new_services) in existing_configs:
                print(f"Record '{record['name']}' already exists in Infoblox with order {new_order}, preference {new_pref}, services {new_services}")
            else:
                # Check for conflicts
                print(f"NAPTR record '{record['name']}' already exists in Infoblox with different configuration:")
                for order, pref, services in existing_configs:
                    print(f"  Existing: order {order}, preference {pref}, services {services}")
                print(f"  New: order {new_order}, preference {new_pref}, services {new_services}")
    
    # Check for DNS zone existence in Infoblox
    parent_domains = {}
    for record in naptr_records:
        if "name" not in record or "view" not in record:
            continue
            
        domain = extract_parent_domain(record['name'])
        if domain not in parent_domains:
            parent_domains[domain] = record['view']
    
    for domain, view in parent_domains.items():
        zone_exists = check_zone_exists(domain, view)
        if not zone_exists:
            print(f"ERROR: Parent domain '{domain}' does not exist in Infoblox")
            validation_failed = True
            failed_domains.append(domain)
    
    # Perform DNS lookup for each NAPTR record
    for record in naptr_records:
        if "name" not in record:
            continue
            
        dns_result = perform_dns_lookup(record['name'])
        if dns_result['rc'] == 0:
            print(f"WARNING: DNS record '{record['name']}' already exists in DNS with result: {dns_result['stdout']}")
    
    # Validate logical consistency of flags, regexp, and replacement
    for record in naptr_records:
        if "flags" not in record:
            continue
            
        flags = record.get("flags", "")
        regexp = record.get("regexp", "")
        replacement = record.get("replacement", "")
        services = record.get("services", "")
        name = record.get("name", "Unknown")
        
        # Check logical consistency based on RFC 3403
        if "U" in flags:
            if replacement != ".":
                print(f"WARNING: Record '{name}' has 'U' flag but replacement is not '.' (got '{replacement}')")
            if not regexp:
                print(f"INFO: Record '{name}' has 'U' flag but no regexp - this is valid but uncommon")
        
        if "S" in flags:
            if replacement == ".":
                print(f"WARNING: Record '{name}' has 'S' flag but replacement is '.' - should point to SRV record")
            if regexp:
                print(f"INFO: Record '{name}' has 'S' flag with regexp - this is valid but uncommon")
        
        if "A" in flags:
            if replacement == ".":
                print(f"WARNING: Record '{name}' has 'A' flag but replacement is '.' - should point to A/AAAA record")
        
        if "P" in flags:
            pass
    
    # Check for duplicate order/preference combinations within the same domain
    domain_orders = {}
    for record in naptr_records:
        if not all(key in record for key in ["name", "order", "preference"]):
            continue
            
        domain = record['name']
        order = record['order']
        preference = record['preference']
        services = record.get('services', '')
        
        if domain not in domain_orders:
            domain_orders[domain] = []
        domain_orders[domain].append((order, preference, services))
    
    for domain, configs in domain_orders.items():
        order_pref_pairs = [(o, p) for o, p, s in configs]
        if len(order_pref_pairs) != len(set(order_pref_pairs)):
            duplicates = []
            seen = set()
            for order, pref, services in configs:
                if (order, pref) in seen:
                    duplicates.append(f"order {order}, preference {pref} (services: {services})")
                seen.add((order, pref))
            print(f"WARNING: Domain '{domain}' has duplicate order/preference combinations: {', '.join(duplicates)}")
    
    # Display validation summary
    print("\nNAPTR Record Validation Summary:")
    print(f"Total records checked: {len(naptr_records)}")
    print(f"Records with missing required fields: {len(missing_required_fields)}")
    print(f"Records with invalid order values: {len(invalid_orders)}")
    print(f"Records with invalid preference values: {len(invalid_preferences)}")
    print(f"Records with invalid flags: {len(invalid_flags)}")
    print(f"Records with invalid regexp: {len(invalid_regexps)}")
    print(f"Records with invalid replacement: {len(invalid_replacements)}")
    print(f"Records with invalid TTL values: {len(invalid_ttls)}")
    print(f"Missing parent domains: {len(failed_domains)}")
    if failed_domains:
        print(f"Failed domains: {', '.join(failed_domains)}")
    
    return not validation_failed

def check_existing_ptr_record(name, view):
    """Check if a PTR record already exists in Infoblox."""
    try:
        response = requests.get(
            f"{BASE_URL}/record:ptr",
            params={"name": name, "view": view},
            auth=(INFOBLOX_USERNAME, INFOBLOX_PASSWORD),
            verify=VALIDATE_CERTS,
            timeout=HTTP_TIMEOUT
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"✗ Error checking PTR record {name}: {response.status_code}")
            return []
    except Exception as e:
        print(f"✗ Error checking PTR record {name}: {str(e)}")
        return []

def check_ptrdname_exists(ptrdname, view):
    """Check if the ptrdname (reverse mapping) exists in Infoblox."""
    try:
        # Try to resolve the ptrdname - could be any record type
        # First check A records
        a_response = requests.get(
            f"{BASE_URL}/record:a",
            params={"name": ptrdname, "view": view},
            auth=(INFOBLOX_USERNAME, INFOBLOX_PASSWORD),
            verify=VALIDATE_CERTS,
            timeout=HTTP_TIMEOUT
        )
        
        if a_response.status_code == 200 and len(a_response.json()) > 0:
            return True
        
        # Check AAAA records
        aaaa_response = requests.get(
            f"{BASE_URL}/record:aaaa",
            params={"name": ptrdname, "view": view},
            auth=(INFOBLOX_USERNAME, INFOBLOX_PASSWORD),
            verify=VALIDATE_CERTS,
            timeout=HTTP_TIMEOUT
        )
        
        if aaaa_response.status_code == 200 and len(aaaa_response.json()) > 0:
            return True
        
        # Check CNAME records
        cname_response = requests.get(
            f"{BASE_URL}/record:cname",
            params={"name": ptrdname, "view": view},
            auth=(INFOBLOX_USERNAME, INFOBLOX_PASSWORD),
            verify=VALIDATE_CERTS,
            timeout=HTTP_TIMEOUT
        )
        
        if cname_response.status_code == 200 and len(cname_response.json()) > 0:
            return True
        
        # Check host records
        host_response = requests.get(
            f"{BASE_URL}/record:host",
            params={"name": ptrdname, "view": view},
            auth=(INFOBLOX_USERNAME, INFOBLOX_PASSWORD),
            verify=VALIDATE_CERTS,
            timeout=HTTP_TIMEOUT
        )
        
        if host_response.status_code == 200 and len(host_response.json()) > 0:
            return True
        
        return False
    except Exception as e:
        print(f"✗ Error checking ptrdname {ptrdname}: {str(e)}")
        return False

def validate_ipv4_ptr_name(ipv4addr, name):
    """Validate if PTR name matches IPv4 address."""
    # Convert IPv4 to in-addr.arpa format and compare with name
    octets = ipv4addr.split('.')
    expected_ptr = f"{octets[3]}.{octets[2]}.{octets[1]}.{octets[0]}.in-addr.arpa"
    return name == expected_ptr

def validate_ipv6_ptr_name(ipv6addr, name):
    """Validate if PTR name matches IPv6 address."""
    try:
        # Convert IPv6 to ip6.arpa format and compare with name
        ip = IPv6Address(ipv6addr)
        expanded_ip = ip.exploded
        hex_digits = expanded_ip.replace(':', '')
        
        # Reverse and separate with dots
        reversed_digits = '.'.join(reversed(hex_digits))
        expected_ptr = f"{reversed_digits}.ip6.arpa"
        
        return name == expected_ptr
    except Exception as e:
        print(f"✗ Error validating IPv6 PTR name: {str(e)}")
        return False

def validate_ptr_records():
    """Validate PTR records from JSON file."""
    print("\n--- PTR Record Validation ---")
    
    ptr_record_file = "../prod_changes/cabgridmgr.amfam.com/ptr_record.json"
    
    # Read PTR record data from JSON file
    try:
        with open(ptr_record_file, 'r') as file:
            ptr_records = json.load(file)
            
            # If the content is not a list, convert it to a list with one item
            if not isinstance(ptr_records, list):
                ptr_records = [ptr_records]
                
            print(f"Found {len(ptr_records)} PTR records to validate.")
    except Exception as e:
        print(f"Error reading file {ptr_record_file}: {str(e)}")
        return False
    
    # Now continue with validation since we have records to check
    validation_failed = False
    missing_required_fields = []
    invalid_ipv4s = []
    invalid_ipv6s = []
    invalid_ptr_names = []
    missing_ptrdnames = []
    failed_domains = []
    invalid_ttls = []
    
    # Check for required fields based on playbook
    for record in ptr_records:
        # Check required fields that the playbook uses
        required_fields = ["name", "ptrdname"]
        missing_fields = [field for field in required_fields if field not in record or record[field] is None]
        if missing_fields:
            missing_required_fields.append(f"{record.get('name', 'Unknown record')}: missing {', '.join(missing_fields)}")
            validation_failed = True
            continue
    
    # Display missing required fields
    for missing in missing_required_fields:
        print(f"ERROR: Missing required fields - {missing}")
    
    # Validate IP Address fields (both are optional in playbook)
    for record in ptr_records:
        has_ipv4 = "ipv4addr" in record and record["ipv4addr"]
        has_ipv6 = "ipv6addr" in record and record["ipv6addr"]
        
        if not has_ipv4 and not has_ipv6:
            print(f"INFO: Record '{record['name']}' has neither ipv4addr nor ipv6addr specified")
        
        # Validate IPv4 format if present
        if has_ipv4:
            if not validate_ipv4_format(record["ipv4addr"]):
                invalid_ipv4s.append(f"{record['name']}: {record['ipv4addr']}")
                validation_failed = True
            else:
                # Validate PTR name matches IPv4 address
                if not validate_ipv4_ptr_name(record["ipv4addr"], record["name"]):
                    invalid_ptr_names.append(f"{record['name']}: does not match IPv4 address {record['ipv4addr']}")
                    validation_failed = True
        
        # Validate IPv6 format if present
        if has_ipv6:
            if not validate_ipv6_format(record["ipv6addr"]):
                invalid_ipv6s.append(f"{record['name']}: {record['ipv6addr']}")
                validation_failed = True
            else:
                # Validate PTR name matches IPv6 address
                if not validate_ipv6_ptr_name(record["ipv6addr"], record["name"]):
                    invalid_ptr_names.append(f"{record['name']}: does not match IPv6 address {record['ipv6addr']}")
                    validation_failed = True
    
    # Display IP validation errors
    for invalid in invalid_ipv4s:
        print(f"ERROR: Invalid IPv4 address format - {invalid}")
    
    for invalid in invalid_ipv6s:
        print(f"ERROR: Invalid IPv6 address format - {invalid}")
    
    for invalid in invalid_ptr_names:
        print(f"ERROR: Invalid PTR name - {invalid}")
    
    # Validate TTL if specified
    for record in ptr_records:
        if "ttl" in record and record["ttl"] is not None:
            try:
                ttl = int(record["ttl"])
                if ttl < 0 or ttl > 2147483647:
                    invalid_ttls.append(f"{record['name']}: TTL {ttl} (must be 0-2147483647)")
                    validation_failed = True
            except (ValueError, TypeError):
                invalid_ttls.append(f"{record['name']}: TTL '{record['ttl']}' is not a valid integer")
                validation_failed = True
    
    # Display invalid TTL values
    for invalid in invalid_ttls:
        print(f"ERROR: Invalid TTL value - {invalid}")
    
    # Check for existing PTR records in Infoblox
    for record in ptr_records:
        if "name" not in record:
            continue
            
        view = record.get("view", "default")  # Playbook uses default('default')
        existing_records = check_existing_ptr_record(record['name'], view)
        if existing_records:
            # Check if a PTR record with the same ptrdname already exists
            existing_ptrdnames = [r.get('ptrdname') for r in existing_records]
            new_ptrdname = record.get('ptrdname')
            
            # Check for exact match
            if new_ptrdname in existing_ptrdnames:
                print(f"Record '{record['name']}' already exists in Infoblox with ptrdname {new_ptrdname}")
            else:
                # Check for conflicts (same name, different ptrdname)
                print(f"PTR record '{record['name']}' already exists in Infoblox with different configuration:")
                for ptrdname in existing_ptrdnames:
                    print(f"  Existing: ptrdname {ptrdname}")
                print(f"  New: ptrdname {new_ptrdname}")
    
    # Check if ptrdnames exist as forward records
    for record in ptr_records:
        if "ptrdname" not in record:
            continue
            
        view = record.get("view", "default")
        if not check_ptrdname_exists(record['ptrdname'], view):
            missing_ptrdnames.append(f"{record['name']}: PTR destination {record['ptrdname']}")
            print(f"WARNING: PTR destination '{record['ptrdname']}' does not resolve to any forward record")
    
    # Check for reverse zone existence in Infoblox
    for record in ptr_records:
        if "name" not in record:
            continue
            
        view = record.get("view", "default")
        
        # Extract the reverse zone from the PTR name
        ptr_name = record['name']
        
        if ptr_name.endswith('.in-addr.arpa'):
            parts = ptr_name.split('.')
            if len(parts) >= 5:
                # Get the first three octets from the right (excluding '.in-addr.arpa')
                zone_name = '.'.join(parts[1:])
            else:
                zone_name = '.'.join(parts)
        
        # For IPv6 PTR records (*.ip6.arpa)
        elif ptr_name.endswith('.ip6.arpa'):
            parts = ptr_name.split('.')
            if len(parts) >= 33:
                zone_name = '.'.join(parts[16:])
            else:
                zone_name = '.'.join(parts)
        else:
            zone_name = ptr_name
        
        zone_exists = check_zone_exists(zone_name, view)
        if not zone_exists:
            # Try alternative reverse zone lengths
            if ptr_name.endswith('.in-addr.arpa'):
                # Try Class C (/24) reverse zone
                parts = ptr_name.split('.')
                if len(parts) >= 6:
                    alt_zone_name = '.'.join(parts[2:])
                    zone_exists = check_zone_exists(alt_zone_name, view)
            
            if not zone_exists:
                print(f"ERROR: Reverse zone '{zone_name}' does not exist in Infoblox")
                validation_failed = True
                failed_domains.append(zone_name)
    
    # Perform DNS lookup for each PTR record
    for record in ptr_records:
        if "name" not in record:
            continue
            
        dns_result = perform_dns_lookup(record['name'])
        if dns_result['rc'] == 0:
            print(f"WARNING: DNS record '{record['name']}' already exists in DNS with result: {dns_result['stdout']}")
    
    # Validate optional fields that playbook accepts
    for record in ptr_records:
        # Check comment field (optional)
        if "comment" in record and record["comment"] is not None:
            if not isinstance(record["comment"], str):
                print(f"WARNING: Comment for record '{record['name']}' should be a string")
        
        # Check extattrs field (optional)
        if "extattrs" in record and record["extattrs"] is not None:
            if not isinstance(record["extattrs"], dict):
                print(f"WARNING: Extended attributes for record '{record['name']}' should be a dictionary")
        
        # Check ptrdname format
        if "ptrdname" in record and record["ptrdname"]:
            ptrdname = record["ptrdname"]
            if not ptrdname.endswith('.'):
                print(f"INFO: PTR destination '{ptrdname}' for record '{record['name']}' should be fully qualified (end with a dot)")
    
    # Display validation summary
    print("\nPTR Record Validation Summary:")
    print(f"Total records checked: {len(ptr_records)}")
    print(f"Records with missing required fields: {len(missing_required_fields)}")
    print(f"Records with invalid IPv4 addresses: {len(invalid_ipv4s)}")
    print(f"Records with invalid IPv6 addresses: {len(invalid_ipv6s)}")
    print(f"Records with mismatched PTR names: {len(invalid_ptr_names)}")
    print(f"Records with non-resolving ptrdnames: {len(missing_ptrdnames)}")
    print(f"Records with invalid TTL values: {len(invalid_ttls)}")
    print(f"Missing reverse zones: {len(failed_domains)}")
    if failed_domains:
        print(f"Failed zones: {', '.join(failed_domains)}")
    
    return not validation_failed and not missing_required_fields

def check_existing_txt_record(name, view):
    """Check if a TXT record already exists in Infoblox."""
    try:
        response = requests.get(
            f"{BASE_URL}/record:txt",
            params={"name": name, "view": view},
            auth=(INFOBLOX_USERNAME, INFOBLOX_PASSWORD),
            verify=VALIDATE_CERTS,
            timeout=HTTP_TIMEOUT
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"✗ Error checking TXT record {name}: {response.status_code}")
            return []
    except Exception as e:
        print(f"✗ Error checking TXT record {name}: {str(e)}")
        return []

def validate_txt_content(text):
    """Validate TXT record text content."""

    if not text:
        return False, "Text content cannot be empty"
    
    if len(text) > 2048:
        return False, f"Text content is too long ({len(text)} characters, recommended max is 2048)"
    
    # Check for valid UTF-8 content
    try:
        text.encode('utf-8')
        return True, None
    except UnicodeEncodeError:
        return False, "Text content contains invalid UTF-8 characters"

def validate_txt_records():
    """Validate TXT records from JSON file."""
    print("\n--- TXT Record Validation ---")
    
    txt_record_file = "../prod_changes/cabgridmgr.amfam.com/txt_record.json"
    
    # Read TXT record data from JSON file
    try:
        with open(txt_record_file, 'r') as file:
            txt_records = json.load(file)
            
            # If the content is not a list, convert it to a list with one item
            if not isinstance(txt_records, list):
                txt_records = [txt_records]
                
            print(f"Found {len(txt_records)} TXT records to validate.")
    except Exception as e:
        print(f"Error reading file {txt_record_file}: {str(e)}")
        return False
    
    # Now continue with validation since we have records to check
    validation_failed = False
    missing_required_fields = []
    invalid_text_content = []
    invalid_ttls = []
    failed_domains = []
    
    # Check for required fields and validate values
    for record in txt_records:
        # Check required fields
        if not all(key in record for key in ["name", "text", "view"]):
            missing_fields = [field for field in ["name", "text", "view"] if field not in record]
            missing_required_fields.append(f"{record.get('name', 'Unknown record')}: missing {', '.join(missing_fields)}")
            validation_failed = True
            continue
        
        # Validate text content
        text_valid, error_message = validate_txt_content(record.get("text", ""))
        if not text_valid:
            invalid_text_content.append(f"{record['name']}: {error_message}")
            validation_failed = True
        
        # Validate TTL if specified
        if "ttl" in record and record["ttl"] is not None:
            try:
                ttl = int(record["ttl"])
                if ttl < 0 or ttl > 2147483647:
                    invalid_ttls.append(f"{record['name']}: TTL {ttl} (must be 0-2147483647)")
                    validation_failed = True
            except (ValueError, TypeError):
                invalid_ttls.append(f"{record['name']}: TTL '{record['ttl']}' is not a valid integer")
                validation_failed = True
    
    # Display validation errors
    for missing in missing_required_fields:
        print(f"ERROR: Missing required fields - {missing}")
    
    for invalid in invalid_text_content:
        print(f"ERROR: Invalid text content - {invalid}")
    
    for invalid in invalid_ttls:
        print(f"ERROR: Invalid TTL value - {invalid}")
    
    # Check for existing TXT records in Infoblox
    for record in txt_records:
        if "name" not in record or "view" not in record:
            continue
            
        existing_records = check_existing_txt_record(record['name'], record['view'])
        if existing_records:
            # Check if a TXT record with the same text already exists
            existing_texts = [r.get('text') for r in existing_records]
            new_text = record.get('text')
            
            # Check for exact match
            if new_text in existing_texts:
                print(f"Record '{record['name']}' already exists in Infoblox with text content: \"{new_text}\"")
            else:
                # Check for conflicts (same name, different text)
                print(f"TXT record '{record['name']}' already exists in Infoblox with different content:")
                for text in existing_texts:
                    print(f"  Existing: \"{text}\"")
                print(f"  New: \"{new_text}\"")
    
    # Check for DNS zone existence in Infoblox
    parent_domains = {}
    for record in txt_records:
        if "name" not in record or "view" not in record:
            continue
            
        domain = extract_parent_domain(record['name'])
        if domain not in parent_domains:
            parent_domains[domain] = record['view']
    
    for domain, view in parent_domains.items():
        zone_exists = check_zone_exists(domain, view)
        if not zone_exists:
            print(f"ERROR: Parent domain '{domain}' does not exist in Infoblox")
            validation_failed = True
            failed_domains.append(domain)
    
    # Perform DNS lookup for each TXT record
    for record in txt_records:
        if "name" not in record:
            continue
            
        # Use specific lookup for TXT records
        dns_result = subprocess.run(['nslookup', '-type=TXT', record['name']], 
                                   capture_output=True, 
                                   text=True, 
                                   check=False)
        
        if dns_result.returncode == 0 and "NXDOMAIN" not in dns_result.stdout:
            print(f"WARNING: DNS record '{record['name']}' already exists in DNS with result: {dns_result.stdout}")
    
    # Validate special use cases for TXT records
    for record in txt_records:
        if "name" not in record or "text" not in record:
            continue
            
        name = record["name"].lower()
        text = record["text"]
        
        # SPF record validation
        if "spf" in name or text.startswith("v=spf1"):
            # Basic SPF syntax check
            if text.startswith("v=spf1") and not any(m in text for m in [" all", " ~all", " -all", " ?all"]):
                print(f"WARNING: SPF record '{name}' does not have a proper 'all' mechanism at the end")
            
            # Check for both SPF and TXT with same SPF content
            if not name.startswith("_spf.") and not name.startswith("spf."):
                pass
        
        # DKIM record validation
        if name.startswith("_domainkey") or "_domainkey." in name:
            if not ("v=dkim1" in text or "p=" in text):
                print(f"WARNING: Possible DKIM record '{name}' doesn't have required DKIM syntax")
        
        # DMARC record validation
        if name.startswith("_dmarc."):
            if not "v=dmarc1" in text:
                print(f"WARNING: DMARC record '{name}' doesn't have required DMARC syntax")
            
            # Check for required tags
            if "p=" not in text:
                print(f"WARNING: DMARC record '{name}' is missing required 'p=' tag")
        
        # Check for unescaped quotes in text content
        quote_count = text.count('"')
        if quote_count % 2 != 0 and '"' not in text:
            print(f"WARNING: TXT record '{name}' may have unescaped quotes in text content")
        
        # Check for potential certificate verification records
        if text.startswith("MS=") or text.startswith("google-site-verification=") or text.startswith("apple-domain-verification="):
            print(f"INFO: TXT record '{name}' appears to be a domain verification record")
    
    # Display validation summary
    print("\nTXT Record Validation Summary:")
    print(f"Total records checked: {len(txt_records)}")
    print(f"Records with missing required fields: {len(missing_required_fields)}")
    print(f"Records with invalid text content: {len(invalid_text_content)}")
    print(f"Records with invalid TTL values: {len(invalid_ttls)}")
    print(f"Missing parent domains: {len(failed_domains)}")
    if failed_domains:
        print(f"Failed domains: {', '.join(failed_domains)}")
    
    return not validation_failed

def check_rpz_license():
    """Check if RPZ license is installed on Grid Members."""
    try:
        response = requests.get(
            f"{BASE_URL}/member:license",
            auth=(INFOBLOX_USERNAME, INFOBLOX_PASSWORD),
            verify=VALIDATE_CERTS,
            timeout=HTTP_TIMEOUT
        )
        
        if response.status_code == 200:
            licenses = response.json()
            rpz_licensed = any('RPZ' in license.get('type', '') for license in licenses)
            return rpz_licensed
        else:
            print(f"✗ Error checking RPZ license: {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Error checking RPZ license: {str(e)}")
        return False

def check_existing_zone_rp(fqdn, view):
    """Check if a Response Policy Zone already exists in Infoblox."""
    try:
        response = requests.get(
            f"{BASE_URL}/zone_rp",
            params={"fqdn": fqdn, "view": view},
            auth=(INFOBLOX_USERNAME, INFOBLOX_PASSWORD),
            verify=VALIDATE_CERTS,
            timeout=HTTP_TIMEOUT
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"✗ Error checking RPZ zone {fqdn}: {response.status_code}")
            return []
    except Exception as e:
        print(f"✗ Error checking RPZ zone {fqdn}: {str(e)}")
        return []

def check_ns_group_exists(ns_group):
    """Check if NS Group exists in Infoblox."""
    try:
        response = requests.get(
            f"{BASE_URL}/nsgroup",
            params={"name": ns_group},
            auth=(INFOBLOX_USERNAME, INFOBLOX_PASSWORD),
            verify=VALIDATE_CERTS,
            timeout=HTTP_TIMEOUT
        )
        
        if response.status_code == 200:
            return len(response.json()) > 0
        else:
            print(f"✗ Error checking NS Group {ns_group}: {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Error checking NS Group {ns_group}: {str(e)}")
        return False

def check_grid_member_exists(member_name):
    """Check if Grid Member exists in Infoblox."""
    try:
        response = requests.get(
            f"{BASE_URL}/member",
            params={"host_name": member_name},
            auth=(INFOBLOX_USERNAME, INFOBLOX_PASSWORD),
            verify=VALIDATE_CERTS,
            timeout=HTTP_TIMEOUT
        )
        
        if response.status_code == 200:
            return len(response.json()) > 0
        else:
            print(f"✗ Error checking Grid Member {member_name}: {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Error checking Grid Member {member_name}: {str(e)}")
        return False

def validate_rpz_priority_range(priority, priority_end):
    """Validate RPZ priority range."""
    try:
        priority = int(priority)
        priority_end = int(priority_end)
        
        # Priority must be between 1 and 999
        if not (1 <= priority <= 999):
            return False, f"Priority {priority} must be between 1 and 999"
        
        # Priority end must be between 1 and 999
        if not (1 <= priority_end <= 999):
            return False, f"Priority end {priority_end} must be between 1 and 999"
        
        # Priority must be less than or equal to priority_end
        if priority > priority_end:
            return False, f"Priority {priority} must be <= priority_end {priority_end}"
        
        return True, None
    except (ValueError, TypeError):
        return False, "Priority values must be valid integers"

def validate_soa_values(record):
    """Validate SOA timing values."""
    soa_fields = {
        'soa_default_ttl': (1, 2147483647),
        'soa_expire': (1, 2147483647),
        'soa_negative_ttl': (1, 2147483647),
        'soa_refresh': (1, 2147483647),
        'soa_retry': (1, 2147483647)
    }
    
    errors = []
    
    for field, (min_val, max_val) in soa_fields.items():
        if field in record and record[field] is not None:
            try:
                value = int(record[field])
                if not (min_val <= value <= max_val):
                    errors.append(f"{field} {value} must be between {min_val} and {max_val}")
            except (ValueError, TypeError):
                errors.append(f"{field} '{record[field]}' is not a valid integer")
    
    # Additional SOA validation rules
    if 'soa_retry' in record and 'soa_refresh' in record:
        try:
            retry = int(record['soa_retry'])
            refresh = int(record['soa_refresh'])
            if retry >= refresh:
                errors.append(f"soa_retry {retry} should be less than soa_refresh {refresh}")
        except (ValueError, TypeError):
            pass  # Already handled above
    
    return errors

def validate_rpz_drop_ip_prefix_lengths(record):
    """Validate RPZ drop IP rule prefix lengths."""
    errors = []
    
    # IPv4 prefix length validation
    if 'rpz_drop_ip_rule_min_prefix_length_ipv4' in record:
        try:
            ipv4_prefix = int(record['rpz_drop_ip_rule_min_prefix_length_ipv4'])
            if not (8 <= ipv4_prefix <= 32):
                errors.append(f"IPv4 prefix length {ipv4_prefix} must be between 8 and 32")
        except (ValueError, TypeError):
            errors.append(f"IPv4 prefix length '{record['rpz_drop_ip_rule_min_prefix_length_ipv4']}' is not a valid integer")
    
    # IPv6 prefix length validation
    if 'rpz_drop_ip_rule_min_prefix_length_ipv6' in record:
        try:
            ipv6_prefix = int(record['rpz_drop_ip_rule_min_prefix_length_ipv6'])
            if not (64 <= ipv6_prefix <= 128):
                errors.append(f"IPv6 prefix length {ipv6_prefix} must be between 64 and 128")
        except (ValueError, TypeError):
            errors.append(f"IPv6 prefix length '{record['rpz_drop_ip_rule_min_prefix_length_ipv6']}' is not a valid integer")
    
    return errors

def validate_zone_rp_records():
    """Validate Response Policy Zone records from JSON file."""
    print("\n--- Response Policy Zone Validation ---")
    
    zone_rp_file = "playbooks/add/cabgridmgr.amfam.com/zone_rp.json"
    
    # Read RPZ record data from JSON file
    try:
        with open(zone_rp_file, 'r') as file:
            zone_rp_records = json.load(file)
            
            # If the content is not a list, convert it to a list with one item
            if not isinstance(zone_rp_records, list):
                zone_rp_records = [zone_rp_records]
                
            print(f"Found {len(zone_rp_records)} Response Policy Zone records to validate.")
    except Exception as e:
        print(f"Error reading file {zone_rp_file}: {str(e)}")
        return False
    
    # First check if RPZ license is available
    rpz_licensed = check_rpz_license()
    if not rpz_licensed:
        print("ERROR: RPZ license is not installed on Grid Members")
        print("Response Policy Zone functionality requires a valid RPZ license")
        return False
    else:
        print("✓ RPZ license is installed and available")
    
    # Now continue with validation since we have records to check
    validation_failed = False
    missing_required_fields = []
    invalid_rpz_policies = []
    invalid_rpz_severities = []
    invalid_rpz_types = []
    invalid_primary_types = []
    invalid_priority_ranges = []
    invalid_soa_values = []
    invalid_prefix_lengths = []
    missing_ns_groups = []
    missing_grid_members = []
    failed_views = []
    non_writable_field_warnings = []
    
    # Valid enum values based on Infoblox documentation
    valid_rpz_policies = ["DISABLED", "GIVEN", "NODATA", "NXDOMAIN", "PASSTHRU", "SUBSTITUTE"]
    valid_rpz_severities = ["INFORMATIONAL", "WARNING", "MINOR", "MAJOR", "CRITICAL"]
    valid_rpz_types = ["FEED", "FIREEYE", "LOCAL"]
    valid_primary_types = ["Grid", "External"]
    
    # Non-writable fields during creation (from playbook)
    non_writable_fields_create = [
        '_ref', 'display_domain', 'dns_soa_email', 'locked_by', 'mask_prefix',
        'member_soa_serials', 'network_view', 'parent', 'primary_type',
        'rpz_last_updated_time', 'rpz_priority', 'rpz_priority_end', 'rpz_type',
        'fireeye_rule_mapping'
    ]
    
    # Writable fields during update (from playbook)
    writable_fields_update = [
        'disable', 'extattrs', 'log_rpz', 'rpz_drop_ip_rule_enabled',
        'rpz_drop_ip_rule_min_prefix_length_ipv4', 'rpz_drop_ip_rule_min_prefix_length_ipv6',
        'rpz_policy', 'rpz_severity', 'soa_default_ttl', 'soa_expire',
        'soa_negative_ttl', 'soa_refresh', 'soa_retry', 'use_grid_zone_timer',
        'use_log_rpz', 'use_record_name_policy', 'use_rpz_drop_ip_rule', 'use_soa_email'
    ]
    
    # Check for required fields based on playbook
    for record in zone_rp_records:
        # Check required fields - fqdn and view are essential
        required_fields = ["fqdn", "view"]
        missing_fields = [field for field in required_fields if field not in record or record[field] is None]
        if missing_fields:
            missing_required_fields.append(f"{record.get('fqdn', 'Unknown zone')}: missing {', '.join(missing_fields)}")
            validation_failed = True
            continue
        
        # Check for non-writable fields that shouldn't be in create request
        for field in non_writable_fields_create:
            if field in record:
                non_writable_field_warnings.append(f"{record['fqdn']}: contains non-writable field '{field}' which will be ignored during creation")
                print(f"WARNING: Zone '{record['fqdn']}' contains non-writable field '{field}' which will be ignored during creation")
    
    # Display missing required fields
    for missing in missing_required_fields:
        print(f"ERROR: Missing required fields - {missing}")
    
    # Validate RPZ-specific fields if present
    for record in zone_rp_records:
        # Validate RPZ policy
        if "rpz_policy" in record and record["rpz_policy"] not in valid_rpz_policies:
            invalid_rpz_policies.append(f"{record['fqdn']}: {record['rpz_policy']} (valid: {', '.join(valid_rpz_policies)})")
            validation_failed = True
        
        # Validate RPZ severity
        if "rpz_severity" in record and record["rpz_severity"] not in valid_rpz_severities:
            invalid_rpz_severities.append(f"{record['fqdn']}: {record['rpz_severity']} (valid: {', '.join(valid_rpz_severities)})")
            validation_failed = True
        
        # Validate RPZ type (if present, though it's non-writable during create)
        if "rpz_type" in record and record["rpz_type"] not in valid_rpz_types:
            invalid_rpz_types.append(f"{record['fqdn']}: {record['rpz_type']} (valid: {', '.join(valid_rpz_types)})")
            print(f"INFO: rpz_type is non-writable during creation but validating value")
        
        # Validate primary type (if present, though it's non-writable during create)
        if "primary_type" in record and record["primary_type"] not in valid_primary_types:
            invalid_primary_types.append(f"{record['fqdn']}: {record['primary_type']} (valid: {', '.join(valid_primary_types)})")
            print(f"INFO: primary_type is non-writable during creation but validating value")
        
        # Validate RPZ priority range (if present, though they're non-writable during create)
        if "rpz_priority" in record and "rpz_priority_end" in record:
            is_valid, error_msg = validate_rpz_priority_range(record["rpz_priority"], record["rpz_priority_end"])
            if not is_valid:
                invalid_priority_ranges.append(f"{record['fqdn']}: {error_msg}")
                print(f"INFO: rpz_priority fields are non-writable during creation but validating values")
        
        # Validate SOA values
        soa_errors = validate_soa_values(record)
        if soa_errors:
            for error in soa_errors:
                invalid_soa_values.append(f"{record['fqdn']}: {error}")
            validation_failed = True
        
        # Validate RPZ drop IP rule prefix lengths
        prefix_errors = validate_rpz_drop_ip_prefix_lengths(record)
        if prefix_errors:
            for error in prefix_errors:
                invalid_prefix_lengths.append(f"{record['fqdn']}: {error}")
            validation_failed = True
    
    # Display validation errors
    for invalid in invalid_rpz_policies:
        print(f"ERROR: Invalid RPZ policy - {invalid}")
    
    for invalid in invalid_rpz_severities:
        print(f"ERROR: Invalid RPZ severity - {invalid}")
    
    for invalid in invalid_rpz_types:
        print(f"INFO: Invalid RPZ type - {invalid}")
    
    for invalid in invalid_primary_types:
        print(f"INFO: Invalid primary type - {invalid}")
    
    for invalid in invalid_priority_ranges:
        print(f"INFO: Invalid priority range - {invalid}")
    
    for invalid in invalid_soa_values:
        print(f"ERROR: Invalid SOA value - {invalid}")
    
    for invalid in invalid_prefix_lengths:
        print(f"ERROR: Invalid prefix length - {invalid}")
    
    # Check for existing RPZ zones in Infoblox
    for record in zone_rp_records:
        if "fqdn" not in record or "view" not in record:
            continue
            
        existing_zones = check_existing_zone_rp(record['fqdn'], record['view'])
        if existing_zones:
            existing_config = existing_zones[0]
            print(f"RPZ Zone '{record['fqdn']}' already exists in view '{record['view']}'")
            print(f"  Current policy: {existing_config.get('rpz_policy', 'N/A')}")
            print(f"  Current severity: {existing_config.get('rpz_severity', 'N/A')}")
            print(f"  Current type: {existing_config.get('rpz_type', 'N/A')}")
            
            # Inform about update limitations
            print(f"  Note: Only these fields will be updated: {', '.join(writable_fields_update)}")
    
    # Check NS Group existence (if present)
    for record in zone_rp_records:
        if "ns_group" in record and record["ns_group"]:
            if not check_ns_group_exists(record["ns_group"]):
                missing_ns_groups.append(f"{record['fqdn']}: NS Group '{record['ns_group']}'")
                print(f"ERROR: NS Group '{record['ns_group']}' does not exist")
                validation_failed = True
    
    # Check Grid Member existence for primary and secondary members (if present)
    for record in zone_rp_records:
        # Check grid primary members
        if "grid_primary" in record and record["grid_primary"]:
            for primary in record["grid_primary"]:
                if "name" in primary:
                    if not check_grid_member_exists(primary["name"]):
                        missing_grid_members.append(f"{record['fqdn']}: Grid Primary '{primary['name']}'")
                        print(f"ERROR: Grid Primary member '{primary['name']}' does not exist")
                        validation_failed = True
        
        # Check grid secondary members
        if "grid_secondaries" in record and record["grid_secondaries"]:
            for secondary in record["grid_secondaries"]:
                if "name" in secondary:
                    if not check_grid_member_exists(secondary["name"]):
                        missing_grid_members.append(f"{record['fqdn']}: Grid Secondary '{secondary['name']}'")
                        print(f"ERROR: Grid Secondary member '{secondary['name']}' does not exist")
                        validation_failed = True
    
    # Check for DNS view existence
    for record in zone_rp_records:
        if "view" not in record:
            continue
            
        try:
            response = requests.get(
                f"{BASE_URL}/view",
                params={"name": record["view"]},
                auth=(INFOBLOX_USERNAME, INFOBLOX_PASSWORD),
                verify=VALIDATE_CERTS,
                timeout=HTTP_TIMEOUT
            )
            
            if response.status_code == 200:
                views = response.json()
                if not views:
                    print(f"ERROR: DNS View '{record['view']}' does not exist")
                    validation_failed = True
                    failed_views.append(record['view'])
            else:
                print(f"✗ Error checking view {record['view']}: {response.status_code}")
                validation_failed = True
        except Exception as e:
            print(f"✗ Error checking view {record['view']}: {str(e)}")
            validation_failed = True
    
    # Validate logical consistency
    for record in zone_rp_records:
        zone_name = record.get('fqdn', 'Unknown')
        
        # Check if external primary is used but no external primaries defined
        if record.get('use_external_primary', False) and not record.get('external_primaries', []):
            print(f"WARNING: Zone '{zone_name}' has use_external_primary=true but no external_primaries defined")
        
        # Check if RPZ drop IP rule is enabled but no prefix lengths defined
        if record.get('rpz_drop_ip_rule_enabled', False) or record.get('use_rpz_drop_ip_rule', False):
            if 'rpz_drop_ip_rule_min_prefix_length_ipv4' not in record and 'rpz_drop_ip_rule_min_prefix_length_ipv6' not in record:
                print(f"WARNING: Zone '{zone_name}' has RPZ drop IP rule enabled but no minimum prefix lengths defined")
        
        # Check if FireEye type but no rule mapping
        if record.get('rpz_type') == 'FIREEYE' and not record.get('fireeye_rule_mapping'):
            print(f"INFO: Zone '{zone_name}' is FireEye type but has no rule mapping defined (fireeye_rule_mapping is non-writable during create)")
    
    # Check for duplicate FQDN/View combinations
    fqdn_view_pairs = [(record.get('fqdn'), record.get('view')) for record in zone_rp_records if 'fqdn' in record and 'view' in record]
    duplicates = []
    seen = set()
    for fqdn, view in fqdn_view_pairs:
        if (fqdn, view) in seen:
            duplicates.append(f"{fqdn} in view {view}")
        seen.add((fqdn, view))
    
    if duplicates:
        print(f"ERROR: Duplicate FQDN/View combinations found: {', '.join(duplicates)}")
        validation_failed = True
    
    # Display validation summary
    print("\nResponse Policy Zone Validation Summary:")
    print(f"Total records checked: {len(zone_rp_records)}")
    print(f"Records with missing required fields: {len(missing_required_fields)}")
    print(f"Records with invalid RPZ policies: {len(invalid_rpz_policies)}")
    print(f"Records with invalid RPZ severities: {len(invalid_rpz_severities)}")
    print(f"Records with invalid RPZ types: {len(invalid_rpz_types)}")
    print(f"Records with invalid primary types: {len(invalid_primary_types)}")
    print(f"Records with invalid priority ranges: {len(invalid_priority_ranges)}")
    print(f"Records with invalid SOA values: {len(invalid_soa_values)}")
    print(f"Records with invalid prefix lengths: {len(invalid_prefix_lengths)}")
    print(f"Records with non-writable fields: {len(non_writable_field_warnings)}")
    print(f"Missing NS Groups: {len(missing_ns_groups)}")
    print(f"Missing Grid Members: {len(missing_grid_members)}")
    print(f"Failed views: {len(failed_views)}")
    if failed_views:
        print(f"Failed views: {', '.join(failed_views)}")
    
    return not validation_failed and rpz_licensed and not missing_required_fields

def check_existing_zone_auth(fqdn, view):
    """Check if a DNS Zone already exists in Infoblox."""
    try:
        response = requests.get(
            f"{BASE_URL}/zone_auth",
            params={"fqdn": fqdn, "view": view},
            auth=(INFOBLOX_USERNAME, INFOBLOX_PASSWORD),
            verify=VALIDATE_CERTS,
            timeout=HTTP_TIMEOUT
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"✗ Error checking DNS zone {fqdn}: {response.status_code}")
            return []
    except Exception as e:
        print(f"✗ Error checking DNS zone {fqdn}: {str(e)}")
        return []

def validate_forward_zone_name(fqdn):
    """Validate forward DNS zone name format."""
    if not fqdn:
        return False, "FQDN cannot be empty"
    
    # Basic FQDN validation
    if len(fqdn) > 253:
        return False, f"FQDN too long ({len(fqdn)} characters, max 253)"
    
    # Check for valid characters
    if not re.match(r'^[a-zA-Z0-9.-]+$', fqdn):
        return False, "FQDN contains invalid characters"
    
    # Check label length (each part between dots)
    labels = fqdn.split('.')
    for label in labels:
        if len(label) > 63:
            return False, f"Label '{label}' too long ({len(label)} characters, max 63)"
        if len(label) == 0:
            return False, "Empty label found in FQDN"
        if label.startswith('-') or label.endswith('-'):
            return False, f"Label '{label}' cannot start or end with hyphen"
    
    # Must have at least one dot for a valid zone
    if '.' not in fqdn:
        return False, "Zone name must contain at least one dot"
    
    return True, None

def validate_ipv4_reverse_zone(fqdn):
    """Validate IPv4 reverse zone format (CIDR notation)."""
    try:
        # Should be in format like "192.168.1.0/24"
        if '/' not in fqdn:
            return False, "IPv4 reverse zone must be in CIDR format (e.g., 192.168.1.0/24)"
        
        network_str = fqdn
        network_parts = network_str.split('/')
        
        if len(network_parts) != 2:
            return False, "Invalid CIDR format"
        
        ip_str, prefix_str = network_parts
        
        # Validate IP address
        try:
            ip = ip_address(ip_str)
            if not isinstance(ip, IPv4Address):
                return False, "Must be IPv4 address for IPv4 reverse zone"
        except ValueError as e:
            return False, f"Invalid IPv4 address: {str(e)}"
        
        # Validate prefix length
        try:
            prefix = int(prefix_str)
            if not (8 <= prefix <= 32):
                return False, f"IPv4 prefix length {prefix} must be between 8 and 32"
        except ValueError:
            return False, f"Invalid prefix length: {prefix_str}"
        
        # Check if it's a valid network address
        try:
            from ipaddress import IPv4Network
            network = IPv4Network(network_str, strict=True)
        except ValueError:
            return False, f"IP address {ip_str} is not a valid network address for /{prefix_str}"
        
        return True, None
        
    except Exception as e:
        return False, f"Error validating IPv4 reverse zone: {str(e)}"

def validate_ipv6_reverse_zone(fqdn):
    """Validate IPv6 reverse zone format (CIDR notation)."""
    try:
        # Should be in format like "2001:db8::/64"
        if '/' not in fqdn:
            return False, "IPv6 reverse zone must be in CIDR format (e.g., 2001:db8::/64)"
        
        network_str = fqdn
        network_parts = network_str.split('/')
        
        if len(network_parts) != 2:
            return False, "Invalid CIDR format"
        
        ip_str, prefix_str = network_parts
        
        # Validate IPv6 address
        try:
            ip = ip_address(ip_str)
            if not isinstance(ip, IPv6Address):
                return False, "Must be IPv6 address for IPv6 reverse zone"
        except ValueError as e:
            return False, f"Invalid IPv6 address: {str(e)}"
        
        # Validate prefix length
        try:
            prefix = int(prefix_str)
            if not (4 <= prefix <= 128):
                return False, f"IPv6 prefix length {prefix} must be between 4 and 128"
            # Recommend standard boundaries
            if prefix % 4 != 0:
                print(f"INFO: IPv6 prefix /{prefix} is not on a nibble boundary (recommended: multiples of 4)")
        except ValueError:
            return False, f"Invalid prefix length: {prefix_str}"
        
        # Check if it's a valid network address
        try:
            from ipaddress import IPv6Network
            network = IPv6Network(network_str, strict=True)
        except ValueError:
            return False, f"IPv6 address {ip_str} is not a valid network address for /{prefix_str}"
        
        return True, None
        
    except Exception as e:
        return False, f"Error validating IPv6 reverse zone: {str(e)}"

def check_parent_zone_exists(fqdn, view, zone_format):
    """Check if parent zone exists for the given zone."""
    try:
        if zone_format == "FORWARD":
            # For forward zones, check if parent domain exists
            parts = fqdn.split('.')
            if len(parts) > 1:
                parent_domain = '.'.join(parts[1:])
                
                # Check if parent zone exists
                response = requests.get(
                    f"{BASE_URL}/zone_auth",
                    params={"fqdn": parent_domain, "view": view},
                    auth=(INFOBLOX_USERNAME, INFOBLOX_PASSWORD),
                    verify=VALIDATE_CERTS,
                    timeout=HTTP_TIMEOUT
                )
                
                if response.status_code == 200:
                    zones = response.json()
                    return len(zones) > 0
        
        elif zone_format in ["IPV4", "IPV6"]:
            # For reverse zones, check if parent reverse zone exists
            # This is more complex as we need to find the parent network
            # For now, we'll skip this check as it's environment-specific
            return True
        
        return True  # Default to true if we can't determine
        
    except Exception as e:
        print(f"✗ Error checking parent zone for {fqdn}: {str(e)}")
        return True  # Default to true on error

def validate_zone_records():
    """Validate DNS Zone records from JSON file."""
    print("\n--- DNS Zone Validation ---")
    
    zone_file = "../prod_changes/cabgridmgr.amfam.com/nios_zone.json"
    
    # Read zone data from JSON file
    try:
        with open(zone_file, 'r') as file:
            zone_records = json.load(file)
            
            # If the content is not a list, convert it to a list with one item
            if not isinstance(zone_records, list):
                zone_records = [zone_records]
                
            print(f"Found {len(zone_records)} DNS zone records to validate.")
    except Exception as e:
        print(f"Error reading file {zone_file}: {str(e)}")
        return False
    
    # Now continue with validation since we have records to check
    validation_failed = False
    missing_required_fields = []
    invalid_zone_formats = []
    invalid_fqdns = []
    invalid_networks = []
    missing_ns_groups = []
    missing_grid_members = []
    failed_views = []
    missing_parent_zones = []
    conflicting_configurations = []
    
    # Valid enum values
    valid_zone_formats = ["FORWARD", "IPV4", "IPV6"]
    
    # Check for required fields and validate basic structure
    for record in zone_records:
        # Check required fields - only fqdn is truly required based on playbook
        required_fields = ["fqdn"]
        missing_fields = [field for field in required_fields if field not in record or record[field] is None]
        if missing_fields:
            missing_required_fields.append(f"{record.get('fqdn', 'Unknown zone')}: missing {', '.join(missing_fields)}")
            validation_failed = True
            continue
    
    # Display missing required fields
    for missing in missing_required_fields:
        print(f"ERROR: Missing required fields - {missing}")
    
    # Validate each zone record
    for record in zone_records:
        if "fqdn" not in record:
            continue
            
        fqdn = record["fqdn"]
        zone_format = record.get("zone_format", "FORWARD")  # Playbook defaults to FORWARD
        view = record.get("view", "default")  # Playbook defaults to default
        
        # Validate zone format
        if zone_format not in valid_zone_formats:
            invalid_zone_formats.append(f"{fqdn}: {zone_format} (valid: {', '.join(valid_zone_formats)})")
            validation_failed = True
            continue
        
        # Validate FQDN based on zone format
        if zone_format == "FORWARD":
            is_valid, error_msg = validate_forward_zone_name(fqdn)
            if not is_valid:
                invalid_fqdns.append(f"{fqdn}: {error_msg}")
                validation_failed = True
        
        elif zone_format == "IPV4":
            is_valid, error_msg = validate_ipv4_reverse_zone(fqdn)
            if not is_valid:
                invalid_networks.append(f"{fqdn}: {error_msg}")
                validation_failed = True
        
        elif zone_format == "IPV6":
            is_valid, error_msg = validate_ipv6_reverse_zone(fqdn)
            if not is_valid:
                invalid_networks.append(f"{fqdn}: {error_msg}")
                validation_failed = True
    
    # Display validation errors
    for invalid in invalid_zone_formats:
        print(f"ERROR: Invalid zone format - {invalid}")
    
    for invalid in invalid_fqdns:
        print(f"ERROR: Invalid forward zone FQDN - {invalid}")
    
    for invalid in invalid_networks:
        print(f"ERROR: Invalid reverse zone network - {invalid}")
    
    # Check for existing zones in Infoblox
    for record in zone_records:
        if "fqdn" not in record:
            continue
            
        view = record.get("view", "default")
        existing_zones = check_existing_zone_auth(record['fqdn'], view)
        if existing_zones:
            existing_zone = existing_zones[0]
            print(f"DNS Zone '{record['fqdn']}' already exists in view '{view}'")
            print(f"  Current format: {existing_zone.get('zone_format', 'N/A')}")
            print(f"  Current comment: {existing_zone.get('comment', 'N/A')}")
    
    # Check NS Group existence if specified
    for record in zone_records:
        if "ns_group" in record and record["ns_group"]:
            if not check_ns_group_exists(record["ns_group"]):
                missing_ns_groups.append(f"{record['fqdn']}: NS Group '{record['ns_group']}'")
                print(f"ERROR: NS Group '{record['ns_group']}' does not exist")
                validation_failed = True
    
    # Check Grid Member existence for primary and secondary members
    for record in zone_records:
        # Check grid primary members - special handling for playbook's format
        if "grid_primary" in record and record["grid_primary"]:
            # The playbook expects grid_primary[0].name format
            if isinstance(record["grid_primary"], list) and len(record["grid_primary"]) > 0:
                primary = record["grid_primary"][0]
                if isinstance(primary, dict) and "name" in primary:
                    if not check_grid_member_exists(primary["name"]):
                        missing_grid_members.append(f"{record['fqdn']}: Grid Primary '{primary['name']}'")
                        print(f"ERROR: Grid Primary member '{primary['name']}' does not exist")
                        validation_failed = True
                else:
                    print(f"ERROR: Invalid grid_primary format for zone '{record['fqdn']}' - expected list with dict containing 'name'")
                    validation_failed = True
            else:
                print(f"ERROR: Invalid grid_primary format for zone '{record['fqdn']}' - expected non-empty list")
                validation_failed = True
        
        # Check grid secondary members
        if "grid_secondaries" in record and record["grid_secondaries"]:
            if isinstance(record["grid_secondaries"], list):
                for secondary in record["grid_secondaries"]:
                    if isinstance(secondary, dict) and "name" in secondary:
                        if not check_grid_member_exists(secondary["name"]):
                            missing_grid_members.append(f"{record['fqdn']}: Grid Secondary '{secondary['name']}'")
                            print(f"ERROR: Grid Secondary member '{secondary['name']}' does not exist")
                            validation_failed = True
                    else:
                        print(f"WARNING: Invalid grid_secondaries format in zone '{record['fqdn']}'")
            else:
                print(f"WARNING: grid_secondaries for zone '{record['fqdn']}' should be a list")
    
    # Check for DNS view existence
    for record in zone_records:
        view = record.get("view", "default")
        
        try:
            response = requests.get(
                f"{BASE_URL}/view",
                params={"name": view},
                auth=(INFOBLOX_USERNAME, INFOBLOX_PASSWORD),
                verify=VALIDATE_CERTS,
                timeout=HTTP_TIMEOUT
            )
            
            if response.status_code == 200:
                views = response.json()
                if not views:
                    print(f"ERROR: DNS View '{view}' does not exist")
                    validation_failed = True
                    failed_views.append(view)
            else:
                print(f"✗ Error checking view {view}: {response.status_code}")
                validation_failed = True
        except Exception as e:
            print(f"✗ Error checking view {view}: {str(e)}")
            validation_failed = True
    
    # Check parent zone existence (informational)
    for record in zone_records:
        if "fqdn" not in record:
            continue
            
        view = record.get("view", "default")
        zone_format = record.get("zone_format", "FORWARD")
        if not check_parent_zone_exists(record["fqdn"], view, zone_format):
            missing_parent_zones.append(f"{record['fqdn']} in view {view}")
            print(f"INFO: Parent zone for '{record['fqdn']}' may not exist - this could be intentional for top-level zones")
    
    # Validate logical consistency
    for record in zone_records:
        zone_name = record.get('fqdn', 'Unknown')
        
        # Check for conflicting primary/secondary configuration
        has_grid_primary = record.get('grid_primary', [])
        has_ns_group = record.get('ns_group')
        
        if has_grid_primary and has_ns_group:
            print(f"WARNING: Zone '{zone_name}' has both grid_primary and ns_group defined - ns_group may take precedence")
        
        if not has_grid_primary and not has_ns_group:
            print(f"WARNING: Zone '{zone_name}' has no primary servers defined (neither grid_primary nor ns_group)")
        
        # Check for reverse zone naming consistency
        zone_format = record.get("zone_format", "FORWARD")
        if zone_format == "IPV4" and "/" not in zone_name:
            print(f"INFO: IPv4 reverse zone '{zone_name}' is using in-addr.arpa format instead of CIDR")
        
        if zone_format == "IPV6" and "/" not in zone_name:
            print(f"INFO: IPv6 reverse zone '{zone_name}' is using ip6.arpa format instead of CIDR")
        
        # Check for forward zone with reverse zone characteristics
        if zone_format == "FORWARD" and ("/" in zone_name or "arpa" in zone_name.lower()):
            print(f"WARNING: Forward zone '{zone_name}' contains reverse zone characteristics")
    
    # Validate optional fields
    for record in zone_records:
        # Check comment field (defaults to empty string in playbook)
        if "comment" in record and record["comment"] is not None:
            if not isinstance(record["comment"], str):
                print(f"WARNING: Comment for zone {record['fqdn']} should be a string")
        
        # Check extattrs field (defaults to empty dict in playbook)
        if "extattrs" in record and record["extattrs"] is not None:
            if not isinstance(record["extattrs"], dict):
                print(f"WARNING: Extended attributes for zone {record['fqdn']} should be a dictionary")
    
    # Check for duplicate FQDN/View combinations
    fqdn_view_pairs = []
    duplicates = []
    seen = set()
    
    for record in zone_records:
        if "fqdn" not in record:
            continue
        fqdn = record["fqdn"]
        view = record.get("view", "default")
        
        if (fqdn, view) in seen:
            duplicates.append(f"{fqdn} in view {view}")
        seen.add((fqdn, view))
        fqdn_view_pairs.append((fqdn, view))
    
    if duplicates:
        print(f"ERROR: Duplicate FQDN/View combinations found: {', '.join(duplicates)}")
        validation_failed = True
    
    # Display validation summary
    print("\nDNS Zone Validation Summary:")
    print(f"Total records checked: {len(zone_records)}")
    print(f"Records with missing required fields: {len(missing_required_fields)}")
    print(f"Records with invalid zone formats: {len(invalid_zone_formats)}")
    print(f"Records with invalid FQDNs: {len(invalid_fqdns)}")
    print(f"Records with invalid networks: {len(invalid_networks)}")
    print(f"Missing NS Groups: {len(missing_ns_groups)}")
    print(f"Missing Grid Members: {len(missing_grid_members)}")
    print(f"Failed views: {len(failed_views)}")
    print(f"Zones with missing parents: {len(missing_parent_zones)}")
    print(f"Duplicate FQDN/View combinations: {len(duplicates)}")
    if failed_views:
        print(f"Failed views: {', '.join(failed_views)}")
    
    return not validation_failed and not missing_required_fields

def check_existing_network(network, network_view):
    """Check if a network already exists in Infoblox."""
    try:
        response = requests.get(
            f"{BASE_URL}/network",
            params={"network": network, "network_view": network_view},
            auth=(INFOBLOX_USERNAME, INFOBLOX_PASSWORD),
            verify=VALIDATE_CERTS,
            timeout=HTTP_TIMEOUT
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"✗ Error checking network {network}: {response.status_code}")
            return []
    except Exception as e:
        print(f"✗ Error checking network {network}: {str(e)}")
        return []

def check_network_view_exists(network_view):
    """Check if a network view exists in Infoblox."""
    try:
        response = requests.get(
            f"{BASE_URL}/networkview",
            params={"name": network_view},
            auth=(INFOBLOX_USERNAME, INFOBLOX_PASSWORD),
            verify=VALIDATE_CERTS,
            timeout=HTTP_TIMEOUT
        )
        
        if response.status_code == 200:
            return len(response.json()) > 0
        else:
            print(f"✗ Error checking network view {network_view}: {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Error checking network view {network_view}: {str(e)}")
        return False

def check_vlan_exists(vlan_ref):
    """Check if a VLAN exists in Infoblox."""
    try:
        # Extract VLAN reference and query directly
        response = requests.get(
            f"{BASE_URL}/{vlan_ref}",
            auth=(INFOBLOX_USERNAME, INFOBLOX_PASSWORD),
            verify=VALIDATE_CERTS,
            timeout=HTTP_TIMEOUT
        )
        
        if response.status_code == 200:
            return True
        else:
            return False
    except Exception as e:
        print(f"✗ Error checking VLAN {vlan_ref}: {str(e)}")
        return False

def validate_network_cidr(network):
    """Validate network CIDR format."""
    try:
        if '/' not in network:
            return False, "Network must be in CIDR format (e.g., 192.168.1.0/24)"
        
        # Parse and validate the network
        from ipaddress import IPv4Network, IPv6Network, AddressValueError
        
        try:
            # Try IPv4 first
            net = IPv4Network(network, strict=True)
            return True, None
        except AddressValueError:
            try:
                # Try IPv6
                net = IPv6Network(network, strict=True)
                return True, None
            except AddressValueError as e:
                return False, f"Invalid network format: {str(e)}"
    
    except Exception as e:
        return False, f"Error validating network: {str(e)}"

def validate_dhcp_option(option):
    """Validate DHCP option structure and values."""
    errors = []
    
    # Check required fields
    required_fields = ["name", "num", "use_option", "vendor_class"]
    for field in required_fields:
        if field not in option:
            errors.append(f"Missing required field: {field}")
    
    if errors:
        return errors
    
    # Validate option number
    try:
        option_num = int(option["num"])
        if not (1 <= option_num <= 254):
            errors.append(f"Option number {option_num} must be between 1 and 254")
    except (ValueError, TypeError):
        errors.append(f"Option number '{option['num']}' must be a valid integer")
    
    # Validate use_option is boolean
    if not isinstance(option.get("use_option"), bool):
        errors.append(f"use_option must be boolean, got: {type(option.get('use_option'))}")
    
    # Validate vendor_class
    valid_vendor_classes = ["DHCP", "DHCPv6"]
    if option.get("vendor_class") not in valid_vendor_classes:
        errors.append(f"vendor_class '{option.get('vendor_class')}' must be one of: {', '.join(valid_vendor_classes)}")
    
    # Validate specific option values based on option name
    option_name = option.get("name", "")
    option_value = option.get("value", "")
    
    if option_name == "domain-name-servers" or option_name == "name-servers":
        # Should be valid IP addresses (comma-separated)
        if option_value:
            ips = [ip.strip() for ip in str(option_value).split(',')]
            for ip in ips:
                try:
                    ip_address(ip)
                except ValueError:
                    errors.append(f"Invalid IP address in {option_name}: {ip}")
    
    elif option_name == "routers":
        # Should be a valid IP address
        if option_value:
            try:
                ip_address(str(option_value))
            except ValueError:
                errors.append(f"Invalid router IP address: {option_value}")
    
    elif option_name == "broadcast-address":
        # Should be a valid IP address
        if option_value:
            try:
                ip_address(str(option_value))
            except ValueError:
                errors.append(f"Invalid broadcast address: {option_value}")
    
    elif option_name == "dhcp-lease-time":
        # Should be a valid integer (seconds)
        try:
            lease_time = int(option_value)
            if lease_time <= 0:
                errors.append(f"DHCP lease time must be positive: {lease_time}")
            elif lease_time > 2147483647:  # Max 32-bit signed integer
                errors.append(f"DHCP lease time too large: {lease_time}")
        except (ValueError, TypeError):
            errors.append(f"DHCP lease time must be a valid integer: {option_value}")
    
    elif option_name == "domain-name":
        # Should be a valid domain name
        if option_value and not re.match(r'^[a-zA-Z0-9.-]+$', str(option_value)):
            errors.append(f"Invalid domain name format: {option_value}")
    
    return errors

def validate_network_consistency(network, options):
    """Validate network and DHCP options for logical consistency."""
    errors = []
    warnings = []
    
    try:
        from ipaddress import IPv4Network
        net = IPv4Network(network)
        
        # Extract relevant options
        router_option = None
        broadcast_option = None
        
        for option in options:
            if option.get("name") == "routers":
                router_option = option.get("value")
            elif option.get("name") == "broadcast-address":
                broadcast_option = option.get("value")
        
        # Validate router is within network
        if router_option:
            try:
                router_ip = ip_address(str(router_option))
                if router_ip not in net:
                    errors.append(f"Router IP {router_ip} is not within network {network}")
                elif router_ip == net.network_address:
                    warnings.append(f"Router IP {router_ip} is the network address")
                elif router_ip == net.broadcast_address:
                    warnings.append(f"Router IP {router_ip} is the broadcast address")
            except ValueError:
                pass  # Already validated in validate_dhcp_option
        
        # Validate broadcast address matches network
        if broadcast_option:
            try:
                broadcast_ip = ip_address(str(broadcast_option))
                if broadcast_ip != net.broadcast_address:
                    errors.append(f"Broadcast address {broadcast_ip} doesn't match network broadcast {net.broadcast_address}")
            except ValueError:
                pass  # Already validated in validate_dhcp_option
        
        # Check for common gateway patterns
        if router_option:
            try:
                router_ip = ip_address(str(router_option))
                # Common patterns: .1, .254, etc.
                last_octet = int(str(router_ip).split('.')[-1])
                if last_octet not in [1, 254] and net.prefixlen <= 24:
                    warnings.append(f"Router IP {router_ip} uses uncommon gateway pattern (not .1 or .254)")
            except:
                pass
    
    except Exception:
        # If it's not IPv4 or other error, skip consistency checks
        pass
    
    return errors, warnings

def validate_networks():
    """Validate network records from JSON file."""
    print("\n--- Network Validation ---")
    
    network_file = "../prod_changes/cabgridmgr.amfam.com/network.json"
    
    # Read network data from JSON file
    try:
        with open(network_file, 'r') as file:
            networks = json.load(file)
            
            # If the content is not a list, convert it to a list with one item
            if not isinstance(networks, list):
                networks = [networks]
                
            print(f"Found {len(networks)} networks to validate.")
    except Exception as e:
        print(f"Error reading file {network_file}: {str(e)}")
        return False
    
    # Define supported DHCP options based on playbook
    supported_dhcp_options = [
        "subnet-mask", "time-offset", "routers", "time-servers", "name-servers",
        "domain-name-servers", "log-servers", "cookie-servers", "lpr-servers",
        "impress-servers", "resource-location-servers", "boot-size", "merit-dump",
        "domain-name", "swap-server", "root-path", "extensions-path", "ip-forwarding",
        "non-local-source-routing", "policy-filter", "max-dgram-reassembly",
        "default-ip-ttl", "path-mtu-aging-timeout", "path-mtu-plateau-table",
        "interface-mtu", "all-subnets-local", "broadcast-address", "perform-mask-discovery",
        "mask-supplier", "router-discovery", "router-solicitation-address",
        "static-routes", "trailer-encapsulation", "arp-cache-timeout",
        "ieee802-3-encapsulation", "default-tcp-ttl", "tcp-keepalive-interval",
        "tcp-keepalive-garbage", "nis-domain", "nis-servers", "ntp-servers",
        "vendor-encapsulated-options", "netbios-name-servers", "netbios-dd-server",
        "netbios-node-type", "netbios-scope", "font-servers", "x-display-manager",
        "dhcp-option-overload", "dhcp-server-identifier", "dhcp-message",
        "dhcp-max-message-size", "vendor-class-identifier", "nwip-domain-name",
        "nisplus-domain-name", "nisplus-severs", "tftp-server-name", "boot-file-name",
        "mobile-ip-home-agent", "smtp-server", "pop-server", "nntp-server",
        "www.-server", "finger-server", "irc-server", "streettalk-server",
        "streettalk-directory-assistance-server", "user-class", "slp-directory-agent",
        "slp-service-scope", "nds-server", "nds-tree-name", "nds-context",
        "bcms-controller-names", "bcms-controller-address", "client-system",
        "client-ndi", "uuid-guid", "uap-servers", "geoconf-civic", "pcode", "tcode",
        "netinfo-server-address", "netinfo-server-tag", "v4-captive-portal+",
        "auto-config", "name-server-search", "subnet-selection", "domain-search",
        "vivco-suboptions", "vivso-suboptions", "pana-agent", "v4-lost",
        "capwap-ac-v4", "sip-ua-cs-domains", "rdnss-selection", "v4-portparams",
        "v4-captive-portal-old+", "option-6rd", "v4-access-domain", "dhcp-lease-time"
    ]
    
    # Now continue with validation
    validation_failed = False
    missing_required_fields = []
    invalid_networks = []
    missing_network_views = []
    overlapping_networks = []
    missing_grid_members = []
    unsupported_dhcp_options = []
    excluded_dhcp_options = []
    
    # Check for required fields based on playbook
    for record in networks:
        # Check required fields that the playbook uses
        required_fields = ["network", "members"]
        missing_fields = [field for field in required_fields if field not in record or record[field] is None]
        if missing_fields:
            missing_required_fields.append(f"{record.get('network', 'Unknown network')}: missing {', '.join(missing_fields)}")
            validation_failed = True
            continue
    
    # Display missing required fields
    for missing in missing_required_fields:
        print(f"ERROR: Missing required fields - {missing}")
    
    # Validate network format (CIDR notation)
    for record in networks:
        if "network" not in record:
            continue
            
        network = record["network"]
        try:
            # Validate CIDR format
            if '/' not in network:
                invalid_networks.append(f"{network}: Missing CIDR prefix")
                validation_failed = True
                continue
            
            network_parts = network.split('/')
            if len(network_parts) != 2:
                invalid_networks.append(f"{network}: Invalid CIDR format")
                validation_failed = True
                continue
            
            ip_str, prefix_str = network_parts
            
            # Validate IP address
            if not validate_ipv4_format(ip_str):
                invalid_networks.append(f"{network}: Invalid IP address")
                validation_failed = True
                continue
            
            # Validate prefix length
            try:
                prefix = int(prefix_str)
                if not (0 <= prefix <= 32):
                    invalid_networks.append(f"{network}: Prefix length {prefix} must be between 0 and 32")
                    validation_failed = True
            except ValueError:
                invalid_networks.append(f"{network}: Invalid prefix length '{prefix_str}'")
                validation_failed = True
            
            # Check if it's a valid network address
            try:
                from ipaddress import IPv4Network
                IPv4Network(network, strict=True)
            except ValueError as e:
                invalid_networks.append(f"{network}: {str(e)}")
                validation_failed = True
                
        except Exception as e:
            invalid_networks.append(f"{network}: {str(e)}")
            validation_failed = True
    
    # Display invalid networks
    for invalid in invalid_networks:
        print(f"ERROR: Invalid network - {invalid}")
    
    # Check network view existence
    for record in networks:
        network_view = record.get("network_view", "default")  # Playbook uses default('default')
        
        if not check_network_view_exists(network_view):
            missing_network_views.append(f"{record['network']}: Network view '{network_view}'")
            print(f"ERROR: Network view '{network_view}' does not exist")
            validation_failed = True
    
    # Validate members field
    for record in networks:
        if "members" not in record:
            continue
            
        if not isinstance(record["members"], list):
            print(f"ERROR: Members for network {record['network']} should be a list")
            validation_failed = True
            continue
        
        # Check if members list is empty
        if len(record["members"]) == 0:
            print(f"ERROR: Network {record['network']} has empty members list")
            validation_failed = True
            continue
        
        for i, member in enumerate(record["members"]):
            if not isinstance(member, dict):
                print(f"ERROR: Member in network {record['network']} should be a dictionary")
                validation_failed = True
                continue
            
            # Based on the JSON data, members have a "name" field
            if "name" in member:
                member_name = member["name"]
                
                # Check if the grid member exists - THIS IS CRITICAL
                if not check_grid_member_exists(member_name):
                    missing_grid_members.append(f"{record['network']}: Member '{member_name}'")
                    print(f"ERROR: Grid member '{member_name}' does not exist in Infoblox")
                    validation_failed = True
                else:
                    print(f"INFO: Network {record['network']} has valid member: {member_name}")
            elif "_struct" in member:
                # Handle structured members if present
                if member["_struct"] == "dhcpmember":
                    if "ipv4addr" not in member:
                        print(f"ERROR: DHCP member in network {record['network']} missing 'ipv4addr' field")
                        validation_failed = True
                    elif not validate_ipv4_format(member["ipv4addr"]):
                        print(f"ERROR: Invalid IP address {member['ipv4addr']} in DHCP member for network {record['network']}")
                        validation_failed = True
                else:
                    print(f"INFO: Member in network {record['network']} has structure type: {member['_struct']}")
            elif "ipv4addr" in member:
                # IP-based member without _struct
                if not validate_ipv4_format(member["ipv4addr"]):
                    print(f"ERROR: Invalid IP address {member['ipv4addr']} in member for network {record['network']}")
                    validation_failed = True
                else:
                    print(f"INFO: Network {record['network']} has IP-based member: {member['ipv4addr']}")
            else:
                # Member must have some identifying field
                print(f"ERROR: Member {i+1} in network {record['network']} missing required fields (name, _struct, or ipv4addr)")
                print(f"       Member contains fields: {', '.join(member.keys())}")
                validation_failed = True
    
    # Validate DHCP options if present
    for record in networks:
        if "options" in record and record["options"]:
            if not isinstance(record["options"], list):
                print(f"ERROR: DHCP options for {record['network']} should be a list")
                validation_failed = True
                continue
            
            for option in record["options"]:
                if not isinstance(option, dict):
                    print(f"ERROR: DHCP option in {record['network']} should be a dictionary")
                    validation_failed = True
                    continue
                
                if "name" not in option:
                    print(f"ERROR: DHCP option in {record['network']} missing 'name' field")
                    validation_failed = True
                    continue
                
                # Check if option is root-path (excluded by playbook)
                if option["name"] == "root-path":
                    excluded_dhcp_options.append(f"{record['network']}: root-path")
                    print(f"INFO: DHCP option 'root-path' for {record['network']} will be excluded by the playbook")
                    continue
                
                # Check if option is in supported list
                if option["name"] not in supported_dhcp_options:
                    unsupported_dhcp_options.append(f"{record['network']}: {option['name']}")
                    print(f"WARNING: DHCP option '{option['name']}' for {record['network']} is not in supported options list")
    
    # Check for existing networks
    for record in networks:
        if "network" not in record:
            continue
            
        network_view = record.get("network_view", "default")
        existing_networks = check_existing_network(record["network"], network_view)
        if existing_networks:
            print(f"Network '{record['network']}' already exists in view '{network_view}'")
            if "comment" in existing_networks[0]:
                print(f"  Current comment: {existing_networks[0]['comment']}")
    
    # Check for overlapping networks within the same view
    from ipaddress import IPv4Network, AddressValueError
    networks_by_view = {}
    
    for record in networks:
        if "network" not in record:
            continue
            
        network_view = record.get("network_view", "default")
        if network_view not in networks_by_view:
            networks_by_view[network_view] = []
        
        try:
            net = IPv4Network(record["network"])
            networks_by_view[network_view].append((record["network"], net))
        except (ValueError, AddressValueError):
            pass  # Already validated above
    
    # Check for overlaps within each view
    for view, view_networks in networks_by_view.items():
        for i, (net1_str, net1) in enumerate(view_networks):
            for j, (net2_str, net2) in enumerate(view_networks[i+1:], i+1):
                if net1.overlaps(net2):
                    overlapping_networks.append(f"{net1_str} and {net2_str} in view {view}")
                    print(f"WARNING: Networks {net1_str} and {net2_str} overlap in view {view}")
    
    # Validate optional fields
    for record in networks:
        # Check comment field
        if "comment" in record and record["comment"] is not None:
            if not isinstance(record["comment"], str):
                print(f"WARNING: Comment for network {record['network']} should be a string")
        
        # Check extattrs field
        if "extattrs" in record and record["extattrs"] is not None:
            if not isinstance(record["extattrs"], dict):
                print(f"WARNING: Extended attributes for network {record['network']} should be a dictionary")
    
    # Display validation summary
    print("\nNetwork Validation Summary:")
    print(f"Total networks checked: {len(networks)}")
    print(f"Networks with missing required fields: {len(missing_required_fields)}")
    print(f"Invalid network formats: {len(invalid_networks)}")
    print(f"Missing network views: {len(set([nv.split(':')[0] for nv in missing_network_views]))}")
    print(f"Missing grid members: {len(missing_grid_members)}")
    print(f"Overlapping networks: {len(overlapping_networks)}")
    print(f"Networks with unsupported DHCP options: {len(set([opt.split(':')[0] for opt in unsupported_dhcp_options]))}")
    print(f"Networks with excluded DHCP options (root-path): {len(excluded_dhcp_options)}")
    
    return not validation_failed and not missing_required_fields and not missing_grid_members

def check_existing_network_view(name):
    """Check if a network view already exists in Infoblox."""
    try:
        response = requests.get(
            f"{BASE_URL}/networkview",
            params={"name": name},
            auth=(INFOBLOX_USERNAME, INFOBLOX_PASSWORD),
            verify=VALIDATE_CERTS,
            timeout=HTTP_TIMEOUT
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"✗ Error checking network view {name}: {response.status_code}")
            return []
    except Exception as e:
        print(f"✗ Error checking network view {name}: {str(e)}")
        return []

def validate_network_view_name(name):
    """Validate network view name format."""
    if not name:
        return False, "Network view name cannot be empty"
    
    # Check length
    if len(name) > 256:
        return False, f"Network view name too long ({len(name)} characters, max 256)"
    
    # Check for valid characters (alphanumeric, underscore, hyphen, period)
    if not re.match(r'^[a-zA-Z0-9._-]+$', name):
        return False, "Network view name contains invalid characters (only alphanumeric, underscore, hyphen, period allowed)"
    
    # Check for reserved names
    reserved_names = ['default', 'internal', 'external', 'system']
    if name.lower() in reserved_names:
        return False, f"Network view name '{name}' is reserved"
    
    # Cannot start with underscore or hyphen
    if name.startswith('_') or name.startswith('-'):
        return False, "Network view name cannot start with underscore or hyphen"
    
    return True, None

def check_associated_networks(network_view_name):
    """Check if there are existing networks in this network view."""
    try:
        response = requests.get(
            f"{BASE_URL}/network",
            params={"network_view": network_view_name, "_max_results": 1},
            auth=(INFOBLOX_USERNAME, INFOBLOX_PASSWORD),
            verify=VALIDATE_CERTS,
            timeout=HTTP_TIMEOUT
        )
        
        if response.status_code == 200:
            networks = response.json()
            return len(networks) > 0, len(networks)
        else:
            print(f"✗ Error checking networks in view {network_view_name}: {response.status_code}")
            return False, 0
    except Exception as e:
        print(f"✗ Error checking networks in view {network_view_name}: {str(e)}")
        return False, 0

def check_associated_dns_views(network_view_name):
    """Check if there are DNS views associated with this network view."""
    try:
        response = requests.get(
            f"{BASE_URL}/view",
            params={"network_view": network_view_name},
            auth=(INFOBLOX_USERNAME, INFOBLOX_PASSWORD),
            verify=VALIDATE_CERTS,
            timeout=HTTP_TIMEOUT
        )
        
        if response.status_code == 200:
            dns_views = response.json()
            return len(dns_views) > 0, [view.get('name') for view in dns_views]
        else:
            print(f"✗ Error checking DNS views for network view {network_view_name}: {response.status_code}")
            return False, []
    except Exception as e:
        print(f"✗ Error checking DNS views for network view {network_view_name}: {str(e)}")
        return False, []

def validate_network_view_records():
    """Validate Network View records from JSON file."""
    print("\n--- Network View Validation ---")
    
    network_view_file = "playbooks/add/cabgridmgr.amfam.com/network_view.json"
    
    # Read network view data from JSON file
    try:
        with open(network_view_file, 'r') as file:
            network_view_records = json.load(file)
            
            # If the content is not a list, convert it to a list with one item
            if not isinstance(network_view_records, list):
                network_view_records = [network_view_records]
                
            print(f"Found {len(network_view_records)} network view records to validate.")
    except Exception as e:
        print(f"Error reading file {network_view_file}: {str(e)}")
        return False
    
    # Now continue with validation since we have records to check
    validation_failed = False
    missing_required_fields = []
    invalid_names = []
    existing_network_views = []
    conflicting_views = []
    
    # Check for required fields and validate basic structure
    for record in network_view_records:
        # Check required fields
        if not all(key in record for key in ["name"]):
            missing_fields = [field for field in ["name"] if field not in record]
            missing_required_fields.append(f"{record.get('name', 'Unknown network view')}: missing {', '.join(missing_fields)}")
            validation_failed = True
            continue
        
        # Validate network view name format
        name = record["name"]
        is_valid, error_msg = validate_network_view_name(name)
        if not is_valid:
            invalid_names.append(f"{name}: {error_msg}")
            validation_failed = True
    
    # Display validation errors
    for missing in missing_required_fields:
        print(f"ERROR: Missing required fields - {missing}")
    
    for invalid in invalid_names:
        print(f"ERROR: Invalid network view name - {invalid}")
    
    # Check for existing network views in Infoblox
    for record in network_view_records:
        if "name" not in record:
            continue
            
        existing_views = check_existing_network_view(record['name'])
        if existing_views:
            existing_view = existing_views[0]
            existing_network_views.append(record['name'])
            print(f"Network view '{record['name']}' already exists in Infoblox")
            
            # Check if there are associated networks
            has_networks, network_count = check_associated_networks(record['name'])
            if has_networks:
                print(f"  Network view '{record['name']}' has {network_count}+ associated networks")
            
            # Check if there are associated DNS views
            has_dns_views, dns_view_names = check_associated_dns_views(record['name'])
            if has_dns_views:
                print(f"  Network view '{record['name']}' has associated DNS views: {', '.join(dns_view_names)}")
            
            # Compare extensible attributes if specified
            if 'extattrs' in record and record['extattrs']:
                existing_extattrs = existing_view.get('extattrs', {})
                for key, expected_value in record['extattrs'].items():
                    actual_value = existing_extattrs.get(key, {}).get('value')
                    if actual_value != expected_value:
                        print(f"  Network view '{record['name']}' extensible attribute '{key}' will be updated: '{actual_value}' -> '{expected_value}'")
    
    # Check for duplicate network view names within the JSON
    view_names = [record.get('name') for record in network_view_records if 'name' in record]
    duplicates = []
    seen = set()
    for name in view_names:
        if name in seen:
            duplicates.append(name)
        seen.add(name)
    
    if duplicates:
        print(f"ERROR: Duplicate network view names found in JSON: {', '.join(duplicates)}")
        validation_failed = True
        conflicting_views.extend(duplicates)
    
    # Check for conflicts with default network view
    for record in network_view_records:
        if record.get('name') == 'default':
            print(f"WARNING: Attempting to create/modify 'default' network view - this is the system default")
    
    # Validate logical consistency
    for record in network_view_records:
        name = record.get('name', 'Unknown')
        
        # Check if comment is provided for documentation
        if 'comment' not in record or not record.get('comment'):
            print(f"INFO: Network view '{name}' has no comment - consider adding documentation")
        
        # Check extensible attributes for common patterns
        if 'extattrs' in record and record['extattrs']:
            extattrs = record['extattrs']
            
            # Look for common organizational attributes
            org_attrs = ['Department', 'Owner', 'Environment', 'Location', 'Cost Center']
            has_org_attr = any(attr in extattrs for attr in org_attrs)
            if not has_org_attr:
                print(f"INFO: Network view '{name}' has no organizational extensible attributes")
            
            # Validate extensible attribute values
            for attr_name, attr_value in extattrs.items():
                if not attr_value or (isinstance(attr_value, str) and not attr_value.strip()):
                    print(f"WARNING: Network view '{name}' has empty extensible attribute '{attr_name}'")
        
        # Check for naming convention consistency
        if len(name) < 3:
            print(f"WARNING: Network view '{name}' has a very short name - consider a more descriptive name")
        
        # Check for common naming patterns
        if name.lower().startswith('test') or name.lower().startswith('dev'):
            print(f"INFO: Network view '{name}' appears to be for testing/development")
        elif name.lower().startswith('prod'):
            print(f"INFO: Network view '{name}' appears to be for production")
    
    # Check for network view dependencies
    for record in network_view_records:
        name = record.get('name')
        if not name:
            continue
        
        # If the network view already exists, check for dependencies
        existing_views = check_existing_network_view(name)
        if existing_views:
            # Check if there are networks that would be affected
            has_networks, network_count = check_associated_networks(name)
            if has_networks:
                print(f"INFO: Network view '{name}' modification may affect {network_count}+ existing networks")
            
            # Check if there are DNS views that would be affected
            has_dns_views, dns_view_names = check_associated_dns_views(name)
            if has_dns_views:
                print(f"INFO: Network view '{name}' modification may affect DNS views: {', '.join(dns_view_names)}")
    
    # Display validation summary
    print("\nNetwork View Validation Summary:")
    print(f"Total records checked: {len(network_view_records)}")
    print(f"Records with missing required fields: {len(missing_required_fields)}")
    print(f"Records with invalid names: {len(invalid_names)}")
    print(f"Existing network views: {len(existing_network_views)}")
    print(f"Conflicting views: {len(conflicting_views)}")
    
    if existing_network_views:
        print(f"Existing network views: {', '.join(existing_network_views)}")
    if conflicting_views:
        print(f"Conflicting views: {', '.join(conflicting_views)}")
    
    return not validation_failed

def check_existing_dhcp_failover(name):
    """Check if a DHCP failover association already exists in Infoblox."""
    try:
        response = requests.get(
            f"{BASE_URL}/dhcpfailover",
            params={"name": name},
            auth=(INFOBLOX_USERNAME, INFOBLOX_PASSWORD),
            verify=VALIDATE_CERTS,
            timeout=HTTP_TIMEOUT
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"✗ Error checking DHCP failover {name}: {response.status_code}")
            return []
    except Exception as e:
        print(f"✗ Error checking DHCP failover {name}: {str(e)}")
        return []

def check_member_association_exists(member_association):
    """Check if a member association exists for DHCP failover."""
    try:
        # Check if the member exists
        member_name = member_association.get("primary") or member_association.get("secondary")
        if member_name:
            response = requests.get(
                f"{BASE_URL}/member",
                params={"host_name": member_name},
                auth=(INFOBLOX_USERNAME, INFOBLOX_PASSWORD),
                verify=VALIDATE_CERTS,
                timeout=HTTP_TIMEOUT
            )
            
            if response.status_code == 200:
                members = response.json()
                return len(members) > 0
            else:
                return False
        return False
    except Exception as e:
        print(f"✗ Error checking member association: {str(e)}")
        return False

def validate_failover_range(failover_range):
    """Validate DHCP failover range configuration."""
    errors = []
    
    # Check required fields
    required_fields = ["start_address", "end_address"]
    for field in required_fields:
        if field not in failover_range:
            errors.append(f"Missing required field: {field}")
    
    if errors:
        return errors
    
    # Validate IP addresses
    start_addr = failover_range.get("start_address")
    end_addr = failover_range.get("end_address")
    
    # Validate start address
    if not validate_ipv4_format(start_addr):
        errors.append(f"Invalid start address format: {start_addr}")
    
    # Validate end address
    if not validate_ipv4_format(end_addr):
        errors.append(f"Invalid end address format: {end_addr}")
    
    # Check if start is before end
    if not errors:  # Only check if both IPs are valid
        try:
            start_ip = ip_address(start_addr)
            end_ip = ip_address(end_addr)
            
            if start_ip > end_ip:
                errors.append(f"Start address {start_addr} must be less than or equal to end address {end_addr}")
        except ValueError:
            pass  # Already handled in format validation
    
    # Validate failover_association if present
    if "failover_association" in failover_range and not failover_range.get("failover_association"):
        errors.append("Failover association cannot be empty")
    
    return errors

def validate_dhcp_failover_association_type(association_type):
    """Validate DHCP failover association type."""
    valid_types = ["ACTIVE_ACTIVE", "ACTIVE_PASSIVE", "LOAD_BALANCED"]
    if association_type not in valid_types:
        return False, f"Invalid association type. Must be one of: {', '.join(valid_types)}"
    return True, None

def validate_dhcp_failover_mode(mode):
    """Validate DHCP failover mode."""
    valid_modes = ["FAILOVER", "LOAD_BALANCE"]
    if mode not in valid_modes:
        return False, f"Invalid failover mode. Must be one of: {', '.join(valid_modes)}"
    return True, None

def validate_dhcp_failover_records():
    """Validate DHCP Failover records from JSON file."""
    print("\n--- DHCP Failover Validation ---")
    
    dhcp_failover_file = "playbooks/add/cabgridmgr.amfam.com/dhcp_failover.json"
    
    # Read DHCP failover data from JSON file
    try:
        with open(dhcp_failover_file, 'r') as file:
            dhcp_failover_data = json.load(file)
            
            # If the content is not a dictionary, there's an issue
            if not isinstance(dhcp_failover_data, dict):
                print(f"ERROR: DHCP failover data must be a dictionary, got {type(dhcp_failover_data)}")
                return False
            
            # Check if it's empty
            if not dhcp_failover_data:
                print(f"DHCP failover file exists but contains no data. Skipping validation.")
                return True
                
            print(f"Found DHCP failover configuration to validate.")
    except Exception as e:
        print(f"Error reading file {dhcp_failover_file}: {str(e)}")
        return False
    
    # Now continue with validation
    validation_failed = False
    missing_required_fields = []
    invalid_association_types = []
    invalid_modes = []
    invalid_ports = []
    invalid_member_associations = []
    missing_members = []
    invalid_ranges = []
    invalid_timers = []
    
    # Check for required fields
    required_fields = ["name", "primary", "secondary"]
    for field in required_fields:
        if field not in dhcp_failover_data:
            missing_required_fields.append(field)
            validation_failed = True
    
    # Display missing required fields
    if missing_required_fields:
        print(f"ERROR: Missing required fields: {', '.join(missing_required_fields)}")
    
    # Validate association type if present
    if "association_type" in dhcp_failover_data:
        is_valid, error_msg = validate_dhcp_failover_association_type(dhcp_failover_data["association_type"])
        if not is_valid:
            invalid_association_types.append(error_msg)
            validation_failed = True
            print(f"ERROR: {error_msg}")
    
    # Validate mode if present
    if "mode" in dhcp_failover_data:
        is_valid, error_msg = validate_dhcp_failover_mode(dhcp_failover_data["mode"])
        if not is_valid:
            invalid_modes.append(error_msg)
            validation_failed = True
            print(f"ERROR: {error_msg}")
    
    # Validate port numbers
    port_fields = ["primary_server_port", "secondary_server_port"]
    for port_field in port_fields:
        if port_field in dhcp_failover_data:
            try:
                port = int(dhcp_failover_data[port_field])
                if not (1 <= port <= 65535):
                    invalid_ports.append(f"{port_field}: {port} (must be 1-65535)")
                    validation_failed = True
                    print(f"ERROR: Invalid port - {port_field}: {port} (must be 1-65535)")
            except (ValueError, TypeError):
                invalid_ports.append(f"{port_field}: '{dhcp_failover_data[port_field]}' is not a valid integer")
                validation_failed = True
                print(f"ERROR: Invalid port - {port_field}: '{dhcp_failover_data[port_field]}' is not a valid integer")
    
    # Validate timer values
    timer_fields = {
        "max_client_lead_time": (0, 2147483647),
        "max_load_balance_delay": (0, 2147483647),
        "max_response_delay": (0, 2147483647),
        "max_unacked_updates": (0, 2147483647),
        "mclt": (0, 2147483647),
        "load_balance_split": (0, 256)  # Usually 0-256 for percentage * 256/100
    }
    
    for timer_field, (min_val, max_val) in timer_fields.items():
        if timer_field in dhcp_failover_data:
            try:
                value = int(dhcp_failover_data[timer_field])
                if not (min_val <= value <= max_val):
                    invalid_timers.append(f"{timer_field}: {value} (must be {min_val}-{max_val})")
                    validation_failed = True
                    print(f"ERROR: Invalid timer value - {timer_field}: {value} (must be {min_val}-{max_val})")
            except (ValueError, TypeError):
                invalid_timers.append(f"{timer_field}: '{dhcp_failover_data[timer_field]}' is not a valid integer")
                validation_failed = True
                print(f"ERROR: Invalid timer value - {timer_field}: '{dhcp_failover_data[timer_field]}' is not a valid integer")
    
    # Check if the failover association already exists
    if "name" in dhcp_failover_data:
        existing_failovers = check_existing_dhcp_failover(dhcp_failover_data["name"])
        if existing_failovers:
            existing = existing_failovers[0]
            print(f"DHCP Failover association '{dhcp_failover_data['name']}' already exists")
            print(f"  Current primary: {existing.get('primary', 'N/A')}")
            print(f"  Current secondary: {existing.get('secondary', 'N/A')}")
            
            # Check if trying to change primary/secondary (which might not be allowed)
            if dhcp_failover_data.get("primary") != existing.get("primary") or \
               dhcp_failover_data.get("secondary") != existing.get("secondary"):
                print(f"WARNING: Attempting to change primary/secondary servers on existing failover association")
    
    # Validate primary and secondary members exist
    if "primary" in dhcp_failover_data:
        if not check_grid_member_exists(dhcp_failover_data["primary"]):
            missing_members.append(f"Primary member: {dhcp_failover_data['primary']}")
            validation_failed = True
            print(f"ERROR: Primary member '{dhcp_failover_data['primary']}' does not exist")
    
    if "secondary" in dhcp_failover_data:
        if not check_grid_member_exists(dhcp_failover_data["secondary"]):
            missing_members.append(f"Secondary member: {dhcp_failover_data['secondary']}")
            validation_failed = True
            print(f"ERROR: Secondary member '{dhcp_failover_data['secondary']}' does not exist")
    
    # Validate member associations if present
    if "member_associations" in dhcp_failover_data:
        for idx, member_assoc in enumerate(dhcp_failover_data["member_associations"]):
            if not check_member_association_exists(member_assoc):
                invalid_member_associations.append(f"Association {idx}: {member_assoc}")
                print(f"ERROR: Member association {idx} references non-existent member")
    
    # Validate failover ranges if present
    if "failover_range" in dhcp_failover_data:
        for idx, failover_range in enumerate(dhcp_failover_data["failover_range"]):
            range_errors = validate_failover_range(failover_range)
            if range_errors:
                for error in range_errors:
                    invalid_ranges.append(f"Range {idx}: {error}")
                    print(f"ERROR: Failover range {idx} - {error}")
                validation_failed = True
    
    # Validate logical consistency
    if "primary" in dhcp_failover_data and "secondary" in dhcp_failover_data:
        if dhcp_failover_data["primary"] == dhcp_failover_data["secondary"]:
            print(f"ERROR: Primary and secondary members cannot be the same: {dhcp_failover_data['primary']}")
            validation_failed = True
    
    # Check for auto_partner_down settings
    if dhcp_failover_data.get("auto_partner_down", False):
        print(f"WARNING: auto_partner_down is enabled - ensure this is intentional")
    
    # Validate load balance settings
    if dhcp_failover_data.get("mode") == "LOAD_BALANCE" or dhcp_failover_data.get("association_type") == "LOAD_BALANCED":
        if "load_balance_split" not in dhcp_failover_data:
            print(f"INFO: Load balance mode selected but no load_balance_split specified (will use default)")
        else:
            # load_balance_split is typically a percentage * 256/100
            try:
                split = int(dhcp_failover_data["load_balance_split"])
                percentage = (split * 100) / 256
                print(f"INFO: Load balance split set to approximately {percentage:.1f}%")
            except:
                pass
    
    # Check for commonly required timer values
    if "mclt" not in dhcp_failover_data:
        print(f"WARNING: No MCLT (Maximum Client Lead Time) specified - this is typically required")
    
    # Display validation summary
    print("\nDHCP Failover Validation Summary:")
    print(f"Records checked: 1")
    print(f"Missing required fields: {len(missing_required_fields)}")
    print(f"Invalid association types: {len(invalid_association_types)}")
    print(f"Invalid modes: {len(invalid_modes)}")
    print(f"Invalid ports: {len(invalid_ports)}")
    print(f"Invalid timer values: {len(invalid_timers)}")
    print(f"Missing members: {len(missing_members)}")
    print(f"Invalid member associations: {len(invalid_member_associations)}")
    print(f"Invalid failover ranges: {len(invalid_ranges)}")
    
    return not validation_failed

def check_existing_dhcp_option_definition(name):
    """Check if a DHCP option definition already exists in Infoblox."""
    try:
        response = requests.get(
            f"{BASE_URL}/dhcpoptiondefinition",
            params={"name": name},
            auth=(INFOBLOX_USERNAME, INFOBLOX_PASSWORD),
            verify=VALIDATE_CERTS,
            timeout=HTTP_TIMEOUT
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"✗ Error checking DHCP option definition {name}: {response.status_code}")
            return []
    except Exception as e:
        print(f"✗ Error checking DHCP option definition {name}: {str(e)}")
        return []

def validate_dhcp_option_type(option_type):
    """Validate DHCP option type."""
    valid_types = [
        "array_of_ip", "array_of_string", "array_of_struct", "boolean", 
        "email", "fqdn", "integer_8", "integer_16", "integer_32", 
        "ip", "record_name", "string", "struct", "text", 
        "unsigned_integer_8", "unsigned_integer_16", "unsigned_integer_32"
    ]
    if option_type not in valid_types:
        return False, f"Invalid option type. Must be one of: {', '.join(valid_types)}"
    return True, None

def validate_dhcp_option_space(space):
    """Validate DHCP option space."""
    # Common valid spaces - this may need to be expanded based on your Infoblox configuration
    valid_spaces = ["DHCP", "DHCPv4", "DHCPv6", "ISC", "SUNW"]
    if space and space not in valid_spaces:
        # Don't fail for custom spaces, just warn
        return True, f"Custom option space '{space}' - ensure it exists in Infoblox"
    return True, None

def validate_dhcp_option_number(num, space="DHCP"):
    """Validate DHCP option number based on space."""
    try:
        option_num = int(num)
        
        # Different spaces have different valid ranges
        if space in ["DHCP", "DHCPv4"]:
            if not (1 <= option_num <= 254):
                return False, f"DHCPv4 option number {option_num} must be between 1 and 254"
        elif space == "DHCPv6":
            if not (1 <= option_num <= 65535):
                return False, f"DHCPv6 option number {option_num} must be between 1 and 65535"
        else:
            # For custom spaces, allow broader range
            if not (1 <= option_num <= 65535):
                return False, f"Option number {option_num} must be between 1 and 65535"
        
        # Check for reserved option numbers in DHCPv4
        if space in ["DHCP", "DHCPv4"]:
            reserved_options = {
                0: "Pad Option",
                255: "End Option"
            }
            if option_num in reserved_options:
                return False, f"Option {option_num} is reserved for '{reserved_options[option_num]}'"
        
        return True, None
    except (ValueError, TypeError):
        return False, f"Option number '{num}' must be a valid integer"

def validate_option_definition_flags(definition):
    """Validate option definition flags and their combinations."""
    warnings = []
    
    # Check array flag consistency
    if definition.get("type", "").startswith("array_of_") and not definition.get("flags", {}).get("array", False):
        warnings.append(f"Option '{definition.get('name')}' has array type but array flag is not set")
    
    # Check struct definition requirements
    if definition.get("type") in ["struct", "array_of_struct"]:
        if "members" not in definition or not definition["members"]:
            return False, f"Option '{definition.get('name')}' with struct type must have members defined"
    
    return True, warnings

def validate_struct_members(members, option_name):
    """Validate struct members for struct-type options."""
    errors = []
    member_names = set()
    
    for idx, member in enumerate(members):
        # Check required fields
        if "name" not in member:
            errors.append(f"Member {idx} missing required field 'name'")
            continue
        
        if "type" not in member:
            errors.append(f"Member '{member.get('name', idx)}' missing required field 'type'")
            continue
        
        # Check for duplicate member names
        if member["name"] in member_names:
            errors.append(f"Duplicate member name '{member['name']}'")
        member_names.add(member["name"])
        
        # Validate member type
        is_valid, error_msg = validate_dhcp_option_type(member["type"])
        if not is_valid:
            errors.append(f"Member '{member['name']}': {error_msg}")
        
        # Validate member option number if specified
        if "num" in member:
            is_valid, error_msg = validate_dhcp_option_number(member["num"])
            if not is_valid:
                errors.append(f"Member '{member['name']}': {error_msg}")
    
    return errors

def validate_dhcp_option_definition_records():
    """Validate DHCP Option Definition records from JSON file."""
    print("\n--- DHCP Option Definition Validation ---")
    
    dhcp_option_def_file = "playbooks/add/cabgridmgr.amfam.com/dhcpoptiondefinition.json"
    
    # Read DHCP option definition data from JSON file
    try:
        with open(dhcp_option_def_file, 'r') as file:
            dhcp_option_definitions = json.load(file)
            
            # If the content is not a list, convert it to a list with one item
            if not isinstance(dhcp_option_definitions, list):
                dhcp_option_definitions = [dhcp_option_definitions]
            
            # Check if it's empty
            if not dhcp_option_definitions:
                print(f"DHCP option definition file exists but contains no records. Skipping validation.")
                return True
                
            print(f"Found {len(dhcp_option_definitions)} DHCP option definitions to validate.")
    except Exception as e:
        print(f"Error reading file {dhcp_option_def_file}: {str(e)}")
        return False
    
    # Now continue with validation
    validation_failed = False
    missing_required_fields = []
    invalid_types = []
    invalid_spaces = []
    invalid_numbers = []
    invalid_codes = []
    invalid_struct_definitions = []
    conflicting_definitions = []
    warnings = []
    
    # Track option numbers per space to detect conflicts
    option_numbers_by_space = {}
    
    for definition in dhcp_option_definitions:
        # Check required fields
        required_fields = ["name", "num", "type"]
        missing_fields = [field for field in required_fields if field not in definition]
        if missing_fields:
            missing_required_fields.append(f"{definition.get('name', 'Unknown')}: missing {', '.join(missing_fields)}")
            validation_failed = True
            continue
        
        option_name = definition["name"]
        option_space = definition.get("space", "DHCP")
        
        # Validate option type
        is_valid, error_msg = validate_dhcp_option_type(definition["type"])
        if not is_valid:
            invalid_types.append(f"{option_name}: {error_msg}")
            validation_failed = True
            print(f"ERROR: Option '{option_name}' - {error_msg}")
        
        # Validate option space
        is_valid, warning_msg = validate_dhcp_option_space(option_space)
        if warning_msg:
            warnings.append(f"{option_name}: {warning_msg}")
            print(f"WARNING: Option '{option_name}' - {warning_msg}")
        
        # Validate option number
        is_valid, error_msg = validate_dhcp_option_number(definition["num"], option_space)
        if not is_valid:
            invalid_numbers.append(f"{option_name}: {error_msg}")
            validation_failed = True
            print(f"ERROR: Option '{option_name}' - {error_msg}")
        else:
            # Track option numbers to detect conflicts
            if option_space not in option_numbers_by_space:
                option_numbers_by_space[option_space] = {}
            
            option_num = int(definition["num"])
            if option_num in option_numbers_by_space[option_space]:
                conflicting_definitions.append(
                    f"Option number {option_num} in space '{option_space}' used by both "
                    f"'{option_numbers_by_space[option_space][option_num]}' and '{option_name}'"
                )
                validation_failed = True
                print(f"ERROR: Conflicting option number {option_num} in space '{option_space}'")
            else:
                option_numbers_by_space[option_space][option_num] = option_name
        
        # Validate code if present
        if "code" in definition:
            code = definition["code"]
            # Code should be a string representation of the option value format
            if not isinstance(code, str):
                invalid_codes.append(f"{option_name}: code must be a string")
                validation_failed = True
                print(f"ERROR: Option '{option_name}' - code must be a string")
        
        # Validate flags and type consistency
        is_valid, flag_warnings = validate_option_definition_flags(definition)
        if not is_valid:
            validation_failed = True
        warnings.extend(flag_warnings)
        for warning in flag_warnings:
            print(f"WARNING: {warning}")
        
        # Validate struct members if applicable
        if definition["type"] in ["struct", "array_of_struct"]:
            if "members" in definition:
                member_errors = validate_struct_members(definition["members"], option_name)
                if member_errors:
                    for error in member_errors:
                        invalid_struct_definitions.append(f"{option_name}: {error}")
                        print(f"ERROR: Option '{option_name}' struct - {error}")
                    validation_failed = True
            else:
                invalid_struct_definitions.append(f"{option_name}: struct type requires 'members' field")
                validation_failed = True
                print(f"ERROR: Option '{option_name}' - struct type requires 'members' field")
        
        # Check if the option definition already exists
        existing_definitions = check_existing_dhcp_option_definition(option_name)
        if existing_definitions:
            existing = existing_definitions[0]
            print(f"DHCP Option Definition '{option_name}' already exists")
            print(f"  Current number: {existing.get('num', 'N/A')}")
            print(f"  Current type: {existing.get('type', 'N/A')}")
            print(f"  Current space: {existing.get('space', 'N/A')}")
            
            # Check for conflicts
            if str(existing.get('num')) != str(definition['num']):
                print(f"  WARNING: Option number will be changed from {existing.get('num')} to {definition['num']}")
            if existing.get('type') != definition['type']:
                print(f"  WARNING: Option type will be changed from '{existing.get('type')}' to '{definition['type']}'")
                print(f"  CRITICAL: Changing option type may affect existing DHCP configurations!")
    
    # Check for conflicts with well-known DHCP options
    well_known_dhcpv4_options = {
        1: "Subnet Mask",
        3: "Router",
        6: "Domain Name Server",
        12: "Host Name",
        15: "Domain Name",
        28: "Broadcast Address",
        42: "NTP Servers",
        44: "NetBIOS Name Servers",
        51: "IP Address Lease Time",
        53: "DHCP Message Type",
        54: "Server Identifier",
        58: "Renewal Time",
        59: "Rebinding Time",
        61: "Client Identifier",
        66: "TFTP Server Name",
        67: "Bootfile Name",
        119: "Domain Search",
        121: "Classless Static Route",
        150: "TFTP Server Address"
    }
    
    for definition in dhcp_option_definitions:
        if definition.get("space", "DHCP") in ["DHCP", "DHCPv4"] and "num" in definition:
            option_num = int(definition["num"])
            if option_num in well_known_dhcpv4_options:
                print(f"WARNING: Option '{definition['name']}' uses well-known option number {option_num} "
                      f"('{well_known_dhcpv4_options[option_num]}') - ensure this is intentional")
    
    # Validate comment length if present
    for definition in dhcp_option_definitions:
        if "comment" in definition and len(definition["comment"]) > 256:
            warnings.append(f"{definition['name']}: Comment exceeds 256 characters")
            print(f"WARNING: Option '{definition['name']}' - Comment exceeds recommended length")
    
    # Display validation summary
    print("\nDHCP Option Definition Validation Summary:")
    print(f"Total records checked: {len(dhcp_option_definitions)}")
    print(f"Records with missing required fields: {len(missing_required_fields)}")
    print(f"Records with invalid types: {len(invalid_types)}")
    print(f"Records with invalid spaces: {len(invalid_spaces)}")
    print(f"Records with invalid numbers: {len(invalid_numbers)}")
    print(f"Records with invalid codes: {len(invalid_codes)}")
    print(f"Records with invalid struct definitions: {len(invalid_struct_definitions)}")
    print(f"Conflicting definitions: {len(conflicting_definitions)}")
    print(f"Warnings: {len(warnings)}")
    
    return not validation_failed

def check_existing_dhcp_ipv6_option_definition(name):
    """Check if a DHCP IPv6 option definition already exists in Infoblox."""
    try:
        response = requests.get(
            f"{BASE_URL}/ipv6dhcpoptiondefinition",
            params={"name": name},
            auth=(INFOBLOX_USERNAME, INFOBLOX_PASSWORD),
            verify=VALIDATE_CERTS,
            timeout=HTTP_TIMEOUT
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"✗ Error checking DHCP IPv6 option definition {name}: {response.status_code}")
            return []
    except Exception as e:
        print(f"✗ Error checking DHCP IPv6 option definition {name}: {str(e)}")
        return []

def validate_dhcp_ipv6_option_type(option_type):
    """Validate DHCP IPv6 option type."""
    valid_types = [
        "ipv6-address", "ipv6-prefix", "domain-list", "domain-name",
        "string", "uint8", "uint16", "uint32", "int8", "int16", "int32",
        "boolean", "empty", "binary", "array-of-ipv6-address",
        "array-of-string", "array-of-uint8", "array-of-uint16",
        "array-of-uint32", "array-of-int8", "array-of-int16",
        "array-of-int32", "struct", "array-of-struct"
    ]
    if option_type not in valid_types:
        return False, f"Invalid IPv6 option type. Must be one of: {', '.join(valid_types)}"
    return True, None

def validate_dhcp_ipv6_option_space(space):
    """Validate DHCP IPv6 option space."""
    # Common valid spaces for IPv6
    valid_spaces = ["dhcpv6", "vendor-class", "vendor-opts", "ISC", "DHCPv6"]
    if space and space.lower() not in [s.lower() for s in valid_spaces]:
        # Don't fail for custom spaces, just warn
        return True, f"Custom IPv6 option space '{space}' - ensure it exists in Infoblox"
    return True, None

def validate_dhcp_ipv6_option_number(num, space="dhcpv6"):
    """Validate DHCP IPv6 option number based on space."""
    try:
        option_num = int(num)
        
        # DHCPv6 option numbers are 16-bit values
        if not (1 <= option_num <= 65535):
            return False, f"DHCPv6 option number {option_num} must be between 1 and 65535"
        
        # Check for reserved DHCPv6 option numbers
        reserved_options = {
            0: "Reserved",
            # Well-known DHCPv6 options
            1: "OPTION_CLIENTID",
            2: "OPTION_SERVERID",
            3: "OPTION_IA_NA",
            4: "OPTION_IA_TA",
            5: "OPTION_IAADDR",
            6: "OPTION_ORO",
            7: "OPTION_PREFERENCE",
            8: "OPTION_ELAPSED_TIME",
            9: "OPTION_RELAY_MSG",
            11: "OPTION_AUTH",
            12: "OPTION_UNICAST",
            13: "OPTION_STATUS_CODE",
            14: "OPTION_RAPID_COMMIT",
            15: "OPTION_USER_CLASS",
            16: "OPTION_VENDOR_CLASS",
            17: "OPTION_VENDOR_OPTS",
            18: "OPTION_INTERFACE_ID",
            19: "OPTION_RECONF_MSG",
            20: "OPTION_RECONF_ACCEPT",
            21: "OPTION_SIP_SERVER_D",
            22: "OPTION_SIP_SERVER_A",
            23: "OPTION_DNS_SERVERS",
            24: "OPTION_DOMAIN_LIST",
            25: "OPTION_IA_PD",
            26: "OPTION_IAPREFIX",
            27: "OPTION_NIS_SERVERS",
            28: "OPTION_NISP_SERVERS",
            29: "OPTION_NIS_DOMAIN_NAME",
            30: "OPTION_NISP_DOMAIN_NAME",
            31: "OPTION_SNTP_SERVERS",
            32: "OPTION_INFORMATION_REFRESH_TIME",
            33: "OPTION_BCMCS_SERVER_D",
            34: "OPTION_BCMCS_SERVER_A",
            36: "OPTION_GEOCONF_CIVIC",
            37: "OPTION_REMOTE_ID",
            38: "OPTION_SUBSCRIBER_ID",
            39: "OPTION_CLIENT_FQDN",
            40: "OPTION_PANA_AGENT",
            41: "OPTION_NEW_POSIX_TIMEZONE",
            42: "OPTION_NEW_TZDB_TIMEZONE",
            43: "OPTION_ERO",
            44: "OPTION_LQ_QUERY",
            45: "OPTION_CLIENT_DATA",
            46: "OPTION_CLT_TIME",
            47: "OPTION_LQ_RELAY_DATA",
            48: "OPTION_LQ_CLIENT_LINK",
            49: "OPTION_MIP6_HNIDF",
            50: "OPTION_MIP6_VDINF",
            51: "OPTION_V6_LOST",
            52: "OPTION_CAPWAP_AC_V6",
            53: "OPTION_RELAY_ID",
            56: "OPTION_NTP_SERVER",
            57: "OPTION_V6_ACCESS_DOMAIN",
            58: "OPTION_SIP_UA_CS_LIST",
            59: "OPTION_BOOTFILE_URL",
            60: "OPTION_BOOTFILE_PARAM",
            61: "OPTION_CLIENT_ARCH_TYPE",
            62: "OPTION_NII",
            63: "OPTION_GEOLOCATION",
            64: "OPTION_AFTR_NAME",
            65: "OPTION_ERP_LOCAL_DOMAIN_NAME",
            66: "OPTION_RSOO",
            67: "OPTION_PD_EXCLUDE",
            68: "OPTION_VSS",
            69: "OPTION_MIP6_IDINF",
            70: "OPTION_MIP6_UDINF",
            71: "OPTION_MIP6_HNP",
            72: "OPTION_MIP6_HAA",
            73: "OPTION_MIP6_HAF",
            74: "OPTION_RDNSS_SELECTION",
            75: "OPTION_KRB_PRINCIPAL_NAME",
            76: "OPTION_KRB_REALM_NAME",
            77: "OPTION_KRB_DEFAULT_REALM_NAME",
            78: "OPTION_KRB_KDC",
            79: "OPTION_CLIENT_LINKLAYER_ADDR",
            80: "OPTION_LINK_ADDRESS",
            81: "OPTION_RADIUS",
            82: "OPTION_SOL_MAX_RT",
            83: "OPTION_INF_MAX_RT"
        }
        
        if option_num == 0:
            return False, f"Option number 0 is reserved"
        
        return True, None
    except (ValueError, TypeError):
        return False, f"Option number '{num}' must be a valid integer"

def validate_ipv6_struct_members(members, option_name):
    """Validate struct members for IPv6 struct-type options."""
    errors = []
    member_names = set()
    
    for idx, member in enumerate(members):
        # Check required fields
        if "name" not in member:
            errors.append(f"Member {idx} missing required field 'name'")
            continue
        
        if "type" not in member:
            errors.append(f"Member '{member.get('name', idx)}' missing required field 'type'")
            continue
        
        # Check for duplicate member names
        if member["name"] in member_names:
            errors.append(f"Duplicate member name '{member['name']}'")
        member_names.add(member["name"])
        
        # Validate member type
        is_valid, error_msg = validate_dhcp_ipv6_option_type(member["type"])
        if not is_valid:
            errors.append(f"Member '{member['name']}': {error_msg}")
        
        # Validate member option number if specified
        if "code" in member:
            try:
                code = int(member["code"])
                if not (0 <= code <= 65535):
                    errors.append(f"Member '{member['name']}': code {code} must be between 0 and 65535")
            except (ValueError, TypeError):
                errors.append(f"Member '{member['name']}': code must be a valid integer")
    
    return errors

def validate_dhcp_ipv6_option_definition_records():
    """Validate DHCP IPv6 Option Definition records from JSON file."""
    print("\n--- DHCP IPv6 Option Definition Validation ---")
    
    dhcp_ipv6_option_def_file = "playbooks/add/cabgridmgr.amfam.com/dhcpoptionipv6definition.json"
    
    # Read DHCP IPv6 option definition data from JSON file
    try:
        with open(dhcp_ipv6_option_def_file, 'r') as file:
            dhcp_ipv6_option_definitions = json.load(file)
            
            # Handle both list and single dictionary formats
            if isinstance(dhcp_ipv6_option_definitions, dict):
                dhcp_ipv6_option_definitions = [dhcp_ipv6_option_definitions]
            elif not isinstance(dhcp_ipv6_option_definitions, list):
                print(f"ERROR: Invalid format - expected list or dictionary")
                return False
            
            # Check if it's empty
            if not dhcp_ipv6_option_definitions:
                print(f"DHCP IPv6 option definition file exists but contains no records. Skipping validation.")
                return True
                
            print(f"Found {len(dhcp_ipv6_option_definitions)} DHCP IPv6 option definitions to validate.")
    except Exception as e:
        print(f"Error reading file {dhcp_ipv6_option_def_file}: {str(e)}")
        return False
    
    # Now continue with validation
    validation_failed = False
    missing_required_fields = []
    invalid_types = []
    invalid_spaces = []
    invalid_numbers = []
    invalid_codes = []
    invalid_struct_definitions = []
    conflicting_definitions = []
    warnings = []
    
    # Track option numbers per space to detect conflicts
    option_numbers_by_space = {}
    
    for definition in dhcp_ipv6_option_definitions:
        # Check required fields
        required_fields = ["name", "code", "type"]
        missing_fields = [field for field in required_fields if field not in definition]
        if missing_fields:
            missing_required_fields.append(f"{definition.get('name', 'Unknown')}: missing {', '.join(missing_fields)}")
            validation_failed = True
            continue
        
        option_name = definition["name"]
        option_space = definition.get("space", "dhcpv6")
        
        # Validate option type
        is_valid, error_msg = validate_dhcp_ipv6_option_type(definition["type"])
        if not is_valid:
            invalid_types.append(f"{option_name}: {error_msg}")
            validation_failed = True
            print(f"ERROR: Option '{option_name}' - {error_msg}")
        
        # Validate option space
        is_valid, warning_msg = validate_dhcp_ipv6_option_space(option_space)
        if warning_msg:
            warnings.append(f"{option_name}: {warning_msg}")
            print(f"WARNING: Option '{option_name}' - {warning_msg}")
        
        # Validate option code (number)
        is_valid, error_msg = validate_dhcp_ipv6_option_number(definition["code"], option_space)
        if not is_valid:
            invalid_numbers.append(f"{option_name}: {error_msg}")
            validation_failed = True
            print(f"ERROR: Option '{option_name}' - {error_msg}")
        else:
            # Track option numbers to detect conflicts
            if option_space not in option_numbers_by_space:
                option_numbers_by_space[option_space] = {}
            
            option_num = int(definition["code"])
            if option_num in option_numbers_by_space[option_space]:
                conflicting_definitions.append(
                    f"Option code {option_num} in space '{option_space}' used by both "
                    f"'{option_numbers_by_space[option_space][option_num]}' and '{option_name}'"
                )
                validation_failed = True
                print(f"ERROR: Conflicting option code {option_num} in space '{option_space}'")
            else:
                option_numbers_by_space[option_space][option_num] = option_name
        
        # Validate struct members if applicable
        if definition["type"] in ["struct", "array-of-struct"]:
            if "members" in definition:
                member_errors = validate_ipv6_struct_members(definition["members"], option_name)
                if member_errors:
                    for error in member_errors:
                        invalid_struct_definitions.append(f"{option_name}: {error}")
                        print(f"ERROR: Option '{option_name}' struct - {error}")
                    validation_failed = True
            else:
                invalid_struct_definitions.append(f"{option_name}: struct type requires 'members' field")
                validation_failed = True
                print(f"ERROR: Option '{option_name}' - struct type requires 'members' field")
        
        # Check if the option definition already exists
        existing_definitions = check_existing_dhcp_ipv6_option_definition(option_name)
        if existing_definitions:
            existing = existing_definitions[0]
            print(f"DHCP IPv6 Option Definition '{option_name}' already exists")
            print(f"  Current code: {existing.get('code', 'N/A')}")
            print(f"  Current type: {existing.get('type', 'N/A')}")
            print(f"  Current space: {existing.get('space', 'N/A')}")
            
            # Check for conflicts
            if str(existing.get('code')) != str(definition['code']):
                print(f"  WARNING: Option code will be changed from {existing.get('code')} to {definition['code']}")
            if existing.get('type') != definition['type']:
                print(f"  WARNING: Option type will be changed from '{existing.get('type')}' to '{definition['type']}'")
                print(f"  CRITICAL: Changing option type may affect existing DHCPv6 configurations!")
    
    # Check for conflicts with well-known DHCPv6 options
    well_known_dhcpv6_options = {
        1: "Client Identifier",
        2: "Server Identifier",
        3: "Identity Association for Non-temporary Addresses",
        4: "Identity Association for Temporary Addresses",
        5: "IA Address",
        6: "Option Request",
        7: "Preference",
        8: "Elapsed Time",
        9: "Relay Message",
        11: "Authentication",
        12: "Server Unicast",
        13: "Status Code",
        14: "Rapid Commit",
        15: "User Class",
        16: "Vendor Class",
        17: "Vendor-specific Information",
        18: "Interface-Id",
        19: "Reconfigure Message",
        20: "Reconfigure Accept",
        23: "DNS Recursive Name Server",
        24: "Domain Search List",
        25: "Identity Association for Prefix Delegation",
        26: "IA_PD Prefix",
        31: "SNTP Servers",
        32: "Information Refresh Time",
        39: "FQDN",
        56: "NTP Server",
        59: "Boot File URL",
        60: "Boot File Parameters",
        61: "Architecture Type",
        82: "SOL_MAX_RT",
        83: "INF_MAX_RT"
    }
    
    for definition in dhcp_ipv6_option_definitions:
        if definition.get("space", "dhcpv6").lower() == "dhcpv6" and "code" in definition:
            option_num = int(definition["code"])
            if option_num in well_known_dhcpv6_options:
                print(f"WARNING: Option '{definition['name']}' uses well-known option code {option_num} "
                      f"('{well_known_dhcpv6_options[option_num]}') - ensure this is intentional")
    
    # Validate array consistency
    for definition in dhcp_ipv6_option_definitions:
        if definition.get("type", "").startswith("array-of-") and definition.get("array", False) is False:
            warnings.append(f"{definition['name']}: Array type but 'array' flag not set to true")
            print(f"WARNING: Option '{definition['name']}' has array type but 'array' flag is not true")
    
    # Validate comment length if present
    for definition in dhcp_ipv6_option_definitions:
        if "comment" in definition and len(definition["comment"]) > 256:
            warnings.append(f"{definition['name']}: Comment exceeds 256 characters")
            print(f"WARNING: Option '{definition['name']}' - Comment exceeds recommended length")
    
    # Display validation summary
    print("\nDHCP IPv6 Option Definition Validation Summary:")
    print(f"Total records checked: {len(dhcp_ipv6_option_definitions)}")
    print(f"Records with missing required fields: {len(missing_required_fields)}")
    print(f"Records with invalid types: {len(invalid_types)}")
    print(f"Records with invalid spaces: {len(invalid_spaces)}")
    print(f"Records with invalid codes: {len(invalid_numbers)}")
    print(f"Records with invalid struct definitions: {len(invalid_struct_definitions)}")
    print(f"Conflicting definitions: {len(conflicting_definitions)}")
    print(f"Warnings: {len(warnings)}")
    
    return not validation_failed

def check_existing_dhcp_ipv6_option_space(name):
    """Check if a DHCP IPv6 option space already exists in Infoblox."""
    try:
        response = requests.get(
            f"{BASE_URL}/ipv6dhcpoptionspace",
            params={"name": name},
            auth=(INFOBLOX_USERNAME, INFOBLOX_PASSWORD),
            verify=VALIDATE_CERTS,
            timeout=HTTP_TIMEOUT
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"✗ Error checking DHCP IPv6 option space {name}: {response.status_code}")
            return []
    except Exception as e:
        print(f"✗ Error checking DHCP IPv6 option space {name}: {str(e)}")
        return []

def validate_dhcp_ipv6_option_space_name(name):
    """Validate DHCP IPv6 option space name format."""
    if not name:
        return False, "Option space name cannot be empty"
    
    # Check length
    if len(name) > 256:
        return False, f"Option space name too long ({len(name)} characters, max 256)"
    
    # Check for valid characters (alphanumeric, underscore, hyphen, period)
    if not re.match(r'^[a-zA-Z0-9._-]+$', name):
        return False, "Option space name contains invalid characters (only alphanumeric, underscore, hyphen, period allowed)"
    
    # Check for reserved names
    reserved_names = ['dhcpv6', 'vendor-class', 'vendor-opts']
    if name.lower() in [r.lower() for r in reserved_names]:
        return False, f"Option space name '{name}' is reserved"
    
    # Cannot start with underscore or hyphen
    if name.startswith('_') or name.startswith('-'):
        return False, "Option space name cannot start with underscore or hyphen"
    
    # Cannot contain consecutive dots
    if '..' in name:
        return False, "Option space name cannot contain consecutive dots"
    
    return True, None

def check_option_definitions_in_space(space_name):
    """Check if there are option definitions using this space."""
    try:
        # Check IPv6 option definitions
        response = requests.get(
            f"{BASE_URL}/ipv6dhcpoptiondefinition",
            params={"space": space_name},
            auth=(INFOBLOX_USERNAME, INFOBLOX_PASSWORD),
            verify=VALIDATE_CERTS,
            timeout=HTTP_TIMEOUT
        )
        
        if response.status_code == 200:
            definitions = response.json()
            return len(definitions), [d.get('name', 'Unknown') for d in definitions]
        else:
            return 0, []
    except Exception as e:
        print(f"✗ Error checking option definitions for space {space_name}: {str(e)}")
        return 0, []

def validate_enterprise_number(enterprise_number):
    """Validate enterprise number for vendor-specific option spaces."""
    if enterprise_number is None:
        return True, None  # Not required for all spaces
    
    try:
        num = int(enterprise_number)
        # Enterprise numbers are assigned by IANA and are 32-bit values
        if not (1 <= num <= 4294967295):
            return False, f"Enterprise number {num} must be between 1 and 4294967295"
        
        # Well-known enterprise numbers (examples)
        well_known = {
            311: "Microsoft",
            2636: "Juniper Networks",
            9: "Cisco Systems",
            122: "Sun Microsystems",
            1916: "Extreme Networks",
            2011: "Huawei",
            25506: "H3C",
            6486: "Alcatel-Lucent",
            1872: "Alteon",
            5771: "VMware"
        }
        
        if num in well_known:
            print(f"INFO: Using well-known enterprise number {num} ({well_known[num]})")
        
        return True, None
    except (ValueError, TypeError):
        return False, "Enterprise number must be a valid integer"

def validate_dhcp_ipv6_option_space_records():
    """Validate DHCP IPv6 Option Space records from JSON file."""
    print("\n--- DHCP IPv6 Option Space Validation ---")
    
    dhcp_ipv6_option_space_file = "playbooks/add/cabgridmgr.amfam.com/dhcpoptionipv6space.json"
    
    # Read DHCP IPv6 option space data from JSON file
    try:
        with open(dhcp_ipv6_option_space_file, 'r') as file:
            dhcp_ipv6_option_spaces = json.load(file)
            
            # Handle both list and single dictionary formats
            if isinstance(dhcp_ipv6_option_spaces, dict):
                dhcp_ipv6_option_spaces = [dhcp_ipv6_option_spaces]
            elif not isinstance(dhcp_ipv6_option_spaces, list):
                print(f"ERROR: Invalid format - expected list or dictionary")
                return False
            
            # Check if it's empty
            if not dhcp_ipv6_option_spaces:
                print(f"DHCP IPv6 option space file exists but contains no records. Skipping validation.")
                return True
                
            print(f"Found {len(dhcp_ipv6_option_spaces)} DHCP IPv6 option spaces to validate.")
    except Exception as e:
        print(f"Error reading file {dhcp_ipv6_option_space_file}: {str(e)}")
        return False
    
    # Now continue with validation
    validation_failed = False
    missing_required_fields = []
    invalid_names = []
    invalid_enterprise_numbers = []
    existing_spaces = []
    spaces_with_definitions = []
    duplicate_spaces = []
    warnings = []
    
    # Track space names to detect duplicates
    space_names_seen = set()
    
    for space in dhcp_ipv6_option_spaces:
        # Check required fields
        required_fields = ["name"]
        missing_fields = [field for field in required_fields if field not in space]
        if missing_fields:
            missing_required_fields.append(f"{space.get('name', 'Unknown')}: missing {', '.join(missing_fields)}")
            validation_failed = True
            continue
        
        space_name = space["name"]
        
        # Check for duplicate space names in the JSON
        if space_name in space_names_seen:
            duplicate_spaces.append(space_name)
            validation_failed = True
            print(f"ERROR: Duplicate space name '{space_name}' found in JSON")
        space_names_seen.add(space_name)
        
        # Validate space name format
        is_valid, error_msg = validate_dhcp_ipv6_option_space_name(space_name)
        if not is_valid:
            invalid_names.append(f"{space_name}: {error_msg}")
            validation_failed = True
            print(f"ERROR: Space '{space_name}' - {error_msg}")
        
        # Validate enterprise number if present
        if "enterprise_number" in space:
            is_valid, error_msg = validate_enterprise_number(space["enterprise_number"])
            if not is_valid:
                invalid_enterprise_numbers.append(f"{space_name}: {error_msg}")
                validation_failed = True
                print(f"ERROR: Space '{space_name}' - {error_msg}")
        
        # Check if the option space already exists
        existing_space_records = check_existing_dhcp_ipv6_option_space(space_name)
        if existing_space_records:
            existing_spaces.append(space_name)
            existing = existing_space_records[0]
            print(f"DHCP IPv6 Option Space '{space_name}' already exists")
            
            # Check if enterprise number is changing
            if "enterprise_number" in space and existing.get("enterprise_number") != space["enterprise_number"]:
                print(f"  WARNING: Enterprise number will be changed from {existing.get('enterprise_number', 'None')} to {space['enterprise_number']}")
                print(f"  CRITICAL: Changing enterprise number may break existing configurations!")
            
            # Check for option definitions using this space
            definition_count, definition_names = check_option_definitions_in_space(space_name)
            if definition_count > 0:
                spaces_with_definitions.append(f"{space_name} ({definition_count} definitions)")
                print(f"  INFO: This space has {definition_count} option definitions: {', '.join(definition_names[:5])}")
                if definition_count > 5:
                    print(f"        ... and {definition_count - 5} more")
                print(f"  WARNING: Modifying this space may affect existing option definitions")
        
        # Validate comment length if present
        if "comment" in space and len(space.get("comment", "")) > 256:
            warnings.append(f"{space_name}: Comment exceeds 256 characters")
            print(f"WARNING: Space '{space_name}' - Comment exceeds recommended length")
        
        # Check for vendor-specific space naming convention
        if "enterprise_number" in space and not any(keyword in space_name.lower() for keyword in ["vendor", "enterprise", "custom"]):
            warnings.append(f"{space_name}: Has enterprise number but name doesn't indicate vendor-specific space")
            print(f"INFO: Space '{space_name}' has enterprise number but name doesn't indicate it's vendor-specific")
    
    # Check for logical consistency
    for space in dhcp_ipv6_option_spaces:
        space_name = space.get("name", "Unknown")
        
        # Check if space has option_definitions field (which should be excluded during update)
        if "option_definitions" in space:
            print(f"INFO: Space '{space_name}' has 'option_definitions' field - this will be excluded during update")
        
        # Warn about spaces without comments
        if "comment" not in space or not space.get("comment"):
            warnings.append(f"{space_name}: No comment/description provided")
            print(f"INFO: Space '{space_name}' has no comment - consider adding documentation")
    
    # Display validation summary
    print("\nDHCP IPv6 Option Space Validation Summary:")
    print(f"Total records checked: {len(dhcp_ipv6_option_spaces)}")
    print(f"Records with missing required fields: {len(missing_required_fields)}")
    print(f"Records with invalid names: {len(invalid_names)}")
    print(f"Records with invalid enterprise numbers: {len(invalid_enterprise_numbers)}")
    print(f"Existing spaces: {len(existing_spaces)}")
    print(f"Spaces with existing definitions: {len(spaces_with_definitions)}")
    print(f"Duplicate spaces in JSON: {len(duplicate_spaces)}")
    print(f"Warnings: {len(warnings)}")
    
    if existing_spaces:
        print(f"\nExisting spaces that will be updated: {', '.join(existing_spaces)}")
    if spaces_with_definitions:
        print(f"\nSpaces with existing definitions: {', '.join(spaces_with_definitions)}")
    
    return not validation_failed

def check_existing_dhcp_option_space(name):
    """Check if a DHCP option space already exists in Infoblox."""
    try:
        response = requests.get(
            f"{BASE_URL}/dhcpoptionspace",
            params={"name": name},
            auth=(INFOBLOX_USERNAME, INFOBLOX_PASSWORD),
            verify=VALIDATE_CERTS,
            timeout=HTTP_TIMEOUT
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"✗ Error checking DHCP option space {name}: {response.status_code}")
            return []
    except Exception as e:
        print(f"✗ Error checking DHCP option space {name}: {str(e)}")
        return []

def validate_dhcp_option_space_name(name):
    """Validate DHCP option space name format."""
    if not name:
        return False, "Option space name cannot be empty"
    
    # Check length
    if len(name) > 256:
        return False, f"Option space name too long ({len(name)} characters, max 256)"
    
    # Check for valid characters (alphanumeric, underscore, hyphen, period)
    if not re.match(r'^[a-zA-Z0-9._-]+$', name):
        return False, "Option space name contains invalid characters (only alphanumeric, underscore, hyphen, period allowed)"
    
    # Check for reserved names
    reserved_names = ['DHCP', 'DHCPv4', 'ISC', 'SUNW', 'vendor-encapsulated-options']
    if name in reserved_names:
        return False, f"Option space name '{name}' is reserved"
    
    # Cannot start with underscore or hyphen
    if name.startswith('_') or name.startswith('-'):
        return False, "Option space name cannot start with underscore or hyphen"
    
    # Cannot contain consecutive dots
    if '..' in name:
        return False, "Option space name cannot contain consecutive dots"
    
    return True, None

def check_dhcp_option_definitions_in_space(space_name):
    """Check if there are DHCP option definitions using this space."""
    try:
        # Check DHCPv4 option definitions
        response = requests.get(
            f"{BASE_URL}/dhcpoptiondefinition",
            params={"space": space_name},
            auth=(INFOBLOX_USERNAME, INFOBLOX_PASSWORD),
            verify=VALIDATE_CERTS,
            timeout=HTTP_TIMEOUT
        )
        
        if response.status_code == 200:
            definitions = response.json()
            return len(definitions), [d.get('name', 'Unknown') for d in definitions]
        else:
            return 0, []
    except Exception as e:
        print(f"✗ Error checking option definitions for space {space_name}: {str(e)}")
        return 0, []

def validate_dhcp_vendor_identifier(vendor_identifier):
    """Validate vendor identifier for vendor-specific option spaces."""
    if vendor_identifier is None:
        return True, None  # Not required for all spaces
    
    if not vendor_identifier:
        return False, "Vendor identifier cannot be empty if specified"
    
    # Vendor identifier is typically a string
    if not isinstance(vendor_identifier, str):
        return False, "Vendor identifier must be a string"
    
    # Check length (reasonable limit)
    if len(vendor_identifier) > 255:
        return False, f"Vendor identifier too long ({len(vendor_identifier)} characters, max 255)"
    
    # Common vendor identifiers
    common_vendors = {
        "MSFT": "Microsoft",
        "docsis": "Cable Modems",
        "pxeclient": "PXE Clients",
        "Etherboot": "Etherboot Clients",
        "gPXE": "gPXE Clients",
        "iPXE": "iPXE Clients",
        "SUNW": "Sun Microsystems"
    }
    
    for prefix, vendor in common_vendors.items():
        if vendor_identifier.startswith(prefix):
            print(f"INFO: Using vendor identifier for {vendor}")
            break
    
    return True, None

def validate_dhcp_option_space_records():
    """Validate DHCP Option Space records from JSON file."""
    print("\n--- DHCP Option Space Validation ---")
    
    dhcp_option_space_file = "playbooks/add/cabgridmgr.amfam.com/dhcpoptionspace.json"
    
    # Read DHCP option space data from JSON file
    try:
        with open(dhcp_option_space_file, 'r') as file:
            dhcp_option_spaces = json.load(file)
            
            # If the content is not a list, convert it to a list
            if not isinstance(dhcp_option_spaces, list):
                dhcp_option_spaces = [dhcp_option_spaces]
            
            # Check if it's empty
            if not dhcp_option_spaces:
                print(f"DHCP option space file exists but contains no records. Skipping validation.")
                return True
                
            print(f"Found {len(dhcp_option_spaces)} DHCP option spaces to validate.")
    except Exception as e:
        print(f"Error reading file {dhcp_option_space_file}: {str(e)}")
        return False
    
    # Now continue with validation
    validation_failed = False
    missing_required_fields = []
    invalid_names = []
    invalid_vendor_identifiers = []
    existing_spaces = []
    spaces_with_definitions = []
    duplicate_spaces = []
    warnings = []
    
    # Track space names to detect duplicates
    space_names_seen = set()
    
    for space in dhcp_option_spaces:
        # Check required fields
        required_fields = ["name"]
        missing_fields = [field for field in required_fields if field not in space]
        if missing_fields:
            missing_required_fields.append(f"{space.get('name', 'Unknown')}: missing {', '.join(missing_fields)}")
            validation_failed = True
            continue
        
        space_name = space["name"]
        
        # Check for duplicate space names in the JSON
        if space_name in space_names_seen:
            duplicate_spaces.append(space_name)
            validation_failed = True
            print(f"ERROR: Duplicate space name '{space_name}' found in JSON")
        space_names_seen.add(space_name)
        
        # Validate space name format
        is_valid, error_msg = validate_dhcp_option_space_name(space_name)
        if not is_valid:
            invalid_names.append(f"{space_name}: {error_msg}")
            validation_failed = True
            print(f"ERROR: Space '{space_name}' - {error_msg}")
        
        # Validate vendor identifier if present
        if "vendor_identifier" in space:
            is_valid, error_msg = validate_dhcp_vendor_identifier(space["vendor_identifier"])
            if not is_valid:
                invalid_vendor_identifiers.append(f"{space_name}: {error_msg}")
                validation_failed = True
                print(f"ERROR: Space '{space_name}' - {error_msg}")
        
        # Check if the option space already exists
        existing_space_records = check_existing_dhcp_option_space(space_name)
        if existing_space_records:
            existing_spaces.append(space_name)
            existing = existing_space_records[0]
            print(f"DHCP Option Space '{space_name}' already exists")
            
            # Check for changes in vendor identifier
            if "vendor_identifier" in space:
                existing_vendor = existing.get("vendor_identifier")
                if existing_vendor != space["vendor_identifier"]:
                    print(f"  WARNING: Vendor identifier will be changed from '{existing_vendor}' to '{space['vendor_identifier']}'")
                    print(f"  CRITICAL: Changing vendor identifier may break existing configurations!")
            
            # Check for option definitions using this space
            definition_count, definition_names = check_dhcp_option_definitions_in_space(space_name)
            if definition_count > 0:
                spaces_with_definitions.append(f"{space_name} ({definition_count} definitions)")
                print(f"  INFO: This space has {definition_count} option definitions: {', '.join(definition_names[:5])}")
                if definition_count > 5:
                    print(f"        ... and {definition_count - 5} more")
                print(f"  WARNING: Modifying this space may affect existing option definitions")
        
        # Validate comment length if present
        if "comment" in space and len(space.get("comment", "")) > 256:
            warnings.append(f"{space_name}: Comment exceeds 256 characters")
            print(f"WARNING: Space '{space_name}' - Comment exceeds recommended length")
        
        # Check for vendor-specific space naming convention
        if "vendor_identifier" in space and not any(keyword in space_name.lower() for keyword in ["vendor", "custom", space.get("vendor_identifier", "").lower()]):
            warnings.append(f"{space_name}: Has vendor identifier but name doesn't indicate vendor-specific space")
            print(f"INFO: Space '{space_name}' has vendor identifier but name doesn't indicate it's vendor-specific")
        
        # Check for fields that will be excluded
        excluded_fields = ['option_definitions', 'space_type', '_ref']
        present_excluded = [field for field in excluded_fields if field in space]
        if present_excluded:
            print(f"INFO: Space '{space_name}' has fields that will be excluded: {', '.join(present_excluded)}")
    
    # Check for logical consistency
    for space in dhcp_option_spaces:
        space_name = space.get("name", "Unknown")
        
        # Warn about spaces without comments
        if "comment" not in space or not space.get("comment"):
            warnings.append(f"{space_name}: No comment/description provided")
            print(f"INFO: Space '{space_name}' has no comment - consider adding documentation")
        
        # Check if it appears to be a vendor space without vendor identifier
        vendor_keywords = ["vendor", "microsoft", "cisco", "pxe", "docsis"]
        if any(keyword in space_name.lower() for keyword in vendor_keywords) and "vendor_identifier" not in space:
            warnings.append(f"{space_name}: Name suggests vendor-specific but no vendor_identifier set")
            print(f"WARNING: Space '{space_name}' name suggests vendor-specific but no vendor_identifier is set")
    
    # Display validation summary
    print("\nDHCP Option Space Validation Summary:")
    print(f"Total records checked: {len(dhcp_option_spaces)}")
    print(f"Records with missing required fields: {len(missing_required_fields)}")
    print(f"Records with invalid names: {len(invalid_names)}")
    print(f"Records with invalid vendor identifiers: {len(invalid_vendor_identifiers)}")
    print(f"Existing spaces: {len(existing_spaces)}")
    print(f"Spaces with existing definitions: {len(spaces_with_definitions)}")
    print(f"Duplicate spaces in JSON: {len(duplicate_spaces)}")
    print(f"Warnings: {len(warnings)}")
    
    if existing_spaces:
        print(f"\nExisting spaces that will be updated: {', '.join(existing_spaces)}")
    if spaces_with_definitions:
        print(f"\nSpaces with existing definitions: {', '.join(spaces_with_definitions)}")
    
    return not validation_failed

def check_existing_dns_grid():
    """Check if DNS Grid exists and get its current configuration."""
    try:
        response = requests.get(
            f"{BASE_URL}/grid:dns",
            auth=(INFOBLOX_USERNAME, INFOBLOX_PASSWORD),
            verify=VALIDATE_CERTS,
            timeout=HTTP_TIMEOUT
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"✗ Error checking DNS Grid: {response.status_code}")
            return []
    except Exception as e:
        print(f"✗ Error checking DNS Grid: {str(e)}")
        return []

def validate_dns_acl_items(acl_items, acl_name):
    """Validate DNS ACL items structure."""
    errors = []
    
    if not isinstance(acl_items, list):
        errors.append(f"{acl_name}: ACL items must be a list")
        return errors
    
    for idx, item in enumerate(acl_items):
        # Check required fields
        if "access_method" not in item:
            errors.append(f"{acl_name}[{idx}]: Missing required field 'access_method'")
            continue
        
        # Validate access_method
        valid_methods = ["ALLOW", "DENY"]
        if item["access_method"] not in valid_methods:
            errors.append(f"{acl_name}[{idx}]: Invalid access_method '{item['access_method']}' (must be ALLOW or DENY)")
        
        # Check for address specification
        has_address = any(key in item for key in ["address", "tsig_key", "tsig_key_alg", "tsig_key_name"])
        if not has_address:
            errors.append(f"{acl_name}[{idx}]: ACL item must specify at least one of: address, tsig_key, tsig_key_alg, or tsig_key_name")
        
        # Validate address if present
        if "address" in item:
            address = item["address"]
            # Check if it's a valid IP address or network
            try:
                # Could be IP, network, or "any"
                if address != "any" and address != "localhost" and address != "localnets":
                    if "/" in address:
                        # It's a network
                        from ipaddress import ip_network
                        ip_network(address)
                    else:
                        # It's an IP address
                        ip_address(address)
            except ValueError:
                errors.append(f"{acl_name}[{idx}]: Invalid address '{address}'")
        
        # Validate TSIG key fields if present
        tsig_fields = ["tsig_key", "tsig_key_alg", "tsig_key_name"]
        tsig_present = [f for f in tsig_fields if f in item]
        if tsig_present and len(tsig_present) != len(tsig_fields):
            errors.append(f"{acl_name}[{idx}]: When using TSIG, all fields must be present: {', '.join(tsig_fields)}")
        
        if "tsig_key_alg" in item:
            valid_algs = ["HMAC-MD5", "HMAC-SHA256", "HMAC-SHA1", "HMAC-SHA224", "HMAC-SHA384", "HMAC-SHA512"]
            if item["tsig_key_alg"] not in valid_algs:
                errors.append(f"{acl_name}[{idx}]: Invalid TSIG algorithm '{item['tsig_key_alg']}'")
    
    return errors

def validate_dns_grid_ports(grid_config):
    """Validate DNS Grid port settings."""
    errors = []
    
    port_fields = {
        "dns_notify_transfer_source_port": (1024, 65535),
        "dns_notify_transfer_source_port_ipv6": (1024, 65535),
        "dns_query_source_port": (1024, 65535),
        "dns_query_source_port_ipv6": (1024, 65535)
    }
    
    for field, (min_port, max_port) in port_fields.items():
        if field in grid_config:
            try:
                port = int(grid_config[field])
                if not (min_port <= port <= max_port):
                    errors.append(f"{field}: Port {port} must be between {min_port} and {max_port}")
            except (ValueError, TypeError):
                errors.append(f"{field}: Invalid port value '{grid_config[field]}'")
    
    return errors

def validate_dns_grid_timeouts(grid_config):
    """Validate DNS Grid timeout settings."""
    errors = []
    
    timeout_fields = {
        "lame_ttl": (0, 2147483647),
        "max_cache_ttl": (0, 2147483647),
        "max_ncache_ttl": (0, 2147483647),
        "nxdomain_redirect_ttl": (0, 2147483647),
        "scavenging_interval": (0, 2147483647),
        "zone_deletion_double_confirm": (0, 30)
    }
    
    for field, (min_val, max_val) in timeout_fields.items():
        if field in grid_config:
            try:
                value = int(grid_config[field])
                if not (min_val <= value <= max_val):
                    errors.append(f"{field}: Value {value} must be between {min_val} and {max_val}")
            except (ValueError, TypeError):
                errors.append(f"{field}: Invalid value '{grid_config[field]}'")
    
    return errors

def validate_dns_grid_records():
    """Validate DNS Grid records from JSON file."""
    print("\n--- DNS Grid Validation ---")
    
    dns_grid_file = "playbooks/add/cabgridmgr.amfam.com/dns_grid.json"
    
    # Read DNS Grid data from JSON file
    try:
        with open(dns_grid_file, 'r') as file:
            dns_grid_configs = json.load(file)
            
            # DNS Grid file should contain a list with one configuration
            if not isinstance(dns_grid_configs, list):
                print(f"ERROR: DNS Grid configuration must be a list")
                return False
            
            if len(dns_grid_configs) == 0:
                print(f"DNS Grid file exists but contains no records. Skipping validation.")
                return True
            
            if len(dns_grid_configs) > 1:
                print(f"WARNING: Multiple DNS Grid configurations found. Only one Grid configuration is allowed.")
                print(f"         Will validate the first configuration only.")
            
            dns_grid_config = dns_grid_configs[0]
            print(f"Found DNS Grid configuration to validate.")
            
    except Exception as e:
        print(f"Error reading file {dns_grid_file}: {str(e)}")
        return False
    
    # Now continue with validation
    validation_failed = False
    acl_errors = []
    port_errors = []
    timeout_errors = []
    boolean_errors = []
    enum_errors = []
    warnings = []
    
    # Check if DNS Grid exists
    existing_grids = check_existing_dns_grid()
    if not existing_grids:
        print(f"ERROR: DNS Grid configuration not found in Infoblox")
        print(f"       DNS Grid must exist before it can be updated")
        return False
    
    existing_grid = existing_grids[0]
    print(f"DNS Grid exists in Infoblox")
    
    # Validate ACL configurations
    acl_fields = [
        "allow_query", "allow_transfer", "allow_update",
        "allow_recursive_query", "blacklist",
        "forwarders", "sortlist"
    ]
    
    for acl_field in acl_fields:
        if acl_field in dns_grid_config:
            acl_items = dns_grid_config[acl_field]
            errors = validate_dns_acl_items(acl_items, acl_field)
            if errors:
                acl_errors.extend(errors)
                validation_failed = True
                for error in errors:
                    print(f"ERROR: {error}")
    
    # Validate port settings
    port_errors_list = validate_dns_grid_ports(dns_grid_config)
    if port_errors_list:
        port_errors.extend(port_errors_list)
        validation_failed = True
        for error in port_errors_list:
            print(f"ERROR: {error}")
    
    # Validate timeout settings
    timeout_errors_list = validate_dns_grid_timeouts(dns_grid_config)
    if timeout_errors_list:
        timeout_errors.extend(timeout_errors_list)
        validation_failed = True
        for error in timeout_errors_list:
            print(f"ERROR: {error}")
    
    # Validate boolean fields
    boolean_fields = [
        "allow_gss_tsig_zone_updates", "allow_query_cache_for_rpz",
        "attack_mitigation", "auto_sort_views", "bind_hostname_directive",
        "blackhole_enabled", "capture_dns_queries_on_all_domains",
        "copy_client_ip_mac_options", "copy_xfer_to_notify",
        "disable_edns", "dns64_enabled", "dns_cache_acceleration_enabled",
        "dns_health_check_anycast_control", "dns_health_check_enabled",
        "dns_health_check_recursion_enabled", "dns_health_check_recursion_flag",
        "dnssec_blacklist_enabled", "dnssec_dns64_enabled",
        "dnssec_enabled", "dnssec_expired_signatures_enabled",
        "dnssec_validation_enabled", "enable_blackhole",
        "enable_blacklist", "enable_capture_dns_queries",
        "enable_capture_dns_responses", "enable_client_subnet_forwarding",
        "enable_client_subnet_recursive", "enable_delete_associated_ptr",
        "enable_dns_health_check", "enable_dtc_dns_fall_through",
        "enable_excluded_domain_names", "enable_fixed_rrset_order_fqdns",
        "enable_gss_tsig", "enable_notify_source_port",
        "enable_query_source_port", "enable_response_rate_limiting",
        "file_transfer_setting", "filter_aaaa_on_v4",
        "fixed_rrset_order_fqdns", "ftc_expired_record_timeout",
        "ftc_expired_record_ttl", "gss_tsig_keys",
        "logging_categories", "notify_delay",
        "nxdomain_log_query", "nxdomain_redirect",
        "nxdomain_rulesets", "queries_per_second",
        "recursive_query_list", "response_rate_limiting",
        "restart_setting", "rpz_disable_nsdname_nsip",
        "rpz_drop_ip_rule_enabled", "rpz_drop_ip_rule_min_prefix_length_ipv4",
        "rpz_drop_ip_rule_min_prefix_length_ipv6", "rpz_qname_wait_recurse",
        "serial_query_rate", "server_id_directive",
        "store_locally", "syslog_facility",
        "transfers_in", "transfers_out", "transfers_per_ns"
    ]
    
    for field in boolean_fields:
        if field in dns_grid_config:
            value = dns_grid_config[field]
            if not isinstance(value, bool):
                boolean_errors.append(f"{field}: Must be boolean (true/false), got {type(value).__name__}")
                validation_failed = True
                print(f"ERROR: {field}: Must be boolean (true/false)")
    
    # Validate enum fields
    enum_validations = {
        "default_ttl": (0, 2147483647),
        "email": lambda x: "@" in x if x else True,
        "recursion": ["True", "False"],
        "rpz_qname_wait_recurse": [True, False],
        "syslog_facility": ["LOCAL0", "LOCAL1", "LOCAL2", "LOCAL3", "LOCAL4", "LOCAL5", "LOCAL6", "LOCAL7"]
    }
    
    for field, validation in enum_validations.items():
        if field in dns_grid_config:
            value = dns_grid_config[field]
            if isinstance(validation, tuple):
                # It's a range
                min_val, max_val = validation
                try:
                    num_value = int(value)
                    if not (min_val <= num_value <= max_val):
                        enum_errors.append(f"{field}: Value {num_value} must be between {min_val} and {max_val}")
                        validation_failed = True
                        print(f"ERROR: {field}: Value must be between {min_val} and {max_val}")
                except (ValueError, TypeError):
                    enum_errors.append(f"{field}: Invalid numeric value")
                    validation_failed = True
            elif isinstance(validation, list):
                # It's an enum
                if value not in validation:
                    enum_errors.append(f"{field}: Invalid value '{value}' (must be one of: {', '.join(map(str, validation))})")
                    validation_failed = True
                    print(f"ERROR: {field}: Invalid value '{value}'")
            elif callable(validation):
                # It's a function
                if not validation(value):
                    enum_errors.append(f"{field}: Invalid value '{value}'")
                    validation_failed = True
                    print(f"ERROR: {field}: Invalid value '{value}'")
    
    # Check for read-only fields that will be excluded
    read_only_fields = ['_ref', 'is_grid_default']
    present_read_only = [field for field in read_only_fields if field in dns_grid_config]
    if present_read_only:
        print(f"INFO: Read-only fields will be excluded: {', '.join(present_read_only)}")
    
    # Validate custom root servers if present
    if "custom_root_name_servers" in dns_grid_config:
        root_servers = dns_grid_config["custom_root_name_servers"]
        if not isinstance(root_servers, list):
            print(f"ERROR: custom_root_name_servers must be a list")
            validation_failed = True
        else:
            for idx, server in enumerate(root_servers):
                if "address" not in server:
                    print(f"ERROR: custom_root_name_servers[{idx}]: Missing required field 'address'")
                    validation_failed = True
                else:
                    # Validate IP address
                    try:
                        ip_address(server["address"])
                    except ValueError:
                        print(f"ERROR: custom_root_name_servers[{idx}]: Invalid IP address '{server['address']}'")
                        validation_failed = True
    
    # Check for critical settings that might impact DNS resolution
    critical_settings = {
        "recursion": "Disabling recursion will prevent DNS resolution for non-authoritative zones",
        "dnssec_validation_enabled": "Disabling DNSSEC validation may reduce security",
        "allow_recursive_query": "Restricting recursive queries may impact client resolution",
        "blackhole_enabled": "Enabling blackhole will drop queries for specified addresses"
    }
    
    for setting, warning in critical_settings.items():
        if setting in dns_grid_config:
            value = dns_grid_config[setting]
            if (setting == "recursion" and value == "False") or \
               (setting != "recursion" and value is False):
                warnings.append(f"{setting}: {warning}")
                print(f"WARNING: {setting} is being disabled - {warning}")
    
    # Display changes that will be made
    print("\nChanges to be applied:")
    for key, new_value in dns_grid_config.items():
        if key not in read_only_fields:
            existing_value = existing_grid.get(key)
            if existing_value != new_value:
                print(f"  {key}: {existing_value} → {new_value}")
    
    # Display validation summary
    print("\nDNS Grid Validation Summary:")
    print(f"Configuration exists: Yes")
    print(f"ACL errors: {len(acl_errors)}")
    print(f"Port errors: {len(port_errors)}")
    print(f"Timeout errors: {len(timeout_errors)}")
    print(f"Boolean field errors: {len(boolean_errors)}")
    print(f"Enum field errors: {len(enum_errors)}")
    print(f"Warnings: {len(warnings)}")
    
    return not validation_failed

def check_existing_dns64_group(name):
    """Check if a DNS64 group already exists in Infoblox."""
    try:
        response = requests.get(
            f"{BASE_URL}/dns64group",
            params={"name": name},
            auth=(INFOBLOX_USERNAME, INFOBLOX_PASSWORD),
            verify=VALIDATE_CERTS,
            timeout=HTTP_TIMEOUT
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"✗ Error checking DNS64 group {name}: {response.status_code}")
            return []
    except Exception as e:
        print(f"✗ Error checking DNS64 group {name}: {str(e)}")
        return []

def validate_dns64_group_name(name):
    """Validate DNS64 group name format."""
    if not name:
        return False, "DNS64 group name cannot be empty"
    
    # Check length
    if len(name) > 256:
        return False, f"DNS64 group name too long ({len(name)} characters, max 256)"
    
    # Check for valid characters (alphanumeric, underscore, hyphen, period, space)
    if not re.match(r'^[a-zA-Z0-9._\- ]+$', name):
        return False, "DNS64 group name contains invalid characters (only alphanumeric, underscore, hyphen, period, and space allowed)"
    
    # Cannot start or end with space
    if name.startswith(' ') or name.endswith(' '):
        return False, "DNS64 group name cannot start or end with space"
    
    # Check for multiple consecutive spaces
    if '  ' in name:
        return False, "DNS64 group name cannot contain multiple consecutive spaces"
    
    return True, None

def validate_dns64_prefix(prefix):
    """Validate DNS64 prefix format."""
    if not prefix:
        return False, "DNS64 prefix cannot be empty"
    
    # DNS64 prefix must be an IPv6 network
    try:
        from ipaddress import IPv6Network
        network = IPv6Network(prefix)
        
        # Check prefix length for DNS64 (typically /32, /40, /48, /56, /64, or /96)
        valid_prefix_lengths = [32, 40, 48, 56, 64, 96]
        if network.prefixlen not in valid_prefix_lengths:
            return True, f"Prefix length /{network.prefixlen} is unusual for DNS64 (common: {', '.join(map(str, valid_prefix_lengths))})"
        
        # Check if it's in the well-known prefix range
        well_known_prefix = IPv6Network("64:ff9b::/96")
        if network.overlaps(well_known_prefix):
            print(f"INFO: Using well-known DNS64 prefix range (64:ff9b::/96)")
        
        return True, None
        
    except ValueError as e:
        return False, f"Invalid IPv6 prefix: {str(e)}"

def validate_dns64_clients(clients, group_name):
    """Validate DNS64 client configuration."""
    errors = []
    
    if not isinstance(clients, list):
        errors.append(f"Clients must be a list")
        return errors
    
    for idx, client in enumerate(clients):
        # Check for required fields
        if "source" not in client:
            errors.append(f"Client[{idx}]: Missing required field 'source'")
            continue
        
        source = client["source"]
        
        # Validate source format (can be IP, network, or "any")
        if source not in ["any", "ANY"]:
            try:
                # Try to parse as IP address or network
                if "/" in source:
                    # It's a network
                    from ipaddress import ip_network
                    ip_network(source)
                else:
                    # It's an IP address
                    ip_address(source)
            except ValueError:
                errors.append(f"Client[{idx}]: Invalid source '{source}' (must be IP, network, or 'any')")
        
        # Check for tsig_key fields if any are present
        tsig_fields = ["tsig_key", "tsig_key_alg", "tsig_key_name"]
        tsig_present = [f for f in tsig_fields if f in client]
        
        if tsig_present and len(tsig_present) != len(tsig_fields):
            errors.append(f"Client[{idx}]: When using TSIG, all fields must be present: {', '.join(tsig_fields)}")
        
        if "tsig_key_alg" in client:
            valid_algs = ["HMAC-MD5", "HMAC-SHA256", "HMAC-SHA1", "HMAC-SHA224", "HMAC-SHA384", "HMAC-SHA512"]
            if client["tsig_key_alg"] not in valid_algs:
                errors.append(f"Client[{idx}]: Invalid TSIG algorithm '{client['tsig_key_alg']}'")
    
    return errors

def validate_dns64_mapped(mapped, group_name):
    """Validate DNS64 mapped configuration."""
    errors = []
    
    if not isinstance(mapped, list):
        errors.append(f"Mapped must be a list")
        return errors
    
    for idx, mapping in enumerate(mapped):
        # Check for required fields
        if "mapped" not in mapping:
            errors.append(f"Mapped[{idx}]: Missing required field 'mapped'")
            continue
        
        mapped_value = mapping["mapped"]
        
        # Validate mapped format (IPv4 address or network)
        try:
            if "/" in mapped_value:
                # It's a network
                from ipaddress import IPv4Network
                network = IPv4Network(mapped_value)
                
                # Check if it's a valid IPv4 network for DNS64
                if network.is_private:
                    print(f"INFO: DNS64 group '{group_name}' mapping to private IPv4 network: {mapped_value}")
            else:
                # It's an IP address
                from ipaddress import IPv4Address
                addr = IPv4Address(mapped_value)
                
                if addr.is_private:
                    print(f"INFO: DNS64 group '{group_name}' mapping to private IPv4 address: {mapped_value}")
                    
        except ValueError:
            errors.append(f"Mapped[{idx}]: Invalid IPv4 address or network '{mapped_value}'")
    
    return errors

def validate_dns64_group_records():
    """Validate DNS64 Group records from JSON file."""
    print("\n--- DNS64 Group Validation ---")
    
    dns64_group_file = "playbooks/add/cabgridmgr.amfam.com/dns64group.json"
    
    # Read DNS64 group data from JSON file
    try:
        with open(dns64_group_file, 'r') as file:
            dns64_groups = json.load(file)
            
            # If the content is not a list, convert it to a list
            if not isinstance(dns64_groups, list):
                dns64_groups = [dns64_groups]
            
            # Check if it's empty
            if not dns64_groups:
                print(f"DNS64 group file exists but contains no records. Skipping validation.")
                return True
                
            print(f"Found {len(dns64_groups)} DNS64 groups to validate.")
            
    except Exception as e:
        print(f"Error reading file {dns64_group_file}: {str(e)}")
        return False
    
    # Now continue with validation
    validation_failed = False
    missing_required_fields = []
    invalid_names = []
    invalid_prefixes = []
    invalid_clients = []
    invalid_mapped = []
    duplicate_groups = []
    existing_groups = []
    warnings = []
    
    # Track group names to detect duplicates
    group_names_seen = set()
    
    for group in dns64_groups:
        # Check required fields
        required_fields = ["name", "dns64_prefix"]
        missing_fields = [field for field in required_fields if field not in group]
        if missing_fields:
            missing_required_fields.append(f"{group.get('name', 'Unknown')}: missing {', '.join(missing_fields)}")
            validation_failed = True
            continue
        
        group_name = group["name"]
        
        # Check for duplicate group names in the JSON
        if group_name in group_names_seen:
            duplicate_groups.append(group_name)
            validation_failed = True
            print(f"ERROR: Duplicate group name '{group_name}' found in JSON")
        group_names_seen.add(group_name)
        
        # Validate group name format
        is_valid, error_msg = validate_dns64_group_name(group_name)
        if not is_valid:
            invalid_names.append(f"{group_name}: {error_msg}")
            validation_failed = True
            print(f"ERROR: Group '{group_name}' - {error_msg}")
        
        # Validate DNS64 prefix
        is_valid, msg = validate_dns64_prefix(group["dns64_prefix"])
        if not is_valid:
            invalid_prefixes.append(f"{group_name}: {msg}")
            validation_failed = True
            print(f"ERROR: Group '{group_name}' - {msg}")
        elif msg:  # It's a warning
            warnings.append(f"{group_name}: {msg}")
            print(f"WARNING: Group '{group_name}' - {msg}")
        
        # Validate clients if present
        if "clients" in group:
            client_errors = validate_dns64_clients(group["clients"], group_name)
            if client_errors:
                invalid_clients.extend([f"{group_name}: {error}" for error in client_errors])
                validation_failed = True
                for error in client_errors:
                    print(f"ERROR: Group '{group_name}' - {error}")
        
        # Validate mapped if present
        if "mapped" in group:
            mapped_errors = validate_dns64_mapped(group["mapped"], group_name)
            if mapped_errors:
                invalid_mapped.extend([f"{group_name}: {error}" for error in mapped_errors])
                validation_failed = True
                for error in mapped_errors:
                    print(f"ERROR: Group '{group_name}' - {error}")
        
        # Validate boolean fields
        boolean_fields = ["disable", "exclude", "enable_dns64"]
        for field in boolean_fields:
            if field in group and not isinstance(group[field], bool):
                print(f"ERROR: Group '{group_name}' - {field} must be boolean (true/false)")
                validation_failed = True
        
        # Check if the DNS64 group already exists
        existing_group_records = check_existing_dns64_group(group_name)
        if existing_group_records:
            existing_groups.append(group_name)
            existing = existing_group_records[0]
            print(f"DNS64 Group '{group_name}' already exists")
            
            # Check for significant changes
            if existing.get("dns64_prefix") != group["dns64_prefix"]:
                print(f"  WARNING: DNS64 prefix will be changed from '{existing.get('dns64_prefix')}' to '{group['dns64_prefix']}'")
                print(f"  CRITICAL: Changing DNS64 prefix may affect existing translations!")
        
        # Validate comment length if present
        if "comment" in group and len(group.get("comment", "")) > 256:
            warnings.append(f"{group_name}: Comment exceeds 256 characters")
            print(f"WARNING: Group '{group_name}' - Comment exceeds recommended length")
        
        # Check for fields that will be excluded
        if "_ref" in group:
            print(f"INFO: Group '{group_name}' has '_ref' field - this will be excluded during create/update")
        
        # Logical consistency checks
        if "disable" in group and group["disable"] is True:
            warnings.append(f"{group_name}: Group is disabled")
            print(f"WARNING: Group '{group_name}' is set to disabled state")
        
        if "exclude" in group and group["exclude"]:
            if not isinstance(group["exclude"], list):
                print(f"ERROR: Group '{group_name}' - 'exclude' must be a list")
                validation_failed = True
            else:
                print(f"INFO: Group '{group_name}' has {len(group['exclude'])} exclusions configured")
        
        # Check for DNS64 synthesis settings
        if "enable_dns64" in group and group["enable_dns64"] is False:
            warnings.append(f"{group_name}: DNS64 synthesis is disabled")
            print(f"WARNING: Group '{group_name}' has DNS64 synthesis disabled - this defeats the purpose of DNS64")
        
        # Validate excluded addresses if present
        if "exclude" in group and isinstance(group["exclude"], list):
            for idx, excluded in enumerate(group["exclude"]):
                try:
                    # Should be IPv6 addresses or networks to exclude
                    if "/" in excluded:
                        from ipaddress import IPv6Network
                        IPv6Network(excluded)
                    else:
                        from ipaddress import IPv6Address
                        IPv6Address(excluded)
                except ValueError:
                    print(f"ERROR: Group '{group_name}' - Invalid excluded address/network at index {idx}: '{excluded}'")
                    validation_failed = True
    
    # Check for DNS64 prerequisites
    print("\nDNS64 Prerequisites Check:")
    print("- Ensure DNS64 is enabled on the DNS members")
    print("- Ensure recursive queries are allowed for DNS64 clients")
    print("- Ensure proper routing between IPv6 clients and IPv4 servers")
    
    # Display validation summary
    print("\nDNS64 Group Validation Summary:")
    print(f"Total records checked: {len(dns64_groups)}")
    print(f"Records with missing required fields: {len(missing_required_fields)}")
    print(f"Records with invalid names: {len(invalid_names)}")
    print(f"Records with invalid prefixes: {len(invalid_prefixes)}")
    print(f"Records with invalid clients: {len(invalid_clients)}")
    print(f"Records with invalid mapped: {len(invalid_mapped)}")
    print(f"Duplicate groups in JSON: {len(duplicate_groups)}")
    print(f"Existing groups: {len(existing_groups)}")
    print(f"Warnings: {len(warnings)}")
    
    if existing_groups:
        print(f"\nExisting groups that will be updated: {', '.join(existing_groups)}")
    
    return not validation_failed

def check_existing_dtc_record_a(dtc_server, ipv4addr):
    """Check if a DTC A record already exists in Infoblox."""
    try:
        response = requests.get(
            f"{BASE_URL}/dtc:record:a",
            params={"dtc_server": dtc_server, "ipv4addr": ipv4addr},
            auth=(INFOBLOX_USERNAME, INFOBLOX_PASSWORD),
            verify=VALIDATE_CERTS,
            timeout=HTTP_TIMEOUT
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"✗ Error checking DTC A record for server {dtc_server}: {response.status_code}")
            return []
    except Exception as e:
        print(f"✗ Error checking DTC A record for server {dtc_server}: {str(e)}")
        return []

def check_dtc_server_exists(dtc_server):
    """Check if a DTC server exists in Infoblox."""
    try:
        response = requests.get(
            f"{BASE_URL}/dtc:server",
            params={"name": dtc_server},
            auth=(INFOBLOX_USERNAME, INFOBLOX_PASSWORD),
            verify=VALIDATE_CERTS,
            timeout=HTTP_TIMEOUT
        )
        
        if response.status_code == 200:
            return len(response.json()) > 0
        else:
            print(f"✗ Error checking DTC server {dtc_server}: {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Error checking DTC server {dtc_server}: {str(e)}")
        return False

def check_dtc_pool_exists(dtc_pool):
    """Check if a DTC pool exists in Infoblox."""
    try:
        response = requests.get(
            f"{BASE_URL}/dtc:pool",
            params={"name": dtc_pool},
            auth=(INFOBLOX_USERNAME, INFOBLOX_PASSWORD),
            verify=VALIDATE_CERTS,
            timeout=HTTP_TIMEOUT
        )
        
        if response.status_code == 200:
            return len(response.json()) > 0
        else:
            print(f"✗ Error checking DTC pool {dtc_pool}: {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Error checking DTC pool {dtc_pool}: {str(e)}")
        return False

def validate_dtc_record_name(name):
    """Validate DTC record name format."""
    if not name:
        return False, "DTC record name cannot be empty"
    
    # Check for valid FQDN format
    if len(name) > 255:
        return False, f"DTC record name too long ({len(name)} characters, max 255)"
    
    # Must contain at least one dot for a valid FQDN
    if '.' not in name:
        return False, "DTC record name must be a fully qualified domain name (FQDN)"
    
    # Check each label in the FQDN
    labels = name.split('.')
    for label in labels:
        if len(label) > 63:
            return False, f"Label '{label}' too long ({len(label)} characters, max 63)"
        if len(label) == 0:
            return False, "Empty label found in FQDN"
        if not re.match(r'^[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?$', label) and label != '':
            return False, f"Invalid label '{label}' in FQDN"
    
    return True, None

def validate_dtc_record_a_records():
    """Validate DTC A records from JSON file."""
    print("\n--- DTC A Record Validation ---")
    
    dtc_record_a_file = "playbooks/add/cabgridmgr.amfam.com/dtc_record_a.json"
    
    # Read DTC A record data from JSON file
    try:
        with open(dtc_record_a_file, 'r') as file:
            dtc_record_as = json.load(file)
            
            # If the content is not a list, convert it to a list
            if not isinstance(dtc_record_as, list):
                dtc_record_as = [dtc_record_as]
            
            # Check if it's empty
            if not dtc_record_as:
                print(f"DTC A record file exists but contains no records. Skipping validation.")
                return True
                
            print(f"Found {len(dtc_record_as)} DTC A records to validate.")
            
    except Exception as e:
        print(f"Error reading file {dtc_record_a_file}: {str(e)}")
        return False
    
    # Now continue with validation
    validation_failed = False
    missing_required_fields = []
    invalid_names = []
    invalid_ips = []
    missing_dtc_servers = []
    missing_dtc_pools = []
    duplicate_records = []
    invalid_ttls = []
    warnings = []
    
    # Track records to detect duplicates
    records_seen = set()
    
    # Check if DTC is licensed
    print("INFO: Ensure DTC (DNS Traffic Control) license is installed on Grid")
    
    for record in dtc_record_as:
        # Check required fields
        required_fields = ["name", "ipv4addr", "dtc_server"]
        missing_fields = [field for field in required_fields if field not in record]
        if missing_fields:
            missing_required_fields.append(f"{record.get('name', 'Unknown')}: missing {', '.join(missing_fields)}")
            validation_failed = True
            continue
        
        record_name = record["name"]
        ipv4addr = record["ipv4addr"]
        dtc_server = record["dtc_server"]
        
        # Create unique identifier for duplicate detection
        record_key = f"{record_name}:{ipv4addr}:{dtc_server}"
        if record_key in records_seen:
            duplicate_records.append(record_key)
            validation_failed = True
            print(f"ERROR: Duplicate DTC A record found: {record_key}")
        records_seen.add(record_key)
        
        # Validate record name format
        is_valid, error_msg = validate_dtc_record_name(record_name)
        if not is_valid:
            invalid_names.append(f"{record_name}: {error_msg}")
            validation_failed = True
            print(f"ERROR: Record '{record_name}' - {error_msg}")
        
        # Validate IPv4 address
        if not validate_ipv4_format(ipv4addr):
            invalid_ips.append(f"{record_name}: {ipv4addr}")
            validation_failed = True
            print(f"ERROR: Record '{record_name}' - Invalid IPv4 address: {ipv4addr}")
        
        # Check if DTC server exists
        if not check_dtc_server_exists(dtc_server):
            missing_dtc_servers.append(f"{record_name}: DTC server '{dtc_server}'")
            validation_failed = True
            print(f"ERROR: Record '{record_name}' - DTC server '{dtc_server}' does not exist")
        
        # Check if DTC pool exists (if specified)
        if "dtc_pool" in record:
            if not check_dtc_pool_exists(record["dtc_pool"]):
                missing_dtc_pools.append(f"{record_name}: DTC pool '{record['dtc_pool']}'")
                validation_failed = True
                print(f"ERROR: Record '{record_name}' - DTC pool '{record['dtc_pool']}' does not exist")
        
        # Validate TTL if specified
        if "ttl" in record and record["ttl"] is not None:
            try:
                ttl = int(record["ttl"])
                if ttl < 0 or ttl > 2147483647:
                    invalid_ttls.append(f"{record_name}: TTL {ttl} (must be 0-2147483647)")
                    validation_failed = True
                    print(f"ERROR: Record '{record_name}' - Invalid TTL: {ttl}")
            except (ValueError, TypeError):
                invalid_ttls.append(f"{record_name}: TTL '{record['ttl']}' is not a valid integer")
                validation_failed = True
                print(f"ERROR: Record '{record_name}' - TTL must be an integer")
        
        # Validate boolean fields
        boolean_fields = ["disable", "use_ttl", "auto_create_ptr"]
        for field in boolean_fields:
            if field in record and not isinstance(record[field], bool):
                print(f"ERROR: Record '{record_name}' - {field} must be boolean (true/false)")
                validation_failed = True
        
        # Check if the DTC A record already exists
        existing_records = check_existing_dtc_record_a(dtc_server, ipv4addr)
        if existing_records:
            existing = existing_records[0]
            print(f"DTC A record for server '{dtc_server}' with IP {ipv4addr} already exists")
            
            # Check for name conflicts
            if existing.get("name") != record_name:
                print(f"  WARNING: Existing record has different name: '{existing.get('name')}' vs '{record_name}'")
                print(f"  CRITICAL: This may indicate a conflict in DTC configuration!")
        
        # Validate comment length if present
        if "comment" in record and len(record.get("comment", "")) > 256:
            warnings.append(f"{record_name}: Comment exceeds 256 characters")
            print(f"WARNING: Record '{record_name}' - Comment exceeds recommended length")
        
        # Check for disabled records
        if record.get("disable", False):
            warnings.append(f"{record_name}: Record is disabled")
            print(f"WARNING: Record '{record_name}' is set to disabled state")
        
        # Check for auto PTR creation
        if record.get("auto_create_ptr", False):
            print(f"INFO: Record '{record_name}' has auto PTR creation enabled")
            # Check if reverse zone exists for this IP
            octets = ipv4addr.split('.')
            reverse_zone = f"{octets[2]}.{octets[1]}.{octets[0]}.in-addr.arpa"
            print(f"      Ensure reverse zone '{reverse_zone}' or parent exists for PTR creation")
    
    # Check for DTC configuration consistency
    print("\nDTC Configuration Checks:")
    
    # Group records by DTC server
    servers_used = {}
    for record in dtc_record_as:
        if "dtc_server" in record:
            server = record["dtc_server"]
            if server not in servers_used:
                servers_used[server] = []
            servers_used[server].append(record.get("name", "Unknown"))
    
    print(f"DTC servers in use: {', '.join(servers_used.keys())}")
    for server, names in servers_used.items():
        print(f"  {server}: {len(names)} records")
    
    # Check for records with same name but different IPs (load balancing scenario)
    name_to_ips = {}
    for record in dtc_record_as:
        if "name" in record and "ipv4addr" in record:
            name = record["name"]
            ip = record["ipv4addr"]
            if name not in name_to_ips:
                name_to_ips[name] = set()
            name_to_ips[name].add(ip)
    
    for name, ips in name_to_ips.items():
        if len(ips) > 1:
            print(f"INFO: Name '{name}' has multiple IPs (load balancing): {', '.join(sorted(ips))}")
    
    # Display validation summary
    print("\nDTC A Record Validation Summary:")
    print(f"Total records checked: {len(dtc_record_as)}")
    print(f"Records with missing required fields: {len(missing_required_fields)}")
    print(f"Records with invalid names: {len(invalid_names)}")
    print(f"Records with invalid IPs: {len(invalid_ips)}")
    print(f"Missing DTC servers: {len(missing_dtc_servers)}")
    print(f"Missing DTC pools: {len(missing_dtc_pools)}")
    print(f"Duplicate records: {len(duplicate_records)}")
    print(f"Records with invalid TTLs: {len(invalid_ttls)}")
    print(f"Warnings: {len(warnings)}")
    
    print("\nDTC Prerequisites:")
    print("- Ensure DTC license is installed")
    print("- Ensure DTC servers are configured and running")
    print("- Ensure DTC pools are created (if referenced)")
    print("- Ensure health monitors are configured for pools")
    
    return not validation_failed

def check_existing_fingerprint(name):
    """Check if a DHCP fingerprint already exists in Infoblox."""
    try:
        response = requests.get(
            f"{BASE_URL}/fingerprint",
            params={"name": name},
            auth=(INFOBLOX_USERNAME, INFOBLOX_PASSWORD),
            verify=VALIDATE_CERTS,
            timeout=HTTP_TIMEOUT
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"✗ Error checking DHCP fingerprint {name}: {response.status_code}")
            return []
    except Exception as e:
        print(f"✗ Error checking DHCP fingerprint {name}: {str(e)}")
        return []

def get_all_existing_fingerprints():
    """Get all existing DHCP fingerprints from Infoblox."""
    try:
        response = requests.get(
            f"{BASE_URL}/fingerprint",
            auth=(INFOBLOX_USERNAME, INFOBLOX_PASSWORD),
            verify=VALIDATE_CERTS,
            timeout=HTTP_TIMEOUT
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"✗ Error getting all fingerprints: {response.status_code}")
            return []
    except Exception as e:
        print(f"✗ Error getting all fingerprints: {str(e)}")
        return []

def validate_fingerprint_name(name):
    """Validate DHCP fingerprint name format."""
    if not name:
        return False, "Fingerprint name cannot be empty"
    
    # Check length
    if len(name) > 256:
        return False, f"Fingerprint name too long ({len(name)} characters, max 256)"
    
    # Check for valid characters
    if not re.match(r'^[a-zA-Z0-9._\-\s]+$', name):
        return False, "Fingerprint name contains invalid characters (only alphanumeric, underscore, hyphen, period, and space allowed)"
    
    # Cannot start or end with space
    if name.startswith(' ') or name.endswith(' '):
        return False, "Fingerprint name cannot start or end with space"
    
    return True, None

def validate_option_sequence(option_sequence, fingerprint_name):
    """Validate DHCP option sequence."""
    errors = []
    
    if not isinstance(option_sequence, list):
        errors.append("Option sequence must be a list")
        return errors
    
    if len(option_sequence) == 0:
        errors.append("Option sequence cannot be empty")
        return errors
    
    # Check for valid option numbers
    seen_options = set()
    for option in option_sequence:
        try:
            option_num = int(option)
            
            # DHCP option numbers are 0-255
            if not (0 <= option_num <= 255):
                errors.append(f"Option {option_num} is out of range (must be 0-255)")
            
            # Check for duplicates within the sequence
            if option_num in seen_options:
                errors.append(f"Duplicate option {option_num} in sequence")
            seen_options.add(option_num)
            
        except (ValueError, TypeError):
            errors.append(f"Invalid option value '{option}' (must be integer)")
    
    return errors

def validate_fingerprint_type(fingerprint_type):
    """Validate fingerprint type."""
    valid_types = ["DEVICE", "VENDOR", "CLASS", "CUSTOM"]
    if fingerprint_type and fingerprint_type not in valid_types:
        return False, f"Invalid fingerprint type. Must be one of: {', '.join(valid_types)}"
    return True, None

def validate_vendor_info(vendor_info):
    """Validate vendor information structure."""
    errors = []
    
    if not isinstance(vendor_info, list):
        errors.append("Vendor info must be a list")
        return errors
    
    for idx, vendor in enumerate(vendor_info):
        # Check for required fields in vendor info
        if not isinstance(vendor, dict):
            errors.append(f"Vendor info[{idx}] must be a dictionary")
            continue
        
        if "vendor_name" not in vendor:
            errors.append(f"Vendor info[{idx}]: Missing required field 'vendor_name'")
        elif not vendor["vendor_name"]:
            errors.append(f"Vendor info[{idx}]: Vendor name cannot be empty")
        
        # Validate option_list if present
        if "option_list" in vendor:
            if not isinstance(vendor["option_list"], list):
                errors.append(f"Vendor info[{idx}]: option_list must be a list")
            else:
                for opt_idx, option in enumerate(vendor["option_list"]):
                    try:
                        opt_num = int(option)
                        if not (0 <= opt_num <= 255):
                            errors.append(f"Vendor info[{idx}]: Option {opt_num} out of range")
                    except (ValueError, TypeError):
                        errors.append(f"Vendor info[{idx}]: Invalid option '{option}'")
    
    return errors

def validate_dhcp_fingerprint_records():
    """Validate DHCP Fingerprint records from JSON file."""
    print("\n--- DHCP Fingerprint Validation ---")
    
    fingerprint_file = "playbooks/add/cabgridmgr.amfam.com/fingerprint.json"
    
    # Read fingerprint data from JSON file
    try:
        with open(fingerprint_file, 'r') as file:
            fingerprint_data = json.load(file)
            
            # If the content is not a list, convert it to a list
            if not isinstance(fingerprint_data, list):
                fingerprint_data = [fingerprint_data]
            
            # Check if it's empty
            if not fingerprint_data:
                print(f"Fingerprint file exists but contains no records. Skipping validation.")
                return True
                
            print(f"Found {len(fingerprint_data)} DHCP fingerprints to validate.")
            
    except Exception as e:
        print(f"Error reading file {fingerprint_file}: {str(e)}")
        return False
    
    # Get all existing fingerprints for option sequence conflict detection
    all_existing_fingerprints = get_all_existing_fingerprints()
    existing_option_sequences = []
    existing_names = set()
    
    for existing in all_existing_fingerprints:
        if "option_sequence" in existing:
            existing_option_sequences.append({
                "name": existing.get("name", "Unknown"),
                "sequence": existing["option_sequence"]
            })
        if "name" in existing:
            existing_names.add(existing["name"])
    
    # Now continue with validation
    validation_failed = False
    missing_required_fields = []
    invalid_names = []
    invalid_option_sequences = []
    invalid_types = []
    invalid_vendor_info = []
    sequence_conflicts = []
    duplicate_names = []
    warnings = []
    
    # Track names to detect duplicates within the file
    names_in_file = set()
    
    for fingerprint in fingerprint_data:
        # Check required fields
        required_fields = ["name", "option_sequence"]
        missing_fields = [field for field in required_fields if field not in fingerprint]
        if missing_fields:
            missing_required_fields.append(f"{fingerprint.get('name', 'Unknown')}: missing {', '.join(missing_fields)}")
            validation_failed = True
            continue
        
        fingerprint_name = fingerprint["name"]
        
        # Check for duplicate names within the file
        if fingerprint_name in names_in_file:
            duplicate_names.append(fingerprint_name)
            validation_failed = True
            print(f"ERROR: Duplicate fingerprint name '{fingerprint_name}' in file")
        names_in_file.add(fingerprint_name)
        
        # Validate name format
        is_valid, error_msg = validate_fingerprint_name(fingerprint_name)
        if not is_valid:
            invalid_names.append(f"{fingerprint_name}: {error_msg}")
            validation_failed = True
            print(f"ERROR: Fingerprint '{fingerprint_name}' - {error_msg}")
        
        # Validate option sequence
        option_sequence_errors = validate_option_sequence(fingerprint["option_sequence"], fingerprint_name)
        if option_sequence_errors:
            invalid_option_sequences.extend([f"{fingerprint_name}: {error}" for error in option_sequence_errors])
            validation_failed = True
            for error in option_sequence_errors:
                print(f"ERROR: Fingerprint '{fingerprint_name}' - {error}")
        
        # Check for option sequence conflicts with existing fingerprints
        fingerprint_sequence = fingerprint["option_sequence"]
        for existing in existing_option_sequences:
            if existing["sequence"] == fingerprint_sequence and existing["name"] != fingerprint_name:
                sequence_conflicts.append(
                    f"'{fingerprint_name}' has same option sequence as existing fingerprint '{existing['name']}': {fingerprint_sequence}"
                )
                validation_failed = True
                print(f"ERROR: Option sequence conflict - '{fingerprint_name}' matches '{existing['name']}'")
        
        # Validate fingerprint type if present
        if "type" in fingerprint:
            is_valid, error_msg = validate_fingerprint_type(fingerprint["type"])
            if not is_valid:
                invalid_types.append(f"{fingerprint_name}: {error_msg}")
                validation_failed = True
                print(f"ERROR: Fingerprint '{fingerprint_name}' - {error_msg}")
        
        # Validate vendor info if present
        if "vendor_info" in fingerprint:
            vendor_errors = validate_vendor_info(fingerprint["vendor_info"])
            if vendor_errors:
                invalid_vendor_info.extend([f"{fingerprint_name}: {error}" for error in vendor_errors])
                validation_failed = True
                for error in vendor_errors:
                    print(f"ERROR: Fingerprint '{fingerprint_name}' - {error}")
        
        # Check if fingerprint exists by name
        if fingerprint_name in existing_names:
            print(f"Fingerprint '{fingerprint_name}' already exists and will be updated")
            
            # Find the existing fingerprint details
            existing_fingerprint = next((f for f in all_existing_fingerprints if f.get("name") == fingerprint_name), None)
            if existing_fingerprint and existing_fingerprint.get("option_sequence") != fingerprint_sequence:
                print(f"  WARNING: Option sequence will change from {existing_fingerprint.get('option_sequence')} to {fingerprint_sequence}")
        
        # Validate comment length if present
        if "comment" in fingerprint and len(fingerprint.get("comment", "")) > 256:
            warnings.append(f"{fingerprint_name}: Comment exceeds 256 characters")
            print(f"WARNING: Fingerprint '{fingerprint_name}' - Comment exceeds recommended length")
        
        # Validate device class if present
        if "device_class" in fingerprint and not fingerprint["device_class"]:
            warnings.append(f"{fingerprint_name}: Device class is empty")
            print(f"WARNING: Fingerprint '{fingerprint_name}' - Device class is empty")
        
        # Validate boolean fields
        boolean_fields = ["disable"]
        for field in boolean_fields:
            if field in fingerprint and not isinstance(fingerprint[field], bool):
                print(f"ERROR: Fingerprint '{fingerprint_name}' - {field} must be boolean (true/false)")
                validation_failed = True
        
        # Check for disabled fingerprints
        if fingerprint.get("disable", False):
            warnings.append(f"{fingerprint_name}: Fingerprint is disabled")
            print(f"WARNING: Fingerprint '{fingerprint_name}' is disabled")
    
    # Display well-known DHCP options for reference
    print("\nCommon DHCP Options Reference:")
    well_known_options = {
        1: "Subnet Mask",
        3: "Router",
        6: "Domain Name Server",
        12: "Host Name",
        15: "Domain Name",
        28: "Broadcast Address",
        43: "Vendor Specific Information",
        51: "IP Address Lease Time",
        53: "DHCP Message Type",
        54: "Server Identifier",
        55: "Parameter Request List",
        57: "Maximum DHCP Message Size",
        58: "Renewal Time",
        59: "Rebinding Time",
        60: "Vendor Class Identifier",
        61: "Client Identifier",
        66: "TFTP Server Name",
        67: "Bootfile Name",
        82: "Relay Agent Information",
        93: "Client System Architecture",
        94: "Client Network Interface Identifier",
        97: "Client Machine Identifier"
    }
    
    # Check if any fingerprints use these well-known options
    for fingerprint in fingerprint_data:
        if "option_sequence" in fingerprint:
            used_options = []
            for opt in fingerprint["option_sequence"]:
                try:
                    opt_num = int(opt)
                    if opt_num in well_known_options:
                        used_options.append(f"{opt_num} ({well_known_options[opt_num]})")
                except:
                    pass
            
            if used_options:
                print(f"INFO: '{fingerprint['name']}' uses options: {', '.join(used_options)}")
    
    # Display validation summary
    print("\nDHCP Fingerprint Validation Summary:")
    print(f"Total records checked: {len(fingerprint_data)}")
    print(f"Records with missing required fields: {len(missing_required_fields)}")
    print(f"Records with invalid names: {len(invalid_names)}")
    print(f"Records with invalid option sequences: {len(invalid_option_sequences)}")
    print(f"Records with invalid types: {len(invalid_types)}")
    print(f"Records with invalid vendor info: {len(invalid_vendor_info)}")
    print(f"Option sequence conflicts: {len(sequence_conflicts)}")
    print(f"Duplicate names in file: {len(duplicate_names)}")
    print(f"Warnings: {len(warnings)}")
    
    return not validation_failed

def check_existing_grid_dhcp_properties():
    """Check if Grid DHCP Properties exist and get current configuration."""
    try:
        response = requests.get(
            f"{BASE_URL}/grid:dhcpproperties",
            auth=(INFOBLOX_USERNAME, INFOBLOX_PASSWORD),
            verify=VALIDATE_CERTS,
            timeout=HTTP_TIMEOUT
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"✗ Error checking Grid DHCP Properties: {response.status_code}")
            return []
    except Exception as e:
        print(f"✗ Error checking Grid DHCP Properties: {str(e)}")
        return []

def validate_grid_dhcp_options(options, property_name):
    """Validate DHCP options structure for Grid DHCP Properties."""
    errors = []
    
    if not isinstance(options, list):
        errors.append(f"{property_name}: Options must be a list")
        return errors
    
    for idx, option in enumerate(options):
        # Check required fields
        if "name" not in option:
            errors.append(f"{property_name}[{idx}]: Missing required field 'name'")
            continue
        
        if "num" not in option:
            errors.append(f"{property_name}[{idx}]: Missing required field 'num'")
            continue
        
        # Validate option number
        try:
            option_num = int(option["num"])
            if not (1 <= option_num <= 254):
                errors.append(f"{property_name}[{idx}]: Option number {option_num} must be between 1 and 254")
        except (ValueError, TypeError):
            errors.append(f"{property_name}[{idx}]: Option number '{option['num']}' must be a valid integer")
        
        # Validate use_option if present
        if "use_option" in option and not isinstance(option["use_option"], bool):
            errors.append(f"{property_name}[{idx}]: use_option must be boolean")
        
        # Validate vendor_class if present
        if "vendor_class" in option:
            valid_vendor_classes = ["DHCP", "DHCPv4", "DHCPv6"]
            if option["vendor_class"] not in valid_vendor_classes:
                errors.append(f"{property_name}[{idx}]: Invalid vendor_class '{option['vendor_class']}'")
    
    return errors

def validate_grid_dhcp_lease_times(grid_dhcp_properties):
    """Validate Grid DHCP lease time settings."""
    errors = []
    
    lease_time_fields = {
        "bootfile_name": (0, 2147483647),
        "bootserver": (0, 2147483647),
        "enable_ddns": "boolean",
        "ddns_generate_hostname": "boolean",
        "ddns_ttl": (0, 2147483647),
        "deny_bootp": "boolean",
        "disable_all_nac_filters": "boolean",
        "dns_update_style": ["NONE", "INTERIM", "STANDARD"],
        "email_list": "email_list",
        "enable_dhcp_on_lan2": "boolean",
        "enable_email_warnings": "boolean",
        "enable_fingerprint": "boolean",
        "enable_gss_tsig": "boolean",
        "enable_hostname_rewrite": "boolean",
        "enable_leasequery": "boolean",
        "enable_snmp_warnings": "boolean",
        "format_log_option_82": "boolean",
        "gss_tsig_keys": "list",
        "high_water_mark": (0, 100),
        "high_water_mark_reset": (0, 100),
        "hostname_rewrite_policy": "string",
        "ignore_dhcp_option_list_request": "boolean",
        "ignore_id": ["NONE", "CLIENT", "MACADDR"],
        "ignore_mac_addresses": "list",
        "immediate_fa_configuration": "boolean",
        "ipv6_captive_portal": "boolean",
        "ipv6_ddns_enable_option_fqdn": "boolean",
        "ipv6_ddns_hostname": "string",
        "ipv6_ddns_ttl": (0, 2147483647),
        "ipv6_dns_update_style": ["NONE", "INTERIM", "STANDARD"],
        "ipv6_domain_name": "string",
        "ipv6_domain_name_servers": "list",
        "ipv6_enable_ddns": "boolean",
        "ipv6_enable_gss_tsig": "boolean",
        "ipv6_enable_lease_scavenging": "boolean",
        "ipv6_enable_retry_updates": "boolean",
        "ipv6_generate_hostname": "boolean",
        "ipv6_gss_tsig_keys": "list",
        "ipv6_kdc_server": "string",
        "ipv6_microsoft_code_page": "string",
        "ipv6_options": "list",
        "ipv6_prefixes": "list",
        "ipv6_recycle_leases": "boolean",
        "ipv6_remember_expired_client_association": "boolean",
        "ipv6_retry_updates_interval": (0, 2147483647),
        "ipv6_update_dns_on_lease_renewal": "boolean",
        "kdc_server": "string",
        "lease_logging_member": "string",
        "lease_per_client_settings": ["DISABLED", "ENABLE_DHCP", "ENABLE_DHCP_BOOTP"],
        "lease_scavenge_time": (0, 2147483647),
        "log_lease_events": "boolean",
        "logic_filter_rules": "list",
        "low_water_mark": (0, 100),
        "low_water_mark_reset": (0, 100),
        "microsoft_code_page": "string",
        "nextserver": "string",
        "option60_match_rules": "list",
        "options": "list",
        "ping_count": (0, 10),
        "ping_timeout": (0, 10000),
        "preferred_lifetime": (0, 2147483647),
        "prefix_length_mode": ["PREFER", "EXACT", "MINIMUM"],
        "pxe_lease_time": (0, 2147483647),
        "recycle_leases": "boolean",
        "restart_setting": "dict",
        "retry_ddns_updates": "boolean",
        "snmp_trap_settings": "dict",
        "syslog_facility": ["LOCAL0", "LOCAL1", "LOCAL2", "LOCAL3", "LOCAL4", "LOCAL5", "LOCAL6", "LOCAL7"],
        "update_dns_on_lease_renewal": "boolean",
        "valid_lifetime": (0, 2147483647)
    }
    
    for field, validation in lease_time_fields.items():
        if field not in grid_dhcp_properties:
            continue
            
        value = grid_dhcp_properties[field]
        
        if validation == "boolean":
            if not isinstance(value, bool):
                errors.append(f"{field}: Must be boolean (true/false)")
        elif validation == "string":
            if not isinstance(value, str):
                errors.append(f"{field}: Must be a string")
        elif validation == "list":
            if not isinstance(value, list):
                errors.append(f"{field}: Must be a list")
        elif validation == "dict":
            if not isinstance(value, dict):
                errors.append(f"{field}: Must be a dictionary")
        elif validation == "email_list":
            if isinstance(value, list):
                for email in value:
                    if "@" not in email:
                        errors.append(f"{field}: Invalid email address '{email}'")
            else:
                errors.append(f"{field}: Must be a list of email addresses")
        elif isinstance(validation, list):
            # It's an enum
            if value not in validation:
                errors.append(f"{field}: Invalid value '{value}' (must be one of: {', '.join(validation)})")
        elif isinstance(validation, tuple):
            # It's a range
            min_val, max_val = validation
            try:
                num_value = int(value)
                if not (min_val <= num_value <= max_val):
                    errors.append(f"{field}: Value {num_value} must be between {min_val} and {max_val}")
            except (ValueError, TypeError):
                errors.append(f"{field}: Must be a valid integer")
    
    return errors

def validate_grid_dhcp_properties_records():
    """Validate Grid DHCP Properties records from JSON file."""
    print("\n--- Grid DHCP Properties Validation ---")
    
    grid_dhcp_properties_file = "playbooks/add/cabgridmgr.amfam.com/grid_dhcp_properties.json"
    
    # Read Grid DHCP Properties data from JSON file
    try:
        with open(grid_dhcp_properties_file, 'r') as file:
            grid_dhcp_properties_data = json.load(file)
            
            # Grid DHCP Properties should be a dictionary (single object)
            if not isinstance(grid_dhcp_properties_data, dict):
                print(f"ERROR: Grid DHCP Properties must be a dictionary/object")
                return False
            
            # Check if it's empty
            if not grid_dhcp_properties_data:
                print(f"Grid DHCP Properties file exists but contains no data. Skipping validation.")
                return True
                
            print(f"Found Grid DHCP Properties configuration to validate.")
            
    except Exception as e:
        print(f"Error reading file {grid_dhcp_properties_file}: {str(e)}")
        return False
    
    # Check if Grid DHCP Properties exist
    existing_properties = check_existing_grid_dhcp_properties()
    if not existing_properties:
        print(f"ERROR: Grid DHCP Properties not found in Infoblox")
        print(f"       Grid DHCP Properties must exist before they can be updated")
        return False
    
    existing_config = existing_properties[0]
    print(f"Grid DHCP Properties exist in Infoblox")
    
    # Now continue with validation
    validation_failed = False
    option_errors = []
    lease_time_errors = []
    boolean_errors = []
    warnings = []
    
    # Validate options if present
    if "options" in grid_dhcp_properties_data:
        errors = validate_grid_dhcp_options(grid_dhcp_properties_data["options"], "options")
        if errors:
            option_errors.extend(errors)
            validation_failed = True
            for error in errors:
                print(f"ERROR: {error}")
    
    # Validate IPv6 options if present
    if "ipv6_options" in grid_dhcp_properties_data:
        errors = validate_grid_dhcp_options(grid_dhcp_properties_data["ipv6_options"], "ipv6_options")
        if errors:
            option_errors.extend(errors)
            validation_failed = True
            for error in errors:
                print(f"ERROR: {error}")
    
    # Validate all lease time and other settings
    lease_errors = validate_grid_dhcp_lease_times(grid_dhcp_properties_data)
    if lease_errors:
        lease_time_errors.extend(lease_errors)
        validation_failed = True
        for error in lease_errors:
            print(f"ERROR: {error}")
    
    # Check for read-only fields that will be excluded
    read_only_fields = ['_ref']
    present_read_only = [field for field in read_only_fields if field in grid_dhcp_properties_data]
    if present_read_only:
        print(f"INFO: Read-only fields will be excluded: {', '.join(present_read_only)}")
    
    # Validate critical settings
    critical_settings = {
        "deny_bootp": "Denying BOOTP may affect legacy devices",
        "disable_all_nac_filters": "Disabling NAC filters reduces security",
        "enable_fingerprint": "Fingerprinting helps with device identification",
        "enable_leasequery": "Lease query is useful for troubleshooting",
        "ignore_dhcp_option_list_request": "Ignoring option requests may break client functionality",
        "recycle_leases": "Lease recycling affects IP address allocation",
        "ipv6_recycle_leases": "IPv6 lease recycling affects address allocation"
    }
    
    for setting, description in critical_settings.items():
        if setting in grid_dhcp_properties_data:
            value = grid_dhcp_properties_data[setting]
            if setting.startswith("enable_") and value is False:
                warnings.append(f"{setting}: Disabling this feature - {description}")
                print(f"WARNING: {setting} is being disabled - {description}")
            elif setting.startswith("deny_") and value is True:
                warnings.append(f"{setting}: Enabling denial - {description}")
                print(f"WARNING: {setting} is being enabled - {description}")
            elif setting.startswith("disable_") and value is True:
                warnings.append(f"{setting}: Disabling feature - {description}")
                print(f"WARNING: {setting} is being enabled - {description}")
    
    # Validate high/low water marks
    if "high_water_mark" in grid_dhcp_properties_data and "low_water_mark" in grid_dhcp_properties_data:
        high = grid_dhcp_properties_data["high_water_mark"]
        low = grid_dhcp_properties_data["low_water_mark"]
        try:
            if int(high) <= int(low):
                print(f"ERROR: high_water_mark ({high}) must be greater than low_water_mark ({low})")
                validation_failed = True
        except:
            pass  # Already validated as integers above
    
    # Validate related settings
    if grid_dhcp_properties_data.get("enable_ddns", False):
        if "dns_update_style" not in grid_dhcp_properties_data or grid_dhcp_properties_data["dns_update_style"] == "NONE":
            warnings.append("DDNS is enabled but dns_update_style is NONE or not set")
            print(f"WARNING: DDNS is enabled but dns_update_style is NONE or not set")
    
    # Display changes that will be made
    print("\nChanges to be applied:")
    for key, new_value in grid_dhcp_properties_data.items():
        if key not in read_only_fields:
            existing_value = existing_config.get(key)
            if existing_value != new_value:
                # Truncate long values for display
                if isinstance(new_value, (list, dict)) and len(str(new_value)) > 100:
                    new_display = f"{type(new_value).__name__} with {len(new_value)} items"
                else:
                    new_display = str(new_value)
                
                if isinstance(existing_value, (list, dict)) and len(str(existing_value)) > 100:
                    existing_display = f"{type(existing_value).__name__} with {len(existing_value)} items"
                else:
                    existing_display = str(existing_value)
                
                print(f"  {key}: {existing_display} → {new_display}")
    
    # Display validation summary
    print("\nGrid DHCP Properties Validation Summary:")
    print(f"Configuration exists: Yes")
    print(f"Option errors: {len(option_errors)}")
    print(f"Setting errors: {len(lease_time_errors)}")
    print(f"Boolean field errors: {len(boolean_errors)}")
    print(f"Warnings: {len(warnings)}")
    
    return not validation_failed

def check_existing_grid_dns_properties():
    """Check if Grid DNS Properties exist and get current configuration."""
    try:
        response = requests.get(
            f"{BASE_URL}/grid:dns",
            auth=(INFOBLOX_USERNAME, INFOBLOX_PASSWORD),
            verify=VALIDATE_CERTS,
            timeout=HTTP_TIMEOUT
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"✗ Error checking Grid DNS Properties: {response.status_code}")
            return []
    except Exception as e:
        print(f"✗ Error checking Grid DNS Properties: {str(e)}")
        return []

def validate_grid_dns_properties_records():
    """Validate Grid DNS Properties records from JSON file."""
    print("\n--- Grid DNS Properties Validation ---")
    
    grid_dns_properties_file = "../prod_changes/cabgridmgr.amfam.com/grid_dns_properties.json"
    
    # Read Grid DNS Properties data from JSON file
    try:
        with open(grid_dns_properties_file, 'r') as file:
            grid_dns_properties_data = json.load(file)
            
            # Grid DNS Properties should be a dictionary (single object)
            if not isinstance(grid_dns_properties_data, dict):
                print(f"ERROR: Grid DNS Properties must be a dictionary/object")
                return False
            
            # Check if it's empty
            if not grid_dns_properties_data:
                print(f"Grid DNS Properties file exists but contains no data. Skipping validation.")
                return True
                
            print(f"Found Grid DNS Properties configuration to validate.")
            
    except Exception as e:
        print(f"Error reading file {grid_dns_properties_file}: {str(e)}")
        return False
    
    # Check if Grid DNS Properties exist
    existing_properties = check_existing_grid_dns_properties()
    if not existing_properties:
        print(f"ERROR: Grid DNS Properties not found in Infoblox")
        print(f"       Grid DNS must exist before properties can be updated")
        return False
    
    existing_config = existing_properties[0]
    print(f"Grid DNS Properties exist in Infoblox")
    
    # Now continue with validation
    validation_failed = False
    boolean_errors = []
    enum_errors = []
    timeout_errors = []
    acl_errors = []
    warnings = []
    
    # Validate boolean fields
    boolean_fields = [
        "allow_bulkhost_ddns", "allow_gss_tsig_zone_updates",
        "allow_query_cache_for_rpz", "allow_recursive_query",
        "attack_mitigation", "auto_sort_views", "bind_check_names_policy",
        "blackhole_enabled", "blacklist_log_query", "blacklist_redirect_addresses",
        "blacklist_redirect_ttl", "blacklist_rulesets", "blacklist_action",
        "capture_dns_queries_on_all_domains", "copy_client_ip_mac_options",
        "copy_xfer_to_notify", "disable_edns", "dns64_enabled",
        "dns_cache_acceleration_enabled", "dns_health_check_anycast_control",
        "dns_health_check_enabled", "dns_health_check_recursion_enabled",
        "dns_health_check_recursion_flag", "dnssec_blacklist_enabled",
        "dnssec_dns64_enabled", "dnssec_enabled", "dnssec_expired_signatures_enabled",
        "dnssec_validation_enabled", "dtc_dns_fall_through", "dtc_edns_prefer_client_subnet",
        "enable_blackhole", "enable_blacklist", "enable_capture_dns_queries",
        "enable_capture_dns_responses", "enable_client_subnet_forwarding",
        "enable_client_subnet_recursive", "enable_delete_associated_ptr",
        "enable_dns_health_check", "enable_dtc_dns_fall_through",
        "enable_excluded_domain_names", "enable_fixed_rrset_order_fqdns",
        "enable_gss_tsig", "enable_notify_source_port", "enable_query_source_port",
        "enable_response_rate_limiting", "filter_aaaa_on_v4", "forward_only",
        "forward_updates", "gss_tsig_keys", "logging_categories",
        "notify_delay", "nxdomain_log_query", "nxdomain_redirect",
        "nxdomain_redirect_addresses", "nxdomain_redirect_addresses_v6",
        "nxdomain_redirect_ttl", "nxdomain_rulesets", "queries_per_second",
        "recursive_query_list", "response_rate_limiting", "rpz_disable_nsdname_nsip",
        "rpz_drop_ip_rule_enabled", "rpz_drop_ip_rule_min_prefix_length_ipv4",
        "rpz_drop_ip_rule_min_prefix_length_ipv6", "rpz_qname_wait_recurse",
        "scavenging_settings", "serial_query_rate", "server_id_directive",
        "store_locally", "syslog_facility", "transfers_in", "transfers_out",
        "transfers_per_ns", "zone_deletion_double_confirm"
    ]
    
    for field in boolean_fields:
        if field in grid_dns_properties_data:
            value = grid_dns_properties_data[field]
            if not isinstance(value, bool):
                boolean_errors.append(f"{field}: Must be boolean (true/false), got {type(value).__name__}")
                validation_failed = True
                print(f"ERROR: {field}: Must be boolean (true/false)")
    
    # Validate enum fields
    enum_validations = {
        "default_ttl": (0, 2147483647),
        "expire_after": (0, 2147483647),
        "negative_ttl": (0, 2147483647),
        "refresh": (0, 2147483647),
        "retry": (0, 2147483647),
        "lame_ttl": (0, 2147483647),
        "max_cache_ttl": (0, 2147483647),
        "max_ncache_ttl": (0, 2147483647),
        "nxdomain_redirect_ttl": (0, 2147483647),
        "scavenging_interval": (0, 2147483647),
        "zone_deletion_double_confirm": (0, 30),
        "bind_check_names_policy": ["fail", "warn", "ignore"],
        "blacklist_action": ["redirect", "refuse"],
        "default_bulk_host_name_template": "string",
        "default_host_name_template": "string",
        "dns_update_style": ["NONE", "INTERIM", "STANDARD"],
        "forward_only": ["True", "False"],
        "recursion": ["True", "False"],
        "rpz_qname_wait_recurse": [True, False],
        "syslog_facility": ["LOCAL0", "LOCAL1", "LOCAL2", "LOCAL3", "LOCAL4", "LOCAL5", "LOCAL6", "LOCAL7"]
    }
    
    for field, validation in enum_validations.items():
        if field in grid_dns_properties_data:
            value = grid_dns_properties_data[field]
            if isinstance(validation, tuple):
                # It's a range
                min_val, max_val = validation
                try:
                    num_value = int(value)
                    if not (min_val <= num_value <= max_val):
                        enum_errors.append(f"{field}: Value {num_value} must be between {min_val} and {max_val}")
                        validation_failed = True
                        print(f"ERROR: {field}: Value must be between {min_val} and {max_val}")
                except (ValueError, TypeError):
                    enum_errors.append(f"{field}: Invalid numeric value")
                    validation_failed = True
            elif isinstance(validation, list):
                # It's an enum
                if value not in validation:
                    enum_errors.append(f"{field}: Invalid value '{value}' (must be one of: {', '.join(map(str, validation))})")
                    validation_failed = True
                    print(f"ERROR: {field}: Invalid value '{value}'")
            elif validation == "string":
                if not isinstance(value, str):
                    enum_errors.append(f"{field}: Must be a string")
                    validation_failed = True
    
    # Validate ACL fields
    acl_fields = [
        "allow_query", "allow_transfer", "allow_update",
        "allow_recursive_query", "blacklist", "forwarders",
        "sortlist", "filter_aaaa_list"
    ]
    
    for acl_field in acl_fields:
        if acl_field in grid_dns_properties_data:
            acl_items = grid_dns_properties_data[acl_field]
            errors = validate_dns_acl_items(acl_items, acl_field)
            if errors:
                acl_errors.extend(errors)
                validation_failed = True
                for error in errors:
                    print(f"ERROR: {error}")
    
    # Validate port settings
    port_fields = {
        "dns_notify_transfer_source_port": (1024, 65535),
        "dns_notify_transfer_source_port_ipv6": (1024, 65535),
        "dns_query_source_port": (1024, 65535),
        "dns_query_source_port_ipv6": (1024, 65535)
    }
    
    for field, (min_port, max_port) in port_fields.items():
        if field in grid_dns_properties_data:
            try:
                port = int(grid_dns_properties_data[field])
                if not (min_port <= port <= max_port):
                    timeout_errors.append(f"{field}: Port {port} must be between {min_port} and {max_port}")
                    validation_failed = True
                    print(f"ERROR: {field}: Port must be between {min_port} and {max_port}")
            except (ValueError, TypeError):
                timeout_errors.append(f"{field}: Invalid port value")
                validation_failed = True
    
    # Check for read-only fields that will be excluded
    read_only_fields = ['_ref', 'is_grid_default']
    present_read_only = [field for field in read_only_fields if field in grid_dns_properties_data]
    if present_read_only:
        print(f"INFO: Read-only fields will be excluded: {', '.join(present_read_only)}")
    
    # Check for critical settings
    critical_settings = {
        "recursion": "Disabling recursion will prevent DNS resolution for non-authoritative zones",
        "dnssec_validation_enabled": "Disabling DNSSEC validation may reduce security",
        "allow_recursive_query": "Restricting recursive queries may impact client resolution",
        "blackhole_enabled": "Enabling blackhole will drop queries for specified addresses",
        "forward_only": "Enabling forward-only will disable authoritative responses"
    }
    
    for setting, warning in critical_settings.items():
        if setting in grid_dns_properties_data:
            value = grid_dns_properties_data[setting]
            if (setting == "recursion" and value == "False") or \
               (setting == "forward_only" and value == "True") or \
               (setting not in ["recursion", "forward_only"] and value is False):
                warnings.append(f"{setting}: {warning}")
                print(f"WARNING: {setting} is being changed - {warning}")
    
    # Display changes that will be made
    print("\nChanges to be applied:")
    for key, new_value in grid_dns_properties_data.items():
        if key not in read_only_fields:
            existing_value = existing_config.get(key)
            if existing_value != new_value:
                print(f"  {key}: {existing_value} → {new_value}")
    
    # Display validation summary
    print("\nGrid DNS Properties Validation Summary:")
    print(f"Configuration exists: Yes")
    print(f"Boolean field errors: {len(boolean_errors)}")
    print(f"Enum field errors: {len(enum_errors)}")
    print(f"ACL errors: {len(acl_errors)}")
    print(f"Timeout/Port errors: {len(timeout_errors)}")
    print(f"Warnings: {len(warnings)}")
    
    return not validation_failed

# Check for Grid DNS Properties file and its content before validation
grid_dns_properties_file = "../prod_changes/cabgridmgr.amfam.com/grid_dns_properties.json"
should_validate_grid_dns_properties = False

if os.path.exists(grid_dns_properties_file):
    try:
        with open(grid_dns_properties_file, 'r') as file:
            grid_dns_properties_data = json.load(file)
            # Only validate if there is data (not empty dict)
            if grid_dns_properties_data and grid_dns_properties_data != {}:
                should_validate_grid_dns_properties = True
            else:
                print("\n--- Grid DNS Properties Validation ---")
                print(f"Grid DNS Properties file exists but contains no data. Skipping validation.")
    except Exception as e:
        print(f"\n--- Grid DNS Properties Validation ---")
        print(f"Error reading Grid DNS Properties file: {str(e)}")
        print("Cannot validate Grid DNS Properties due to file error.")
else:
    print("\n--- Grid DNS Properties Validation ---")
    print(f"Grid DNS Properties file not found: {grid_dns_properties_file}")
    print("Skipping Grid DNS Properties validation.")

# Only call the validation function if we have data to validate
if should_validate_grid_dns_properties:
    grid_dns_properties_valid = validate_grid_dns_properties_records()
    if not grid_dns_properties_valid:
        print("\n✗ Pre-check failed: Grid DNS Properties validation failed")
        sys.exit(1)

def check_existing_grid_dns_properties():
    """Check if Grid DNS Properties exist and get current configuration."""
    try:
        response = requests.get(
            f"{BASE_URL}/grid:dns",
            auth=(INFOBLOX_USERNAME, INFOBLOX_PASSWORD),
            verify=VALIDATE_CERTS,
            timeout=HTTP_TIMEOUT
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"✗ Error checking Grid DNS Properties: {response.status_code}")
            return []
    except Exception as e:
        print(f"✗ Error checking Grid DNS Properties: {str(e)}")
        return []

def validate_grid_dns_properties_records():
    """Validate Grid DNS Properties records from JSON file."""
    print("\n--- Grid DNS Properties Validation ---")
    
    grid_dns_properties_file = "../prod_changes/cabgridmgr.amfam.com/grid_dns_properties.json"
    
    # Read Grid DNS Properties data from JSON file
    try:
        with open(grid_dns_properties_file, 'r') as file:
            grid_dns_properties_data = json.load(file)
            
            # Grid DNS Properties should be a dictionary (single object)
            if not isinstance(grid_dns_properties_data, dict):
                print(f"ERROR: Grid DNS Properties must be a dictionary/object")
                return False
            
            # Check if it's empty
            if not grid_dns_properties_data:
                print(f"Grid DNS Properties file exists but contains no data. Skipping validation.")
                return True
                
            print(f"Found Grid DNS Properties configuration to validate.")
            
    except Exception as e:
        print(f"Error reading file {grid_dns_properties_file}: {str(e)}")
        return False
    
    # Check if Grid DNS Properties exist
    existing_properties = check_existing_grid_dns_properties()
    if not existing_properties:
        print(f"ERROR: Grid DNS Properties not found in Infoblox")
        print(f"       Grid DNS must exist before properties can be updated")
        return False
    
    existing_config = existing_properties[0]
    print(f"Grid DNS Properties exist in Infoblox")
    
    # Now continue with validation
    validation_failed = False
    integer_errors = []
    boolean_errors = []
    string_errors = []
    list_errors = []
    struct_errors = []
    acl_errors = []
    warnings = []
    
    # Define field types based on the playbook
    integer_fields = [
        "default_ttl", "dns_cache_acceleration_ttl", "dns_health_check_interval",
        "dns_health_check_retries", "dns_health_check_timeout", "dns_query_capture_file_time_limit",
        "edns_udp_size", "expire_after", "ftc_expired_record_timeout", "ftc_expired_record_ttl",
        "max_cache_ttl", "max_cached_lifetime", "max_ncache_ttl", "max_udp_size",
        "negative_ttl", "notify_delay", "nxdomain_redirect_ttl", "refresh_timer",
        "resolver_query_timeout", "retry_timer", "rpz_drop_ip_rule_min_prefix_length_ipv4",
        "rpz_drop_ip_rule_min_prefix_length_ipv6", "serial_query_rate", "transfers_in",
        "transfers_out", "transfers_per_ns", "client_subnet_ipv4_prefix_length",
        "client_subnet_ipv6_prefix_length", "notify_source_port", "query_source_port",
        "blacklist_redirect_ttl"
    ]
    
    boolean_fields = [
        "add_client_ip_mac_options", "allow_gss_tsig_zone_updates", "allow_recursive_query",
        "anonymize_response_logging", "copy_client_ip_mac_options", "copy_xfer_to_notify",
        "ddns_force_creation_timestamp_update", "ddns_principal_tracking", "ddns_restrict_patterns",
        "ddns_restrict_protected", "ddns_restrict_secure", "ddns_restrict_static",
        "disable_edns", "dns_health_check_anycast_control", "dns_health_check_recursion_flag",
        "dnssec_blacklist_enabled", "dnssec_dns64_enabled", "dnssec_enabled",
        "dnssec_expired_signatures_enabled", "dnssec_nxdomain_enabled", "dnssec_rpz_enabled",
        "dnssec_validation_enabled", "dtc_edns_prefer_client_subnet", "enable_blackhole",
        "enable_blacklist", "enable_capture_dns_queries", "enable_capture_dns_responses",
        "enable_client_subnet_forwarding", "enable_client_subnet_recursive",
        "enable_delete_associated_ptr", "enable_dns64", "enable_dns_health_check",
        "enable_dnstap_queries", "enable_dnstap_responses", "enable_excluded_domain_names",
        "enable_fixed_rrset_order_fqdns", "enable_ftc", "enable_gss_tsig",
        "enable_host_rrset_order", "enable_hsm_signing", "enable_notify_source_port",
        "enable_query_rewrite", "enable_query_source_port", "forward_only",
        "forward_updates", "member_secondary_notify", "nxdomain_log_query",
        "nxdomain_redirect", "preserve_host_rrset_order_on_secondaries",
        "rpz_disable_nsdname_nsip", "rpz_drop_ip_rule_enabled", "rpz_qname_wait_recurse",
        "store_locally", "zone_deletion_double_confirm"
    ]
    
    string_fields = [
        "allow_bulkhost_ddns", "bind_check_names_policy", "bind_hostname_directive",
        "blacklist_action", "default_bulk_host_name_template", "ddns_principal_group",
        "email", "filter_aaaa", "nsgroup_default", "root_name_server_type",
        "server_id_directive", "syslog_facility", "transfer_format",
        "dtc_dns_queries_specific_behavior", "dtc_dnssec_mode", "query_rewrite_prefix"
    ]
    
    list_fields = [
        "blacklist_redirect_addresses", "blacklist_rulesets", "client_subnet_domains",
        "ddns_restrict_patterns_list", "dns64_groups", "dns_health_check_domain_list",
        "dnssec_negative_trust_anchors", "dnssec_trusted_keys", "domains_to_capture_dns_queries",
        "dtc_topology_ea_list", "excluded_domain_names", "forwarders", "nsgroups",
        "nxdomain_redirect_addresses", "nxdomain_redirect_addresses_v6", "nxdomain_rulesets",
        "query_rewrite_domain_names", "transfer_excluded_servers"
    ]
    
    struct_fields = [
        "attack_mitigation", "auto_blackhole", "dnssec_key_params", "dnstap_setting",
        "dtc_scheduled_backup", "file_transfer_setting", "logging_categories",
        "response_rate_limiting", "restart_setting", "scavenging_settings"
    ]
    
    list_of_structs_fields = [
        "allow_query", "allow_transfer", "allow_update", "blackhole_list",
        "bulk_host_name_templates", "custom_root_name_servers", "filter_aaaa_list",
        "fixed_rrset_order_fqdns", "gss_tsig_keys", "last_queried_acl",
        "protocol_record_name_policies", "recursive_query_list", "sortlist"
    ]
    
    # Validate integer fields
    integer_ranges = {
        "default_ttl": (0, 2147483647),
        "dns_cache_acceleration_ttl": (0, 2147483647),
        "dns_health_check_interval": (10, 2147483647),
        "dns_health_check_retries": (1, 10),
        "dns_health_check_timeout": (1, 30),
        "dns_query_capture_file_time_limit": (0, 2147483647),
        "edns_udp_size": (512, 4096),
        "expire_after": (0, 2147483647),
        "ftc_expired_record_timeout": (0, 2147483647),
        "ftc_expired_record_ttl": (0, 2147483647),
        "max_cache_ttl": (0, 2147483647),
        "max_cached_lifetime": (0, 2147483647),
        "max_ncache_ttl": (0, 2147483647),
        "max_udp_size": (512, 4096),
        "negative_ttl": (0, 2147483647),
        "notify_delay": (0, 60),
        "nxdomain_redirect_ttl": (0, 2147483647),
        "refresh_timer": (0, 2147483647),
        "resolver_query_timeout": (0, 30),
        "retry_timer": (0, 2147483647),
        "rpz_drop_ip_rule_min_prefix_length_ipv4": (8, 32),
        "rpz_drop_ip_rule_min_prefix_length_ipv6": (64, 128),
        "serial_query_rate": (0, 1000),
        "transfers_in": (0, 1000),
        "transfers_out": (0, 1000),
        "transfers_per_ns": (0, 1000),
        "client_subnet_ipv4_prefix_length": (0, 32),
        "client_subnet_ipv6_prefix_length": (0, 128),
        "notify_source_port": (1024, 65535),
        "query_source_port": (1024, 65535),
        "blacklist_redirect_ttl": (0, 2147483647)
    }
    
    for field in integer_fields:
        if field in grid_dns_properties_data:
            value = grid_dns_properties_data[field]
            try:
                int_value = int(value)
                # Check range if defined
                if field in integer_ranges:
                    min_val, max_val = integer_ranges[field]
                    if not (min_val <= int_value <= max_val):
                        integer_errors.append(f"{field}: Value {int_value} must be between {min_val} and {max_val}")
                        validation_failed = True
                        print(f"ERROR: {field}: Value {int_value} must be between {min_val} and {max_val}")
            except (ValueError, TypeError):
                integer_errors.append(f"{field}: Invalid integer value '{value}'")
                validation_failed = True
                print(f"ERROR: {field}: Invalid integer value '{value}'")
    
    # Validate boolean fields
    for field in boolean_fields:
        if field in grid_dns_properties_data:
            value = grid_dns_properties_data[field]
            if not isinstance(value, bool):
                boolean_errors.append(f"{field}: Must be boolean (true/false), got {type(value).__name__}")
                validation_failed = True
                print(f"ERROR: {field}: Must be boolean (true/false), got {type(value).__name__}")
    
    # Validate string fields with specific enums
    string_enums = {
        "bind_check_names_policy": ["fail", "warn", "ignore"],
        "blacklist_action": ["redirect", "refuse"],
        "filter_aaaa": ["no", "yes", "break-dnssec"],
        "root_name_server_type": ["internet", "custom"],
        "syslog_facility": ["LOCAL0", "LOCAL1", "LOCAL2", "LOCAL3", "LOCAL4", "LOCAL5", "LOCAL6", "LOCAL7"],
        "transfer_format": ["one-answer", "many-answers"],
        "dtc_dns_queries_specific_behavior": ["FAIL_TO_ALL", "FAIL_TO_NONE"],
        "dtc_dnssec_mode": ["secure", "insecure"]
    }
    
    for field in string_fields:
        if field in grid_dns_properties_data:
            value = grid_dns_properties_data[field]
            if not isinstance(value, str):
                string_errors.append(f"{field}: Must be string, got {type(value).__name__}")
                validation_failed = True
                print(f"ERROR: {field}: Must be string")
            elif field in string_enums and value not in string_enums[field]:
                string_errors.append(f"{field}: Invalid value '{value}' (must be one of: {', '.join(string_enums[field])})")
                validation_failed = True
                print(f"ERROR: {field}: Invalid value '{value}'")
    
    # Validate list fields
    for field in list_fields:
        if field in grid_dns_properties_data:
            value = grid_dns_properties_data[field]
            if not isinstance(value, list):
                list_errors.append(f"{field}: Must be list, got {type(value).__name__}")
                validation_failed = True
                print(f"ERROR: {field}: Must be list")
    
    # Validate struct fields
    for field in struct_fields:
        if field in grid_dns_properties_data:
            value = grid_dns_properties_data[field]
            if not isinstance(value, dict):
                struct_errors.append(f"{field}: Must be dictionary/object, got {type(value).__name__}")
                validation_failed = True
                print(f"ERROR: {field}: Must be dictionary/object")
    
    # Validate list of structs fields (ACLs)
    for field in list_of_structs_fields:
        if field in grid_dns_properties_data:
            value = grid_dns_properties_data[field]
            if not isinstance(value, list):
                acl_errors.append(f"{field}: Must be list, got {type(value).__name__}")
                validation_failed = True
                print(f"ERROR: {field}: Must be list")
            else:
                # Validate ACL items if it's an ACL field
                acl_fields = ["allow_query", "allow_transfer", "allow_update", "recursive_query_list", "sortlist"]
                if field in acl_fields:
                    errors = validate_dns_acl_items(value, field)
                    if errors:
                        acl_errors.extend(errors)
                        validation_failed = True
                        for error in errors:
                            print(f"ERROR: {error}")
    
    # Validate email format
    if "email" in grid_dns_properties_data:
        email = grid_dns_properties_data["email"]
        if "@" not in email:
            string_errors.append(f"email: Invalid email format '{email}'")
            validation_failed = True
            print(f"ERROR: Invalid email format '{email}'")
    
    # Check for critical settings
    critical_settings = {
        "allow_recursive_query": "Disabling recursive queries will prevent DNS resolution for clients",
        "dnssec_validation_enabled": "Disabling DNSSEC validation may reduce security",
        "forward_only": "Enabling forward-only will disable authoritative responses",
        "enable_blackhole": "Enabling blackhole will drop queries for specified addresses",
        "enable_dns64": "Enabling DNS64 requires proper IPv6 configuration",
        "dnssec_enabled": "Disabling DNSSEC will remove security for signed zones",
        "enable_dns_health_check": "Disabling health checks may impact failover capabilities"
    }
    
    for setting, description in critical_settings.items():
        if setting in grid_dns_properties_data:
            value = grid_dns_properties_data[setting]
            if (setting.startswith("enable_") and value is False) or \
               (setting.startswith("allow_") and value is False) or \
               (setting == "forward_only" and value is True):
                warnings.append(f"{setting}: {description}")
                print(f"WARNING: {setting} is being changed - {description}")
    
    # Validate DNSSEC settings consistency
    if grid_dns_properties_data.get("dnssec_enabled", False):
        # If DNSSEC is enabled, check related settings
        if not grid_dns_properties_data.get("dnssec_validation_enabled", True):
            warnings.append("DNSSEC enabled but validation disabled - unusual configuration")
            print(f"WARNING: DNSSEC enabled but validation disabled")
    
    # Validate RPZ settings
    if grid_dns_properties_data.get("rpz_drop_ip_rule_enabled", False):
        # Check if prefix lengths are set
        if "rpz_drop_ip_rule_min_prefix_length_ipv4" not in grid_dns_properties_data:
            warnings.append("RPZ drop IP rule enabled but IPv4 prefix length not set")
            print(f"WARNING: RPZ drop IP rule enabled but IPv4 prefix length not set")
        if "rpz_drop_ip_rule_min_prefix_length_ipv6" not in grid_dns_properties_data:
            warnings.append("RPZ drop IP rule enabled but IPv6 prefix length not set")
            print(f"WARNING: RPZ drop IP rule enabled but IPv6 prefix length not set")
    
    # Check for read-only fields
    read_only_fields = ['_ref']
    present_read_only = [field for field in read_only_fields if field in grid_dns_properties_data]
    if present_read_only:
        print(f"INFO: Read-only fields will be excluded: {', '.join(present_read_only)}")
    
    # Display changes that will be made
    print("\nChanges to be applied:")
    changes_count = 0
    for key, new_value in grid_dns_properties_data.items():
        if key not in read_only_fields:
            existing_value = existing_config.get(key)
            if existing_value != new_value:
                changes_count += 1
                # Truncate long values for display
                if isinstance(new_value, (list, dict)) and len(str(new_value)) > 100:
                    new_display = f"{type(new_value).__name__} with {len(new_value)} items"
                else:
                    new_display = str(new_value)
                
                if isinstance(existing_value, (list, dict)) and len(str(existing_value)) > 100:
                    existing_display = f"{type(existing_value).__name__} with {len(existing_value)} items"
                else:
                    existing_display = str(existing_value)
                
                print(f"  {key}: {existing_display} → {new_display}")
    
    if changes_count == 0:
        print("  No changes detected - all values match current configuration")
    
    # Display validation summary
    print("\nGrid DNS Properties Validation Summary:")
    print(f"Configuration exists: Yes")
    print(f"Integer field errors: {len(integer_errors)}")
    print(f"Boolean field errors: {len(boolean_errors)}")
    print(f"String field errors: {len(string_errors)}")
    print(f"List field errors: {len(list_errors)}")
    print(f"Struct field errors: {len(struct_errors)}")
    print(f"ACL configuration errors: {len(acl_errors)}")
    print(f"Warnings: {len(warnings)}")
    print(f"Changes to apply: {changes_count}")
    
    return not validation_failed

def check_existing_member_dns_properties(host_name):
    """Check if Member DNS Properties exist for a specific member."""
    try:
        response = requests.get(
            f"{BASE_URL}/member:dns",
            params={"host_name": host_name},
            auth=(INFOBLOX_USERNAME, INFOBLOX_PASSWORD),
            verify=VALIDATE_CERTS,
            timeout=HTTP_TIMEOUT
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"✗ Error checking Member DNS Properties for {host_name}: {response.status_code}")
            return []
    except Exception as e:
        print(f"✗ Error checking Member DNS Properties for {host_name}: {str(e)}")
        return []

def validate_member_dns_properties_records():
    """Validate Member DNS Properties records from JSON file."""
    print("\n--- Member DNS Properties Validation ---")
    
    member_dns_properties_file = "playbooks/add/cabgridmgr.amfam.com/member_dns_properties.json"
    
    # Read Member DNS Properties data from JSON file
    try:
        with open(member_dns_properties_file, 'r') as file:
            member_dns_properties_data = json.load(file)
            
            # Member DNS Properties should be a list of member configurations
            if not isinstance(member_dns_properties_data, list):
                # If it's a single dict, convert to list
                if isinstance(member_dns_properties_data, dict):
                    member_dns_properties_data = [member_dns_properties_data]
                else:
                    print(f"ERROR: Member DNS Properties must be a list or dictionary")
                    return False
            
            # Check if it's empty
            if not member_dns_properties_data:
                print(f"Member DNS Properties file exists but contains no data. Skipping validation.")
                return True
                
            print(f"Found {len(member_dns_properties_data)} Member DNS Properties configurations to validate.")
            
    except Exception as e:
        print(f"Error reading file {member_dns_properties_file}: {str(e)}")
        return False
    
    # Now continue with validation
    validation_failed = False
    missing_members = []
    missing_host_names = []
    integer_errors = []
    boolean_errors = []
    string_errors = []
    list_errors = []
    struct_errors = []
    acl_errors = []
    warnings = []
    members_to_update = []
    
    # Define field types (similar to Grid DNS Properties but for members)
    integer_fields = [
        "additional_ip_list_struct", "dns_cache_acceleration_ttl", "dns_notify_transfer_source_port",
        "dns_query_source_port", "edns_udp_size", "file_transfer_connection_timeout",
        "max_concurrent_queries", "minimal_resp_recursion_depth", "query_source_port",
        "recursion_query_timeout", "response_transaction_id_source_port", "resolver_query_timeout",
        "serial_query_rate", "tcp_idle_timeout", "transfer_tcp_idle_timeout", "transfers_in",
        "transfers_out", "transfers_per_ns"
    ]
    
    boolean_fields = [
        "anonymize_response_logging", "attack_mitigation", "auto_blackhole", "bind_hostname_directive",
        "blackhole_enabled", "blacklist_log_query", "blacklist_redirect_addresses_v4",
        "blacklist_redirect_addresses_v6", "blacklist_rulesets", "capture_dns_queries_on_all_domains",
        "disable_edns", "dns64_enabled", "dns_cache_acceleration_enabled", "dns_health_check_anycast_control",
        "dns_health_check_enabled", "dns_health_check_recursion_enabled", "dns_health_check_recursion_flag",
        "dns_lameness_check", "dns_log_dyn_updates", "dns_log_queries", "dns_log_responses",
        "dns_log_updates", "dns_notify_transfer_source", "dns_query_source_interface",
        "dnssec_blacklist_enabled", "dnssec_dns64_enabled", "dnssec_enabled",
        "dnssec_expired_signatures_enabled", "dnssec_rpz_enabled", "dnssec_validation_enabled",
        "enable_blackhole", "enable_blacklist", "enable_capture_dns_queries",
        "enable_capture_dns_responses", "enable_excluded_domain_names", "enable_fixed_rrset_order_fqdns",
        "enable_ftc", "enable_gss_tsig", "enable_notify_source_port", "enable_query_source_port",
        "filter_aaaa_on_v4", "forwarders_only", "ftc", "gss_tsig_keys", "lan2_enabled",
        "notify_delay", "nxdomain_log_query", "nxdomain_redirect", "nxdomain_redirect_addresses",
        "nxdomain_redirect_addresses_v6", "nxdomain_redirect_ttl", "nxdomain_rulesets",
        "queries_per_second", "query_rewrite", "recursion", "recursive_query_list",
        "response_rate_limiting", "rpz_disable_nsdname_nsip", "rpz_drop_ip_rule_enabled",
        "rpz_drop_ip_rule_min_prefix_length_ipv4", "rpz_drop_ip_rule_min_prefix_length_ipv6",
        "rpz_qname_wait_recurse", "use_blacklist", "use_dns_health_check", "use_fixed_rrset_order_fqdns",
        "use_ftc", "use_lan2_ipv6_port", "use_lan2_port", "use_lan_ipv6_port", "use_lan_port",
        "use_mgmt_ipv6_port", "use_mgmt_port", "use_nxdomain_redirect", "use_recursion",
        "use_response_rate_limiting", "use_rpz_drop_ip_rule", "use_source_ports"
    ]
    
    string_fields = [
        "bind_check_names_policy", "blacklist_action", "blacklist_redirect_ttl",
        "dns_a_record_query_analysis", "forward_only", "log_guest_lookups",
        "max_cache_ttl", "max_ncache_ttl", "notify_source_port", "query_source_port",
        "recursion_available", "root_name_server_type", "server_id_directive",
        "sortlist", "syslog_facility", "zone_deletion_double_confirm"
    ]
    
    list_fields = [
        "additional_ip_list", "blackhole_list", "blacklist_redirect_addresses",
        "dns_health_check_domain_list", "dns_health_check_recursion_flag",
        "dns_health_check_source_ip", "domains_to_capture_dns_queries",
        "excluded_domain_names", "filter_aaaa_list", "fixed_rrset_order_fqdns",
        "forwarders", "ipv4acl", "ipv6acl", "lan2_ipv6_setting", "nsgroups",
        "nxdomain_redirect_addresses", "nxdomain_redirect_addresses_v6",
        "query_rewrite_domain_names", "query_rewrite_prefix", "source_ip_list"
    ]
    
    struct_fields = [
        "attack_mitigation", "auto_blackhole", "custom_root_name_servers",
        "dns_cache_acceleration_settings", "dns_health_check_member_settings",
        "dns_health_check_settings", "dnssec_key_params", "dnssec_settings",
        "dnstap_setting", "dtc_scheduled_backup", "file_transfer_setting",
        "ftc_settings", "logging_categories", "query_settings",
        "response_rate_limiting", "rpz_drop_ip_rule_settings"
    ]
    
    list_of_structs_fields = [
        "allow_query", "allow_transfer", "allow_update", "also_notify",
        "blackhole_list", "filter_aaaa_list", "forwarders",
        "gss_tsig_keys", "recursive_query_list", "sortlist"
    ]
    
    # Validate each member configuration
    for member_idx, member_config in enumerate(member_dns_properties_data):
        # Check for required host_name field
        if "host_name" not in member_config:
            missing_host_names.append(f"Member configuration at index {member_idx}")
            validation_failed = True
            print(f"ERROR: Member configuration at index {member_idx} missing required field 'host_name'")
            continue
        
        host_name = member_config["host_name"]
        print(f"\nValidating member: {host_name}")
        
        # Check if member exists
        existing_member_dns = check_existing_member_dns_properties(host_name)
        if not existing_member_dns:
            missing_members.append(host_name)
            validation_failed = True
            print(f"ERROR: Member '{host_name}' not found in Infoblox")
            continue
        
        existing_config = existing_member_dns[0]
        members_to_update.append(host_name)
        
        # Validate integer fields
        for field in integer_fields:
            if field in member_config:
                value = member_config[field]
                try:
                    int_value = int(value)
                    # Add specific range validations if needed
                    if field == "edns_udp_size" and not (512 <= int_value <= 4096):
                        integer_errors.append(f"{host_name}.{field}: Value {int_value} must be between 512 and 4096")
                        validation_failed = True
                    elif field == "query_source_port" and not (1024 <= int_value <= 65535):
                        integer_errors.append(f"{host_name}.{field}: Port {int_value} must be between 1024 and 65535")
                        validation_failed = True
                except (ValueError, TypeError):
                    integer_errors.append(f"{host_name}.{field}: Invalid integer value '{value}'")
                    validation_failed = True
                    print(f"ERROR: {host_name}.{field}: Invalid integer value '{value}'")
        
        # Validate boolean fields
        for field in boolean_fields:
            if field in member_config:
                value = member_config[field]
                if not isinstance(value, bool):
                    boolean_errors.append(f"{host_name}.{field}: Must be boolean (true/false)")
                    validation_failed = True
                    print(f"ERROR: {host_name}.{field}: Must be boolean (true/false)")
        
        # Validate string fields with enums
        string_enums = {
            "bind_check_names_policy": ["fail", "warn", "ignore"],
            "blacklist_action": ["redirect", "refuse"],
            "forward_only": ["True", "False"],
            "recursion_available": ["True", "False"],
            "root_name_server_type": ["internet", "custom"],
            "syslog_facility": ["LOCAL0", "LOCAL1", "LOCAL2", "LOCAL3", "LOCAL4", "LOCAL5", "LOCAL6", "LOCAL7"]
        }
        
        for field in string_fields:
            if field in member_config:
                value = member_config[field]
                if not isinstance(value, str):
                    string_errors.append(f"{host_name}.{field}: Must be string")
                    validation_failed = True
                    print(f"ERROR: {host_name}.{field}: Must be string")
                elif field in string_enums and value not in string_enums[field]:
                    string_errors.append(f"{host_name}.{field}: Invalid value '{value}'")
                    validation_failed = True
                    print(f"ERROR: {host_name}.{field}: Invalid value '{value}'")
        
        # Validate list fields
        for field in list_fields:
            if field in member_config:
                value = member_config[field]
                if not isinstance(value, list):
                    list_errors.append(f"{host_name}.{field}: Must be list")
                    validation_failed = True
                    print(f"ERROR: {host_name}.{field}: Must be list")
        
        # Validate struct fields
        for field in struct_fields:
            if field in member_config:
                value = member_config[field]
                if not isinstance(value, dict):
                    struct_errors.append(f"{host_name}.{field}: Must be dictionary/object")
                    validation_failed = True
                    print(f"ERROR: {host_name}.{field}: Must be dictionary/object")
        
        # Validate list of structs fields (ACLs)
        for field in list_of_structs_fields:
            if field in member_config:
                value = member_config[field]
                if not isinstance(value, list):
                    acl_errors.append(f"{host_name}.{field}: Must be list")
                    validation_failed = True
                    print(f"ERROR: {host_name}.{field}: Must be list")
                else:
                    # Validate ACL items if it's an ACL field
                    acl_fields = ["allow_query", "allow_transfer", "allow_update", "recursive_query_list"]
                    if field in acl_fields:
                        errors = validate_dns_acl_items(value, f"{host_name}.{field}")
                        if errors:
                            acl_errors.extend(errors)
                            validation_failed = True
                            for error in errors:
                                print(f"ERROR: {error}")
        
        # Check for critical settings
        critical_settings = {
            "recursion": "Disabling recursion will prevent DNS resolution for clients",
            "dnssec_validation_enabled": "Disabling DNSSEC validation may reduce security",
            "dns_health_check_enabled": "Disabling health checks may impact failover",
            "enable_blackhole": "Enabling blackhole will drop queries for specified addresses"
        }
        
        for setting, description in critical_settings.items():
            if setting in member_config:
                value = member_config[setting]
                if (setting == "recursion" and value is False) or \
                   (setting.startswith("enable_") and value is False and setting != "enable_blackhole") or \
                   (setting == "enable_blackhole" and value is True):
                    warnings.append(f"{host_name}.{setting}: {description}")
                    print(f"WARNING: {host_name}.{setting} - {description}")
        
        # Display changes for this member
        print(f"\nChanges to be applied for member {host_name}:")
        changes_count = 0
        for key, new_value in member_config.items():
            if key != "host_name" and key != "_ref":
                existing_value = existing_config.get(key)
                if existing_value != new_value:
                    changes_count += 1
                    # Truncate long values for display
                    if isinstance(new_value, (list, dict)) and len(str(new_value)) > 100:
                        new_display = f"{type(new_value).__name__} with {len(new_value)} items"
                    else:
                        new_display = str(new_value)
                    
                    if isinstance(existing_value, (list, dict)) and len(str(existing_value)) > 100:
                        existing_display = f"{type(existing_value).__name__} with {len(existing_value)} items"
                    else:
                        existing_display = str(existing_value)
                    
                    print(f"  {key}: {existing_display} → {new_display}")
        
        if changes_count == 0:
            print(f"  No changes detected for member {host_name}")
    
    # Display validation summary
    print("\nMember DNS Properties Validation Summary:")
    print(f"Total member configurations: {len(member_dns_properties_data)}")
    print(f"Members to update: {len(members_to_update)}")
    print(f"Missing members: {len(missing_members)}")
    print(f"Missing host_name fields: {len(missing_host_names)}")
    print(f"Integer field errors: {len(integer_errors)}")
    print(f"Boolean field errors: {len(boolean_errors)}")
    print(f"String field errors: {len(string_errors)}")
    print(f"List field errors: {len(list_errors)}")
    print(f"Struct field errors: {len(struct_errors)}")
    print(f"ACL configuration errors: {len(acl_errors)}")
    print(f"Warnings: {len(warnings)}")
    
    if missing_members:
        print(f"\nMissing members: {', '.join(missing_members)}")
    if members_to_update:
        print(f"\nMembers to update: {', '.join(members_to_update)}")
    
    return not validation_failed

def check_existing_member_dns(host_name):
    """Check if Member DNS exists for a specific member."""
    try:
        response = requests.get(
            f"{BASE_URL}/member:dns",
            params={"host_name": host_name},
            auth=(INFOBLOX_USERNAME, INFOBLOX_PASSWORD),
            verify=VALIDATE_CERTS,
            timeout=HTTP_TIMEOUT
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"✗ Error checking Member DNS for {host_name}: {response.status_code}")
            return []
    except Exception as e:
        print(f"✗ Error checking Member DNS for {host_name}: {str(e)}")
        return []

def validate_member_dns_records():
    """Validate Member DNS records from JSON file."""
    print("\n--- Member DNS Validation ---")
    
    member_dns_file = "playbooks/add/cabgridmgr.amfam.com/member_dns.json"
    
    # Read Member DNS data from JSON file
    try:
        with open(member_dns_file, 'r') as file:
            member_dns_data = json.load(file)
            
            # Member DNS should be a list of member configurations
            if not isinstance(member_dns_data, list):
                # If it's a single dict, convert to list
                if isinstance(member_dns_data, dict):
                    member_dns_data = [member_dns_data]
                else:
                    print(f"ERROR: Member DNS must be a list or dictionary")
                    return False
            
            # Check if it's empty
            if not member_dns_data:
                print(f"Member DNS file exists but contains no data. Skipping validation.")
                return True
                
            print(f"Found {len(member_dns_data)} Member DNS configurations to validate.")
            
    except Exception as e:
        print(f"Error reading file {member_dns_file}: {str(e)}")
        return False
    
    # Now continue with validation
    validation_failed = False
    missing_members = []
    missing_host_names = []
    integer_errors = []
    boolean_errors = []
    string_errors = []
    list_errors = []
    struct_errors = []
    acl_errors = []
    port_errors = []
    warnings = []
    members_to_update = []
    
    # Define field types based on the playbook
    integer_fields = [
        "dns_cache_acceleration_ttl", "dns_health_check_interval", "dns_health_check_retries",
        "dns_health_check_timeout", "dns_query_capture_file_time_limit", "edns_udp_size",
        "ftc_expired_record_timeout", "ftc_expired_record_ttl", "max_cache_ttl",
        "max_cached_lifetime", "max_ncache_ttl", "max_udp_size", "notify_delay",
        "nxdomain_redirect_ttl", "resolver_query_timeout", "serial_query_rate",
        "transfers_in", "transfers_out", "transfers_per_ns", "recursive_client_limit",
        "rpz_drop_ip_rule_min_prefix_length_ipv4", "rpz_drop_ip_rule_min_prefix_length_ipv6",
        "tcp_idle_timeout", "tls_session_duration", "doh_https_session_duration"
    ]
    
    boolean_fields = [
        "add_client_ip_mac_options", "allow_gss_tsig_zone_updates", "allow_recursive_query",
        "anonymize_response_logging", "atc_fwd_enable", "auto_create_a_and_ptr_for_lan2",
        "auto_create_aaaa_and_ipv6ptr_for_lan2", "auto_sort_views",
        "check_names_for_ddns_and_zone_transfer", "copy_client_ip_mac_options",
        "copy_xfer_to_notify", "disable_edns", "dns_health_check_anycast_control",
        "dns_health_check_recursion_flag", "dns_over_tls_service", "dnssec_blacklist_enabled",
        "dnssec_dns64_enabled", "dnssec_enabled", "dnssec_expired_signatures_enabled",
        "dnssec_nxdomain_enabled", "dnssec_rpz_enabled", "dnssec_validation_enabled",
        "dtc_edns_prefer_client_subnet", "enable_blackhole", "enable_blacklist",
        "enable_capture_dns_queries", "enable_capture_dns_responses", "enable_dns",
        "enable_dns64", "enable_dns_cache_acceleration", "enable_dns_health_check",
        "enable_dnstap_queries", "enable_dnstap_responses", "enable_excluded_domain_names",
        "enable_fixed_rrset_order_fqdns", "enable_ftc", "enable_gss_tsig",
        "enable_notify_source_port", "enable_query_rewrite", "enable_query_source_port",
        "forward_only", "forward_updates", "minimal_resp", "nxdomain_log_query",
        "nxdomain_redirect", "rpz_disable_nsdname_nsip", "rpz_drop_ip_rule_enabled",
        "rpz_qname_wait_recurse", "skip_in_grid_rpz_queries", "store_locally",
        "use_root_server_for_all_views", "use_lan_port", "use_lan2_port",
        "use_lan_ipv6_port", "use_lan2_ipv6_port", "use_mgmt_port", "use_mgmt_ipv6_port"
    ]
    
    string_fields = [
        "bind_check_names_policy", "bind_hostname_directive", "bind_hostname_directive_fqdn",
        "blacklist_action", "dns_notify_transfer_source", "dns_notify_transfer_source_address",
        "dns_query_source_interface", "dns_query_source_address",
        "dtc_dns_queries_specific_behavior", "dtc_health_source", "dtc_health_source_address",
        "filter_aaaa", "record_name_policy", "recursive_resolver", "root_name_server_type",
        "server_id_directive", "server_id_directive_string", "syslog_facility",
        "transfer_format", "upstream_address_family_preference"
    ]
    
    list_fields = [
        "additional_ip_list", "blacklist_redirect_addresses", "blacklist_rulesets",
        "dns64_groups", "dns_health_check_domain_list", "dnssec_negative_trust_anchors",
        "dnssec_trusted_keys", "domains_to_capture_dns_queries", "excluded_domain_names",
        "forwarders", "nxdomain_redirect_addresses", "nxdomain_redirect_addresses_v6",
        "nxdomain_rulesets", "transfer_excluded_servers", "views"
    ]
    
    struct_fields = [
        "attack_mitigation", "auto_blackhole", "dnstap_setting", "file_transfer_setting",
        "logging_categories", "response_rate_limiting", "extattrs"
    ]
    
    list_of_structs_fields = [
        "allow_query", "allow_transfer", "allow_update", "blackhole_list",
        "custom_root_name_servers", "filter_aaaa_list", "fixed_rrset_order_fqdns",
        "recursive_query_list", "sortlist", "gss_tsig_keys", "dns_view_address_settings",
        "glue_record_addresses", "ipv6_glue_record_addresses", "additional_ip_list_struct"
    ]
    
    # Integer field ranges
    integer_ranges = {
        "edns_udp_size": (512, 4096),
        "max_udp_size": (512, 4096),
        "dns_health_check_interval": (10, 2147483647),
        "dns_health_check_retries": (1, 10),
        "dns_health_check_timeout": (1, 30),
        "notify_delay": (0, 60),
        "resolver_query_timeout": (0, 30),
        "serial_query_rate": (0, 1000),
        "transfers_in": (0, 1000),
        "transfers_out": (0, 1000),
        "transfers_per_ns": (0, 1000),
        "recursive_client_limit": (0, 2147483647),
        "rpz_drop_ip_rule_min_prefix_length_ipv4": (8, 32),
        "rpz_drop_ip_rule_min_prefix_length_ipv6": (64, 128),
        "tcp_idle_timeout": (0, 2147483647),
        "tls_session_duration": (0, 2147483647),
        "doh_https_session_duration": (0, 2147483647)
    }
    
    # Validate each member configuration
    for member_idx, member_config in enumerate(member_dns_data):
        # Check for required host_name field
        if "host_name" not in member_config:
            missing_host_names.append(f"Member configuration at index {member_idx}")
            validation_failed = True
            print(f"ERROR: Member configuration at index {member_idx} missing required field 'host_name'")
            continue
        
        host_name = member_config["host_name"]
        print(f"\nValidating member: {host_name}")
        
        # Check if member exists
        existing_member_dns = check_existing_member_dns(host_name)
        if not existing_member_dns:
            missing_members.append(host_name)
            validation_failed = True
            print(f"ERROR: Member '{host_name}' not found in Infoblox")
            continue
        
        existing_config = existing_member_dns[0]
        members_to_update.append(host_name)
        
        # Check if DNS is enabled on the member
        if not existing_config.get("enable_dns", True):
            warnings.append(f"{host_name}: DNS is currently disabled on this member")
            print(f"WARNING: DNS is currently disabled on member '{host_name}'")
        
        # Validate integer fields
        for field in integer_fields:
            if field in member_config:
                value = member_config[field]
                try:
                    int_value = int(value)
                    # Check range if defined
                    if field in integer_ranges:
                        min_val, max_val = integer_ranges[field]
                        if not (min_val <= int_value <= max_val):
                            integer_errors.append(f"{host_name}.{field}: Value {int_value} must be between {min_val} and {max_val}")
                            validation_failed = True
                            print(f"ERROR: {host_name}.{field}: Value {int_value} must be between {min_val} and {max_val}")
                except (ValueError, TypeError):
                    integer_errors.append(f"{host_name}.{field}: Invalid integer value '{value}'")
                    validation_failed = True
                    print(f"ERROR: {host_name}.{field}: Invalid integer value '{value}'")
        
        # Validate boolean fields
        for field in boolean_fields:
            if field in member_config:
                value = member_config[field]
                if not isinstance(value, bool):
                    boolean_errors.append(f"{host_name}.{field}: Must be boolean (true/false)")
                    validation_failed = True
                    print(f"ERROR: {host_name}.{field}: Must be boolean (true/false)")
        
        # Validate string fields with enums
        string_enums = {
            "bind_check_names_policy": ["fail", "warn", "ignore"],
            "blacklist_action": ["redirect", "refuse"],
            "dns_notify_transfer_source": ["GRID", "MEMBER"],
            "dns_query_source_interface": ["ANY", "LAN", "LAN2", "MGMT"],
            "dtc_dns_queries_specific_behavior": ["FAIL_TO_ALL", "FAIL_TO_NONE"],
            "dtc_health_source": ["GRID", "MEMBER"],
            "filter_aaaa": ["no", "yes", "break-dnssec"],
            "record_name_policy": ["generate", "user-defined"],
            "recursive_resolver": ["STATIC", "DYNAMIC"],
            "root_name_server_type": ["internet", "custom"],
            "syslog_facility": ["LOCAL0", "LOCAL1", "LOCAL2", "LOCAL3", "LOCAL4", "LOCAL5", "LOCAL6", "LOCAL7"],
            "transfer_format": ["one-answer", "many-answers"],
            "upstream_address_family_preference": ["IPv4", "IPv6", "ANY"]
        }
        
        for field in string_fields:
            if field in member_config:
                value = member_config[field]
                if not isinstance(value, str):
                    string_errors.append(f"{host_name}.{field}: Must be string")
                    validation_failed = True
                    print(f"ERROR: {host_name}.{field}: Must be string")
                elif field in string_enums and value not in string_enums[field]:
                    string_errors.append(f"{host_name}.{field}: Invalid value '{value}' (must be one of: {', '.join(string_enums[field])})")
                    validation_failed = True
                    print(f"ERROR: {host_name}.{field}: Invalid value '{value}'")
        
        # Validate list fields
        for field in list_fields:
            if field in member_config:
                value = member_config[field]
                if not isinstance(value, list):
                    list_errors.append(f"{host_name}.{field}: Must be list")
                    validation_failed = True
                    print(f"ERROR: {host_name}.{field}: Must be list")
        
        # Validate struct fields
        for field in struct_fields:
            if field in member_config:
                value = member_config[field]
                if not isinstance(value, dict):
                    struct_errors.append(f"{host_name}.{field}: Must be dictionary/object")
                    validation_failed = True
                    print(f"ERROR: {host_name}.{field}: Must be dictionary/object")
        
        # Validate list of structs fields (ACLs)
        for field in list_of_structs_fields:
            if field in member_config:
                value = member_config[field]
                if not isinstance(value, list):
                    acl_errors.append(f"{host_name}.{field}: Must be list")
                    validation_failed = True
                    print(f"ERROR: {host_name}.{field}: Must be list")
                else:
                    # Validate ACL items if it's an ACL field
                    acl_fields = ["allow_query", "allow_transfer", "allow_update", "recursive_query_list"]
                    if field in acl_fields:
                        errors = validate_dns_acl_items(value, f"{host_name}.{field}")
                        if errors:
                            acl_errors.extend(errors)
                            validation_failed = True
                            for error in errors:
                                print(f"ERROR: {error}")
        
        # Validate port usage settings
        port_fields = ["use_lan_port", "use_lan2_port", "use_lan_ipv6_port", 
                      "use_lan2_ipv6_port", "use_mgmt_port", "use_mgmt_ipv6_port"]
        enabled_ports = []
        for port_field in port_fields:
            if member_config.get(port_field, False):
                enabled_ports.append(port_field)
        
        if not enabled_ports and "enable_dns" in member_config and member_config["enable_dns"]:
            warnings.append(f"{host_name}: DNS is enabled but no ports are configured for use")
            print(f"WARNING: {host_name}: DNS is enabled but no ports are configured for use")
        
        # Check for critical settings
        critical_settings = {
            "enable_dns": "Disabling DNS will stop DNS service on this member",
            "allow_recursive_query": "Disabling recursive queries will prevent DNS resolution for clients",
            "dnssec_validation_enabled": "Disabling DNSSEC validation may reduce security",
            "dns_health_check_enabled": "Disabling health checks may impact failover",
            "enable_blackhole": "Enabling blackhole will drop queries for specified addresses",
            "forward_only": "Enabling forward-only will disable authoritative responses"
        }
        
        for setting, description in critical_settings.items():
            if setting in member_config:
                value = member_config[setting]
                if (setting == "enable_dns" and value is False) or \
                   (setting.startswith("enable_") and value is False and setting not in ["enable_blackhole", "enable_dns"]) or \
                   (setting == "enable_blackhole" and value is True) or \
                   (setting == "forward_only" and value is True) or \
                   (setting == "allow_recursive_query" and value is False):
                    warnings.append(f"{host_name}.{setting}: {description}")
                    print(f"WARNING: {host_name}.{setting} - {description}")
        
        # Validate DNS over TLS/HTTPS settings
        if member_config.get("dns_over_tls_service", False):
            if not member_config.get("tls_session_duration"):
                warnings.append(f"{host_name}: DNS over TLS enabled but tls_session_duration not set")
                print(f"WARNING: {host_name}: DNS over TLS enabled but tls_session_duration not set")
        
        # Display changes for this member
        print(f"\nChanges to be applied for member {host_name}:")
        changes_count = 0
        for key, new_value in member_config.items():
            if key not in ["host_name", "_ref"]:
                existing_value = existing_config.get(key)
                if existing_value != new_value:
                    changes_count += 1
                    # Truncate long values for display
                    if isinstance(new_value, (list, dict)) and len(str(new_value)) > 100:
                        new_display = f"{type(new_value).__name__} with {len(new_value)} items"
                    else:
                        new_display = str(new_value)
                    
                    if isinstance(existing_value, (list, dict)) and len(str(existing_value)) > 100:
                        existing_display = f"{type(existing_value).__name__} with {len(existing_value)} items"
                    else:
                        existing_display = str(existing_value)
                    
                    print(f"  {key}: {existing_display} → {new_display}")
        
        if changes_count == 0:
            print(f"  No changes detected for member {host_name}")
    
    # Display validation summary
    print("\nMember DNS Validation Summary:")
    print(f"Total member configurations: {len(member_dns_data)}")
    print(f"Members to update: {len(members_to_update)}")
    print(f"Missing members: {len(missing_members)}")
    print(f"Missing host_name fields: {len(missing_host_names)}")
    print(f"Integer field errors: {len(integer_errors)}")
    print(f"Boolean field errors: {len(boolean_errors)}")
    print(f"String field errors: {len(string_errors)}")
    print(f"List field errors: {len(list_errors)}")
    print(f"Struct field errors: {len(struct_errors)}")
    print(f"ACL configuration errors: {len(acl_errors)}")
    print(f"Port configuration issues: {len(port_errors)}")
    print(f"Warnings: {len(warnings)}")
    
    if missing_members:
        print(f"\nMissing members: {', '.join(missing_members)}")
    if members_to_update:
        print(f"\nMembers to update: {', '.join(members_to_update)}")
    
    return not validation_failed

def check_existing_named_acl(name):
    """Check if a Named ACL already exists in Infoblox."""
    try:
        response = requests.get(
            f"{BASE_URL}/namedacl",
            params={"name": name},
            auth=(INFOBLOX_USERNAME, INFOBLOX_PASSWORD),
            verify=VALIDATE_CERTS,
            timeout=HTTP_TIMEOUT
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"✗ Error checking Named ACL {name}: {response.status_code}")
            return []
    except Exception as e:
        print(f"✗ Error checking Named ACL {name}: {str(e)}")
        return []

def validate_named_acl_name(name):
    """Validate Named ACL name format."""
    if not name:
        return False, "Named ACL name cannot be empty"
    
    # Check length
    if len(name) > 256:
        return False, f"Named ACL name too long ({len(name)} characters, max 256)"
    
    # Check for valid characters (alphanumeric, underscore, hyphen, period)
    if not re.match(r'^[a-zA-Z0-9._\-]+$', name):
        return False, "Named ACL name contains invalid characters (only alphanumeric, underscore, hyphen, period allowed)"
    
    # Cannot start with underscore or hyphen
    if name.startswith('_') or name.startswith('-'):
        return False, "Named ACL name cannot start with underscore or hyphen"
    
    # Check for reserved names
    reserved_names = ['any', 'none', 'localhost', 'localnets']
    if name.lower() in reserved_names:
        return False, f"Named ACL name '{name}' is reserved"
    
    return True, None

def validate_named_acl_access_list(access_list, acl_name):
    """Validate Named ACL access list entries."""
    errors = []
    
    if not isinstance(access_list, list):
        errors.append(f"Access list must be a list")
        return errors
    
    for idx, entry in enumerate(access_list):
        if not isinstance(entry, dict):
            errors.append(f"Access list entry {idx} must be a dictionary")
            continue
        
        # Check for required permission field
        if "permission" not in entry:
            errors.append(f"Access list entry {idx}: Missing required field 'permission'")
            continue
        
        # Validate permission
        valid_permissions = ["ALLOW", "DENY"]
        if entry["permission"] not in valid_permissions:
            errors.append(f"Access list entry {idx}: Invalid permission '{entry['permission']}' (must be ALLOW or DENY)")
        
        # Check for address specification
        has_address = any(key in entry for key in ["address", "tsig_key", "tsig_key_alg", "tsig_key_name"])
        if not has_address:
            errors.append(f"Access list entry {idx}: Must specify at least one of: address, tsig_key")
        
        # Validate address if present
        if "address" in entry:
            address = entry["address"]
            # Check if it's a valid IP address, network, or special keyword
            special_addresses = ["any", "localhost", "localnets"]
            if address not in special_addresses:
                try:
                    if "/" in address:
                        # It's a network
                        from ipaddress import ip_network
                        ip_network(address)
                    else:
                        # It's an IP address
                        ip_address(address)
                except ValueError:
                    # Could be a named ACL reference
                    if not re.match(r'^[a-zA-Z0-9._\-]+$', address):
                        errors.append(f"Access list entry {idx}: Invalid address '{address}'")
        
        # Validate TSIG key fields if present
        tsig_fields = ["tsig_key", "tsig_key_alg", "tsig_key_name"]
        tsig_present = [f for f in tsig_fields if f in entry and entry[f]]
        if tsig_present:
            # If any TSIG field is present, all should be present
            if len(tsig_present) != len(tsig_fields):
                errors.append(f"Access list entry {idx}: When using TSIG, all fields must be present: {', '.join(tsig_fields)}")
            elif "tsig_key_alg" in entry:
                valid_algs = ["HMAC-MD5", "HMAC-SHA256", "HMAC-SHA1", "HMAC-SHA224", "HMAC-SHA384", "HMAC-SHA512"]
                if entry["tsig_key_alg"] not in valid_algs:
                    errors.append(f"Access list entry {idx}: Invalid TSIG algorithm '{entry['tsig_key_alg']}'")
    
    return errors

def validate_named_acl_records():
    """Validate Named ACL records from JSON file."""
    print("\n--- Named ACL Validation ---")
    
    named_acl_file = "playbooks/add/cabgridmgr.amfam.com/namedacl.json"
    
    # Read Named ACL data from JSON file
    try:
        with open(named_acl_file, 'r') as file:
            named_acl_data = json.load(file)
            
            # Named ACL data should be a list
            if not isinstance(named_acl_data, list):
                # If it's a single dict, convert to list
                if isinstance(named_acl_data, dict):
                    named_acl_data = [named_acl_data]
                else:
                    print(f"ERROR: Named ACL data must be a list or dictionary")
                    return False
            
            # Check if it's empty
            if not named_acl_data:
                print(f"Named ACL file exists but contains no data. Skipping validation.")
                return True
                
            print(f"Found {len(named_acl_data)} Named ACL configurations to validate.")
            
    except Exception as e:
        print(f"Error reading file {named_acl_file}: {str(e)}")
        return False
    
    # Now continue with validation
    validation_failed = False
    missing_required_fields = []
    invalid_names = []
    invalid_access_lists = []
    invalid_extattrs = []
    duplicate_names = []
    existing_acls = []
    warnings = []
    
    # Track ACL names to detect duplicates
    acl_names_seen = set()
    
    # Validate each Named ACL
    for acl_idx, acl in enumerate(named_acl_data):
        # Check for required name field
        if "name" not in acl:
            missing_required_fields.append(f"ACL at index {acl_idx}: Missing required field 'name'")
            validation_failed = True
            print(f"ERROR: ACL at index {acl_idx} missing required field 'name'")
            continue
        
        acl_name = acl["name"]
        print(f"\nValidating Named ACL: {acl_name}")
        
        # Check for duplicate names in the JSON
        if acl_name in acl_names_seen:
            duplicate_names.append(acl_name)
            validation_failed = True
            print(f"ERROR: Duplicate Named ACL name '{acl_name}' found in JSON")
        acl_names_seen.add(acl_name)
        
        # Validate name format
        is_valid, error_msg = validate_named_acl_name(acl_name)
        if not is_valid:
            invalid_names.append(f"{acl_name}: {error_msg}")
            validation_failed = True
            print(f"ERROR: {error_msg}")
        
        # Check if ACL already exists
        existing_acl = check_existing_named_acl(acl_name)
        if existing_acl:
            existing_acls.append(acl_name)
            print(f"Named ACL '{acl_name}' already exists in Infoblox")
            
            # Compare access lists if both exist
            if "access_list" in acl and "access_list" in existing_acl[0]:
                existing_count = len(existing_acl[0]["access_list"])
                new_count = len(acl["access_list"])
                if existing_count != new_count:
                    print(f"  Access list entries will change from {existing_count} to {new_count}")
        
        # Validate access_list if present
        if "access_list" in acl:
            access_list_errors = validate_named_acl_access_list(acl["access_list"], acl_name)
            if access_list_errors:
                invalid_access_lists.extend([f"{acl_name}: {error}" for error in access_list_errors])
                validation_failed = True
                for error in access_list_errors:
                    print(f"ERROR: {acl_name}: {error}")
        else:
            warnings.append(f"{acl_name}: No access_list defined (ACL will have no rules)")
            print(f"WARNING: {acl_name}: No access_list defined")
        
        # Validate comment if present
        if "comment" in acl:
            if not isinstance(acl["comment"], str):
                print(f"ERROR: {acl_name}: Comment must be a string")
                validation_failed = True
            elif len(acl["comment"]) > 256:
                warnings.append(f"{acl_name}: Comment exceeds 256 characters")
                print(f"WARNING: {acl_name}: Comment exceeds recommended length")
        
        # Validate extensible attributes if present
        if "extattrs" in acl:
            if not isinstance(acl["extattrs"], dict):
                invalid_extattrs.append(f"{acl_name}: extattrs must be a dictionary")
                validation_failed = True
                print(f"ERROR: {acl_name}: extattrs must be a dictionary")
            else:
                # Validate each extensible attribute
                for attr_name, attr_value in acl["extattrs"].items():
                    if not isinstance(attr_name, str):
                        invalid_extattrs.append(f"{acl_name}: Extensible attribute name must be string")
                        validation_failed = True
                    if attr_value is None or (isinstance(attr_value, str) and not attr_value.strip()):
                        warnings.append(f"{acl_name}: Extensible attribute '{attr_name}' has empty value")
                        print(f"WARNING: {acl_name}: Extensible attribute '{attr_name}' has empty value")
        
        # Check for _ref field that should be excluded
        if "_ref" in acl:
            print(f"INFO: {acl_name}: '_ref' field will be excluded during create/update")
        
        # Validate circular references
        if "access_list" in acl:
            for entry in acl["access_list"]:
                if "address" in entry and entry["address"] == acl_name:
                    warnings.append(f"{acl_name}: Self-reference detected in access list")
                    print(f"WARNING: {acl_name}: ACL references itself in access list")
        
        # Display what will be changed
        if existing_acl:
            print(f"\nChanges to be applied for Named ACL '{acl_name}':")
            changes_count = 0
            
            existing_config = existing_acl[0]
            
            # Check access_list changes
            if "access_list" in acl:
                existing_access_list = existing_config.get("access_list", [])
                if acl["access_list"] != existing_access_list:
                    changes_count += 1
                    print(f"  access_list: {len(existing_access_list)} entries → {len(acl['access_list'])} entries")
            
            # Check comment changes
            if "comment" in acl:
                existing_comment = existing_config.get("comment", "")
                if acl["comment"] != existing_comment:
                    changes_count += 1
                    print(f"  comment: '{existing_comment}' → '{acl['comment']}'")
            
            # Check extattrs changes
            if "extattrs" in acl:
                existing_extattrs = existing_config.get("extattrs", {})
                if acl["extattrs"] != existing_extattrs:
                    changes_count += 1
                    print(f"  extattrs: will be updated")
            
            if changes_count == 0:
                print(f"  No changes detected for Named ACL '{acl_name}'")
    
    # Check for ACL dependencies
    print("\nChecking for ACL dependencies...")
    acl_references = {}
    for acl in named_acl_data:
        if "name" in acl and "access_list" in acl:
            acl_name = acl["name"]
            for entry in acl["access_list"]:
                if "address" in entry:
                    address = entry["address"]
                    # Check if address is another ACL name
                    if address in acl_names_seen and address != acl_name:
                        if address not in acl_references:
                            acl_references[address] = []
                        acl_references[address].append(acl_name)
    
    if acl_references:
        print("ACL references found:")
        for referenced_acl, referencing_acls in acl_references.items():
            print(f"  '{referenced_acl}' is referenced by: {', '.join(referencing_acls)}")
    
    # Display validation summary
    print("\nNamed ACL Validation Summary:")
    print(f"Total ACL configurations: {len(named_acl_data)}")
    print(f"ACLs with missing required fields: {len(missing_required_fields)}")
    print(f"ACLs with invalid names: {len(invalid_names)}")
    print(f"ACLs with invalid access lists: {len(set([err.split(':')[0] for err in invalid_access_lists]))}")
    print(f"ACLs with invalid extattrs: {len(set([err.split(':')[0] for err in invalid_extattrs]))}")
    print(f"Duplicate ACL names: {len(duplicate_names)}")
    print(f"Existing ACLs to update: {len(existing_acls)}")
    print(f"Warnings: {len(warnings)}")
    
    if existing_acls:
        print(f"\nExisting ACLs that will be updated: {', '.join(existing_acls)}")
    
    return not validation_failed

def check_existing_named_acl(name):
    """Check if a Named ACL already exists in Infoblox."""
    try:
        response = requests.get(
            f"{BASE_URL}/namedacl",
            params={"name": name},
            auth=(INFOBLOX_USERNAME, INFOBLOX_PASSWORD),
            verify=VALIDATE_CERTS,
            timeout=HTTP_TIMEOUT
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"✗ Error checking Named ACL {name}: {response.status_code}")
            return []
    except Exception as e:
        print(f"✗ Error checking Named ACL {name}: {str(e)}")
        return []

def validate_named_acl_name(name):
    """Validate Named ACL name format."""
    if not name:
        return False, "Named ACL name cannot be empty"
    
    # Check length
    if len(name) > 256:
        return False, f"Named ACL name too long ({len(name)} characters, max 256)"
    
    # Check for valid characters (alphanumeric, underscore, hyphen, period)
    if not re.match(r'^[a-zA-Z0-9._\-]+$', name):
        return False, "Named ACL name contains invalid characters (only alphanumeric, underscore, hyphen, period allowed)"
    
    # Cannot start with underscore or hyphen
    if name.startswith('_') or name.startswith('-'):
        return False, "Named ACL name cannot start with underscore or hyphen"
    
    # Check for reserved names
    reserved_names = ['any', 'none', 'localhost', 'localnets']
    if name.lower() in reserved_names:
        return False, f"Named ACL name '{name}' is reserved"
    
    return True, None

def validate_named_acl_access_list(access_list, acl_name):
    """Validate Named ACL access list entries."""
    errors = []
    
    if not isinstance(access_list, list):
        errors.append(f"Access list must be a list")
        return errors
    
    for idx, entry in enumerate(access_list):
        if not isinstance(entry, dict):
            errors.append(f"Access list entry {idx} must be a dictionary")
            continue
        
        # Check for required permission field
        if "permission" not in entry:
            errors.append(f"Access list entry {idx}: Missing required field 'permission'")
            continue
        
        # Validate permission
        valid_permissions = ["ALLOW", "DENY"]
        if entry["permission"] not in valid_permissions:
            errors.append(f"Access list entry {idx}: Invalid permission '{entry['permission']}' (must be ALLOW or DENY)")
        
        # Check for address specification
        has_address = any(key in entry for key in ["address", "tsig_key", "tsig_key_alg", "tsig_key_name"])
        if not has_address:
            errors.append(f"Access list entry {idx}: Must specify at least one of: address, tsig_key")
        
        # Validate address if present
        if "address" in entry:
            address = entry["address"]
            # Check if it's a valid IP address, network, or special keyword
            special_addresses = ["any", "localhost", "localnets"]
            if address not in special_addresses:
                try:
                    if "/" in address:
                        # It's a network
                        from ipaddress import ip_network
                        ip_network(address)
                    else:
                        # It's an IP address
                        ip_address(address)
                except ValueError:
                    # Could be a named ACL reference
                    if not re.match(r'^[a-zA-Z0-9._\-]+$', address):
                        errors.append(f"Access list entry {idx}: Invalid address '{address}'")
        
        # Validate TSIG key fields if present
        tsig_fields = ["tsig_key", "tsig_key_alg", "tsig_key_name"]
        tsig_present = [f for f in tsig_fields if f in entry and entry[f]]
        if tsig_present:
            # If any TSIG field is present, all should be present
            if len(tsig_present) != len(tsig_fields):
                errors.append(f"Access list entry {idx}: When using TSIG, all fields must be present: {', '.join(tsig_fields)}")
            elif "tsig_key_alg" in entry:
                valid_algs = ["HMAC-MD5", "HMAC-SHA256", "HMAC-SHA1", "HMAC-SHA224", "HMAC-SHA384", "HMAC-SHA512"]
                if entry["tsig_key_alg"] not in valid_algs:
                    errors.append(f"Access list entry {idx}: Invalid TSIG algorithm '{entry['tsig_key_alg']}'")
    
    return errors

def validate_named_acl_records():
    """Validate Named ACL records from JSON file."""
    print("\n--- Named ACL Validation ---")
    
    named_acl_file = "playbooks/add/cabgridmgr.amfam.com/namedacl.json"
    
    # Read Named ACL data from JSON file
    try:
        with open(named_acl_file, 'r') as file:
            named_acl_data = json.load(file)
            
            # Named ACL data should be a list
            if not isinstance(named_acl_data, list):
                # If it's a single dict, convert to list
                if isinstance(named_acl_data, dict):
                    named_acl_data = [named_acl_data]
                else:
                    print(f"ERROR: Named ACL data must be a list or dictionary")
                    return False
            
            # Check if it's empty
            if not named_acl_data:
                print(f"Named ACL file exists but contains no data. Skipping validation.")
                return True
                
            print(f"Found {len(named_acl_data)} Named ACL configurations to validate.")
            
    except Exception as e:
        print(f"Error reading file {named_acl_file}: {str(e)}")
        return False
    
    # Now continue with validation
    validation_failed = False
    missing_required_fields = []
    invalid_names = []
    invalid_access_lists = []
    invalid_extattrs = []
    duplicate_names = []
    existing_acls = []
    warnings = []
    
    # Track ACL names to detect duplicates
    acl_names_seen = set()
    
    # Validate each Named ACL
    for acl_idx, acl in enumerate(named_acl_data):
        # Check for required name field
        if "name" not in acl:
            missing_required_fields.append(f"ACL at index {acl_idx}: Missing required field 'name'")
            validation_failed = True
            print(f"ERROR: ACL at index {acl_idx} missing required field 'name'")
            continue
        
        acl_name = acl["name"]
        print(f"\nValidating Named ACL: {acl_name}")
        
        # Check for duplicate names in the JSON
        if acl_name in acl_names_seen:
            duplicate_names.append(acl_name)
            validation_failed = True
            print(f"ERROR: Duplicate Named ACL name '{acl_name}' found in JSON")
        acl_names_seen.add(acl_name)
        
        # Validate name format
        is_valid, error_msg = validate_named_acl_name(acl_name)
        if not is_valid:
            invalid_names.append(f"{acl_name}: {error_msg}")
            validation_failed = True
            print(f"ERROR: {error_msg}")
        
        # Check if ACL already exists
        existing_acl = check_existing_named_acl(acl_name)
        if existing_acl:
            existing_acls.append(acl_name)
            print(f"Named ACL '{acl_name}' already exists in Infoblox")
            
            # Compare access lists if both exist
            if "access_list" in acl and "access_list" in existing_acl[0]:
                existing_count = len(existing_acl[0]["access_list"])
                new_count = len(acl["access_list"])
                if existing_count != new_count:
                    print(f"  Access list entries will change from {existing_count} to {new_count}")
        
        # Validate access_list if present
        if "access_list" in acl:
            access_list_errors = validate_named_acl_access_list(acl["access_list"], acl_name)
            if access_list_errors:
                invalid_access_lists.extend([f"{acl_name}: {error}" for error in access_list_errors])
                validation_failed = True
                for error in access_list_errors:
                    print(f"ERROR: {acl_name}: {error}")
        else:
            warnings.append(f"{acl_name}: No access_list defined (ACL will have no rules)")
            print(f"WARNING: {acl_name}: No access_list defined")
        
        # Validate comment if present
        if "comment" in acl:
            if not isinstance(acl["comment"], str):
                print(f"ERROR: {acl_name}: Comment must be a string")
                validation_failed = True
            elif len(acl["comment"]) > 256:
                warnings.append(f"{acl_name}: Comment exceeds 256 characters")
                print(f"WARNING: {acl_name}: Comment exceeds recommended length")
        
        # Validate extensible attributes if present
        if "extattrs" in acl:
            if not isinstance(acl["extattrs"], dict):
                invalid_extattrs.append(f"{acl_name}: extattrs must be a dictionary")
                validation_failed = True
                print(f"ERROR: {acl_name}: extattrs must be a dictionary")
            else:
                # Validate each extensible attribute
                for attr_name, attr_value in acl["extattrs"].items():
                    if not isinstance(attr_name, str):
                        invalid_extattrs.append(f"{acl_name}: Extensible attribute name must be string")
                        validation_failed = True
                    if attr_value is None or (isinstance(attr_value, str) and not attr_value.strip()):
                        warnings.append(f"{acl_name}: Extensible attribute '{attr_name}' has empty value")
                        print(f"WARNING: {acl_name}: Extensible attribute '{attr_name}' has empty value")
        
        # Check for _ref field that should be excluded
        if "_ref" in acl:
            print(f"INFO: {acl_name}: '_ref' field will be excluded during create/update")
        
        # Validate circular references
        if "access_list" in acl:
            for entry in acl["access_list"]:
                if "address" in entry and entry["address"] == acl_name:
                    warnings.append(f"{acl_name}: Self-reference detected in access list")
                    print(f"WARNING: {acl_name}: ACL references itself in access list")
        
        # Display what will be changed
        if existing_acl:
            print(f"\nChanges to be applied for Named ACL '{acl_name}':")
            changes_count = 0
            
            existing_config = existing_acl[0]
            
            # Check access_list changes
            if "access_list" in acl:
                existing_access_list = existing_config.get("access_list", [])
                if acl["access_list"] != existing_access_list:
                    changes_count += 1
                    print(f"  access_list: {len(existing_access_list)} entries → {len(acl['access_list'])} entries")
            
            # Check comment changes
            if "comment" in acl:
                existing_comment = existing_config.get("comment", "")
                if acl["comment"] != existing_comment:
                    changes_count += 1
                    print(f"  comment: '{existing_comment}' → '{acl['comment']}'")
            
            # Check extattrs changes
            if "extattrs" in acl:
                existing_extattrs = existing_config.get("extattrs", {})
                if acl["extattrs"] != existing_extattrs:
                    changes_count += 1
                    print(f"  extattrs: will be updated")
            
            if changes_count == 0:
                print(f"  No changes detected for Named ACL '{acl_name}'")
    
    # Check for ACL dependencies
    print("\nChecking for ACL dependencies...")
    acl_references = {}
    for acl in named_acl_data:
        if "name" in acl and "access_list" in acl:
            acl_name = acl["name"]
            for entry in acl["access_list"]:
                if "address" in entry:
                    address = entry["address"]
                    # Check if address is another ACL name
                    if address in acl_names_seen and address != acl_name:
                        if address not in acl_references:
                            acl_references[address] = []
                        acl_references[address].append(acl_name)
    
    if acl_references:
        print("ACL references found:")
        for referenced_acl, referencing_acls in acl_references.items():
            print(f"  '{referenced_acl}' is referenced by: {', '.join(referencing_acls)}")
    
    # Display validation summary
    print("\nNamed ACL Validation Summary:")
    print(f"Total ACL configurations: {len(named_acl_data)}")
    print(f"ACLs with missing required fields: {len(missing_required_fields)}")
    print(f"ACLs with invalid names: {len(invalid_names)}")
    print(f"ACLs with invalid access lists: {len(set([err.split(':')[0] for err in invalid_access_lists]))}")
    print(f"ACLs with invalid extattrs: {len(set([err.split(':')[0] for err in invalid_extattrs]))}")
    print(f"Duplicate ACL names: {len(duplicate_names)}")
    print(f"Existing ACLs to update: {len(existing_acls)}")
    print(f"Warnings: {len(warnings)}")
    
    if existing_acls:
        print(f"\nExisting ACLs that will be updated: {', '.join(existing_acls)}")
    
    return not validation_failed

def check_existing_adminuser(name):
    """Check if an admin user already exists in Infoblox."""
    try:
        response = requests.get(
            f"{BASE_URL}/adminuser",
            params={"name": name},
            auth=(INFOBLOX_USERNAME, INFOBLOX_PASSWORD),
            verify=VALIDATE_CERTS,
            timeout=HTTP_TIMEOUT
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"✗ Error checking admin user {name}: {response.status_code}")
            return []
    except Exception as e:
        print(f"✗ Error checking admin user {name}: {str(e)}")
        return []

def validate_adminuser_name(name):
    """Validate admin user name format."""
    if not name:
        return False, "Admin user name cannot be empty"
    
    # Check length
    if len(name) > 256:
        return False, f"Admin user name too long ({len(name)} characters, max 256)"
    
    # Check for valid characters (alphanumeric, underscore, hyphen, period)
    if not re.match(r'^[a-zA-Z0-9._-]+$', name):
        return False, "Admin user name contains invalid characters (only alphanumeric, underscore, hyphen, period allowed)"
    
    # Cannot start with underscore or hyphen
    if name.startswith('_') or name.startswith('-'):
        return False, "Admin user name cannot start with underscore or hyphen"
    
    # Check for reserved names
    reserved_names = ['admin', 'root', 'system', 'administrator']
    if name.lower() in reserved_names:
        return False, f"Admin user name '{name}' is reserved"
    
    return True, None

def check_admingroup_exists(group_name):
    """Check if an admin group exists in Infoblox."""
    try:
        response = requests.get(
            f"{BASE_URL}/admingroup",
            params={"name": group_name},
            auth=(INFOBLOX_USERNAME, INFOBLOX_PASSWORD),
            verify=VALIDATE_CERTS,
            timeout=HTTP_TIMEOUT
        )
        
        if response.status_code == 200:
            return len(response.json()) > 0
        else:
            print(f"✗ Error checking admin group {group_name}: {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Error checking admin group {group_name}: {str(e)}")
        return False

def validate_adminuser_records():
    """Validate Admin User records from JSON file."""
    print("\n--- Admin User Validation ---")
    
    adminuser_file = "playbooks/add/cabgridmgr.amfam.com/adminuser.json"
    
    # Read admin user data from JSON file
    try:
        with open(adminuser_file, 'r') as file:
            adminuser_records = json.load(file)
            
            # If the content is not a list, convert it to a list with one item
            if not isinstance(adminuser_records, list):
                adminuser_records = [adminuser_records]
                
            print(f"Found {len(adminuser_records)} admin user records to validate.")
    except Exception as e:
        print(f"Error reading file {adminuser_file}: {str(e)}")
        return False
    
    # Now continue with validation since we have records to check
    validation_failed = False
    missing_required_fields = []
    invalid_names = []
    invalid_emails = []
    missing_admin_groups = []
    existing_admin_users = []
    disabled_users = []
    
    # Check for required fields and validate basic structure
    for record in adminuser_records:
        # Check required fields
        if not all(key in record for key in ["name"]):
            missing_fields = [field for field in ["name"] if field not in record]
            missing_required_fields.append(f"{record.get('name', 'Unknown admin user')}: missing {', '.join(missing_fields)}")
            validation_failed = True
            continue
        
        # Validate admin user name format
        name = record["name"]
        is_valid, error_msg = validate_adminuser_name(name)
        if not is_valid:
            invalid_names.append(f"{name}: {error_msg}")
            validation_failed = True
        
        # Validate email format if present
        if "email" in record and record["email"]:
            email = record["email"]
            # Basic email validation
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, email):
                invalid_emails.append(f"{name}: Invalid email format '{email}'")
                validation_failed = True
        
        # Check if user is disabled
        if "disable" in record and record["disable"]:
            disabled_users.append(name)
            print(f"INFO: Admin user '{name}' is set to be disabled")
    
    # Display validation errors
    for missing in missing_required_fields:
        print(f"ERROR: Missing required fields - {missing}")
    
    for invalid in invalid_names:
        print(f"ERROR: Invalid admin user name - {invalid}")
    
    for invalid in invalid_emails:
        print(f"ERROR: Invalid email - {invalid}")
    
    # Check for existing admin users in Infoblox
    for record in adminuser_records:
        if "name" not in record:
            continue
            
        existing_users = check_existing_adminuser(record['name'])
        if existing_users:
            existing_user = existing_users[0]
            existing_admin_users.append(record['name'])
            print(f"Admin user '{record['name']}' already exists in Infoblox")
            
            # Note about password
            print(f"  Note: Password will not be updated for existing user '{record['name']}'")
            
            # Compare admin groups if specified
            if 'admin_groups' in record and record['admin_groups']:
                existing_groups = existing_user.get('admin_groups', [])
                new_groups = record['admin_groups']
                
                # Extract group names from references
                existing_group_names = []
                for group_ref in existing_groups:
                    if isinstance(group_ref, dict) and 'name' in group_ref:
                        existing_group_names.append(group_ref['name'])
                    elif isinstance(group_ref, str) and 'admingroup/' in group_ref:
                        # Extract group name from reference
                        group_name = group_ref.split(':')[-1]
                        existing_group_names.append(group_name)
                
                new_group_names = []
                for group in new_groups:
                    if isinstance(group, dict) and 'name' in group:
                        new_group_names.append(group['name'])
                    elif isinstance(group, str):
                        new_group_names.append(group)
                
                if set(existing_group_names) != set(new_group_names):
                    print(f"  Admin groups will be updated: {existing_group_names} -> {new_group_names}")
            
            # Compare other attributes
            if 'email' in record and record.get('email') != existing_user.get('email'):
                print(f"  Email will be updated: '{existing_user.get('email', '')}' -> '{record['email']}'")
            
            if 'disable' in record and record.get('disable') != existing_user.get('disable', False):
                status_change = "disabled" if record['disable'] else "enabled"
                print(f"  User will be {status_change}")
        else:
            # New user
            print(f"INFO: Admin user '{record['name']}' does not exist and will be skipped (password not specified in JSON)")
    
    # Check admin group existence
    for record in adminuser_records:
        if "admin_groups" in record and record["admin_groups"]:
            for group in record["admin_groups"]:
                group_name = None
                
                if isinstance(group, dict) and 'name' in group:
                    group_name = group['name']
                elif isinstance(group, str):
                    group_name = group
                
                if group_name and not check_admingroup_exists(group_name):
                    missing_admin_groups.append(f"{record['name']}: Admin Group '{group_name}'")
                    print(f"ERROR: Admin Group '{group_name}' does not exist")
                    validation_failed = True
    
    # Check for duplicate admin user names within the JSON
    user_names = [record.get('name') for record in adminuser_records if 'name' in record]
    duplicates = []
    seen = set()
    for name in user_names:
        if name in seen:
            duplicates.append(name)
        seen.add(name)
    
    if duplicates:
        print(f"ERROR: Duplicate admin user names found in JSON: {', '.join(duplicates)}")
        validation_failed = True
    
    # Validate logical consistency
    for record in adminuser_records:
        name = record.get('name', 'Unknown')
        
        # Check if comment is provided for documentation
        if 'comment' not in record or not record.get('comment'):
            print(f"INFO: Admin user '{name}' has no comment - consider adding documentation")
        
        # Check time zone if specified
        if 'time_zone' in record and record['time_zone']:
            # Common time zones for validation
            common_timezones = ['UTC', 'US/Eastern', 'US/Central', 'US/Mountain', 'US/Pacific', 
                               'Europe/London', 'Europe/Paris', 'Asia/Tokyo', 'Australia/Sydney']
            if record['time_zone'] not in common_timezones:
                print(f"INFO: Admin user '{name}' has uncommon time zone '{record['time_zone']}' - verify it's valid")
        
        # Check for auth_type consistency
        if 'auth_type' in record:
            auth_type = record['auth_type']
            valid_auth_types = ['LOCAL', 'RADIUS', 'TACACS_PLUS', 'SAML', 'CERTIFICATE']
            if auth_type not in valid_auth_types:
                print(f"WARNING: Admin user '{name}' has invalid auth_type '{auth_type}' (valid: {', '.join(valid_auth_types)})")
        
        # Check for use_time_zone flag
        if 'use_time_zone' in record and record['use_time_zone'] and 'time_zone' not in record:
            print(f"WARNING: Admin user '{name}' has use_time_zone=true but no time_zone specified")
    
    # Display validation summary
    print("\nAdmin User Validation Summary:")
    print(f"Total records checked: {len(adminuser_records)}")
    print(f"Records with missing required fields: {len(missing_required_fields)}")
    print(f"Records with invalid names: {len(invalid_names)}")
    print(f"Records with invalid emails: {len(invalid_emails)}")
    print(f"Missing admin groups: {len(missing_admin_groups)}")
    print(f"Existing admin users: {len(existing_admin_users)}")
    print(f"Disabled users: {len(disabled_users)}")
    
    if existing_admin_users:
        print(f"Existing admin users: {', '.join(existing_admin_users)}")
    if disabled_users:
        print(f"Disabled users: {', '.join(disabled_users)}")
    
    return not validation_failed

def check_existing_network_container(network, network_view):
    """Check if a network container already exists in Infoblox."""
    try:
        response = requests.get(
            f"{BASE_URL}/networkcontainer",
            params={"network": network, "network_view": network_view},
            auth=(INFOBLOX_USERNAME, INFOBLOX_PASSWORD),
            verify=VALIDATE_CERTS,
            timeout=HTTP_TIMEOUT
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"✗ Error checking network container {network}: {response.status_code}")
            return []
    except Exception as e:
        print(f"✗ Error checking network container {network}: {str(e)}")
        return []

def validate_network_container_cidr(network):
    """Validate network container CIDR format."""
    try:
        if '/' not in network:
            return False, "Network container must be in CIDR format (e.g., 192.168.0.0/16)"
        
        # Parse and validate the network
        from ipaddress import IPv4Network, IPv6Network, AddressValueError
        
        try:
            # Try IPv4 first
            net = IPv4Network(network, strict=True)
            # Network containers are typically larger subnets
            if net.prefixlen > 24:
                print(f"INFO: Network container {network} has small prefix length (/{net.prefixlen}) - containers are typically larger subnets")
            return True, None
        except AddressValueError:
            try:
                # Try IPv6
                net = IPv6Network(network, strict=True)
                return True, None
            except AddressValueError as e:
                return False, f"Invalid network format: {str(e)}"
    
    except Exception as e:
        return False, f"Error validating network: {str(e)}"

def check_network_container_conflicts(network, network_view, existing_containers):
    """Check for conflicts with existing network containers."""
    conflicts = []
    warnings = []
    
    try:
        from ipaddress import IPv4Network, IPv6Network
        
        # Parse the new network
        try:
            new_net = IPv4Network(network)
            is_ipv4 = True
        except:
            new_net = IPv6Network(network)
            is_ipv4 = False
        
        # Check against existing containers
        for container in existing_containers:
            existing_network = container.get('network')
            existing_view = container.get('network_view')
            
            if existing_view != network_view:
                continue  # Different views, no conflict
            
            try:
                if is_ipv4:
                    existing_net = IPv4Network(existing_network)
                else:
                    existing_net = IPv6Network(existing_network)
                
                # Check for overlaps
                if new_net.overlaps(existing_net):
                    if new_net == existing_net:
                        conflicts.append(f"Exact match with existing container {existing_network}")
                    elif new_net.subnet_of(existing_net):
                        warnings.append(f"Is a subnet of existing container {existing_network}")
                    elif existing_net.subnet_of(new_net):
                        warnings.append(f"Contains existing container {existing_network}")
                    else:
                        conflicts.append(f"Overlaps with existing container {existing_network}")
            except:
                continue  # Skip if can't parse
                
    except Exception as e:
        print(f"Error checking conflicts: {str(e)}")
    
    return conflicts, warnings

def validate_network_container_records():
    """Validate Network Container records from JSON file."""
    print("\n--- Network Container Validation ---")
    
    networkcontainer_file = "playbooks/add/cabgridmgr.amfam.com/networkcontainer.json"
    
    # Read network container data from JSON file
    try:
        with open(networkcontainer_file, 'r') as file:
            networkcontainer_records = json.load(file)
            
            # If the content is not a list, convert it to a list with one item
            if not isinstance(networkcontainer_records, list):
                networkcontainer_records = [networkcontainer_records]
                
            print(f"Found {len(networkcontainer_records)} network container records to validate.")
    except Exception as e:
        print(f"Error reading file {networkcontainer_file}: {str(e)}")
        return False
    
    # Now continue with validation since we have records to check
    validation_failed = False
    missing_required_fields = []
    invalid_networks = []
    invalid_dhcp_options = []
    missing_network_views = []
    missing_discovery_members = []
    network_conflicts = []
    network_warnings = []
    existing_containers = []
    
    # Get all existing network containers first for conflict checking
    all_existing_containers = []
    for record in networkcontainer_records:
        if "network_view" in record:
            try:
                response = requests.get(
                    f"{BASE_URL}/networkcontainer",
                    params={"network_view": record["network_view"]},
                    auth=(INFOBLOX_USERNAME, INFOBLOX_PASSWORD),
                    verify=VALIDATE_CERTS,
                    timeout=HTTP_TIMEOUT
                )
                if response.status_code == 200:
                    all_existing_containers.extend(response.json())
            except:
                pass
    
    # Check for required fields and validate basic structure
    for record in networkcontainer_records:
        # Check required fields
        if not all(key in record for key in ["network", "network_view"]):
            missing_fields = [field for field in ["network", "network_view"] if field not in record]
            missing_required_fields.append(f"{record.get('network', 'Unknown network container')}: missing {', '.join(missing_fields)}")
            validation_failed = True
            continue
        
        # Validate network CIDR format
        network = record["network"]
        is_valid, error_msg = validate_network_container_cidr(network)
        if not is_valid:
            invalid_networks.append(f"{network}: {error_msg}")
            validation_failed = True
        
        # Check for conflicts with existing containers
        conflicts, warnings = check_network_container_conflicts(network, record["network_view"], all_existing_containers)
        for conflict in conflicts:
            network_conflicts.append(f"{network}: {conflict}")
            validation_failed = True
        for warning in warnings:
            network_warnings.append(f"{network}: {warning}")
        
        # Validate DHCP options if present
        if "options" in record and record["options"]:
            for option in record["options"]:
                if not all(key in option for key in ["name", "num", "use_option", "vendor_class"]):
                    invalid_dhcp_options.append(f"{network}: DHCP option missing required fields")
                    validation_failed = True
    
    # Display validation errors
    for missing in missing_required_fields:
        print(f"ERROR: Missing required fields - {missing}")
    
    for invalid in invalid_networks:
        print(f"ERROR: Invalid network format - {invalid}")
    
    for invalid in invalid_dhcp_options:
        print(f"ERROR: Invalid DHCP option - {invalid}")
    
    for conflict in network_conflicts:
        print(f"ERROR: Network conflict - {conflict}")
    
    for warning in network_warnings:
        print(f"WARNING: Network relationship - {warning}")
    
    # Check for existing network containers in Infoblox
    for record in networkcontainer_records:
        if "network" not in record or "network_view" not in record:
            continue
            
        existing_nc = check_existing_network_container(record['network'], record['network_view'])
        if existing_nc:
            existing_container = existing_nc[0]
            existing_containers.append(record['network'])
            print(f"Network container '{record['network']}' already exists in network view '{record['network_view']}'")
            print(f"  Current comment: {existing_container.get('comment', 'N/A')}")
            
            # Compare key attributes
            if 'enable_ddns' in record and record.get('enable_ddns') != existing_container.get('enable_ddns'):
                print(f"  DDNS will be updated: {existing_container.get('enable_ddns')} -> {record['enable_ddns']}")
            
            if 'enable_dhcp_thresholds' in record and record.get('enable_dhcp_thresholds') != existing_container.get('enable_dhcp_thresholds'):
                print(f"  DHCP thresholds will be updated: {existing_container.get('enable_dhcp_thresholds')} -> {record['enable_dhcp_thresholds']}")
    
    # Check Network View existence
    for record in networkcontainer_records:
        if "network_view" not in record:
            continue
            
        if not check_network_view_exists(record["network_view"]):
            missing_network_views.append(f"{record['network']}: Network View '{record['network_view']}'")
            print(f"ERROR: Network View '{record['network_view']}' does not exist")
            validation_failed = True
    
    # Check Discovery Member existence
    for record in networkcontainer_records:
        if "discovery_member" in record and record["discovery_member"]:
            if not check_grid_member_exists(record["discovery_member"]):
                missing_discovery_members.append(f"{record['network']}: Discovery Member '{record['discovery_member']}'")
                print(f"ERROR: Discovery Member '{record['discovery_member']}' does not exist")
                validation_failed = True
    
    # Check for overlapping network containers within the same network view
    from ipaddress import IPv4Network, IPv6Network
    
    ipv4_containers = []
    ipv6_containers = []
    
    for record in networkcontainer_records:
        if "network" not in record or "network_view" not in record:
            continue
            
        network = record["network"]
        network_view = record["network_view"]
        
        try:
            # Try IPv4
            net = IPv4Network(network)
            ipv4_containers.append((network, net, network_view))
        except:
            try:
                # Try IPv6
                net = IPv6Network(network)
                ipv6_containers.append((network, net, network_view))
            except:
                pass  # Already validated above
    
    # Check for overlapping IPv4 containers
    for i, (network1, net1, view1) in enumerate(ipv4_containers):
        for j, (network2, net2, view2) in enumerate(ipv4_containers[i+1:], i+1):
            if view1 == view2:
                if net1.overlaps(net2) and net1 != net2:
                    print(f"WARNING: Network containers '{network1}' and '{network2}' overlap in network view '{view1}'")
                elif net1.subnet_of(net2):
                    print(f"INFO: Network container '{network1}' is a subnet of '{network2}' in view '{view1}'")
                elif net2.subnet_of(net1):
                    print(f"INFO: Network container '{network2}' is a subnet of '{network1}' in view '{view1}'")
    
    # Check for duplicate network/network_view combinations
    network_view_pairs = [(record.get('network'), record.get('network_view')) for record in networkcontainer_records if 'network' in record and 'network_view' in record]
    duplicates = []
    seen = set()
    for network, network_view in network_view_pairs:
        if (network, network_view) in seen:
            duplicates.append(f"{network} in network view {network_view}")
        seen.add((network, network_view))
    
    if duplicates:
        print(f"ERROR: Duplicate network/network_view combinations found: {', '.join(duplicates)}")
        validation_failed = True
    
    # Validate logical consistency
    for record in networkcontainer_records:
        network = record.get('network', 'Unknown')
        
        # Check if comment is provided for documentation
        if 'comment' not in record or not record.get('comment'):
            print(f"INFO: Network container '{network}' has no comment - consider adding documentation")
        
        # Check DDNS settings consistency
        if record.get('enable_ddns', False):
            ddns_settings = ['ddns_domainname', 'ddns_ttl', 'ddns_generate_hostname']
            missing_ddns = [s for s in ddns_settings if s not in record or not record.get(s)]
            if missing_ddns:
                print(f"INFO: Network container '{network}' has DDNS enabled but missing settings: {', '.join(missing_ddns)}")
        
        # Check discovery settings consistency
        if record.get('enable_discovery', False) and 'discovery_member' not in record:
            print(f"WARNING: Network container '{network}' has discovery enabled but no discovery_member specified")
        
        # Check email warnings consistency
        if record.get('enable_email_warnings', False) and not record.get('email_list'):
            print(f"WARNING: Network container '{network}' has email warnings enabled but no email_list specified")
        
        # Check for very large containers
        try:
            from ipaddress import IPv4Network
            net = IPv4Network(record.get('network', ''))
            if net.prefixlen < 16:
                print(f"INFO: Network container '{network}' is very large (/{net.prefixlen}) - ensure this is intentional")
        except:
            pass
    
    # Display validation summary
    print("\nNetwork Container Validation Summary:")
    print(f"Total records checked: {len(networkcontainer_records)}")
    print(f"Records with missing required fields: {len(missing_required_fields)}")
    print(f"Records with invalid network formats: {len(invalid_networks)}")
    print(f"Records with invalid DHCP options: {len(invalid_dhcp_options)}")
    print(f"Records with network conflicts: {len(network_conflicts)}")
    print(f"Records with network warnings: {len(network_warnings)}")
    print(f"Missing network views: {len(missing_network_views)}")
    print(f"Missing discovery members: {len(missing_discovery_members)}")
    print(f"Existing network containers: {len(existing_containers)}")
    
    if existing_containers:
        print(f"Existing network containers: {', '.join(existing_containers)}")
    
    return not validation_failed

def check_existing_ipv6_network_container(network, network_view):
    """Check if an IPv6 network container already exists in Infoblox."""
    try:
        response = requests.get(
            f"{BASE_URL}/ipv6networkcontainer",
            params={"network": network, "network_view": network_view},
            auth=(INFOBLOX_USERNAME, INFOBLOX_PASSWORD),
            verify=VALIDATE_CERTS,
            timeout=HTTP_TIMEOUT
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"✗ Error checking IPv6 network container {network}: {response.status_code}")
            return []
    except Exception as e:
        print(f"✗ Error checking IPv6 network container {network}: {str(e)}")
        return []

def validate_ipv6_network_container_cidr(network):
    """Validate IPv6 network container CIDR format."""
    try:
        if '/' not in network:
            return False, "IPv6 network container must be in CIDR format (e.g., 2001:db8::/32)"
        
        # Parse and validate the network
        from ipaddress import IPv6Network, AddressValueError
        
        try:
            net = IPv6Network(network, strict=True)
            
            # IPv6 containers are typically larger prefixes
            if net.prefixlen > 64:
                print(f"INFO: IPv6 network container {network} has small prefix length (/{net.prefixlen}) - containers are typically larger subnets")
            
            # Common IPv6 container prefix lengths
            if net.prefixlen not in [32, 48, 56, 64]:
                print(f"INFO: IPv6 network container {network} uses non-standard prefix length (/{net.prefixlen}) - common values are /32, /48, /56, /64")
            
            return True, None
        except AddressValueError as e:
            return False, f"Invalid IPv6 network format: {str(e)}"
    
    except Exception as e:
        return False, f"Error validating IPv6 network: {str(e)}"

def check_ipv6_network_container_conflicts(network, network_view, existing_containers):
    """Check for conflicts with existing IPv6 network containers."""
    conflicts = []
    warnings = []
    
    try:
        from ipaddress import IPv6Network
        
        # Parse the new network
        new_net = IPv6Network(network)
        
        # Check against existing containers
        for container in existing_containers:
            existing_network = container.get('network')
            existing_view = container.get('network_view')
            
            if existing_view != network_view:
                continue  # Different views, no conflict
            
            try:
                existing_net = IPv6Network(existing_network)
                
                # Check for overlaps
                if new_net.overlaps(existing_net):
                    if new_net == existing_net:
                        conflicts.append(f"Exact match with existing IPv6 container {existing_network}")
                    elif new_net.subnet_of(existing_net):
                        warnings.append(f"Is a subnet of existing IPv6 container {existing_network}")
                    elif existing_net.subnet_of(new_net):
                        warnings.append(f"Contains existing IPv6 container {existing_network}")
                    else:
                        conflicts.append(f"Overlaps with existing IPv6 container {existing_network}")
            except:
                continue  # Skip if can't parse
                
    except Exception as e:
        print(f"Error checking IPv6 conflicts: {str(e)}")
    
    return conflicts, warnings

def validate_ipv6_dhcp_option(option):
    """Validate IPv6 DHCP option structure and values."""
    errors = []
    
    # Check required fields
    required_fields = ["name", "num", "use_option", "vendor_class"]
    for field in required_fields:
        if field not in option:
            errors.append(f"Missing required field: {field}")
    
    if errors:
        return errors
    
    # Validate option number for DHCPv6
    try:
        option_num = int(option["num"])
        # DHCPv6 option numbers have different range than DHCPv4
        if not (1 <= option_num <= 65535):
            errors.append(f"DHCPv6 option number {option_num} must be between 1 and 65535")
    except (ValueError, TypeError):
        errors.append(f"Option number '{option['num']}' must be a valid integer")
    
    # Validate vendor_class for IPv6
    if option.get("vendor_class") != "DHCPv6":
        errors.append(f"vendor_class must be 'DHCPv6' for IPv6 networks, got: {option.get('vendor_class')}")
    
    # Validate specific DHCPv6 option values
    option_name = option.get("name", "")
    option_value = option.get("value", "")
    
    # Common DHCPv6 options
    if option_name == "dhcp6.name-servers":
        # Should be valid IPv6 addresses (comma-separated)
        if option_value:
            ips = [ip.strip() for ip in str(option_value).split(',')]
            for ip in ips:
                try:
                    from ipaddress import IPv6Address
                    IPv6Address(ip)
                except ValueError:
                    errors.append(f"Invalid IPv6 address in {option_name}: {ip}")
    
    elif option_name == "dhcp6.domain-search":
        # Should be valid domain names
        if option_value and not re.match(r'^[a-zA-Z0-9.-]+$', str(option_value)):
            errors.append(f"Invalid domain search format: {option_value}")
    
    return errors

def validate_ipv6_network_container_records():
    """Validate IPv6 Network Container records from JSON file."""
    print("\n--- IPv6 Network Container Validation ---")
    
    ipv6networkcontainer_file = "playbooks/add/cabgridmgr.amfam.com/networkipv6container.json"
    
    # Read IPv6 network container data from JSON file
    try:
        with open(ipv6networkcontainer_file, 'r') as file:
            ipv6networkcontainer_records = json.load(file)
            
            # If the content is not a list, convert it to a list with one item
            if not isinstance(ipv6networkcontainer_records, list):
                ipv6networkcontainer_records = [ipv6networkcontainer_records]
                
            print(f"Found {len(ipv6networkcontainer_records)} IPv6 network container records to validate.")
    except Exception as e:
        print(f"Error reading file {ipv6networkcontainer_file}: {str(e)}")
        return False
    
    # Now continue with validation since we have records to check
    validation_failed = False
    missing_required_fields = []
    invalid_networks = []
    invalid_dhcp_options = []
    invalid_lifetimes = []
    missing_network_views = []
    network_conflicts = []
    network_warnings = []
    existing_containers = []
    
    # Get all existing IPv6 network containers first for conflict checking
    all_existing_containers = []
    for record in ipv6networkcontainer_records:
        if "network_view" in record:
            try:
                response = requests.get(
                    f"{BASE_URL}/ipv6networkcontainer",
                    params={"network_view": record["network_view"]},
                    auth=(INFOBLOX_USERNAME, INFOBLOX_PASSWORD),
                    verify=VALIDATE_CERTS,
                    timeout=HTTP_TIMEOUT
                )
                if response.status_code == 200:
                    all_existing_containers.extend(response.json())
            except:
                pass
    
    # Check for required fields and validate basic structure
    for record in ipv6networkcontainer_records:
        # Check required fields
        if not all(key in record for key in ["network", "network_view"]):
            missing_fields = [field for field in ["network", "network_view"] if field not in record]
            missing_required_fields.append(f"{record.get('network', 'Unknown IPv6 network container')}: missing {', '.join(missing_fields)}")
            validation_failed = True
            continue
        
        # Validate network CIDR format
        network = record["network"]
        is_valid, error_msg = validate_ipv6_network_container_cidr(network)
        if not is_valid:
            invalid_networks.append(f"{network}: {error_msg}")
            validation_failed = True
        
        # Check for conflicts with existing containers
        conflicts, warnings = check_ipv6_network_container_conflicts(network, record["network_view"], all_existing_containers)
        for conflict in conflicts:
            network_conflicts.append(f"{network}: {conflict}")
            validation_failed = True
        for warning in warnings:
            network_warnings.append(f"{network}: {warning}")
        
        # Validate DHCPv6 options if present
        if "options" in record and record["options"]:
            for option in record["options"]:
                option_errors = validate_ipv6_dhcp_option(option)
                if option_errors:
                    for error in option_errors:
                        invalid_dhcp_options.append(f"{network}: {error}")
                    validation_failed = True
        
        # Validate IPv6-specific lifetime values
        if "preferred_lifetime" in record:
            try:
                pref_lifetime = int(record["preferred_lifetime"])
                if pref_lifetime < 0 or pref_lifetime > 4294967295:
                    invalid_lifetimes.append(f"{network}: preferred_lifetime {pref_lifetime} must be 0-4294967295")
                    validation_failed = True
            except (ValueError, TypeError):
                invalid_lifetimes.append(f"{network}: preferred_lifetime must be a valid integer")
                validation_failed = True
        
        if "valid_lifetime" in record:
            try:
                valid_lifetime = int(record["valid_lifetime"])
                if valid_lifetime < 0 or valid_lifetime > 4294967295:
                    invalid_lifetimes.append(f"{network}: valid_lifetime {valid_lifetime} must be 0-4294967295")
                    validation_failed = True
            except (ValueError, TypeError):
                invalid_lifetimes.append(f"{network}: valid_lifetime must be a valid integer")
                validation_failed = True
        
        # Check lifetime consistency
        if "preferred_lifetime" in record and "valid_lifetime" in record:
            try:
                pref = int(record["preferred_lifetime"])
                valid = int(record["valid_lifetime"])
                if pref > valid:
                    invalid_lifetimes.append(f"{network}: preferred_lifetime ({pref}) cannot be greater than valid_lifetime ({valid})")
                    validation_failed = True
            except:
                pass  # Already validated above
    
    # Display validation errors
    for missing in missing_required_fields:
        print(f"ERROR: Missing required fields - {missing}")
    
    for invalid in invalid_networks:
        print(f"ERROR: Invalid network format - {invalid}")
    
    for invalid in invalid_dhcp_options:
        print(f"ERROR: Invalid DHCPv6 option - {invalid}")
    
    for invalid in invalid_lifetimes:
        print(f"ERROR: Invalid lifetime value - {invalid}")
    
    for conflict in network_conflicts:
        print(f"ERROR: Network conflict - {conflict}")
    
    for warning in network_warnings:
        print(f"WARNING: Network relationship - {warning}")
    
    # Check for existing IPv6 network containers in Infoblox
    for record in ipv6networkcontainer_records:
        if "network" not in record or "network_view" not in record:
            continue
            
        existing_nc = check_existing_ipv6_network_container(record['network'], record['network_view'])
        if existing_nc:
            existing_container = existing_nc[0]
            existing_containers.append(record['network'])
            print(f"IPv6 network container '{record['network']}' already exists in network view '{record['network_view']}'")
            print(f"  Current comment: {existing_container.get('comment', 'N/A')}")
            
            # Compare key attributes
            if 'enable_ddns' in record and record.get('enable_ddns') != existing_container.get('enable_ddns'):
                print(f"  DDNS will be updated: {existing_container.get('enable_ddns')} -> {record['enable_ddns']}")
            
            if 'preferred_lifetime' in record and record.get('preferred_lifetime') != existing_container.get('preferred_lifetime'):
                print(f"  Preferred lifetime will be updated: {existing_container.get('preferred_lifetime')} -> {record['preferred_lifetime']}")
            
            if 'valid_lifetime' in record and record.get('valid_lifetime') != existing_container.get('valid_lifetime'):
                print(f"  Valid lifetime will be updated: {existing_container.get('valid_lifetime')} -> {record['valid_lifetime']}")
    
    # Check Network View existence
    for record in ipv6networkcontainer_records:
        if "network_view" not in record:
            continue
            
        if not check_network_view_exists(record["network_view"]):
            missing_network_views.append(f"{record['network']}: Network View '{record['network_view']}'")
            print(f"ERROR: Network View '{record['network_view']}' does not exist")
            validation_failed = True
    
    # Check for overlapping IPv6 network containers within the same network view
    from ipaddress import IPv6Network
    
    ipv6_containers = []
    
    for record in ipv6networkcontainer_records:
        if "network" not in record or "network_view" not in record:
            continue
            
        network = record["network"]
        network_view = record["network_view"]
        
        try:
            net = IPv6Network(network)
            ipv6_containers.append((network, net, network_view))
        except:
            pass  # Already validated above
    
    # Check for overlapping IPv6 containers
    for i, (network1, net1, view1) in enumerate(ipv6_containers):
        for j, (network2, net2, view2) in enumerate(ipv6_containers[i+1:], i+1):
            if view1 == view2:
                if net1.overlaps(net2) and net1 != net2:
                    print(f"WARNING: IPv6 network containers '{network1}' and '{network2}' overlap in network view '{view1}'")
                elif net1.subnet_of(net2):
                    print(f"INFO: IPv6 network container '{network1}' is a subnet of '{network2}' in view '{view1}'")
                elif net2.subnet_of(net1):
                    print(f"INFO: IPv6 network container '{network2}' is a subnet of '{network1}' in view '{view1}'")
    
    # Check for duplicate network/network_view combinations
    network_view_pairs = [(record.get('network'), record.get('network_view')) for record in ipv6networkcontainer_records if 'network' in record and 'network_view' in record]
    duplicates = []
    seen = set()
    for network, network_view in network_view_pairs:
        if (network, network_view) in seen:
            duplicates.append(f"{network} in network view {network_view}")
        seen.add((network, network_view))
    
    if duplicates:
        print(f"ERROR: Duplicate network/network_view combinations found: {', '.join(duplicates)}")
        validation_failed = True
    
    # Validate logical consistency
    for record in ipv6networkcontainer_records:
        network = record.get('network', 'Unknown')
        
        # Check if comment is provided for documentation
        if 'comment' not in record or not record.get('comment'):
            print(f"INFO: IPv6 network container '{network}' has no comment - consider adding documentation")
        
        # Check DDNS settings consistency
        if record.get('enable_ddns', False):
            ddns_settings = ['ddns_domainname', 'ddns_ttl', 'ddns_generate_hostname']
            missing_ddns = [s for s in ddns_settings if s not in record or not record.get(s)]
            if missing_ddns:
                print(f"INFO: IPv6 network container '{network}' has DDNS enabled but missing settings: {', '.join(missing_ddns)}")
        
        # Check for very large IPv6 containers
        try:
            net = IPv6Network(record.get('network', ''))
            if net.prefixlen < 32:
                print(f"INFO: IPv6 network container '{network}' is very large (/{net.prefixlen}) - ensure this is intentional")
        except:
            pass
    
    # Display validation summary
    print("\nIPv6 Network Container Validation Summary:")
    print(f"Total records checked: {len(ipv6networkcontainer_records)}")
    print(f"Records with missing required fields: {len(missing_required_fields)}")
    print(f"Records with invalid network formats: {len(invalid_networks)}")
    print(f"Records with invalid DHCPv6 options: {len(invalid_dhcp_options)}")
    print(f"Records with invalid lifetime values: {len(invalid_lifetimes)}")
    print(f"Records with network conflicts: {len(network_conflicts)}")
    print(f"Records with network warnings: {len(network_warnings)}")
    print(f"Missing network views: {len(missing_network_views)}")
    print(f"Existing IPv6 network containers: {len(existing_containers)}")
    
    if existing_containers:
        print(f"Existing IPv6 network containers: {', '.join(existing_containers)}")
    
    return not validation_failed

def check_existing_range(start_addr, end_addr, network_view):
    """Check if a DHCP range already exists in Infoblox."""
    try:
        response = requests.get(
            f"{BASE_URL}/range",
            params={"start_addr": start_addr, "end_addr": end_addr, "network_view": network_view},
            auth=(INFOBLOX_USERNAME, INFOBLOX_PASSWORD),
            verify=VALIDATE_CERTS,
            timeout=HTTP_TIMEOUT
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"✗ Error checking range {start_addr}-{end_addr}: {response.status_code}")
            return []
    except Exception as e:
        print(f"✗ Error checking range {start_addr}-{end_addr}: {str(e)}")
        return []

def validate_range_addresses(start_addr, end_addr, network):
    """Validate range addresses and their relationship."""
    errors = []
    
    try:
        from ipaddress import ip_address, ip_network
        
        # Validate start address
        try:
            start_ip = ip_address(start_addr)
        except ValueError:
            errors.append(f"Invalid start address: {start_addr}")
            return errors
        
        # Validate end address
        try:
            end_ip = ip_address(end_addr)
        except ValueError:
            errors.append(f"Invalid end address: {end_addr}")
            return errors
        
        # Check if addresses are same type (IPv4 or IPv6)
        if type(start_ip) != type(end_ip):
            errors.append(f"Start and end addresses must be same type (IPv4 or IPv6)")
            return errors
        
        # Check if start is before end
        if start_ip > end_ip:
            errors.append(f"Start address {start_addr} must be before end address {end_addr}")
        
        # Validate network if provided
        if network:
            try:
                net = ip_network(network)
                
                # Check if addresses are within network
                if start_ip not in net:
                    errors.append(f"Start address {start_addr} is not within network {network}")
                if end_ip not in net:
                    errors.append(f"End address {end_addr} is not within network {network}")
                
                # Check if range uses network or broadcast address
                if start_ip == net.network_address:
                    errors.append(f"Range should not include network address {start_addr}")
                if end_ip == net.broadcast_address and net.num_addresses > 1:
                    errors.append(f"Range should not include broadcast address {end_addr}")
                    
            except ValueError as e:
                errors.append(f"Invalid network: {network} - {str(e)}")
        
        # Calculate range size
        range_size = int(end_ip) - int(start_ip) + 1
        if range_size > 65536:  # Warn for very large ranges
            print(f"WARNING: Large range size ({range_size} addresses) from {start_addr} to {end_addr}")
            
    except Exception as e:
        errors.append(f"Error validating range: {str(e)}")
    
    return errors

def check_range_overlaps(start_addr, end_addr, network_view, existing_ranges):
    """Check for overlaps with existing ranges."""
    overlaps = []
    
    try:
        from ipaddress import ip_address
        
        new_start = ip_address(start_addr)
        new_end = ip_address(end_addr)
        
        for existing in existing_ranges:
            if existing.get('network_view') != network_view:
                continue
                
            existing_start = ip_address(existing.get('start_addr'))
            existing_end = ip_address(existing.get('end_addr'))
            
            # Check for overlaps
            if not (new_end < existing_start or new_start > existing_end):
                if new_start == existing_start and new_end == existing_end:
                    overlaps.append(f"Exact match with existing range {existing_start}-{existing_end}")
                else:
                    overlaps.append(f"Overlaps with existing range {existing_start}-{existing_end}")
                    
    except Exception as e:
        print(f"Error checking range overlaps: {str(e)}")
    
    return overlaps

def check_ms_server_exists(ms_server_ref):
    """Check if Microsoft server exists in Infoblox."""
    try:
        # MS server references are typically in format "ms_server/..."
        if ms_server_ref and ms_server_ref.startswith('ms_server/'):
            response = requests.get(
                f"{BASE_URL}/{ms_server_ref}",
                auth=(INFOBLOX_USERNAME, INFOBLOX_PASSWORD),
                verify=VALIDATE_CERTS,
                timeout=HTTP_TIMEOUT
            )
            return response.status_code == 200
        return False
    except Exception as e:
        print(f"✗ Error checking MS server {ms_server_ref}: {str(e)}")
        return False

def validate_range_records():
    """Validate DHCP Range records from JSON file."""
    print("\n--- DHCP Range Validation ---")
    
    range_file = "../prod_changes/cabgridmgr.amfam.com/network_range.json"
    
    # Read range data from JSON file
    try:
        with open(range_file, 'r') as file:
            range_records = json.load(file)
            
            # If the content is not a list, convert it to a list with one item
            if not isinstance(range_records, list):
                range_records = [range_records]
                
            print(f"Found {len(range_records)} DHCP range records to validate.")
    except Exception as e:
        print(f"Error reading file {range_file}: {str(e)}")
        return False
    
    # Now continue with validation since we have records to check
    validation_failed = False
    missing_required_fields = []
    invalid_addresses = []
    invalid_associations = []
    missing_network_views = []
    missing_networks = []
    missing_members = []
    missing_ms_servers = []
    range_overlaps = []
    existing_ranges = []
    disabled_ranges = []
    
    # Valid server association types
    valid_association_types = ['NONE', 'MEMBER', 'MS_SERVER', 'MS_FAILOVER', 'FAILOVER']
    
    # Get all existing ranges first for overlap checking
    all_existing_ranges = []
    for record in range_records:
        network_view = record.get('network_view', 'default')
        try:
            response = requests.get(
                f"{BASE_URL}/range",
                params={"network_view": network_view, "_max_results": 1000},
                auth=(INFOBLOX_USERNAME, INFOBLOX_PASSWORD),
                verify=VALIDATE_CERTS,
                timeout=HTTP_TIMEOUT
            )
            if response.status_code == 200:
                all_existing_ranges.extend(response.json())
        except:
            pass
    
    # Check for required fields and validate basic structure
    for record in range_records:
        # Check required fields
        required_fields = ["start_addr", "end_addr", "network"]
        if not all(key in record for key in required_fields):
            missing_fields = [field for field in required_fields if field not in record]
            range_id = f"{record.get('start_addr', '?')}-{record.get('end_addr', '?')}"
            missing_required_fields.append(f"{range_id}: missing {', '.join(missing_fields)}")
            validation_failed = True
            continue
        
        # Validate address formats and relationship
        start_addr = record["start_addr"]
        end_addr = record["end_addr"]
        network = record["network"]
        
        address_errors = validate_range_addresses(start_addr, end_addr, network)
        if address_errors:
            for error in address_errors:
                invalid_addresses.append(f"{start_addr}-{end_addr}: {error}")
            validation_failed = True
        
        # Check for overlaps with existing ranges
        network_view = record.get('network_view', 'default')
        overlaps = check_range_overlaps(start_addr, end_addr, network_view, all_existing_ranges)
        for overlap in overlaps:
            range_overlaps.append(f"{start_addr}-{end_addr}: {overlap}")
        
        # Validate server association type
        if 'server_association_type' in record:
            assoc_type = record['server_association_type']
            if assoc_type not in valid_association_types:
                invalid_associations.append(f"{start_addr}-{end_addr}: Invalid association type '{assoc_type}' (valid: {', '.join(valid_association_types)})")
                validation_failed = True
        
        # Check if range is disabled
        if record.get('disable', False):
            disabled_ranges.append(f"{start_addr}-{end_addr}")
            print(f"INFO: Range {start_addr}-{end_addr} is set to be disabled")
    
    # Display validation errors
    for missing in missing_required_fields:
        print(f"ERROR: Missing required fields - {missing}")
    
    for invalid in invalid_addresses:
        print(f"ERROR: Invalid address - {invalid}")
    
    for invalid in invalid_associations:
        print(f"ERROR: Invalid association - {invalid}")
    
    for overlap in range_overlaps:
        print(f"WARNING: Range overlap - {overlap}")
    
    # Check for existing ranges in Infoblox
    for record in range_records:
        if not all(key in record for key in ["start_addr", "end_addr"]):
            continue
            
        start_addr = record["start_addr"]
        end_addr = record["end_addr"]
        network_view = record.get('network_view', 'default')
        
        existing = check_existing_range(start_addr, end_addr, network_view)
        if existing:
            existing_range = existing[0]
            existing_ranges.append(f"{start_addr}-{end_addr}")
            print(f"Range {start_addr}-{end_addr} already exists in network view '{network_view}'")
            
            # Compare attributes
            if 'comment' in record and record.get('comment') != existing_range.get('comment'):
                print(f"  Comment will be updated: '{existing_range.get('comment', '')}' -> '{record['comment']}'")
            
            if 'disable' in record and record.get('disable') != existing_range.get('disable', False):
                status = "disabled" if record['disable'] else "enabled"
                print(f"  Range will be {status}")
    
    # Check Network View existence
    for record in range_records:
        network_view = record.get('network_view', 'default')
        if network_view != 'default' and not check_network_view_exists(network_view):
            missing_network_views.append(f"{record['start_addr']}-{record['end_addr']}: Network View '{network_view}'")
            print(f"ERROR: Network View '{network_view}' does not exist")
            validation_failed = True
    
    # Check Network existence
    for record in range_records:
        if 'network' not in record:
            continue
            
        network = record['network']
        network_view = record.get('network_view', 'default')
        
        if not check_network_exists(network, network_view):
            missing_networks.append(f"{record['start_addr']}-{record['end_addr']}: Network '{network}'")
            print(f"ERROR: Network '{network}' does not exist in view '{network_view}'")
            validation_failed = True
    
    # Check Member existence for MEMBER association
    for record in range_records:
        if record.get('server_association_type') == 'MEMBER' and 'member' in record:
            member_name = record['member'].get('name') if isinstance(record['member'], dict) else record['member']
            if member_name and not check_grid_member_exists(member_name):
                missing_members.append(f"{record['start_addr']}-{record['end_addr']}: Member '{member_name}'")
                print(f"ERROR: Grid Member '{member_name}' does not exist")
                validation_failed = True
    
    # Check MS Server existence for MS_SERVER association
    for record in range_records:
        if record.get('server_association_type') == 'MS_SERVER' and 'ms_server' in record:
            ms_server = record['ms_server']
            if ms_server and not check_ms_server_exists(ms_server):
                missing_ms_servers.append(f"{record['start_addr']}-{record['end_addr']}: MS Server '{ms_server}'")
                print(f"ERROR: Microsoft Server '{ms_server}' does not exist")
                validation_failed = True
    
    # Validate logical consistency
    for record in range_records:
        start_addr = record.get('start_addr', '')
        end_addr = record.get('end_addr', '')
        range_id = f"{start_addr}-{end_addr}"
        
        # Check association consistency
        assoc_type = record.get('server_association_type', 'NONE')
        
        if assoc_type == 'MEMBER' and 'member' not in record:
            print(f"WARNING: Range {range_id} has MEMBER association but no member specified")
        
        if assoc_type == 'MS_SERVER' and 'ms_server' not in record:
            print(f"WARNING: Range {range_id} has MS_SERVER association but no ms_server specified")
        
        if assoc_type == 'MS_FAILOVER' and 'failover_association' not in record:
            print(f"WARNING: Range {range_id} has MS_FAILOVER association but no failover_association specified")
        
        if assoc_type == 'FAILOVER' and 'failover_association' not in record:
            print(f"WARNING: Range {range_id} has FAILOVER association but no failover_association specified")
        
        # Check if name is provided for documentation
        if 'name' not in record or not record.get('name'):
            print(f"INFO: Range {range_id} has no name - consider adding for documentation")
        
        # Check if comment is provided
        if 'comment' not in record or not record.get('comment'):
            print(f"INFO: Range {range_id} has no comment - consider adding documentation")
    
    # Check for duplicate ranges in JSON
    range_pairs = []
    for record in range_records:
        if all(key in record for key in ["start_addr", "end_addr", "network_view"]):
            range_pair = (record["start_addr"], record["end_addr"], record.get("network_view", "default"))
            range_pairs.append(range_pair)
    
    duplicates = []
    seen = set()
    for range_pair in range_pairs:
        if range_pair in seen:
            duplicates.append(f"{range_pair[0]}-{range_pair[1]} in view {range_pair[2]}")
        seen.add(range_pair)
    
    if duplicates:
        print(f"ERROR: Duplicate ranges found in JSON: {', '.join(duplicates)}")
        validation_failed = True
    
    # Display validation summary
    print("\nDHCP Range Validation Summary:")
    print(f"Total records checked: {len(range_records)}")
    print(f"Records with missing required fields: {len(missing_required_fields)}")
    print(f"Records with invalid addresses: {len(invalid_addresses)}")
    print(f"Records with invalid associations: {len(invalid_associations)}")
    print(f"Records with range overlaps: {len(range_overlaps)}")
    print(f"Missing network views: {len(missing_network_views)}")
    print(f"Missing networks: {len(missing_networks)}")
    print(f"Missing members: {len(missing_members)}")
    print(f"Missing MS servers: {len(missing_ms_servers)}")
    print(f"Existing ranges: {len(existing_ranges)}")
    print(f"Disabled ranges: {len(disabled_ranges)}")
    
    if existing_ranges:
        print(f"Existing ranges: {', '.join(existing_ranges[:5])}" + (" ..." if len(existing_ranges) > 5 else ""))
    if disabled_ranges:
        print(f"Disabled ranges: {', '.join(disabled_ranges[:5])}" + (" ..." if len(disabled_ranges) > 5 else ""))
    
    return not validation_failed

def check_existing_srv_record(name, view):
    """Check if an SRV record already exists in Infoblox."""
    try:
        response = requests.get(
            f"{BASE_URL}/record:srv",
            params={"name": name, "view": view},
            auth=(INFOBLOX_USERNAME, INFOBLOX_PASSWORD),
            verify=VALIDATE_CERTS,
            timeout=HTTP_TIMEOUT
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"✗ Error checking SRV record {name}: {response.status_code}")
            return []
    except Exception as e:
        print(f"✗ Error checking SRV record {name}: {str(e)}")
        return []

def validate_srv_name_format(name):
    """Validate SRV record name format."""
    # SRV record format: _service._protocol.domain
    # Example: _http._tcp.example.com
    
    if not name:
        return False, "SRV record name cannot be empty"
    
    # Check if name starts with underscore
    if not name.startswith('_'):
        return False, "SRV record name must start with underscore (e.g., _service._protocol.domain)"
    
    # Split into components
    parts = name.split('.')
    if len(parts) < 3:
        return False, "SRV record name must have format _service._protocol.domain"
    
    # Check service name
    if not parts[0].startswith('_') or len(parts[0]) < 2:
        return False, f"Invalid service name '{parts[0]}' - must start with underscore"
    
    # Check protocol
    if not parts[1].startswith('_') or parts[1] not in ['_tcp', '_udp', '_tls', '_sctp']:
        return False, f"Invalid protocol '{parts[1]}' - must be _tcp, _udp, _tls, or _sctp"
    
    # Common service names for validation
    common_services = ['_http', '_https', '_ldap', '_ldaps', '_sip', '_sips', '_xmpp', '_imap', 
                      '_pop3', '_smtp', '_ftp', '_ssh', '_telnet', '_kerberos', '_ntp']
    
    if parts[0] not in common_services:
        print(f"INFO: Uncommon service name '{parts[0]}' - verify it's correct")
    
    return True, None

def validate_srv_target(target):
    """Validate SRV target format."""
    if not target:
        return False, "SRV target cannot be empty"
    
    # Target should be a valid hostname
    if not re.match(r'^[a-zA-Z0-9.-]+$', target):
        return False, "SRV target contains invalid characters"
    
    # Should end with a dot for FQDN
    if not target.endswith('.'):
        return False, "SRV target should be fully qualified (end with a dot)"
    
    return True, None

def validate_srv_values(priority, weight, port):
    """Validate SRV priority, weight, and port values."""
    errors = []
    
    # Validate priority (0-65535)
    try:
        priority_val = int(priority)
        if not (0 <= priority_val <= 65535):
            errors.append(f"Priority {priority_val} must be between 0 and 65535")
    except (ValueError, TypeError):
        errors.append(f"Priority '{priority}' must be a valid integer")
    
    # Validate weight (0-65535)
    try:
        weight_val = int(weight)
        if not (0 <= weight_val <= 65535):
            errors.append(f"Weight {weight_val} must be between 0 and 65535")
    except (ValueError, TypeError):
        errors.append(f"Weight '{weight}' must be a valid integer")
    
    # Validate port (1-65535)
    try:
        port_val = int(port)
        if not (1 <= port_val <= 65535):
            errors.append(f"Port {port_val} must be between 1 and 65535")
    except (ValueError, TypeError):
        errors.append(f"Port '{port}' must be a valid integer")
    
    return errors

def check_srv_target_exists(target, view):
    """Check if the SRV target exists as a valid record."""
    # Remove trailing dot for lookup
    target_name = target.rstrip('.')
    
    # Check A records
    try:
        response = requests.get(
            f"{BASE_URL}/record:a",
            params={"name": target_name, "view": view},
            auth=(INFOBLOX_USERNAME, INFOBLOX_PASSWORD),
            verify=VALIDATE_CERTS,
            timeout=HTTP_TIMEOUT
        )
        if response.status_code == 200 and len(response.json()) > 0:
            return True
    except:
        pass
    
    # Check AAAA records
    try:
        response = requests.get(
            f"{BASE_URL}/record:aaaa",
            params={"name": target_name, "view": view},
            auth=(INFOBLOX_USERNAME, INFOBLOX_PASSWORD),
            verify=VALIDATE_CERTS,
            timeout=HTTP_TIMEOUT
        )
        if response.status_code == 200 and len(response.json()) > 0:
            return True
    except:
        pass
    
    # Check CNAME records
    try:
        response = requests.get(
            f"{BASE_URL}/record:cname",
            params={"name": target_name, "view": view},
            auth=(INFOBLOX_USERNAME, INFOBLOX_PASSWORD),
            verify=VALIDATE_CERTS,
            timeout=HTTP_TIMEOUT
        )
        if response.status_code == 200 and len(response.json()) > 0:
            return True
    except:
        pass
    
    return False

def validate_srv_records():
    """Validate SRV records from JSON file."""
    print("\n--- SRV Record Validation ---")
    
    srv_record_file = "../prod_changes/cabgridmgr.amfam.com/srv_record.json"
    
    # Read SRV record data from JSON file
    try:
        with open(srv_record_file, 'r') as file:
            srv_records = json.load(file)
            
            # If the content is not a list, convert it to a list with one item
            if not isinstance(srv_records, list):
                srv_records = [srv_records]
                
            print(f"Found {len(srv_records)} SRV records to validate.")
    except Exception as e:
        print(f"Error reading file {srv_record_file}: {str(e)}")
        return False
    
    # Now continue with validation since we have records to check
    validation_failed = False
    missing_required_fields = []
    invalid_names = []
    invalid_targets = []
    invalid_values = []
    missing_targets = []
    failed_domains = []
    invalid_ttls = []
    existing_records = []
    
    # Check for required fields and validate values
    for record in srv_records:
        # Check required fields
        required_fields = ["name", "port", "priority", "target", "weight", "view"]
        if not all(key in record for key in required_fields):
            missing_fields = [field for field in required_fields if field not in record]
            missing_required_fields.append(f"{record.get('name', 'Unknown record')}: missing {', '.join(missing_fields)}")
            validation_failed = True
            continue
        
        # Validate SRV name format
        name = record["name"]
        is_valid, error_msg = validate_srv_name_format(name)
        if not is_valid:
            invalid_names.append(f"{name}: {error_msg}")
            validation_failed = True
        
        # Validate target format
        target = record["target"]
        is_valid, error_msg = validate_srv_target(target)
        if not is_valid:
            invalid_targets.append(f"{name}: target '{target}' - {error_msg}")
            validation_failed = True
        
        # Validate priority, weight, and port
        value_errors = validate_srv_values(record["priority"], record["weight"], record["port"])
        if value_errors:
            for error in value_errors:
                invalid_values.append(f"{name}: {error}")
            validation_failed = True
        
        # Validate TTL if specified
        if "ttl" in record and record["ttl"] is not None:
            try:
                ttl = int(record["ttl"])
                if ttl < 0 or ttl > 2147483647:
                    invalid_ttls.append(f"{name}: TTL {ttl} (must be 0-2147483647)")
                    validation_failed = True
            except (ValueError, TypeError):
                invalid_ttls.append(f"{name}: TTL '{record['ttl']}' is not a valid integer")
                validation_failed = True
    
    # Display validation errors
    for missing in missing_required_fields:
        print(f"ERROR: Missing required fields - {missing}")
    
    for invalid in invalid_names:
        print(f"ERROR: Invalid SRV name - {invalid}")
    
    for invalid in invalid_targets:
        print(f"ERROR: Invalid target - {invalid}")
    
    for invalid in invalid_values:
        print(f"ERROR: Invalid value - {invalid}")
    
    for invalid in invalid_ttls:
        print(f"ERROR: Invalid TTL value - {invalid}")
    
    # Check for existing SRV records in Infoblox
    for record in srv_records:
        if "name" not in record or "view" not in record:
            continue
            
        existing_srv = check_existing_srv_record(record['name'], record['view'])
        if existing_srv:
            existing_records.append(record['name'])
            print(f"SRV record '{record['name']}' already exists in view '{record['view']}'")
            
            # Check if configuration matches
            for existing in existing_srv:
                if (existing.get('port') == record['port'] and 
                    existing.get('priority') == record['priority'] and
                    existing.get('weight') == record['weight'] and
                    existing.get('target') == record['target']):
                    print(f"  Exact match found for {record['name']}")
                else:
                    print(f"  Different configuration exists:")
                    print(f"    Existing: priority={existing.get('priority')}, weight={existing.get('weight')}, port={existing.get('port')}, target={existing.get('target')}")
                    print(f"    New: priority={record['priority']}, weight={record['weight']}, port={record['port']}, target={record['target']}")
    
    # Check if targets exist
    for record in srv_records:
        if "target" not in record or "view" not in record:
            continue
            
        if not check_srv_target_exists(record['target'], record['view']):
            missing_targets.append(f"{record['name']}: target '{record['target']}'")
            print(f"WARNING: SRV target '{record['target']}' does not resolve to any record")
    
    # Check for DNS zone existence
    parent_domains = {}
    for record in srv_records:
        if "name" not in record or "view" not in record:
            continue
            
        # Extract domain from SRV name (_service._protocol.domain)
        parts = record['name'].split('.', 2)
        if len(parts) >= 3:
            domain = parts[2]
            if domain not in parent_domains:
                parent_domains[domain] = record['view']
    
    for domain, view in parent_domains.items():
        zone_exists = check_zone_exists(domain, view)
        if not zone_exists:
            print(f"ERROR: Parent domain '{domain}' does not exist in Infoblox")
            validation_failed = True
            failed_domains.append(domain)
    
    # Validate logical consistency
    for record in srv_records:
        name = record.get('name', 'Unknown')
        
        # Check for common patterns
        if '_http._tcp' in name and record.get('port') != 80:
            print(f"INFO: HTTP service '{name}' uses non-standard port {record.get('port')} (standard: 80)")
        
        if '_https._tcp' in name and record.get('port') != 443:
            print(f"INFO: HTTPS service '{name}' uses non-standard port {record.get('port')} (standard: 443)")
        
        if '_ldap._tcp' in name and record.get('port') not in [389, 636]:
            print(f"INFO: LDAP service '{name}' uses non-standard port {record.get('port')} (standard: 389 or 636)")
        
        # Check for load balancing configuration
        srv_by_service = {}
        for r in srv_records:
            if r.get('view') == record.get('view'):
                service_key = r['name']
                if service_key not in srv_by_service:
                    srv_by_service[service_key] = []
                srv_by_service[service_key].append(r)
        
        # Check for multiple targets with same priority
        service_records = srv_by_service.get(name, [])
        if len(service_records) > 1:
            priorities = [r['priority'] for r in service_records]
            if len(set(priorities)) == 1:
                print(f"INFO: Service '{name}' has multiple records with same priority - load balancing by weight")
    
    # Check for duplicate SRV records
    srv_tuples = []
    for record in srv_records:
        if all(key in record for key in ["name", "port", "priority", "target", "weight", "view"]):
            srv_tuple = (record["name"], record["port"], record["priority"], record["target"], record["weight"], record["view"])
            srv_tuples.append(srv_tuple)
    
    duplicates = []
    seen = set()
    for srv_tuple in srv_tuples:
        if srv_tuple in seen:
            duplicates.append(f"{srv_tuple[0]} (port={srv_tuple[1]}, priority={srv_tuple[2]}, target={srv_tuple[3]})")
        seen.add(srv_tuple)
    
    if duplicates:
        print(f"ERROR: Duplicate SRV records found: {', '.join(duplicates)}")
        validation_failed = True
    
    # Display validation summary
    print("\nSRV Record Validation Summary:")
    print(f"Total records checked: {len(srv_records)}")
    print(f"Records with missing required fields: {len(missing_required_fields)}")
    print(f"Records with invalid names: {len(invalid_names)}")
    print(f"Records with invalid targets: {len(invalid_targets)}")
    print(f"Records with invalid values: {len(invalid_values)}")
    print(f"Records with invalid TTL values: {len(invalid_ttls)}")
    print(f"Records with non-resolving targets: {len(missing_targets)}")
    print(f"Missing parent domains: {len(failed_domains)}")
    print(f"Existing SRV records: {len(existing_records)}")
    
    if failed_domains:
        print(f"Failed domains: {', '.join(failed_domains)}")
    
    return not validation_failed

def check_existing_vlan(name, vlan_id, parent):
    """Check if a VLAN already exists in Infoblox."""
    try:
        response = requests.get(
            f"{BASE_URL}/vlan",
            params={"name": name, "id": vlan_id, "parent": parent},
            auth=(INFOBLOX_USERNAME, INFOBLOX_PASSWORD),
            verify=VALIDATE_CERTS,
            timeout=HTTP_TIMEOUT
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"✗ Error checking VLAN {name}: {response.status_code}")
            return []
    except Exception as e:
        print(f"✗ Error checking VLAN {name}: {str(e)}")
        return []

def check_vlan_view_exists(vlan_view_name):
    """Check if a VLAN View exists in Infoblox."""
    try:
        response = requests.get(
            f"{BASE_URL}/vlanview",
            params={"name": vlan_view_name},
            auth=(INFOBLOX_USERNAME, INFOBLOX_PASSWORD),
            verify=VALIDATE_CERTS,
            timeout=HTTP_TIMEOUT
        )
        
        if response.status_code == 200:
            return len(response.json()) > 0
        else:
            print(f"✗ Error checking VLAN view {vlan_view_name}: {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Error checking VLAN view {vlan_view_name}: {str(e)}")
        return False

def validate_vlan_id(vlan_id):
    """Validate VLAN ID is within valid range."""
    try:
        id_num = int(vlan_id)
        if 1 <= id_num <= 4094:
            return True, None
        else:
            return False, f"VLAN ID {id_num} must be between 1 and 4094"
    except (ValueError, TypeError):
        return False, f"VLAN ID '{vlan_id}' must be a valid integer"

def validate_vlan_records():
    """Validate VLAN records from JSON file."""
    print("\n--- VLAN Validation ---")
    
    vlan_file = "playbooks/add/cabgridmgr.amfam.com/vlan.json"
    
    # Read VLAN data from JSON file
    try:
        with open(vlan_file, 'r') as file:
            vlan_records = json.load(file)
            
            # If the content is not a list, convert it to a list with one item
            if not isinstance(vlan_records, list):
                vlan_records = [vlan_records]
                
            print(f"Found {len(vlan_records)} VLAN records to validate.")
    except Exception as e:
        print(f"Error reading file {vlan_file}: {str(e)}")
        return False
    
    # Now continue with validation since we have records to check
    validation_failed = False
    missing_required_fields = []
    invalid_vlan_ids = []
    missing_vlan_views = []
    duplicate_vlans = []
    
    # Check for required fields and validate basic structure
    for record in vlan_records:
        # Check required fields
        if not all(key in record for key in ["name", "id", "parent"]):
            missing_fields = [field for field in ["name", "id", "parent"] if field not in record]
            missing_required_fields.append(f"{record.get('name', 'Unknown VLAN')}: missing {', '.join(missing_fields)}")
            validation_failed = True
            continue
        
        # Validate VLAN ID
        is_valid, error_msg = validate_vlan_id(record["id"])
        if not is_valid:
            invalid_vlan_ids.append(f"{record['name']}: {error_msg}")
            validation_failed = True
        
        # Validate VLAN name length
        if len(record["name"]) > 64:
            print(f"WARNING: VLAN name '{record['name']}' is longer than 64 characters")
        
        # Check for reserved VLANs
        if "reserved" in record and record["reserved"]:
            print(f"INFO: VLAN '{record['name']}' (ID: {record['id']}) is marked as reserved")
    
    # Display validation errors
    for missing in missing_required_fields:
        print(f"ERROR: Missing required fields - {missing}")
    
    for invalid in invalid_vlan_ids:
        print(f"ERROR: Invalid VLAN ID - {invalid}")
    
    # Extract VLAN view name from parent reference
    vlan_view_names = set()
    for record in vlan_records:
        if "parent" in record:
            parent = record["parent"]
            # Extract view name from parent reference
            if ":" in parent:
                parts = parent.split(":")
                if len(parts) > 1:
                    view_part = parts[1].split("/")[0]
                    vlan_view_names.add(view_part)
            else:
                # If parent is just the view name
                vlan_view_names.add(parent)
    
    # Check VLAN View existence
    for vlan_view_name in vlan_view_names:
        if not check_vlan_view_exists(vlan_view_name):
            missing_vlan_views.append(vlan_view_name)
            print(f"ERROR: VLAN View '{vlan_view_name}' does not exist")
            validation_failed = True
    
    # Check for existing VLANs in Infoblox
    for record in vlan_records:
        if not all(key in record for key in ["name", "id", "parent"]):
            continue
            
        existing_vlans = check_existing_vlan(record['name'], record['id'], record['parent'])
        if existing_vlans:
            existing_vlan = existing_vlans[0]
            print(f"VLAN '{record['name']}' (ID: {record['id']}) already exists in Infoblox")
            
            # Compare attributes
            if 'comment' in record and record['comment'] != existing_vlan.get('comment'):
                print(f"  Comment will be updated: '{existing_vlan.get('comment')}' -> '{record['comment']}'")
            if 'contact' in record and record['contact'] != existing_vlan.get('contact'):
                print(f"  Contact will be updated: '{existing_vlan.get('contact')}' -> '{record['contact']}'")
            if 'department' in record and record['department'] != existing_vlan.get('department'):
                print(f"  Department will be updated: '{existing_vlan.get('department')}' -> '{record['department']}'")
    
    # Check for duplicate VLAN IDs within the same view
    vlan_id_view_pairs = []
    for record in vlan_records:
        if all(key in record for key in ["id", "parent"]):
            vlan_id_view_pairs.append((record['id'], record['parent']))
    
    seen = set()
    for vlan_id, parent in vlan_id_view_pairs:
        if (vlan_id, parent) in seen:
            duplicate_vlans.append(f"VLAN ID {vlan_id} in parent {parent}")
        seen.add((vlan_id, parent))
    
    if duplicate_vlans:
        print(f"ERROR: Duplicate VLAN IDs found: {', '.join(duplicate_vlans)}")
        validation_failed = True
    
    # Check for commonly reserved VLAN IDs
    reserved_vlan_ids = {1: "Default VLAN", 1002: "FDDI Default", 1003: "Token Ring Default", 
                        1004: "FDDINET Default", 1005: "TRNET Default"}
    
    for record in vlan_records:
        if "id" in record:
            try:
                vlan_id = int(record["id"])
                if vlan_id in reserved_vlan_ids:
                    print(f"WARNING: VLAN ID {vlan_id} is commonly reserved for '{reserved_vlan_ids[vlan_id]}'")
            except:
                pass
    
    # Display validation summary
    print("\nVLAN Validation Summary:")
    print(f"Total records checked: {len(vlan_records)}")
    print(f"Records with missing required fields: {len(missing_required_fields)}")
    print(f"Records with invalid VLAN IDs: {len(invalid_vlan_ids)}")
    print(f"Missing VLAN views: {len(missing_vlan_views)}")
    print(f"Duplicate VLANs: {len(duplicate_vlans)}")
    
    if missing_vlan_views:
        print(f"Missing VLAN views: {', '.join(missing_vlan_views)}")
    
    return not validation_failed

def check_existing_vlan_view(name):
    """Check if a VLAN View already exists in Infoblox."""
    try:
        response = requests.get(
            f"{BASE_URL}/vlanview",
            params={"name": name},
            auth=(INFOBLOX_USERNAME, INFOBLOX_PASSWORD),
            verify=VALIDATE_CERTS,
            timeout=HTTP_TIMEOUT
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"✗ Error checking VLAN view {name}: {response.status_code}")
            return []
    except Exception as e:
        print(f"✗ Error checking VLAN view {name}: {str(e)}")
        return []

def validate_vlan_view_name(name):
    """Validate VLAN View name format."""
    if not name:
        return False, "VLAN View name cannot be empty"
    
    # Check length
    if len(name) > 256:
        return False, f"VLAN View name too long ({len(name)} characters, max 256)"
    
    # Check for valid characters (alphanumeric, underscore, hyphen, period)
    if not re.match(r'^[a-zA-Z0-9._-]+$', name):
        return False, "VLAN View name contains invalid characters (only alphanumeric, underscore, hyphen, period allowed)"
    
    # Cannot start with underscore or hyphen
    if name.startswith('_') or name.startswith('-'):
        return False, "VLAN View name cannot start with underscore or hyphen"
    
    return True, None

def check_vlans_in_view(vlan_view_name):
    """Check if there are VLANs in this VLAN View."""
    try:
        response = requests.get(
            f"{BASE_URL}/vlan",
            params={"parent": vlan_view_name, "_max_results": 1},
            auth=(INFOBLOX_USERNAME, INFOBLOX_PASSWORD),
            verify=VALIDATE_CERTS,
            timeout=HTTP_TIMEOUT
        )
        
        if response.status_code == 200:
            vlans = response.json()
            return len(vlans) > 0, len(vlans)
        else:
            print(f"✗ Error checking VLANs in view {vlan_view_name}: {response.status_code}")
            return False, 0
    except Exception as e:
        print(f"✗ Error checking VLANs in view {vlan_view_name}: {str(e)}")
        return False, 0

def validate_vlan_view_records():
    """Validate VLAN View records from JSON file."""
    print("\n--- VLAN View Validation ---")
    
    vlan_view_file = "playbooks/add/cabgridmgr.amfam.com/vlanview.json"
    
    # Read VLAN View data from JSON file
    try:
        with open(vlan_view_file, 'r') as file:
            vlan_view_records = json.load(file)
            
            # If the content is not a list, convert it to a list with one item
            if not isinstance(vlan_view_records, list):
                vlan_view_records = [vlan_view_records]
                
            print(f"Found {len(vlan_view_records)} VLAN View records to validate.")
    except Exception as e:
        print(f"Error reading file {vlan_view_file}: {str(e)}")
        return False
    
    # Now continue with validation since we have records to check
    validation_failed = False
    missing_required_fields = []
    invalid_names = []
    existing_vlan_views = []
    conflicting_views = []
    
    # Check for required fields and validate basic structure
    for record in vlan_view_records:
        # Check required fields
        if not all(key in record for key in ["name"]):
            missing_fields = [field for field in ["name"] if field not in record]
            missing_required_fields.append(f"{record.get('name', 'Unknown VLAN view')}: missing {', '.join(missing_fields)}")
            validation_failed = True
            continue
        
        # Validate VLAN View name format
        name = record["name"]
        is_valid, error_msg = validate_vlan_view_name(name)
        if not is_valid:
            invalid_names.append(f"{name}: {error_msg}")
            validation_failed = True
    
    # Display validation errors
    for missing in missing_required_fields:
        print(f"ERROR: Missing required fields - {missing}")
    
    for invalid in invalid_names:
        print(f"ERROR: Invalid VLAN View name - {invalid}")
    
    # Check for existing VLAN Views in Infoblox
    for record in vlan_view_records:
        if "name" not in record:
            continue
            
        existing_views = check_existing_vlan_view(record['name'])
        if existing_views:
            existing_view = existing_views[0]
            existing_vlan_views.append(record['name'])
            print(f"VLAN View '{record['name']}' already exists in Infoblox")
            
            # Check if there are VLANs in this view
            has_vlans, vlan_count = check_vlans_in_view(record['name'])
            if has_vlans:
                print(f"  VLAN View '{record['name']}' has {vlan_count}+ associated VLANs")
            
            # Compare attributes
            if 'comment' in record and record['comment'] != existing_view.get('comment'):
                print(f"  Comment will be updated: '{existing_view.get('comment')}' -> '{record['comment']}'")
            
            # Compare extensible attributes if specified
            if 'extattrs' in record and record['extattrs']:
                existing_extattrs = existing_view.get('extattrs', {})
                for key, value in record['extattrs'].items():
                    # Handle both formats: direct value or {'value': ...}
                    if isinstance(value, dict) and 'value' in value:
                        expected_value = value['value']
                    else:
                        expected_value = value
                    
                    actual_value = existing_extattrs.get(key, {}).get('value') if isinstance(existing_extattrs.get(key), dict) else existing_extattrs.get(key)
                    
                    if actual_value != expected_value:
                        print(f"  Extensible attribute '{key}' will be updated: '{actual_value}' -> '{expected_value}'")
    
    # Check for duplicate VLAN View names within the JSON
    view_names = [record.get('name') for record in vlan_view_records if 'name' in record]
    duplicates = []
    seen = set()
    for name in view_names:
        if name in seen:
            duplicates.append(name)
        seen.add(name)
    
    if duplicates:
        print(f"ERROR: Duplicate VLAN View names found in JSON: {', '.join(duplicates)}")
        validation_failed = True
        conflicting_views.extend(duplicates)
    
    # Validate logical consistency
    for record in vlan_view_records:
        name = record.get('name', 'Unknown')
        
        # Check if comment is provided for documentation
        if 'comment' not in record or not record.get('comment'):
            print(f"INFO: VLAN View '{name}' has no comment - consider adding documentation")
        
        # Check for start and end VLAN IDs if specified
        if 'start_vlan_id' in record and 'end_vlan_id' in record:
            try:
                start_id = int(record['start_vlan_id'])
                end_id = int(record['end_vlan_id'])
                
                if start_id < 1 or start_id > 4094:
                    print(f"ERROR: VLAN View '{name}' has invalid start_vlan_id: {start_id} (must be 1-4094)")
                    validation_failed = True
                
                if end_id < 1 or end_id > 4094:
                    print(f"ERROR: VLAN View '{name}' has invalid end_vlan_id: {end_id} (must be 1-4094)")
                    validation_failed = True
                
                if start_id > end_id:
                    print(f"ERROR: VLAN View '{name}' has start_vlan_id ({start_id}) greater than end_vlan_id ({end_id})")
                    validation_failed = True
                
            except (ValueError, TypeError):
                print(f"ERROR: VLAN View '{name}' has non-numeric VLAN ID values")
                validation_failed = True
        
        # Check extensible attributes for common patterns
        if 'extattrs' in record and record['extattrs']:
            extattrs = record['extattrs']
            
            # Look for common organizational attributes
            org_attrs = ['Department', 'Owner', 'Environment', 'Location', 'Region']
            has_org_attr = any(attr in extattrs for attr in org_attrs)
            if not has_org_attr:
                print(f"INFO: VLAN View '{name}' has no organizational extensible attributes")
            
            # Validate extensible attribute values
            for attr_name, attr_value in extattrs.items():
                # Handle both formats
                if isinstance(attr_value, dict) and 'value' in attr_value:
                    actual_value = attr_value['value']
                else:
                    actual_value = attr_value
                
                if not actual_value or (isinstance(actual_value, str) and not actual_value.strip()):
                    print(f"WARNING: VLAN View '{name}' has empty extensible attribute '{attr_name}'")
        
        # Check for naming convention consistency
        if len(name) < 3:
            print(f"WARNING: VLAN View '{name}' has a very short name - consider a more descriptive name")
    
    # Display validation summary
    print("\nVLAN View Validation Summary:")
    print(f"Total records checked: {len(vlan_view_records)}")
    print(f"Records with missing required fields: {len(missing_required_fields)}")
    print(f"Records with invalid names: {len(invalid_names)}")
    print(f"Existing VLAN views: {len(existing_vlan_views)}")
    print(f"Conflicting views: {len(conflicting_views)}")
    
    if existing_vlan_views:
        print(f"Existing VLAN views: {', '.join(existing_vlan_views)}")
    if conflicting_views:
        print(f"Conflicting views: {', '.join(conflicting_views)}")
    
    return not validation_failed

def check_existing_upgrade_group(name):
    """Check if an Upgrade Group already exists in Infoblox."""
    try:
        response = requests.get(
            f"{BASE_URL}/upgradegroup",
            params={"name": name},
            auth=(INFOBLOX_USERNAME, INFOBLOX_PASSWORD),
            verify=VALIDATE_CERTS,
            timeout=HTTP_TIMEOUT
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"✗ Error checking upgrade group {name}: {response.status_code}")
            return []
    except Exception as e:
        print(f"✗ Error checking upgrade group {name}: {str(e)}")
        return []

def validate_upgrade_group_name(name):
    """Validate Upgrade Group name format."""
    if not name:
        return False, "Upgrade Group name cannot be empty"
    
    # Check length
    if len(name) > 256:
        return False, f"Upgrade Group name too long ({len(name)} characters, max 256)"
    
    # Check for valid characters
    if not re.match(r'^[a-zA-Z0-9\s._-]+$', name):
        return False, "Upgrade Group name contains invalid characters"
    
    # Check for system reserved groups
    reserved_groups = ['Grid Master', 'Default']
    if name in reserved_groups:
        return False, f"Upgrade Group name '{name}' is reserved and cannot be modified"
    
    return True, None

def check_grid_members_for_group(members):
    """Check if Grid Members exist for upgrade group."""
    missing_members = []
    for member in members:
        try:
            response = requests.get(
                f"{BASE_URL}/member",
                params={"host_name": member},
                auth=(INFOBLOX_USERNAME, INFOBLOX_PASSWORD),
                verify=VALIDATE_CERTS,
                timeout=HTTP_TIMEOUT
            )
            
            if response.status_code != 200 or not response.json():
                missing_members.append(member)
        except Exception as e:
            print(f"✗ Error checking member {member}: {str(e)}")
            missing_members.append(member)
    
    return missing_members

def validate_upgrade_group_records():
    """Validate Upgrade Group records from JSON file."""
    print("\n--- Upgrade Group Validation ---")
    
    upgrade_group_file = "playbooks/add/cabgridmgr.amfam.com/upgradegroup.json"
    
    # Read Upgrade Group data from JSON file
    try:
        with open(upgrade_group_file, 'r') as file:
            upgrade_group_records = json.load(file)
            
            # If the content is not a list, convert it to a list with one item
            if not isinstance(upgrade_group_records, list):
                upgrade_group_records = [upgrade_group_records]
                
            print(f"Found {len(upgrade_group_records)} Upgrade Group records to validate.")
    except Exception as e:
        print(f"Error reading file {upgrade_group_file}: {str(e)}")
        return False
    
    # Now continue with validation since we have records to check
    validation_failed = False
    missing_required_fields = []
    invalid_names = []
    reserved_groups = []
    missing_members = []
    duplicate_groups = []
    duplicate_members = []
    
    # Non-editable groups from playbook
    non_editable_groups = ["Grid Master"]
    
    # Check for required fields and validate basic structure
    for record in upgrade_group_records:
        # Check required fields
        if not all(key in record for key in ["name"]):
            missing_fields = [field for field in ["name"] if field not in record]
            missing_required_fields.append(f"{record.get('name', 'Unknown upgrade group')}: missing {', '.join(missing_fields)}")
            validation_failed = True
            continue
        
        # Check if trying to modify non-editable group
        if record["name"] in non_editable_groups:
            reserved_groups.append(record["name"])
            print(f"ERROR: Cannot modify system upgrade group '{record['name']}'")
            validation_failed = True
            continue
        
        # Validate Upgrade Group name format
        name = record["name"]
        is_valid, error_msg = validate_upgrade_group_name(name)
        if not is_valid:
            invalid_names.append(f"{name}: {error_msg}")
            validation_failed = True
        
        # Validate members if specified
        if "members" in record and record["members"]:
            if not isinstance(record["members"], list):
                print(f"ERROR: Upgrade Group '{name}' members must be a list")
                validation_failed = True
            else:
                # Check if members exist
                missing = check_grid_members_for_group(record["members"])
                if missing:
                    for member in missing:
                        missing_members.append(f"{name}: Member '{member}'")
                    validation_failed = True
        
        # Validate upgrade_dependent_group if specified
        if "upgrade_dependent_group" in record and record["upgrade_dependent_group"]:
            dependent_group = record["upgrade_dependent_group"]
            # Check if dependent group exists or will be created
            dependent_exists = False
            
            # Check in Infoblox
            existing_dependent = check_existing_upgrade_group(dependent_group)
            if existing_dependent:
                dependent_exists = True
            
            # Check if it's being created in the same batch
            for other_record in upgrade_group_records:
                if other_record.get("name") == dependent_group:
                    dependent_exists = True
                    break
            
            if not dependent_exists:
                print(f"WARNING: Upgrade Group '{name}' depends on '{dependent_group}' which doesn't exist")
    
    # Display validation errors
    for missing in missing_required_fields:
        print(f"ERROR: Missing required fields - {missing}")
    
    for invalid in invalid_names:
        print(f"ERROR: Invalid upgrade group name - {invalid}")
    
    for reserved in reserved_groups:
        print(f"ERROR: Attempting to modify reserved group - {reserved}")
    
    for missing in missing_members:
        print(f"ERROR: Missing grid member - {missing}")
    
    # Check for existing upgrade groups in Infoblox
    for record in upgrade_group_records:
        if "name" not in record or record["name"] in non_editable_groups:
            continue
            
        existing_groups = check_existing_upgrade_group(record['name'])
        if existing_groups:
            existing_group = existing_groups[0]
            print(f"Upgrade Group '{record['name']}' already exists in Infoblox")
            
            # Compare attributes
            if 'comment' in record and record['comment'] != existing_group.get('comment'):
                print(f"  Comment will be updated: '{existing_group.get('comment')}' -> '{record['comment']}'")
            
            if 'members' in record:
                existing_members = set(existing_group.get('members', []))
                new_members = set(record.get('members', []))
                
                added = new_members - existing_members
                removed = existing_members - new_members
                
                if added:
                    print(f"  Members to be added: {', '.join(added)}")
                if removed:
                    print(f"  Members to be removed: {', '.join(removed)}")
            
            if 'upgrade_dependent_group' in record:
                existing_dep = existing_group.get('upgrade_dependent_group')
                new_dep = record.get('upgrade_dependent_group')
                if existing_dep != new_dep:
                    print(f"  Dependent group will be updated: '{existing_dep}' -> '{new_dep}'")
    
    # Check for duplicate upgrade group names within the JSON
    group_names = [record.get('name') for record in upgrade_group_records if 'name' in record]
    seen = set()
    for name in group_names:
        if name in seen:
            duplicate_groups.append(name)
        seen.add(name)
    
    if duplicate_groups:
        print(f"ERROR: Duplicate upgrade group names found in JSON: {', '.join(duplicate_groups)}")
        validation_failed = True
    
    # Check for members in multiple groups
    member_to_groups = {}
    for record in upgrade_group_records:
        if "members" in record and record["members"]:
            for member in record["members"]:
                if member not in member_to_groups:
                    member_to_groups[member] = []
                member_to_groups[member].append(record["name"])
    
    for member, groups in member_to_groups.items():
        if len(groups) > 1:
            duplicate_members.append(f"Member '{member}' in multiple groups: {', '.join(groups)}")
            print(f"WARNING: Member '{member}' appears in multiple upgrade groups: {', '.join(groups)}")
    
    # Check for circular dependencies
    dependencies = {}
    for record in upgrade_group_records:
        if "upgrade_dependent_group" in record and record["upgrade_dependent_group"]:
            dependencies[record["name"]] = record["upgrade_dependent_group"]
    
    def check_circular_dependency(group, visited, path):
        if group in visited:
            return True, path + [group]
        if group not in dependencies:
            return False, []
        
        visited.add(group)
        path.append(group)
        
        return check_circular_dependency(dependencies[group], visited, path)
    
    for group in dependencies:
        visited = set()
        is_circular, path = check_circular_dependency(group, visited, [])
        if is_circular:
            print(f"ERROR: Circular dependency detected: {' -> '.join(path)}")
            validation_failed = True
    
    # Validate logical consistency
    for record in upgrade_group_records:
        name = record.get('name', 'Unknown')
        
        # Check if comment is provided for documentation
        if 'comment' not in record or not record.get('comment'):
            print(f"INFO: Upgrade Group '{name}' has no comment - consider adding documentation")
        
        # Check for empty groups
        if 'members' not in record or not record.get('members'):
            print(f"WARNING: Upgrade Group '{name}' has no members defined")
        
        # Check for reasonable group size
        if 'members' in record and isinstance(record['members'], list):
            member_count = len(record['members'])
            if member_count > 50:
                print(f"INFO: Upgrade Group '{name}' has {member_count} members - consider splitting into smaller groups")
    
    # Display validation summary
    print("\nUpgrade Group Validation Summary:")
    print(f"Total records checked: {len(upgrade_group_records)}")
    print(f"Records with missing required fields: {len(missing_required_fields)}")
    print(f"Records with invalid names: {len(invalid_names)}")
    print(f"Reserved groups attempted: {len(reserved_groups)}")
    print(f"Missing grid members: {len(set(missing_members))}")
    print(f"Duplicate group names: {len(duplicate_groups)}")
    print(f"Members in multiple groups: {len(duplicate_members)}")
    
    return not validation_failed

def check_existing_ns_group(name):
    """Check if an NS Group already exists in Infoblox."""
    try:
        response = requests.get(
            f"{BASE_URL}/nsgroup",
            params={"name": name},
            auth=(INFOBLOX_USERNAME, INFOBLOX_PASSWORD),
            verify=VALIDATE_CERTS,
            timeout=HTTP_TIMEOUT
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"✗ Error checking NS group {name}: {response.status_code}")
            return []
    except Exception as e:
        print(f"✗ Error checking NS group {name}: {str(e)}")
        return []

def validate_ns_group_name(name):
    """Validate NS Group name format."""
    if not name:
        return False, "NS Group name cannot be empty"
    
    # Check length
    if len(name) > 256:
        return False, f"NS Group name too long ({len(name)} characters, max 256)"
    
    # Check for valid characters
    if not re.match(r'^[a-zA-Z0-9._-]+$', name):
        return False, "NS Group name contains invalid characters (only alphanumeric, underscore, hyphen, period allowed)"
    
    # Cannot start with underscore or hyphen
    if name.startswith('_') or name.startswith('-'):
        return False, "NS Group name cannot start with underscore or hyphen"
    
    return True, None

def validate_external_server(server):
    """Validate external server configuration."""
    errors = []
    
    # Check required fields
    if "address" not in server:
        errors.append("Missing required field 'address'")
        return errors
    
    # Validate IP address
    try:
        ip_address(server["address"])
    except ValueError:
        errors.append(f"Invalid IP address: {server['address']}")
    
    # Validate TSIGs if present
    if "tsig_key" in server and server["tsig_key"]:
        tsig = server["tsig_key"]
        if not isinstance(tsig, str):
            errors.append("TSIG key must be a string")
    
    # Validate port if present
    if "port" in server:
        try:
            port = int(server["port"])
            if not (1 <= port <= 65535):
                errors.append(f"Port {port} must be between 1 and 65535")
        except (ValueError, TypeError):
            errors.append(f"Invalid port: {server['port']}")
    
    return errors

def validate_ns_group_records():
    """Validate NS Group records from JSON file."""
    print("\n--- NS Group Validation ---")
    
    ns_group_file = "playbooks/add/cabgridmgr.amfam.com/nsgroup.json"
    
    # Read NS Group data from JSON file
    try:
        with open(ns_group_file, 'r') as file:
            ns_group_records = json.load(file)
            
            # If the content is not a list, convert it to a list with one item
            if not isinstance(ns_group_records, list):
                ns_group_records = [ns_group_records]
                
            print(f"Found {len(ns_group_records)} NS Group records to validate.")
    except Exception as e:
        print(f"Error reading file {ns_group_file}: {str(e)}")
        return False
    
    # Now continue with validation since we have records to check
    validation_failed = False
    missing_required_fields = []
    invalid_names = []
    invalid_external_servers = []
    missing_grid_members = []
    conflicting_primary_config = []
    duplicate_groups = []
    
    # Check for required fields and validate basic structure
    for record in ns_group_records:
        # Check required fields
        if not all(key in record for key in ["name"]):
            missing_fields = [field for field in ["name"] if field not in record]
            missing_required_fields.append(f"{record.get('name', 'Unknown NS group')}: missing {', '.join(missing_fields)}")
            validation_failed = True
            continue
        
        # Validate NS Group name format
        name = record["name"]
        is_valid, error_msg = validate_ns_group_name(name)
        if not is_valid:
            invalid_names.append(f"{name}: {error_msg}")
            validation_failed = True
        
        # Validate external primaries
        if "external_primaries" in record and record["external_primaries"]:
            if not isinstance(record["external_primaries"], list):
                print(f"ERROR: NS Group '{name}' external_primaries must be a list")
                validation_failed = True
            else:
                for idx, server in enumerate(record["external_primaries"]):
                    errors = validate_external_server(server)
                    if errors:
                        for error in errors:
                            invalid_external_servers.append(f"{name} external_primary[{idx}]: {error}")
                        validation_failed = True
        
        # Validate external secondaries
        if "external_secondaries" in record and record["external_secondaries"]:
            if not isinstance(record["external_secondaries"], list):
                print(f"ERROR: NS Group '{name}' external_secondaries must be a list")
                validation_failed = True
            else:
                for idx, server in enumerate(record["external_secondaries"]):
                    errors = validate_external_server(server)
                    if errors:
                        for error in errors:
                            invalid_external_servers.append(f"{name} external_secondary[{idx}]: {error}")
                        validation_failed = True
        
        # Validate grid primary
        if "grid_primary" in record and record["grid_primary"]:
            if not isinstance(record["grid_primary"], list):
                print(f"ERROR: NS Group '{name}' grid_primary must be a list")
                validation_failed = True
            else:
                for primary in record["grid_primary"]:
                    if "name" in primary:
                        if not check_grid_member_exists(primary["name"]):
                            missing_grid_members.append(f"{name}: Grid Primary '{primary['name']}'")
                            validation_failed = True
        
        # Validate grid secondaries
        if "grid_secondaries" in record and record["grid_secondaries"]:
            if not isinstance(record["grid_secondaries"], list):
                print(f"ERROR: NS Group '{name}' grid_secondaries must be a list")
                validation_failed = True
            else:
                for secondary in record["grid_secondaries"]:
                    if "name" in secondary:
                        if not check_grid_member_exists(secondary["name"]):
                            missing_grid_members.append(f"{name}: Grid Secondary '{secondary['name']}'")
                            validation_failed = True
        
        # Check for conflicting primary configurations
        has_external_primary = record.get("external_primaries") and len(record.get("external_primaries", [])) > 0
        has_grid_primary = record.get("grid_primary") and len(record.get("grid_primary", [])) > 0
        use_external_primary = record.get("use_external_primary", False)
        
        if use_external_primary and not has_external_primary:
            conflicting_primary_config.append(f"{name}: use_external_primary is True but no external primaries defined")
            validation_failed = True
        
        if not use_external_primary and not has_grid_primary and not record.get("is_grid_default", False):
            conflicting_primary_config.append(f"{name}: No grid primary defined and use_external_primary is False")
            print(f"WARNING: NS Group '{name}' has no primary servers defined")
    
    # Display validation errors
    for missing in missing_required_fields:
        print(f"ERROR: Missing required fields - {missing}")
    
    for invalid in invalid_names:
        print(f"ERROR: Invalid NS group name - {invalid}")
    
    for invalid in invalid_external_servers:
        print(f"ERROR: Invalid external server - {invalid}")
    
    for missing in missing_grid_members:
        print(f"ERROR: Missing grid member - {missing}")
    
    for conflict in conflicting_primary_config:
        print(f"ERROR: Primary configuration conflict - {conflict}")
    
    # Check for existing NS groups in Infoblox
    for record in ns_group_records:
        if "name" not in record:
            continue
            
        existing_groups = check_existing_ns_group(record['name'])
        if existing_groups:
            existing_group = existing_groups[0]
            print(f"NS Group '{record['name']}' already exists in Infoblox")
            
            # Check if it's a grid default
            if existing_group.get("is_grid_default", False):
                print(f"  WARNING: '{record['name']}' is a grid default NS Group")
            
            # Compare attributes
            if 'comment' in record and record['comment'] != existing_group.get('comment'):
                print(f"  Comment will be updated: '{existing_group.get('comment')}' -> '{record['comment']}'")
            
            # Compare external primaries
            if 'external_primaries' in record:
                existing_ext_prim = existing_group.get('external_primaries', [])
                new_ext_prim = record.get('external_primaries', [])
                
                if len(existing_ext_prim) != len(new_ext_prim):
                    print(f"  External primaries count will change: {len(existing_ext_prim)} -> {len(new_ext_prim)}")
                else:
                    # Compare addresses
                    existing_addrs = [p.get('address') for p in existing_ext_prim]
                    new_addrs = [p.get('address') for p in new_ext_prim]
                    if existing_addrs != new_addrs:
                        print(f"  External primary addresses will be updated")
            
            # Compare grid members
            if 'grid_primary' in record:
                existing_grid_prim = [m.get('name') for m in existing_group.get('grid_primary', [])]
                new_grid_prim = [m.get('name') for m in record.get('grid_primary', [])]
                
                added = set(new_grid_prim) - set(existing_grid_prim)
                removed = set(existing_grid_prim) - set(new_grid_prim)
                
                if added:
                    print(f"  Grid primaries to be added: {', '.join(added)}")
                if removed:
                    print(f"  Grid primaries to be removed: {', '.join(removed)}")
            
            # Compare use_external_primary
            if 'use_external_primary' in record:
                if record['use_external_primary'] != existing_group.get('use_external_primary', False):
                    print(f"  use_external_primary will be updated: {existing_group.get('use_external_primary', False)} -> {record['use_external_primary']}")
    
    # Check for duplicate NS group names within the JSON
    group_names = [record.get('name') for record in ns_group_records if 'name' in record]
    seen = set()
    for name in group_names:
        if name in seen:
            duplicate_groups.append(name)
        seen.add(name)
    
    if duplicate_groups:
        print(f"ERROR: Duplicate NS group names found in JSON: {', '.join(duplicate_groups)}")
        validation_failed = True
    
    # Check for NS Groups referenced in zones
    for record in ns_group_records:
        name = record.get('name', 'Unknown')
        
        # Check if this NS Group is used by any zones
        try:
            response = requests.get(
                f"{BASE_URL}/zone_auth",
                params={"ns_group": name, "_max_results": 1},
                auth=(INFOBLOX_USERNAME, INFOBLOX_PASSWORD),
                verify=VALIDATE_CERTS,
                timeout=HTTP_TIMEOUT
            )
            
            if response.status_code == 200 and response.json():
                print(f"INFO: NS Group '{name}' is used by one or more DNS zones")
        except:
            pass  # Not critical for validation
    
    # Validate logical consistency
    for record in ns_group_records:
        name = record.get('name', 'Unknown')
        
        # Check if comment is provided for documentation
        if 'comment' not in record or not record.get('comment'):
            print(f"INFO: NS Group '{name}' has no comment - consider adding documentation")
        
        # Check for reasonable server counts
        total_servers = 0
        if 'external_primaries' in record:
            total_servers += len(record.get('external_primaries', []))
        if 'external_secondaries' in record:
            total_servers += len(record.get('external_secondaries', []))
        if 'grid_primary' in record:
            total_servers += len(record.get('grid_primary', []))
        if 'grid_secondaries' in record:
            total_servers += len(record.get('grid_secondaries', []))
        
        if total_servers == 0 and not record.get('is_grid_default', False):
            print(f"WARNING: NS Group '{name}' has no servers defined")
        elif total_servers > 20:
            print(f"INFO: NS Group '{name}' has {total_servers} servers - consider if all are necessary")
    
    # Display validation summary
    print("\nNS Group Validation Summary:")
    print(f"Total records checked: {len(ns_group_records)}")
    print(f"Records with missing required fields: {len(missing_required_fields)}")
    print(f"Records with invalid names: {len(invalid_names)}")
    print(f"Invalid external server configurations: {len(invalid_external_servers)}")
    print(f"Missing grid members: {len(set(missing_grid_members))}")
    print(f"Primary configuration conflicts: {len(conflicting_primary_config)}")
    print(f"Duplicate group names: {len(duplicate_groups)}")
    
    return not validation_failed

def check_dns_view_exists(view_name):
    """Check if a DNS view exists in Infoblox."""
    try:
        response = requests.get(
            f"{BASE_URL}/view",
            params={"name": view_name},
            auth=(INFOBLOX_USERNAME, INFOBLOX_PASSWORD),
            verify=VALIDATE_CERTS,
            timeout=HTTP_TIMEOUT
        )
        
        if response.status_code == 200:
            return len(response.json()) > 0
        else:
            print(f"✗ Error checking DNS view {view_name}: {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Error checking DNS view {view_name}: {str(e)}")
        return False

def check_rpz_zone_exists(zone_ref):
    """Check if an RPZ zone exists by reference."""
    try:
        # Extract the reference and query directly
        response = requests.get(
            f"{BASE_URL}/{zone_ref}",
            auth=(INFOBLOX_USERNAME, INFOBLOX_PASSWORD),
            verify=VALIDATE_CERTS,
            timeout=HTTP_TIMEOUT
        )
        
        if response.status_code == 200:
            return True, response.json()
        else:
            return False, None
    except Exception as e:
        print(f"✗ Error checking RPZ zone {zone_ref}: {str(e)}")
        return False, None

def get_current_ordered_rpz(view_name):
    """Get current ordered response policy zones for a view."""
    try:
        response = requests.get(
            f"{BASE_URL}/orderedresponsepolicyzones",
            params={"view": view_name, "_return_fields": "rp_zones"},
            auth=(INFOBLOX_USERNAME, INFOBLOX_PASSWORD),
            verify=VALIDATE_CERTS,
            timeout=HTTP_TIMEOUT
        )
        
        if response.status_code == 200:
            results = response.json()
            if results:
                return results[0].get('rp_zones', [])
        return []
    except Exception as e:
        print(f"✗ Error getting ordered RPZ for view {view_name}: {str(e)}")
        return []

def validate_ordered_rpz_records():
    """Validate Ordered Response Policy Zones records from JSON file."""
    print("\n--- Ordered Response Policy Zones Validation ---")
    
    ordered_rpz_file = "playbooks/add/cabgridmgr.amfam.com/ordered_response_policy_zones.json"
    
    # Read Ordered RPZ data from JSON file
    try:
        with open(ordered_rpz_file, 'r') as file:
            ordered_rpz_records = json.load(file)
            
            # If the content is not a list, convert it to a list with one item
            if not isinstance(ordered_rpz_records, list):
                ordered_rpz_records = [ordered_rpz_records]
                
            print(f"Found {len(ordered_rpz_records)} Ordered Response Policy Zones records to validate.")
    except Exception as e:
        print(f"Error reading file {ordered_rpz_file}: {str(e)}")
        return False
    
    # Now continue with validation since we have records to check
    validation_failed = False
    missing_required_fields = []
    missing_views = []
    invalid_rpz_zones = []
    duplicate_views = []
    rpz_priority_conflicts = []
    
    # Check if RPZ license is available
    rpz_licensed = check_rpz_license()
    if not rpz_licensed:
        print("ERROR: RPZ license is not installed on Grid Members")
        print("Ordered Response Policy Zones functionality requires a valid RPZ license")
        return False
    else:
        print("✓ RPZ license is installed and available")
    
    # Check for required fields and validate basic structure
    for record in ordered_rpz_records:
        # Check required fields
        if not all(key in record for key in ["view", "rp_zones"]):
            missing_fields = [field for field in ["view", "rp_zones"] if field not in record]
            missing_required_fields.append(f"{record.get('view', 'Unknown view')}: missing {', '.join(missing_fields)}")
            validation_failed = True
            continue
        
        # Validate view exists
        view_name = record["view"]
        if not check_dns_view_exists(view_name):
            missing_views.append(view_name)
            print(f"ERROR: DNS View '{view_name}' does not exist")
            validation_failed = True
            continue
        
        # Validate rp_zones is a list
        if not isinstance(record["rp_zones"], list):
            print(f"ERROR: View '{view_name}' rp_zones must be a list")
            validation_failed = True
            continue
        
        # Get current ordered RPZ for comparison
        current_rpz_zones = get_current_ordered_rpz(view_name)
        
        # Validate each RPZ zone in the list
        zone_priorities = {}
        for idx, zone_ref in enumerate(record["rp_zones"]):
            if not isinstance(zone_ref, str):
                invalid_rpz_zones.append(f"{view_name}: Zone at index {idx} must be a string reference")
                validation_failed = True
                continue
            
            # Check if the RPZ zone exists
            exists, zone_data = check_rpz_zone_exists(zone_ref)
            if not exists:
                invalid_rpz_zones.append(f"{view_name}: RPZ zone '{zone_ref}' does not exist")
                validation_failed = True
            else:
                # Get zone details
                zone_name = zone_data.get('fqdn', 'Unknown')
                rpz_priority = zone_data.get('rpz_priority', 0)
                rpz_severity = zone_data.get('rpz_severity', 'INFORMATIONAL')
                rpz_type = zone_data.get('rpz_type', 'LOCAL')
                
                print(f"  Found RPZ zone '{zone_name}' (Priority: {rpz_priority}, Severity: {rpz_severity}, Type: {rpz_type})")
                
                # Check for priority conflicts within the same view
                if rpz_priority in zone_priorities:
                    rpz_priority_conflicts.append(
                        f"{view_name}: Priority {rpz_priority} conflict between '{zone_name}' and '{zone_priorities[rpz_priority]}'"
                    )
                    print(f"WARNING: Priority conflict in view '{view_name}': zones '{zone_name}' and '{zone_priorities[rpz_priority]}' both have priority {rpz_priority}")
                else:
                    zone_priorities[rpz_priority] = zone_name
        
        # Compare with current configuration
        if current_rpz_zones:
            current_count = len(current_rpz_zones)
            new_count = len(record["rp_zones"])
            
            if current_count != new_count:
                print(f"View '{view_name}' RPZ zone count will change: {current_count} -> {new_count}")
            
            # Check order changes
            order_changed = False
            for idx, zone_ref in enumerate(record["rp_zones"]):
                if idx < len(current_rpz_zones) and zone_ref != current_rpz_zones[idx]:
                    order_changed = True
                    break
            
            if order_changed:
                print(f"View '{view_name}' RPZ zone order will be updated")
        else:
            print(f"View '{view_name}' currently has no ordered RPZ zones configured")
    
    # Display validation errors
    for missing in missing_required_fields:
        print(f"ERROR: Missing required fields - {missing}")
    
    for missing_view in missing_views:
        print(f"ERROR: Missing DNS view - {missing_view}")
    
    for invalid in invalid_rpz_zones:
        print(f"ERROR: Invalid RPZ zone - {invalid}")
    
    for conflict in rpz_priority_conflicts:
        print(f"WARNING: RPZ priority conflict - {conflict}")
    
    # Check for duplicate views within the JSON
    view_names = [record.get('view') for record in ordered_rpz_records if 'view' in record]
    seen = set()
    for view in view_names:
        if view in seen:
            duplicate_views.append(view)
        seen.add(view)
    
    if duplicate_views:
        print(f"ERROR: Duplicate views found in JSON: {', '.join(duplicate_views)}")
        validation_failed = True
    
    # Validate logical consistency
    for record in ordered_rpz_records:
        view_name = record.get('view', 'Unknown')
        rp_zones = record.get('rp_zones', [])
        
        # Check for empty RPZ zones list
        if not rp_zones:
            print(f"WARNING: View '{view_name}' has empty RPZ zones list - this will disable RPZ for the view")
        
        # Check for reasonable number of RPZ zones
        if len(rp_zones) > 50:
            print(f"WARNING: View '{view_name}' has {len(rp_zones)} RPZ zones - consider performance impact")
        
        # Validate RPZ zone ordering recommendations
        priority_order_issues = []
        last_priority = -1
        
        for zone_ref in rp_zones:
            exists, zone_data = check_rpz_zone_exists(zone_ref)
            if exists:
                current_priority = zone_data.get('rpz_priority', 0)
                if current_priority < last_priority:
                    priority_order_issues.append(f"Priority {current_priority} comes after {last_priority}")
                last_priority = current_priority
        
        if priority_order_issues:
            print(f"INFO: View '{view_name}' RPZ zones are not in priority order: {', '.join(priority_order_issues)}")
            print(f"      Consider ordering by priority for clarity (lower priority = higher precedence)")
    
    # Check for RPZ zone usage across multiple views
    zone_view_usage = {}
    for record in ordered_rpz_records:
        view_name = record.get('view')
        for zone_ref in record.get('rp_zones', []):
            if zone_ref not in zone_view_usage:
                zone_view_usage[zone_ref] = []
            zone_view_usage[zone_ref].append(view_name)
    
    for zone_ref, views in zone_view_usage.items():
        if len(views) > 1:
            exists, zone_data = check_rpz_zone_exists(zone_ref)
            zone_name = zone_data.get('fqdn', zone_ref) if exists else zone_ref
            print(f"INFO: RPZ zone '{zone_name}' is used in multiple views: {', '.join(views)}")
    
    # Display validation summary
    print("\nOrdered Response Policy Zones Validation Summary:")
    print(f"Total records checked: {len(ordered_rpz_records)}")
    print(f"Records with missing required fields: {len(missing_required_fields)}")
    print(f"Missing DNS views: {len(missing_views)}")
    print(f"Invalid RPZ zone references: {len(invalid_rpz_zones)}")
    print(f"RPZ priority conflicts: {len(rpz_priority_conflicts)}")
    print(f"Duplicate view configurations: {len(duplicate_views)}")
    
    return not validation_failed and rpz_licensed

def main():
    """Main function."""
    print("Starting pre-check validation...")
    
    # Check if we can connect to Infoblox
    if not authenticate():
        print("✗ Pre-check failed: Cannot connect to Infoblox")
        sys.exit(1)
    
    # Check for A record file and its content before validation
    a_record_file = "../prod_changes/cabgridmgr.amfam.com/a_record.json"
    should_validate_a_records = False
    
    if os.path.exists(a_record_file):
        try:
            with open(a_record_file, 'r') as file:
                a_records = json.load(file)
                # Only validate if there are records (not empty list/object)
                if a_records and not (isinstance(a_records, list) and len(a_records) == 0):
                    should_validate_a_records = True
                else:
                    print("\n--- A Record Validation ---")
                    print(f"A record file exists but contains no records. Skipping validation.")
        except Exception as e:
            print(f"\n--- A Record Validation ---")
            print(f"Error reading A record file: {str(e)}")
            print("Cannot validate A records due to file error.")
    else:
        print("\n--- A Record Validation ---")
        print(f"A record file not found: {a_record_file}")
        print("Skipping A record validation.")
    
    # Only call the validation function if we have records to validate
    if should_validate_a_records:
        a_records_valid = validate_a_records()
        if not a_records_valid:
            print("\n✗ Pre-check failed: A Record validation failed")
            sys.exit(1)
    
    # Check for AAAA record file and its content before validation
    aaaa_record_file = "../prod_changes/cabgridmgr.amfam.com/aaaa_record.json"
    should_validate_aaaa_records = False
    
    if os.path.exists(aaaa_record_file):
        try:
            with open(aaaa_record_file, 'r') as file:
                aaaa_records = json.load(file)
                # Only validate if there are records (not empty list/object)
                if aaaa_records and not (isinstance(aaaa_records, list) and len(aaaa_records) == 0):
                    should_validate_aaaa_records = True
                else:
                    print("\n--- AAAA Record Validation ---")
                    print(f"AAAA record file exists but contains no records. Skipping validation.")
        except Exception as e:
            print(f"\n--- AAAA Record Validation ---")
            print(f"Error reading AAAA record file: {str(e)}")
            print("Cannot validate AAAA records due to file error.")
    else:
        print("\n--- AAAA Record Validation ---")
        print(f"AAAA record file not found: {aaaa_record_file}")
        print("Skipping AAAA record validation.")
    
    # Only call the validation function if we have records to validate
    if should_validate_aaaa_records:
        aaaa_records_valid = validate_aaaa_records()
        if not aaaa_records_valid:
            print("\n✗ Pre-check failed: AAAA Record validation failed")
            sys.exit(1)
    
    # Check for Alias record file and its content before validation
    alias_record_file = "playbooks/add/cabgridmgr.amfam.com/alias_record.json"
    should_validate_alias_records = False
    
    if os.path.exists(alias_record_file):
        try:
            with open(alias_record_file, 'r') as file:
                alias_records = json.load(file)
                # Only validate if there are records (not empty list/object)
                if alias_records and not (isinstance(alias_records, list) and len(alias_records) == 0):
                    should_validate_alias_records = True
                else:
                    print("\n--- Alias Record Validation ---")
                    print(f"Alias record file exists but contains no records. Skipping validation.")
        except Exception as e:
            print(f"\n--- Alias Record Validation ---")
            print(f"Error reading Alias record file: {str(e)}")
            print("Cannot validate Alias records due to file error.")
    else:
        print("\n--- Alias Record Validation ---")
        print(f"Alias record file not found: {alias_record_file}")
        print("Skipping Alias record validation.")
    
    # Only call the validation function if we have records to validate
    if should_validate_alias_records:
        alias_records_valid = validate_alias_records()
        if not alias_records_valid:
            print("\n✗ Pre-check failed: Alias Record validation failed")
            sys.exit(1)
    
    # Check for CNAME record file and its content before validation
    cname_record_file = "../prod_changes/cabgridmgr.amfam.com/cname_record.json"
    should_validate_cname_records = False
    
    if os.path.exists(cname_record_file):
        try:
            with open(cname_record_file, 'r') as file:
                cname_records = json.load(file)
                # Only validate if there are records (not empty list/object)
                if cname_records and not (isinstance(cname_records, list) and len(cname_records) == 0):
                    should_validate_cname_records = True
                else:
                    print("\n--- CNAME Record Validation ---")
                    print(f"CNAME record file exists but contains no records. Skipping validation.")
        except Exception as e:
            print(f"\n--- CNAME Record Validation ---")
            print(f"Error reading CNAME record file: {str(e)}")
            print("Cannot validate CNAME records due to file error.")
    else:
        print("\n--- CNAME Record Validation ---")
        print(f"CNAME record file not found: {cname_record_file}")
        print("Skipping CNAME record validation.")
    
    # Only call the validation function if we have records to validate
    if should_validate_cname_records:
        cname_records_valid = validate_cname_records()
        if not cname_records_valid:
            print("\n✗ Pre-check failed: CNAME Record validation failed")
            sys.exit(1)
    

    # Check for fixed address file and its content before validation
    fixed_address_file = "../prod_changes/cabgridmgr.amfam.com/fixed_address.json"
    should_validate_fixed_addresses = False
    
    if os.path.exists(fixed_address_file):
        try:
            with open(fixed_address_file, 'r') as file:
                fixed_addresses = json.load(file)
                # Only validate if there are records (not empty list/object)
                if fixed_addresses and not (isinstance(fixed_addresses, list) and len(fixed_addresses) == 0):
                    should_validate_fixed_addresses = True
                else:
                    print("\n--- Fixed Address Validation ---")
                    print(f"Fixed address file exists but contains no records. Skipping validation.")
        except Exception as e:
            print(f"\n--- Fixed Address Validation ---")
            print(f"Error reading fixed address file: {str(e)}")
            print("Cannot validate fixed addresses due to file error.")
    else:
        print("\n--- Fixed Address Validation ---")
        print(f"Fixed address file not found: {fixed_address_file}")
        print("Skipping fixed address validation.")
    
    # Only call the validation function if we have records to validate
    if should_validate_fixed_addresses:
        fixed_addresses_valid = validate_fixed_addresses()
        if not fixed_addresses_valid:
            print("\n✗ Pre-check failed: Fixed Address validation failed")
            sys.exit(1)
    

    # Check for host record file and its content before validation
    host_record_file = "../prod_changes/cabgridmgr.amfam.com/host_record.json"
    should_validate_host_records = False
    
    if os.path.exists(host_record_file):
        try:
            with open(host_record_file, 'r') as file:
                host_records = json.load(file)
                
                # Filter out any null entries
                if isinstance(host_records, list):
                    host_records = [record for record in host_records if record is not None]
                
                # Only validate if there are records (not empty list/object)
                if host_records and not (isinstance(host_records, list) and len(host_records) == 0):
                    should_validate_host_records = True
                else:
                    print("\n--- Host Record Validation ---")
                    print(f"Host record file exists but contains no valid records. Skipping validation.")
        except Exception as e:
            print(f"\n--- Host Record Validation ---")
            print(f"Error reading host record file: {str(e)}")
            print("Cannot validate host records due to file error.")
    else:
        print("\n--- Host Record Validation ---")
        print(f"Host record file not found: {host_record_file}")
        print("Skipping host record validation.")
    
    # Only call the validation function if we have records to validate
    if should_validate_host_records:
        host_records_valid = validate_host_records()
        if not host_records_valid:
            print("\n✗ Pre-check failed: Host Record validation failed")
            sys.exit(1)
    

    # Check for MX record file and its content before validation
    mx_record_file = "../prod_changes/cabgridmgr.amfam.com/mx_record.json"
    should_validate_mx_records = False
    
    if os.path.exists(mx_record_file):
        try:
            with open(mx_record_file, 'r') as file:
                mx_records = json.load(file)
                # Only validate if there are records
                if mx_records and not (isinstance(mx_records, list) and len(mx_records) == 0):
                    should_validate_mx_records = True
                else:
                    print("\n--- MX Record Validation ---")
                    print(f"MX record file exists but contains no records. Skipping validation.")
        except Exception as e:
            print(f"\n--- MX Record Validation ---")
            print(f"Error reading MX record file: {str(e)}")
            print("Cannot validate MX records due to file error.")
    else:
        print("\n--- MX Record Validation ---")
        print(f"MX record file not found: {mx_record_file}")
        print("Skipping MX record validation.")
    
    # Only call the validation function if we have records to validate
    if should_validate_mx_records:
        mx_records_valid = validate_mx_records()
        if not mx_records_valid:
            print("\n✗ Pre-check failed: MX Record validation failed")
            sys.exit(1)
    

    # Check for NAPTR record file and its content before validation
    naptr_record_file = "playbooks/add/cabgridmgr.amfam.com/naptr_record.json"
    should_validate_naptr_records = False
    
    if os.path.exists(naptr_record_file):
        try:
            with open(naptr_record_file, 'r') as file:
                naptr_records = json.load(file)
                # Only validate if there are records
                if naptr_records and not (isinstance(naptr_records, list) and len(naptr_records) == 0):
                    should_validate_naptr_records = True
                else:
                    print("\n--- NAPTR Record Validation ---")
                    print(f"NAPTR record file exists but contains no records. Skipping validation.")
        except Exception as e:
            print(f"\n--- NAPTR Record Validation ---")
            print(f"Error reading NAPTR record file: {str(e)}")
            print("Cannot validate NAPTR records due to file error.")
    else:
        print("\n--- NAPTR Record Validation ---")
        print(f"NAPTR record file not found: {naptr_record_file}")
        print("Skipping NAPTR record validation.")
    
    # Only call the validation function if we have records to validate
    if should_validate_naptr_records:
        naptr_records_valid = validate_naptr_records()
        if not naptr_records_valid:
            print("\n✗ Pre-check failed: NAPTR Record validation failed")
            sys.exit(1)
    

    # Check for PTR record file and its content before validation
    ptr_record_file = "../prod_changes/cabgridmgr.amfam.com/ptr_record.json"
    should_validate_ptr_records = False
    
    if os.path.exists(ptr_record_file):
        try:
            with open(ptr_record_file, 'r') as file:
                ptr_records = json.load(file)
                # Only validate if there are records (not empty list/object)
                if ptr_records and not (isinstance(ptr_records, list) and len(ptr_records) == 0):
                    should_validate_ptr_records = True
                else:
                    print("\n--- PTR Record Validation ---")
                    print(f"PTR record file exists but contains no records. Skipping validation.")
        except Exception as e:
            print(f"\n--- PTR Record Validation ---")
            print(f"Error reading PTR record file: {str(e)}")
            print("Cannot validate PTR records due to file error.")
    else:
        print("\n--- PTR Record Validation ---")
        print(f"PTR record file not found: {ptr_record_file}")
        print("Skipping PTR record validation.")
    
    # Only call the validation function if we have records to validate
    if should_validate_ptr_records:
        ptr_records_valid = validate_ptr_records()
        if not ptr_records_valid:
            print("\n✗ Pre-check failed: PTR Record validation failed")
            sys.exit(1)
    
    
    # Check for TXT record file and its content before validation
    txt_record_file = "../prod_changes/cabgridmgr.amfam.com/txt_record.json"
    should_validate_txt_records = False
    
    if os.path.exists(txt_record_file):
        try:
            with open(txt_record_file, 'r') as file:
                txt_records = json.load(file)
                # Only validate if there are records (not empty list/object)
                if txt_records and not (isinstance(txt_records, list) and len(txt_records) == 0):
                    should_validate_txt_records = True
                else:
                    print("\n--- TXT Record Validation ---")
                    print(f"TXT record file exists but contains no records. Skipping validation.")
        except Exception as e:
            print(f"\n--- TXT Record Validation ---")
            print(f"Error reading TXT record file: {str(e)}")
            print("Cannot validate TXT records due to file error.")
    else:
        print("\n--- TXT Record Validation ---")
        print(f"TXT record file not found: {txt_record_file}")
        print("Skipping TXT record validation.")
    
    # Only call the validation function if we have records to validate
    if should_validate_txt_records:
        txt_records_valid = validate_txt_records()
        if not txt_records_valid:
            print("\n✗ Pre-check failed: TXT Record validation failed")
            sys.exit(1)

    # Check for Response Policy Zone file and its content before validation
    zone_rp_file = "playbooks/add/cabgridmgr.amfam.com/zone_rp.json"
    should_validate_zone_rp = False
    
    if os.path.exists(zone_rp_file):
        try:
            with open(zone_rp_file, 'r') as file:
                zone_rp_records = json.load(file)
                # Only validate if there are records (not empty list/object)
                if zone_rp_records and not (isinstance(zone_rp_records, list) and len(zone_rp_records) == 0):
                    should_validate_zone_rp = True
                else:
                    print("\n--- Response Policy Zone Validation ---")
                    print(f"Response Policy Zone file exists but contains no records. Skipping validation.")
        except Exception as e:
            print(f"\n--- Response Policy Zone Validation ---")
            print(f"Error reading Response Policy Zone file: {str(e)}")
            print("Cannot validate Response Policy Zones due to file error.")
    else:
        print("\n--- Response Policy Zone Validation ---")
        print(f"Response Policy Zone file not found: {zone_rp_file}")
        print("Skipping Response Policy Zone validation.")
    
    # Only call the validation function if we have records to validate
    if should_validate_zone_rp:
        zone_rp_valid = validate_zone_rp_records()
        if not zone_rp_valid:
            print("\n✗ Pre-check failed: Response Policy Zone validation failed")
            sys.exit(1)

    # Check for DNS Zone file and its content before validation
    zone_file = "../prod_changes/cabgridmgr.amfam.com/nios_zone.json"
    should_validate_zones = False
    
    if os.path.exists(zone_file):
        try:
            with open(zone_file, 'r') as file:
                zone_records = json.load(file)
                # Only validate if there are records (not empty list/object)
                if zone_records and not (isinstance(zone_records, list) and len(zone_records) == 0):
                    should_validate_zones = True
                else:
                    print("\n--- DNS Zone Validation ---")
                    print(f"DNS Zone file exists but contains no records. Skipping validation.")
        except Exception as e:
            print(f"\n--- DNS Zone Validation ---")
            print(f"Error reading DNS Zone file: {str(e)}")
            print("Cannot validate DNS Zones due to file error.")
    else:
        print("\n--- DNS Zone Validation ---")
        print(f"DNS Zone file not found: {zone_file}")
        print("Skipping DNS Zone validation.")
    
    # Only call the validation function if we have records to validate
    if should_validate_zones:
        zones_valid = validate_zone_records()
        if not zones_valid:
            print("\n✗ Pre-check failed: DNS Zone validation failed")
            sys.exit(1)

# Check for Network file and its content before validation
network_file = "../prod_changes/cabgridmgr.amfam.com/network.json"
should_validate_networks = False

if os.path.exists(network_file):
    try:
        with open(network_file, 'r') as file:
            network_records = json.load(file)
            # Only validate if there are records (not empty list/object)
            if network_records and not (isinstance(network_records, list) and len(network_records) == 0):
                should_validate_networks = True
            else:
                print("\n--- Network Validation ---")
                print(f"Network file exists but contains no records. Skipping validation.")
    except Exception as e:
        print(f"\n--- Network Validation ---")
        print(f"Error reading Network file: {str(e)}")
        print("Cannot validate Networks due to file error.")
else:
    print("\n--- Network Validation ---")
    print(f"Network file not found: {network_file}")
    print("Skipping Network validation.")

# Only call the validation function if we have records to validate
if should_validate_networks:
    networks_valid = validate_networks()
    if not networks_valid:
        print("\n✗ Pre-check failed: Network validation failed")
        sys.exit(1)

    print("\n✓ All pre-checks passed successfully")
    sys.exit(0)

    # Check for Network View file and its content before validation
    network_view_file = "playbooks/add/cabgridmgr.amfam.com/network_view.json"
    should_validate_network_views = False
    
    if os.path.exists(network_view_file):
        try:
            with open(network_view_file, 'r') as file:
                network_view_records = json.load(file)
                # Only validate if there are records (not empty list/object)
                if network_view_records and not (isinstance(network_view_records, list) and len(network_view_records) == 0):
                    should_validate_network_views = True
                else:
                    print("\n--- Network View Validation ---")
                    print(f"Network View file exists but contains no records. Skipping validation.")
        except Exception as e:
            print(f"\n--- Network View Validation ---")
            print(f"Error reading Network View file: {str(e)}")
            print("Cannot validate Network Views due to file error.")
    else:
        print("\n--- Network View Validation ---")
        print(f"Network View file not found: {network_view_file}")
        print("Skipping Network View validation.")
    
    # Only call the validation function if we have records to validate
    if should_validate_network_views:
        network_views_valid = validate_network_view_records()
        if not network_views_valid:
            print("\n✗ Pre-check failed: Network View validation failed")
            sys.exit(1)

   # Check for DHCP Failover file and its content before validation
    dhcp_failover_file = "playbooks/add/cabgridmgr.amfam.com/dhcp_failover.json"
    should_validate_dhcp_failover = False
    
    if os.path.exists(dhcp_failover_file):
        try:
            with open(dhcp_failover_file, 'r') as file:
                dhcp_failover_data = json.load(file)
                # Only validate if there is data (not empty dict)
                if dhcp_failover_data and dhcp_failover_data != {}:
                    should_validate_dhcp_failover = True
                else:
                    print("\n--- DHCP Failover Validation ---")
                    print(f"DHCP Failover file exists but contains no data. Skipping validation.")
        except Exception as e:
            print(f"\n--- DHCP Failover Validation ---")
            print(f"Error reading DHCP Failover file: {str(e)}")
            print("Cannot validate DHCP Failover due to file error.")
    else:
        print("\n--- DHCP Failover Validation ---")
        print(f"DHCP Failover file not found: {dhcp_failover_file}")
        print("Skipping DHCP Failover validation.")
    
    # Only call the validation function if we have data to validate
    if should_validate_dhcp_failover:
        dhcp_failover_valid = validate_dhcp_failover_records()
        if not dhcp_failover_valid:
            print("\n✗ Pre-check failed: DHCP Failover validation failed")
            sys.exit(1)

   # Check for DHCP Option Definition file and its content before validation
    dhcp_option_def_file = "playbooks/add/cabgridmgr.amfam.com/dhcpoptiondefinition.json"
    should_validate_dhcp_option_defs = False
    
    if os.path.exists(dhcp_option_def_file):
        try:
            with open(dhcp_option_def_file, 'r') as file:
                dhcp_option_definitions = json.load(file)
                # Only validate if there are records (not empty list)
                if dhcp_option_definitions and not (isinstance(dhcp_option_definitions, list) and len(dhcp_option_definitions) == 0):
                    should_validate_dhcp_option_defs = True
                else:
                    print("\n--- DHCP Option Definition Validation ---")
                    print(f"DHCP Option Definition file exists but contains no records. Skipping validation.")
        except Exception as e:
            print(f"\n--- DHCP Option Definition Validation ---")
            print(f"Error reading DHCP Option Definition file: {str(e)}")
            print("Cannot validate DHCP Option Definitions due to file error.")
    else:
        print("\n--- DHCP Option Definition Validation ---")
        print(f"DHCP Option Definition file not found: {dhcp_option_def_file}")
        print("Skipping DHCP Option Definition validation.")
    
    # Only call the validation function if we have records to validate
    if should_validate_dhcp_option_defs:
        dhcp_option_defs_valid = validate_dhcp_option_definition_records()
        if not dhcp_option_defs_valid:
            print("\n✗ Pre-check failed: DHCP Option Definition validation failed")
            sys.exit(1)
            
                     
   # Check for DHCP IPv6 Option Definition file and its content before validation
    dhcp_ipv6_option_def_file = "playbooks/add/cabgridmgr.amfam.com/dhcpoptionipv6definition.json"
    should_validate_dhcp_ipv6_option_defs = False
    
    if os.path.exists(dhcp_ipv6_option_def_file):
        try:
            with open(dhcp_ipv6_option_def_file, 'r') as file:
                dhcp_ipv6_option_definitions = json.load(file)
                # Handle both list and single dictionary formats
                if isinstance(dhcp_ipv6_option_definitions, dict):
                    should_validate_dhcp_ipv6_option_defs = True
                elif isinstance(dhcp_ipv6_option_definitions, list) and len(dhcp_ipv6_option_definitions) > 0:
                    should_validate_dhcp_ipv6_option_defs = True
                else:
                    print("\n--- DHCP IPv6 Option Definition Validation ---")
                    print(f"DHCP IPv6 Option Definition file exists but contains no records. Skipping validation.")
        except Exception as e:
            print(f"\n--- DHCP IPv6 Option Definition Validation ---")
            print(f"Error reading DHCP IPv6 Option Definition file: {str(e)}")
            print("Cannot validate DHCP IPv6 Option Definitions due to file error.")
    else:
        print("\n--- DHCP IPv6 Option Definition Validation ---")
        print(f"DHCP IPv6 Option Definition file not found: {dhcp_ipv6_option_def_file}")
        print("Skipping DHCP IPv6 Option Definition validation.")
    
    # Only call the validation function if we have records to validate
    if should_validate_dhcp_ipv6_option_defs:
        dhcp_ipv6_option_defs_valid = validate_dhcp_ipv6_option_definition_records()
        if not dhcp_ipv6_option_defs_valid:
            print("\n✗ Pre-check failed: DHCP IPv6 Option Definition validation failed")
            sys.exit(1)

# Check for DHCP IPv6 Option Space file and its content before validation
    dhcp_ipv6_option_space_file = "playbooks/add/cabgridmgr.amfam.com/dhcpoptionipv6space.json"
    should_validate_dhcp_ipv6_option_spaces = False
    
    if os.path.exists(dhcp_ipv6_option_space_file):
        try:
            with open(dhcp_ipv6_option_space_file, 'r') as file:
                dhcp_ipv6_option_spaces = json.load(file)
                # Handle both list and single dictionary formats
                if isinstance(dhcp_ipv6_option_spaces, dict):
                    should_validate_dhcp_ipv6_option_spaces = True
                elif isinstance(dhcp_ipv6_option_spaces, list) and len(dhcp_ipv6_option_spaces) > 0:
                    should_validate_dhcp_ipv6_option_spaces = True
                else:
                    print("\n--- DHCP IPv6 Option Space Validation ---")
                    print(f"DHCP IPv6 Option Space file exists but contains no records. Skipping validation.")
        except Exception as e:
            print(f"\n--- DHCP IPv6 Option Space Validation ---")
            print(f"Error reading DHCP IPv6 Option Space file: {str(e)}")
            print("Cannot validate DHCP IPv6 Option Spaces due to file error.")
    else:
        print("\n--- DHCP IPv6 Option Space Validation ---")
        print(f"DHCP IPv6 Option Space file not found: {dhcp_ipv6_option_space_file}")
        print("Skipping DHCP IPv6 Option Space validation.")
    
    # Only call the validation function if we have records to validate
    if should_validate_dhcp_ipv6_option_spaces:
        dhcp_ipv6_option_spaces_valid = validate_dhcp_ipv6_option_space_records()
        if not dhcp_ipv6_option_spaces_valid:
            print("\n✗ Pre-check failed: DHCP IPv6 Option Space validation failed")
            sys.exit(1)

# Check for DHCP Option Space file and its content before validation
    dhcp_option_space_file = "playbooks/add/cabgridmgr.amfam.com/dhcpoptionspace.json"
    should_validate_dhcp_option_spaces = False
    
    if os.path.exists(dhcp_option_space_file):
        try:
            with open(dhcp_option_space_file, 'r') as file:
                dhcp_option_spaces = json.load(file)
                # Only validate if there are records (not empty list)
                if dhcp_option_spaces and not (isinstance(dhcp_option_spaces, list) and len(dhcp_option_spaces) == 0):
                    should_validate_dhcp_option_spaces = True
                else:
                    print("\n--- DHCP Option Space Validation ---")
                    print(f"DHCP Option Space file exists but contains no records. Skipping validation.")
        except Exception as e:
            print(f"\n--- DHCP Option Space Validation ---")
            print(f"Error reading DHCP Option Space file: {str(e)}")
            print("Cannot validate DHCP Option Spaces due to file error.")
    else:
        print("\n--- DHCP Option Space Validation ---")
        print(f"DHCP Option Space file not found: {dhcp_option_space_file}")
        print("Skipping DHCP Option Space validation.")
    
    # Only call the validation function if we have records to validate
    if should_validate_dhcp_option_spaces:
        dhcp_option_spaces_valid = validate_dhcp_option_space_records()
        if not dhcp_option_spaces_valid:
            print("\n✗ Pre-check failed: DHCP Option Space validation failed")
            sys.exit(1)

# Check for DNS Grid file and its content before validation
    dns_grid_file = "playbooks/add/cabgridmgr.amfam.com/dns_grid.json"
    should_validate_dns_grid = False
    
    if os.path.exists(dns_grid_file):
        try:
            with open(dns_grid_file, 'r') as file:
                dns_grid_configs = json.load(file)
                # Only validate if there are records (not empty list)
                if dns_grid_configs and isinstance(dns_grid_configs, list) and len(dns_grid_configs) > 0:
                    should_validate_dns_grid = True
                else:
                    print("\n--- DNS Grid Validation ---")
                    print(f"DNS Grid file exists but contains no records. Skipping validation.")
        except Exception as e:
            print(f"\n--- DNS Grid Validation ---")
            print(f"Error reading DNS Grid file: {str(e)}")
            print("Cannot validate DNS Grid due to file error.")
    else:
        print("\n--- DNS Grid Validation ---")
        print(f"DNS Grid file not found: {dns_grid_file}")
        print("Skipping DNS Grid validation.")
    
    # Only call the validation function if we have records to validate
    if should_validate_dns_grid:
        dns_grid_valid = validate_dns_grid_records()
        if not dns_grid_valid:
            print("\n✗ Pre-check failed: DNS Grid validation failed")
            sys.exit(1)

# Check for DNS64 Group file and its content before validation
    dns64_group_file = "playbooks/add/cabgridmgr.amfam.com/dns64group.json"
    should_validate_dns64_groups = False
    
    if os.path.exists(dns64_group_file):
        try:
            with open(dns64_group_file, 'r') as file:
                dns64_groups = json.load(file)
                # Only validate if there are records (not empty list)
                if dns64_groups and not (isinstance(dns64_groups, list) and len(dns64_groups) == 0):
                    should_validate_dns64_groups = True
                else:
                    print("\n--- DNS64 Group Validation ---")
                    print(f"DNS64 Group file exists but contains no records. Skipping validation.")
        except Exception as e:
            print(f"\n--- DNS64 Group Validation ---")
            print(f"Error reading DNS64 Group file: {str(e)}")
            print("Cannot validate DNS64 Groups due to file error.")
    else:
        print("\n--- DNS64 Group Validation ---")
        print(f"DNS64 Group file not found: {dns64_group_file}")
        print("Skipping DNS64 Group validation.")
    
    # Only call the validation function if we have records to validate
    if should_validate_dns64_groups:
        dns64_groups_valid = validate_dns64_group_records()
        if not dns64_groups_valid:
            print("\n✗ Pre-check failed: DNS64 Group validation failed")
            sys.exit(1)

# Check for DTC A Record file and its content before validation
    dtc_record_a_file = "playbooks/add/cabgridmgr.amfam.com/dtc_record_a.json"
    should_validate_dtc_record_a = False
    
    if os.path.exists(dtc_record_a_file):
        try:
            with open(dtc_record_a_file, 'r') as file:
                dtc_record_as = json.load(file)
                # Only validate if there are records (not empty list)
                if dtc_record_as and not (isinstance(dtc_record_as, list) and len(dtc_record_as) == 0):
                    should_validate_dtc_record_a = True
                else:
                    print("\n--- DTC A Record Validation ---")
                    print(f"DTC A record file exists but contains no records. Skipping validation.")
        except Exception as e:
            print(f"\n--- DTC A Record Validation ---")
            print(f"Error reading DTC A record file: {str(e)}")
            print("Cannot validate DTC A records due to file error.")
    else:
        print("\n--- DTC A Record Validation ---")
        print(f"DTC A record file not found: {dtc_record_a_file}")
        print("Skipping DTC A record validation.")
    
    # Only call the validation function if we have records to validate
    if should_validate_dtc_record_a:
        dtc_record_a_valid = validate_dtc_record_a_records()
        if not dtc_record_a_valid:
            print("\n✗ Pre-check failed: DTC A Record validation failed")
            sys.exit(1)

# Check for DHCP Fingerprint file and its content before validation
    fingerprint_file = "playbooks/add/cabgridmgr.amfam.com/fingerprint.json"
    should_validate_fingerprints = False
    
    if os.path.exists(fingerprint_file):
        try:
            with open(fingerprint_file, 'r') as file:
                fingerprint_data = json.load(file)
                # Only validate if there are records (not empty list)
                if fingerprint_data and not (isinstance(fingerprint_data, list) and len(fingerprint_data) == 0):
                    should_validate_fingerprints = True
                else:
                    print("\n--- DHCP Fingerprint Validation ---")
                    print(f"DHCP Fingerprint file exists but contains no records. Skipping validation.")
        except Exception as e:
            print(f"\n--- DHCP Fingerprint Validation ---")
            print(f"Error reading DHCP Fingerprint file: {str(e)}")
            print("Cannot validate DHCP Fingerprints due to file error.")
    else:
        print("\n--- DHCP Fingerprint Validation ---")
        print(f"DHCP Fingerprint file not found: {fingerprint_file}")
        print("Skipping DHCP Fingerprint validation.")
    
    # Only call the validation function if we have records to validate
    if should_validate_fingerprints:
        fingerprints_valid = validate_dhcp_fingerprint_records()
        if not fingerprints_valid:
            print("\n✗ Pre-check failed: DHCP Fingerprint validation failed")
            sys.exit(1)

# Check for Grid DHCP Properties file and its content before validation
    grid_dhcp_properties_file = "playbooks/add/cabgridmgr.amfam.com/grid_dhcp_properties.json"
    should_validate_grid_dhcp_properties = False
    
    if os.path.exists(grid_dhcp_properties_file):
        try:
            with open(grid_dhcp_properties_file, 'r') as file:
                grid_dhcp_properties_data = json.load(file)
                # Only validate if there is data (not empty dict)
                if grid_dhcp_properties_data and grid_dhcp_properties_data != {}:
                    should_validate_grid_dhcp_properties = True
                else:
                    print("\n--- Grid DHCP Properties Validation ---")
                    print(f"Grid DHCP Properties file exists but contains no data. Skipping validation.")
        except Exception as e:
            print(f"\n--- Grid DHCP Properties Validation ---")
            print(f"Error reading Grid DHCP Properties file: {str(e)}")
            print("Cannot validate Grid DHCP Properties due to file error.")
    else:
        print("\n--- Grid DHCP Properties Validation ---")
        print(f"Grid DHCP Properties file not found: {grid_dhcp_properties_file}")
        print("Skipping Grid DHCP Properties validation.")
    
    # Only call the validation function if we have data to validate
    if should_validate_grid_dhcp_properties:
        grid_dhcp_properties_valid = validate_grid_dhcp_properties_records()
        if not grid_dhcp_properties_valid:
            print("\n✗ Pre-check failed: Grid DHCP Properties validation failed")
            sys.exit(1)

# Check for Grid DNS Properties file and its content before validation
grid_dns_properties_file = "../prod_changes/cabgridmgr.amfam.com/grid_dns_properties.json"
should_validate_grid_dns_properties = False

if os.path.exists(grid_dns_properties_file):
    try:
        with open(grid_dns_properties_file, 'r') as file:
            grid_dns_properties_data = json.load(file)
            # Only validate if there is data (not empty dict)
            if grid_dns_properties_data and grid_dns_properties_data != {}:
                should_validate_grid_dns_properties = True
            else:
                print("\n--- Grid DNS Properties Validation ---")
                print(f"Grid DNS Properties file exists but contains no data. Skipping validation.")
    except Exception as e:
        print(f"\n--- Grid DNS Properties Validation ---")
        print(f"Error reading Grid DNS Properties file: {str(e)}")
        print("Cannot validate Grid DNS Properties due to file error.")
else:
    print("\n--- Grid DNS Properties Validation ---")
    print(f"Grid DNS Properties file not found: {grid_dns_properties_file}")
    print("Skipping Grid DNS Properties validation.")

# Only call the validation function if we have data to validate
if should_validate_grid_dns_properties:
    grid_dns_properties_valid = validate_grid_dns_properties_records()
    if not grid_dns_properties_valid:
        print("\n✗ Pre-check failed: Grid DNS Properties validation failed")
        sys.exit(1)

# Check for Member DNS Properties file and its content before validation
member_dns_properties_file = "playbooks/add/cabgridmgr.amfam.com/member_dns_properties.json"
should_validate_member_dns_properties = False

if os.path.exists(member_dns_properties_file):
    try:
        with open(member_dns_properties_file, 'r') as file:
            member_dns_properties_data = json.load(file)
            # Only validate if there is data
            if member_dns_properties_data:
                if isinstance(member_dns_properties_data, list) and len(member_dns_properties_data) > 0:
                    should_validate_member_dns_properties = True
                elif isinstance(member_dns_properties_data, dict) and member_dns_properties_data != {}:
                    should_validate_member_dns_properties = True
                else:
                    print("\n--- Member DNS Properties Validation ---")
                    print(f"Member DNS Properties file exists but contains no data. Skipping validation.")
            else:
                print("\n--- Member DNS Properties Validation ---")
                print(f"Member DNS Properties file exists but contains no data. Skipping validation.")
    except Exception as e:
        print(f"\n--- Member DNS Properties Validation ---")
        print(f"Error reading Member DNS Properties file: {str(e)}")
        print("Cannot validate Member DNS Properties due to file error.")
else:
    print("\n--- Member DNS Properties Validation ---")
    print(f"Member DNS Properties file not found: {member_dns_properties_file}")
    print("Skipping Member DNS Properties validation.")

# Only call the validation function if we have data to validate
if should_validate_member_dns_properties:
    member_dns_properties_valid = validate_member_dns_properties_records()
    if not member_dns_properties_valid:
        print("\n✗ Pre-check failed: Member DNS Properties validation failed")
        sys.exit(1)

# Check for Member DNS file and its content before validation
member_dns_file = "playbooks/add/cabgridmgr.amfam.com/member_dns.json"
should_validate_member_dns = False

if os.path.exists(member_dns_file):
    try:
        with open(member_dns_file, 'r') as file:
            member_dns_data = json.load(file)
            # Only validate if there is data
            if member_dns_data:
                if isinstance(member_dns_data, list) and len(member_dns_data) > 0:
                    should_validate_member_dns = True
                elif isinstance(member_dns_data, dict) and member_dns_data != {}:
                    should_validate_member_dns = True
                else:
                    print("\n--- Member DNS Validation ---")
                    print(f"Member DNS file exists but contains no data. Skipping validation.")
            else:
                print("\n--- Member DNS Validation ---")
                print(f"Member DNS file exists but contains no data. Skipping validation.")
    except Exception as e:
        print(f"\n--- Member DNS Validation ---")
        print(f"Error reading Member DNS file: {str(e)}")
        print("Cannot validate Member DNS due to file error.")
else:
    print("\n--- Member DNS Validation ---")
    print(f"Member DNS file not found: {member_dns_file}")
    print("Skipping Member DNS validation.")

# Only call the validation function if we have data to validate
if should_validate_member_dns:
    member_dns_valid = validate_member_dns_records()
    if not member_dns_valid:
        print("\n✗ Pre-check failed: Member DNS validation failed")
        sys.exit(1)

# Check for Named ACL file and its content before validation
named_acl_file = "playbooks/add/cabgridmgr.amfam.com/namedacl.json"
should_validate_named_acl = False

if os.path.exists(named_acl_file):
    try:
        with open(named_acl_file, 'r') as file:
            named_acl_data = json.load(file)
            # Only validate if there is data
            if named_acl_data:
                if isinstance(named_acl_data, list) and len(named_acl_data) > 0:
                    should_validate_named_acl = True
                elif isinstance(named_acl_data, dict) and named_acl_data != {}:
                    should_validate_named_acl = True
                else:
                    print("\n--- Named ACL Validation ---")
                    print(f"Named ACL file exists but contains no data. Skipping validation.")
            else:
                print("\n--- Named ACL Validation ---")
                print(f"Named ACL file exists but contains no data. Skipping validation.")
    except Exception as e:
        print(f"\n--- Named ACL Validation ---")
        print(f"Error reading Named ACL file: {str(e)}")
        print("Cannot validate Named ACLs due to file error.")
else:
    print("\n--- Named ACL Validation ---")
    print(f"Named ACL file not found: {named_acl_file}")
    print("Skipping Named ACL validation.")

# Only call the validation function if we have data to validate
if should_validate_named_acl:
    named_acl_valid = validate_named_acl_records()
    if not named_acl_valid:
        print("\n✗ Pre-check failed: Named ACL validation failed")
        sys.exit(1)

# Check for Named ACL file and its content before validation
named_acl_file = "playbooks/add/cabgridmgr.amfam.com/namedacl.json"
should_validate_named_acl = False

if os.path.exists(named_acl_file):
    try:
        with open(named_acl_file, 'r') as file:
            named_acl_data = json.load(file)
            # Only validate if there is data
            if named_acl_data:
                if isinstance(named_acl_data, list) and len(named_acl_data) > 0:
                    should_validate_named_acl = True
                elif isinstance(named_acl_data, dict) and named_acl_data != {}:
                    should_validate_named_acl = True
                else:
                    print("\n--- Named ACL Validation ---")
                    print(f"Named ACL file exists but contains no data. Skipping validation.")
            else:
                print("\n--- Named ACL Validation ---")
                print(f"Named ACL file exists but contains no data. Skipping validation.")
    except Exception as e:
        print(f"\n--- Named ACL Validation ---")
        print(f"Error reading Named ACL file: {str(e)}")
        print("Cannot validate Named ACLs due to file error.")
else:
    print("\n--- Named ACL Validation ---")
    print(f"Named ACL file not found: {named_acl_file}")
    print("Skipping Named ACL validation.")

# Only call the validation function if we have data to validate
if should_validate_named_acl:
    named_acl_valid = validate_named_acl_records()
    if not named_acl_valid:
        print("\n✗ Pre-check failed: Named ACL validation failed")
        sys.exit(1)

# Check for Admin User file and its content before validation
    adminuser_file = "playbooks/add/cabgridmgr.amfam.com/adminuser.json"
    should_validate_adminusers = False
    
    if os.path.exists(adminuser_file):
        try:
            with open(adminuser_file, 'r') as file:
                adminuser_records = json.load(file)
                # Only validate if there are records (not empty list/object)
                if adminuser_records and not (isinstance(adminuser_records, list) and len(adminuser_records) == 0):
                    should_validate_adminusers = True
                else:
                    print("\n--- Admin User Validation ---")
                    print(f"Admin User file exists but contains no records. Skipping validation.")
        except Exception as e:
            print(f"\n--- Admin User Validation ---")
            print(f"Error reading Admin User file: {str(e)}")
            print("Cannot validate Admin Users due to file error.")
    else:
        print("\n--- Admin User Validation ---")
        print(f"Admin User file not found: {adminuser_file}")
        print("Skipping Admin User validation.")
    
    # Only call the validation function if we have records to validate
    if should_validate_adminusers:
        adminusers_valid = validate_adminuser_records()
        if not adminusers_valid:
            print("\n✗ Pre-check failed: Admin User validation failed")
            sys.exit(1)

# Check for Network Container file and its content before validation
    networkcontainer_file = "playbooks/add/cabgridmgr.amfam.com/networkcontainer.json"
    should_validate_networkcontainers = False
    
    if os.path.exists(networkcontainer_file):
        try:
            with open(networkcontainer_file, 'r') as file:
                networkcontainer_records = json.load(file)
                # Only validate if there are records (not empty list/object)
                if networkcontainer_records and not (isinstance(networkcontainer_records, list) and len(networkcontainer_records) == 0):
                    should_validate_networkcontainers = True
                else:
                    print("\n--- Network Container Validation ---")
                    print(f"Network Container file exists but contains no records. Skipping validation.")
        except Exception as e:
            print(f"\n--- Network Container Validation ---")
            print(f"Error reading Network Container file: {str(e)}")
            print("Cannot validate Network Containers due to file error.")
    else:
        print("\n--- Network Container Validation ---")
        print(f"Network Container file not found: {networkcontainer_file}")
        print("Skipping Network Container validation.")
    
    # Only call the validation function if we have records to validate
    if should_validate_networkcontainers:
        networkcontainers_valid = validate_network_container_records()
        if not networkcontainers_valid:
            print("\n✗ Pre-check failed: Network Container validation failed")
            sys.exit(1)

    # Check for IPv6 Network Container file and its content before validation
    ipv6networkcontainer_file = "playbooks/add/cabgridmgr.amfam.com/networkipv6container.json"
    should_validate_ipv6networkcontainers = False
    
    if os.path.exists(ipv6networkcontainer_file):
        try:
            with open(ipv6networkcontainer_file, 'r') as file:
                ipv6networkcontainer_records = json.load(file)
                # Only validate if there are records (not empty list/object)
                if ipv6networkcontainer_records and not (isinstance(ipv6networkcontainer_records, list) and len(ipv6networkcontainer_records) == 0):
                    should_validate_ipv6networkcontainers = True
                else:
                    print("\n--- IPv6 Network Container Validation ---")
                    print(f"IPv6 Network Container file exists but contains no records. Skipping validation.")
        except Exception as e:
            print(f"\n--- IPv6 Network Container Validation ---")
            print(f"Error reading IPv6 Network Container file: {str(e)}")
            print("Cannot validate IPv6 Network Containers due to file error.")
    else:
        print("\n--- IPv6 Network Container Validation ---")
        print(f"IPv6 Network Container file not found: {ipv6networkcontainer_file}")
        print("Skipping IPv6 Network Container validation.")
    
    # Only call the validation function if we have records to validate
    if should_validate_ipv6networkcontainers:
        ipv6networkcontainers_valid = validate_ipv6_network_container_records()
        if not ipv6networkcontainers_valid:
            print("\n✗ Pre-check failed: IPv6 Network Container validation failed")
            sys.exit(1)

    # Check for Range file and its content before validation
    range_file = "../prod_changes/cabgridmgr.amfam.com/network_range.json"
    should_validate_ranges = False
    
    if os.path.exists(range_file):
        try:
            with open(range_file, 'r') as file:
                range_records = json.load(file)
                # Only validate if there are records (not empty list/object)
                if range_records and not (isinstance(range_records, list) and len(range_records) == 0):
                    should_validate_ranges = True
                else:
                    print("\n--- DHCP Range Validation ---")
                    print(f"Range file exists but contains no records. Skipping validation.")
        except Exception as e:
            print(f"\n--- DHCP Range Validation ---")
            print(f"Error reading Range file: {str(e)}")
            print("Cannot validate Ranges due to file error.")
    else:
        print("\n--- DHCP Range Validation ---")
        print(f"Range file not found: {range_file}")
        print("Skipping Range validation.")
    
    # Only call the validation function if we have records to validate
    if should_validate_ranges:
        ranges_valid = validate_range_records()
        if not ranges_valid:
            print("\n✗ Pre-check failed: DHCP Range validation failed")
            sys.exit(1)

    # Check for SRV record file and its content before validation
    srv_record_file = "../prod_changes/cabgridmgr.amfam.com/srv_record.json"
    should_validate_srv_records = False
    
    if os.path.exists(srv_record_file):
        try:
            with open(srv_record_file, 'r') as file:
                srv_records = json.load(file)
                # Only validate if there are records (not empty list/object)
                if srv_records and not (isinstance(srv_records, list) and len(srv_records) == 0):
                    should_validate_srv_records = True
                else:
                    print("\n--- SRV Record Validation ---")
                    print(f"SRV record file exists but contains no records. Skipping validation.")
        except Exception as e:
            print(f"\n--- SRV Record Validation ---")
            print(f"Error reading SRV record file: {str(e)}")
            print("Cannot validate SRV records due to file error.")
    else:
        print("\n--- SRV Record Validation ---")
        print(f"SRV record file not found: {srv_record_file}")
        print("Skipping SRV record validation.")
    
    # Only call the validation function if we have records to validate
    if should_validate_srv_records:
        srv_records_valid = validate_srv_records()
        if not srv_records_valid:
            print("\n✗ Pre-check failed: SRV Record validation failed")
            sys.exit(1)

# Check for VLAN file and its content before validation
    vlan_file = "playbooks/add/cabgridmgr.amfam.com/vlan.json"
    should_validate_vlans = False
    
    if os.path.exists(vlan_file):
        try:
            with open(vlan_file, 'r') as file:
                vlan_records = json.load(file)
                # Only validate if there are records (not empty list/object)
                if vlan_records and not (isinstance(vlan_records, list) and len(vlan_records) == 0):
                    should_validate_vlans = True
                else:
                    print("\n--- VLAN Validation ---")
                    print(f"VLAN file exists but contains no records. Skipping validation.")
        except Exception as e:
            print(f"\n--- VLAN Validation ---")
            print(f"Error reading VLAN file: {str(e)}")
            print("Cannot validate VLANs due to file error.")
    else:
        print("\n--- VLAN Validation ---")
        print(f"VLAN file not found: {vlan_file}")
        print("Skipping VLAN validation.")
    
    # Only call the validation function if we have records to validate
    if should_validate_vlans:
        vlans_valid = validate_vlan_records()
        if not vlans_valid:
            print("\n✗ Pre-check failed: VLAN validation failed")
            sys.exit(1)

# Check for VLAN View file and its content before validation
    vlan_view_file = "playbooks/add/cabgridmgr.amfam.com/vlanview.json"
    should_validate_vlan_views = False
    
    if os.path.exists(vlan_view_file):
        try:
            with open(vlan_view_file, 'r') as file:
                vlan_view_records = json.load(file)
                # Only validate if there are records (not empty list/object)
                if vlan_view_records and not (isinstance(vlan_view_records, list) and len(vlan_view_records) == 0):
                    should_validate_vlan_views = True
                else:
                    print("\n--- VLAN View Validation ---")
                    print(f"VLAN View file exists but contains no records. Skipping validation.")
        except Exception as e:
            print(f"\n--- VLAN View Validation ---")
            print(f"Error reading VLAN View file: {str(e)}")
            print("Cannot validate VLAN Views due to file error.")
    else:
        print("\n--- VLAN View Validation ---")
        print(f"VLAN View file not found: {vlan_view_file}")
        print("Skipping VLAN View validation.")
    
    # Only call the validation function if we have records to validate
    if should_validate_vlan_views:
        vlan_views_valid = validate_vlan_view_records()
        if not vlan_views_valid:
            print("\n✗ Pre-check failed: VLAN View validation failed")
            sys.exit(1)

# Check for Upgrade Group file and its content before validation
    upgrade_group_file = "playbooks/add/cabgridmgr.amfam.com/upgradegroup.json"
    should_validate_upgrade_groups = False
    
    if os.path.exists(upgrade_group_file):
        try:
            with open(upgrade_group_file, 'r') as file:
                upgrade_group_records = json.load(file)
                # Only validate if there are records (not empty list/object)
                if upgrade_group_records and not (isinstance(upgrade_group_records, list) and len(upgrade_group_records) == 0):
                    should_validate_upgrade_groups = True
                else:
                    print("\n--- Upgrade Group Validation ---")
                    print(f"Upgrade Group file exists but contains no records. Skipping validation.")
        except Exception as e:
            print(f"\n--- Upgrade Group Validation ---")
            print(f"Error reading Upgrade Group file: {str(e)}")
            print("Cannot validate Upgrade Groups due to file error.")
    else:
        print("\n--- Upgrade Group Validation ---")
        print(f"Upgrade Group file not found: {upgrade_group_file}")
        print("Skipping Upgrade Group validation.")
    
    # Only call the validation function if we have records to validate
    if should_validate_upgrade_groups:
        upgrade_groups_valid = validate_upgrade_group_records()
        if not upgrade_groups_valid:
            print("\n✗ Pre-check failed: Upgrade Group validation failed")
            sys.exit(1)

# Check for NS Group file and its content before validation
    ns_group_file = "playbooks/add/cabgridmgr.amfam.com/nsgroup.json"
    should_validate_ns_groups = False
    
    if os.path.exists(ns_group_file):
        try:
            with open(ns_group_file, 'r') as file:
                ns_group_records = json.load(file)
                # Only validate if there are records (not empty list/object)
                if ns_group_records and not (isinstance(ns_group_records, list) and len(ns_group_records) == 0):
                    should_validate_ns_groups = True
                else:
                    print("\n--- NS Group Validation ---")
                    print(f"NS Group file exists but contains no records. Skipping validation.")
        except Exception as e:
            print(f"\n--- NS Group Validation ---")
            print(f"Error reading NS Group file: {str(e)}")
            print("Cannot validate NS Groups due to file error.")
    else:
        print("\n--- NS Group Validation ---")
        print(f"NS Group file not found: {ns_group_file}")
        print("Skipping NS Group validation.")
    
    # Only call the validation function if we have records to validate
    if should_validate_ns_groups:
        ns_groups_valid = validate_ns_group_records()
        if not ns_groups_valid:
            print("\n✗ Pre-check failed: NS Group validation failed")
            sys.exit(1)

# Check for Ordered Response Policy Zones file and its content before validation
    ordered_rpz_file = "playbooks/add/cabgridmgr.amfam.com/ordered_response_policy_zones.json"
    should_validate_ordered_rpz = False
    
    if os.path.exists(ordered_rpz_file):
        try:
            with open(ordered_rpz_file, 'r') as file:
                ordered_rpz_records = json.load(file)
                # Only validate if there are records (not empty list/object)
                if ordered_rpz_records and not (isinstance(ordered_rpz_records, list) and len(ordered_rpz_records) == 0):
                    should_validate_ordered_rpz = True
                else:
                    print("\n--- Ordered Response Policy Zones Validation ---")
                    print(f"Ordered RPZ file exists but contains no records. Skipping validation.")
        except Exception as e:
            print(f"\n--- Ordered Response Policy Zones Validation ---")
            print(f"Error reading Ordered RPZ file: {str(e)}")
            print("Cannot validate Ordered Response Policy Zones due to file error.")
    else:
        print("\n--- Ordered Response Policy Zones Validation ---")
        print(f"Ordered RPZ file not found: {ordered_rpz_file}")
        print("Skipping Ordered Response Policy Zones validation.")
    
    # Only call the validation function if we have records to validate
    if should_validate_ordered_rpz:
        ordered_rpz_valid = validate_ordered_rpz_records()
        if not ordered_rpz_valid:
            print("\n✗ Pre-check failed: Ordered Response Policy Zones validation failed")
            sys.exit(1)

    print("\n✓ All pre-checks passed successfully")
    sys.exit(0)

if __name__ == "__main__":
    main()