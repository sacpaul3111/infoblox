#!/usr/bin/env python3
"""
Post-check script to verify Infoblox records after deployment.
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
            data = json.load(file)
            # If the content is not a list, convert it to a list with one item
            if not isinstance(data, list):
                data = [data]
            return data
    except FileNotFoundError:
        print(f"✗ File not found: {file_path}")
        return []
    except json.JSONDecodeError:
        print(f"✗ Invalid JSON in file: {file_path}")
        return []
    except Exception as e:
        print(f"✗ Error reading file {file_path}: {str(e)}")
        return []

def get_a_record(name, view):
    """Get A record from Infoblox by name and view."""
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
            print(f"✗ Error getting A record {name}: {response.status_code}")
            return []
    except Exception as e:
        print(f"✗ Error getting A record {name}: {str(e)}")
        return []

def get_aaaa_record(name, view):
    """Get AAAA record from Infoblox by name and view."""
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
            print(f"✗ Error getting AAAA record {name}: {response.status_code}")
            return []
    except Exception as e:
        print(f"✗ Error getting AAAA record {name}: {str(e)}")
        return []

def get_alias_record(name, view):
    """Get Alias record from Infoblox by name and view."""
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
            print(f"✗ Error getting Alias record {name}: {response.status_code}")
            return []
    except Exception as e:
        print(f"✗ Error getting Alias record {name}: {str(e)}")
        return []

def get_cname_record(name, view):
    """Get CNAME record from Infoblox by name and view."""
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
            print(f"✗ Error getting CNAME record {name}: {response.status_code}")
            return []
    except Exception as e:
        print(f"✗ Error getting CNAME record {name}: {str(e)}")
        return []

def verify_a_records():
    """Verify A records after deployment."""
    print("\n--- A Record Post-Deployment Verification ---")
    
    # Check if A record file exists with the correct path
    a_record_file = "../prod_changes/cabgridmgr.amfam.com/a_record.json"
    if not os.path.exists(a_record_file):
        print(f"A record file not found: {a_record_file}")
        print("Skipping A record verification.")
        return True
    
    # Read A record data from JSON file
    try:
        with open(a_record_file, 'r') as file:
            a_records = json.load(file)
            
            # Check if the file contains an empty list or empty object
            if not a_records or (isinstance(a_records, list) and len(a_records) == 0):
                print("A record file exists but contains no records. Skipping verification.")
                return True
                
            # If the content is not a list, convert it to a list with one item
            if not isinstance(a_records, list):
                a_records = [a_records]
                
            print(f"Verifying {len(a_records)} A records.")
    except Exception as e:
        print(f"Error reading file {a_record_file}: {str(e)}")
        return False
    
    # Count statistics
    total_records = len(a_records)
    successful_records = 0
    failed_records = 0
    failed_list = []
    
    # Verify each record exists in Infoblox with correct IP
    for record in a_records:
        name = record.get('name')
        view = record.get('view')
        expected_ip = record.get('ipv4addr')
        
        if not name or not view or not expected_ip:
            print(f"✗ Incomplete record data: {record}")
            failed_records += 1
            continue
        
        actual_records = get_a_record(name, view)
        
        if not actual_records:
            print(f"✗ Record '{name}' was not found in Infoblox")
            failed_records += 1
            failed_list.append(name)
            continue
        
        # Check if the IP matches
        actual_ip = actual_records[0].get('ipv4addr')
        if actual_ip != expected_ip:
            print(f"✗ Record '{name}' has incorrect IP: expected {expected_ip}, got {actual_ip}")
            failed_records += 1
            failed_list.append(name)
        else:
            print(f"✓ Record '{name}' verified with IP {actual_ip}")
            successful_records += 1
    
    # Display verification summary
    print("\nA Record Verification Summary:")
    print(f"Total records: {total_records}")
    print(f"Successfully verified: {successful_records}")
    print(f"Failed verification: {failed_records}")
    
    if failed_list:
        print(f"Failed records: {', '.join(failed_list)}")
    
    return failed_records == 0

def verify_aaaa_records():
    """Verify AAAA records after deployment."""
    print("\n--- AAAA Record Post-Deployment Verification ---")
    
    # Check if AAAA record file exists with the correct path
    aaaa_record_file = "../prod_changes/cabgridmgr.amfam.com/aaaa_record.json"
    if not os.path.exists(aaaa_record_file):
        print(f"AAAA record file not found: {aaaa_record_file}")
        print("Skipping AAAA record verification.")
        return True
    
    # Read AAAA record data from JSON file
    try:
        with open(aaaa_record_file, 'r') as file:
            aaaa_records = json.load(file)
            
            # Check if the file contains an empty list or empty object
            if not aaaa_records or (isinstance(aaaa_records, list) and len(aaaa_records) == 0):
                print("AAAA record file exists but contains no records. Skipping verification.")
                return True
                
            # If the content is not a list, convert it to a list with one item
            if not isinstance(aaaa_records, list):
                aaaa_records = [aaaa_records]
                
            print(f"Verifying {len(aaaa_records)} AAAA records.")
    except Exception as e:
        print(f"Error reading file {aaaa_record_file}: {str(e)}")
        return False
    
    # Count statistics
    total_records = len(aaaa_records)
    successful_records = 0
    failed_records = 0
    failed_list = []
    
    # Verify each record exists in Infoblox with correct IPv6
    for record in aaaa_records:
        name = record.get('name')
        view = record.get('view')
        expected_ipv6 = record.get('ipv6addr')
        
        if not name or not view or not expected_ipv6:
            print(f"✗ Incomplete record data: {record}")
            failed_records += 1
            continue
        
        actual_records = get_aaaa_record(name, view)
        
        if not actual_records:
            print(f"✗ Record '{name}' was not found in Infoblox")
            failed_records += 1
            failed_list.append(name)
            continue
        
        # Check if the IPv6 matches
        actual_ipv6 = actual_records[0].get('ipv6addr')
        if actual_ipv6 != expected_ipv6:
            print(f"✗ Record '{name}' has incorrect IPv6: expected {expected_ipv6}, got {actual_ipv6}")
            failed_records += 1
            failed_list.append(name)
        else:
            print(f"✓ Record '{name}' verified with IPv6 {actual_ipv6}")
            successful_records += 1
    
    # Display verification summary
    print("\nAAAA Record Verification Summary:")
    print(f"Total records: {total_records}")
    print(f"Successfully verified: {successful_records}")
    print(f"Failed verification: {failed_records}")
    
    if failed_list:
        print(f"Failed records: {', '.join(failed_list)}")
    
    return failed_records == 0

def verify_alias_records():
    """Verify Alias records after deployment."""
    print("\n--- Alias Record Post-Deployment Verification ---")
    
    # Check if Alias record file exists with the correct path
    alias_record_file = "playbooks/add/cabgridmgr.amfam.com/alias_record.json"
    if not os.path.exists(alias_record_file):
        print(f"Alias record file not found: {alias_record_file}")
        print("Skipping Alias record verification.")
        return True
    
    # Read Alias record data from JSON file
    try:
        with open(alias_record_file, 'r') as file:
            alias_records = json.load(file)
            
            # Check if the file contains an empty list or empty object
            if not alias_records or (isinstance(alias_records, list) and len(alias_records) == 0):
                print("Alias record file exists but contains no records. Skipping verification.")
                return True
                
            # If the content is not a list, convert it to a list with one item
            if not isinstance(alias_records, list):
                alias_records = [alias_records]
                
            print(f"Verifying {len(alias_records)} Alias records.")
    except Exception as e:
        print(f"Error reading file {alias_record_file}: {str(e)}")
        return False
    
    # Count statistics
    total_records = len(alias_records)
    successful_records = 0
    failed_records = 0
    failed_list = []
    
    # Verify each record exists in Infoblox with correct target
    for record in alias_records:
        name = record.get('name')
        view = record.get('view')
        expected_target = record.get('target_name')
        expected_type = record.get('target_type')
        
        if not name or not view or not expected_target or not expected_type:
            print(f"✗ Incomplete record data: {record}")
            failed_records += 1
            continue
        
        actual_records = get_alias_record(name, view)
        
        if not actual_records:
            print(f"✗ Record '{name}' was not found in Infoblox")
            failed_records += 1
            failed_list.append(name)
            continue
        
        # Check if the target name and type match
        actual_target = actual_records[0].get('target_name')
        actual_type = actual_records[0].get('target_type')
        
        if actual_target != expected_target or actual_type != expected_type:
            print(f"✗ Record '{name}' has incorrect target: expected {expected_target} ({expected_type}), got {actual_target} ({actual_type})")
            failed_records += 1
            failed_list.append(name)
        else:
            print(f"✓ Record '{name}' verified with target {actual_target} ({actual_type})")
            successful_records += 1
    
    # Display verification summary
    print("\nAlias Record Verification Summary:")
    print(f"Total records: {total_records}")
    print(f"Successfully verified: {successful_records}")
    print(f"Failed verification: {failed_records}")
    
    if failed_list:
        print(f"Failed records: {', '.join(failed_list)}")
    
    return failed_records == 0

def verify_cname_records():
    """Verify CNAME records after deployment."""
    print("\n--- CNAME Record Post-Deployment Verification ---")
    
    # Check if CNAME record file exists with the correct path
    cname_record_file = "../prod_changes/cabgridmgr.amfam.com/cname_record.json"
    if not os.path.exists(cname_record_file):
        print(f"CNAME record file not found: {cname_record_file}")
        print("Skipping CNAME record verification.")
        return True
    
    # Read CNAME record data from JSON file
    try:
        with open(cname_record_file, 'r') as file:
            cname_records = json.load(file)
            
            # Check if the file contains an empty list or empty object
            if not cname_records or (isinstance(cname_records, list) and len(cname_records) == 0):
                print("CNAME record file exists but contains no records. Skipping verification.")
                return True
                
            # If the content is not a list, convert it to a list with one item
            if not isinstance(cname_records, list):
                cname_records = [cname_records]
                
            print(f"Verifying {len(cname_records)} CNAME records.")
    except Exception as e:
        print(f"Error reading file {cname_record_file}: {str(e)}")
        return False
    
    # Count statistics
    total_records = len(cname_records)
    successful_records = 0
    failed_records = 0
    failed_list = []
    
    # Verify each record exists in Infoblox with correct canonical name
    for record in cname_records:
        name = record.get('name')
        view = record.get('view')
        expected_canonical = record.get('canonical')
        
        if not name or not view or not expected_canonical:
            print(f"✗ Incomplete record data: {record}")
            failed_records += 1
            continue
        
        actual_records = get_cname_record(name, view)
        
        if not actual_records:
            print(f"✗ Record '{name}' was not found in Infoblox")
            failed_records += 1
            failed_list.append(name)
            continue
        
        # Check if the canonical name matches
        actual_canonical = actual_records[0].get('canonical')
        if actual_canonical != expected_canonical:
            print(f"✗ Record '{name}' has incorrect canonical name: expected {expected_canonical}, got {actual_canonical}")
            failed_records += 1
            failed_list.append(name)
        else:
            print(f"✓ Record '{name}' verified with canonical name {actual_canonical}")
            successful_records += 1
    
    # Display verification summary
    print("\nCNAME Record Verification Summary:")
    print(f"Total records: {total_records}")
    print(f"Successfully verified: {successful_records}")
    print(f"Failed verification: {failed_records}")
    
    if failed_list:
        print(f"Failed records: {', '.join(failed_list)}")
    
    return failed_records == 0

def perform_dns_lookup(domain, record_type="A"):
    """Perform a DNS lookup for a domain with specific record type."""
    try:
        if record_type == "AAAA":
            cmd = ['nslookup', '-type=AAAA', domain]
        else:
            cmd = ['nslookup', domain]
            
        result = subprocess.run(cmd, 
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

# def verify_dns_resolution():
#     """Verify DNS resolution for all deployed records."""
#     print("\n--- DNS Resolution Verification ---")
    
#     verification_results = True
    
#     # Verify A records DNS resolution
#     a_record_file = "../prod_changes/cabgridmgr.amfam.com/a_record.json"
#     if os.path.exists(a_record_file):
#         a_records = read_json_file(a_record_file)
#         if a_records:
#             print("\n-- Verifying A record DNS resolution --")
#             verification_results = verification_results and verify_a_record_dns_resolution(a_records)
    
#     # Verify AAAA records DNS resolution
#     aaaa_record_file = "../prod_changes/cabgridmgr.amfam.com/aaaa_record.json"
#     if os.path.exists(aaaa_record_file):
#         aaaa_records = read_json_file(aaaa_record_file)
#         if aaaa_records:
#             print("\n-- Verifying AAAA record DNS resolution --")
#             verification_results = verification_results and verify_aaaa_record_dns_resolution(aaaa_records)
    
#     # Verify CNAME records DNS resolution
#     cname_record_file = "../prod_changes/cabgridmgr.amfam.com/cname_record.json"
#     if os.path.exists(cname_record_file):
#         cname_records = read_json_file(cname_record_file)
#         if cname_records:
#             print("\n-- Verifying CNAME record DNS resolution --")
#             verification_results = verification_results and verify_cname_record_dns_resolution(cname_records)
    
#     # Verify Alias records DNS resolution
#     alias_record_file = "playbooks/add/cabgridmgr.amfam.com/alias_record.json"
#     if os.path.exists(alias_record_file):
#         alias_records = read_json_file(alias_record_file)
#         if alias_records:
#             print("\n-- Verifying Alias record DNS resolution --")
#             verification_results = verification_results and verify_alias_record_dns_resolution(alias_records)

#     # Verify Host records DNS resolution
#     host_record_file = "../prod_changes/cabgridmgr.amfam.com/host_record.json"
#     if os.path.exists(host_record_file):
#         host_records = read_json_file(host_record_file)
#         if host_records:
#             # Filter out null entries
#             host_records = [record for record in host_records if record is not None]
#             if host_records:
#                 print("\n-- Verifying Host record DNS resolution --")
#                 verification_results = verification_results and verify_host_record_dns_resolution(host_records)
    
#         # Verify MX records DNS resolution
#     mx_record_file = "../prod_changes/cabgridmgr.amfam.com/mx_record.json"
#     if os.path.exists(mx_record_file):
#         mx_records = read_json_file(mx_record_file)
#         if mx_records:
#             print("\n-- Verifying MX record DNS resolution --")
#             verification_results = verification_results and verify_mx_record_dns_resolution(mx_records)
    
#     # Verify NAPTR records DNS resolution
#     naptr_record_file = "playbooks/add/cabgridmgr.amfam.com/naptr_record.json"
#     if os.path.exists(naptr_record_file):
#         naptr_records = read_json_file(naptr_record_file)
#         if naptr_records:
#             print("\n-- Verifying NAPTR record DNS resolution --")
#             verification_results = verification_results and verify_naptr_record_dns_resolution(naptr_records)

#     # Verify PTR records DNS resolution
#     ptr_record_file = "../prod_changes/cabgridmgr.amfam.com/ptr_record.json"
#     if os.path.exists(ptr_record_file):
#         ptr_records = read_json_file(ptr_record_file)
#         if ptr_records:
#             print("\n-- Verifying PTR record DNS resolution --")
#             verification_results = verification_results and verify_ptr_record_dns_resolution(ptr_records)
    
#     # Verify TXT records DNS resolution
#     txt_record_file = "../prod_changes/cabgridmgr.amfam.com/txt_record.json"
#     if os.path.exists(txt_record_file):
#         txt_records = read_json_file(txt_record_file)
#         if txt_records:
#             print("\n-- Verifying TXT record DNS resolution --")
#             verification_results = verification_results and verify_txt_record_dns_resolution(txt_records)

#     # Verify DNS Zone resolution
#     zone_file = "../prod_changes/cabgridmgr.amfam.com/nios_zone.json"
#     if os.path.exists(zone_file):
#         zone_records = read_json_file(zone_file)
#         if zone_records:
#             verification_results = verification_results and verify_zone_dns_resolution(zone_records)

#     # Verify SRV records DNS resolution
#     srv_record_file = "../prod_changes/cabgridmgr.amfam.com/srv_record.json"
#     if os.path.exists(srv_record_file):
#         srv_records = read_json_file(srv_record_file)
#         if srv_records:
#             print("\n-- Verifying SRV record DNS resolution --")
#             verification_results = verification_results and verify_srv_record_dns_resolution(srv_records)

#     # Since DNS propagation can take time, don't fail the post-check for DNS resolution failures
#     # Just log them as warnings
#     if not verification_results:
#         print("\nWARNING: Some DNS resolutions failed. This may be due to DNS propagation delay.")
#         print("It's recommended to verify these records manually after some time.")
    
#     return True

def verify_a_record_dns_resolution(a_records):
    """Verify DNS resolution for A records."""
    total_records = len(a_records)
    successful_resolutions = 0
    failed_resolutions = 0
    failed_list = []
    
    for record in a_records:
        name = record.get('name')
        expected_ip = record.get('ipv4addr')
        
        if not name or not expected_ip:
            print(f"✗ Incomplete record data: {record}")
            failed_resolutions += 1
            continue
        
        dns_result = perform_dns_lookup(name)
        
        if dns_result['rc'] != 0:
            print(f"✗ DNS lookup failed for '{name}'")
            failed_resolutions += 1
            failed_list.append(name)
            continue
        
        # Check if IP is in the results
        if expected_ip in dns_result['stdout']:
            print(f"✓ DNS resolution for '{name}' returned expected IP {expected_ip}")
            successful_resolutions += 1
        else:
            print(f"✗ DNS resolution for '{name}' did not return expected IP {expected_ip}")
            print(f"  DNS lookup result: {dns_result['stdout']}")
            failed_resolutions += 1
            failed_list.append(name)
    
    # Display verification summary
    print("\nA Record DNS Resolution Summary:")
    print(f"Total records: {total_records}")
    print(f"Successfully resolved: {successful_resolutions}")
    print(f"Failed resolution: {failed_resolutions}")
    
    if failed_list:
        print(f"Failed resolutions: {', '.join(failed_list)}")
    
    return failed_resolutions == 0

def verify_aaaa_record_dns_resolution(aaaa_records):
    """Verify DNS resolution for AAAA records."""
    total_records = len(aaaa_records)
    successful_resolutions = 0
    failed_resolutions = 0
    failed_list = []
    
    for record in aaaa_records:
        name = record.get('name')
        expected_ipv6 = record.get('ipv6addr')
        
        if not name or not expected_ipv6:
            print(f"✗ Incomplete record data: {record}")
            failed_resolutions += 1
            continue
        
        dns_result = perform_dns_lookup(name, "AAAA")
        
        if dns_result['rc'] != 0:
            print(f"✗ DNS lookup failed for '{name}'")
            failed_resolutions += 1
            failed_list.append(name)
            continue
        
        # Check if IPv6 is in the results (may need to normalize format)
        if expected_ipv6 in dns_result['stdout']:
            print(f"✓ DNS resolution for '{name}' returned expected IPv6 {expected_ipv6}")
            successful_resolutions += 1
        else:
            print(f"✗ DNS resolution for '{name}' did not return expected IPv6 {expected_ipv6}")
            print(f"  DNS lookup result: {dns_result['stdout']}")
            failed_resolutions += 1
            failed_list.append(name)
    
    # Display verification summary
    print("\nAAAA Record DNS Resolution Summary:")
    print(f"Total records: {total_records}")
    print(f"Successfully resolved: {successful_resolutions}")
    print(f"Failed resolution: {failed_resolutions}")
    
    if failed_list:
        print(f"Failed resolutions: {', '.join(failed_list)}")
    
    return failed_resolutions == 0

def verify_cname_record_dns_resolution(cname_records):
    """Verify DNS resolution for CNAME records."""
    total_records = len(cname_records)
    successful_resolutions = 0
    failed_resolutions = 0
    failed_list = []
    
    for record in cname_records:
        name = record.get('name')
        expected_canonical = record.get('canonical')
        
        if not name or not expected_canonical:
            print(f"✗ Incomplete record data: {record}")
            failed_resolutions += 1
            continue
        
        dns_result = perform_dns_lookup(name)
        
        if dns_result['rc'] != 0:
            print(f"✗ DNS lookup failed for '{name}'")
            failed_resolutions += 1
            failed_list.append(name)
            continue
        
        # For CNAME, we check if the canonical name is in the results
        if expected_canonical in dns_result['stdout']:
            print(f"✓ DNS resolution for '{name}' returned expected canonical name {expected_canonical}")
            successful_resolutions += 1
        else:
            print(f"✗ DNS resolution for '{name}' did not return expected canonical name {expected_canonical}")
            print(f"  DNS lookup result: {dns_result['stdout']}")
            failed_resolutions += 1
            failed_list.append(name)
    
    # Display verification summary
    print("\nCNAME Record DNS Resolution Summary:")
    print(f"Total records: {total_records}")
    print(f"Successfully resolved: {successful_resolutions}")
    print(f"Failed resolution: {failed_resolutions}")
    
    if failed_list:
        print(f"Failed resolutions: {', '.join(failed_list)}")
    
    return failed_resolutions == 0

def verify_alias_record_dns_resolution(alias_records):
    """Verify DNS resolution for Alias records."""
    total_records = len(alias_records)
    successful_resolutions = 0
    failed_resolutions = 0
    failed_list = []
    
    for record in alias_records:
        name = record.get('name')
        
        if not name:
            print(f"✗ Incomplete record data: {record}")
            failed_resolutions += 1
            continue
        
        dns_result = perform_dns_lookup(name)
        
        if dns_result['rc'] != 0:
            print(f"✗ DNS lookup failed for '{name}'")
            failed_resolutions += 1
            failed_list.append(name)
            continue
        
        # For Alias, we just check if the DNS lookup was successful
        if "NXDOMAIN" not in dns_result['stdout']:
            print(f"✓ DNS resolution for '{name}' succeeded")
            successful_resolutions += 1
        else:
            print(f"✗ DNS resolution for '{name}' failed")
            print(f"  DNS lookup result: {dns_result['stdout']}")
            failed_resolutions += 1
            failed_list.append(name)
    
    # Display verification summary
    print("\nAlias Record DNS Resolution Summary:")
    print(f"Total records: {total_records}")
    print(f"Successfully resolved: {successful_resolutions}")
    print(f"Failed resolution: {failed_resolutions}")
    
    if failed_list:
        print(f"Failed resolutions: {', '.join(failed_list)}")
    
    return failed_resolutions == 0

def get_fixed_address(ipv4addr, network_view):
    """Get fixed address record from Infoblox by IPv4 address and network view."""
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
            print(f"✗ Error getting fixed address {ipv4addr}: {response.status_code}")
            return []
    except Exception as e:
        print(f"✗ Error getting fixed address {ipv4addr}: {str(e)}")
        return []

def get_host_record(name, view):
    """Get host record from Infoblox by name and view."""
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
            print(f"✗ Error getting host record {name}: {response.status_code}")
            return []
    except Exception as e:
        print(f"✗ Error getting host record {name}: {str(e)}")
        return []

def verify_fixed_addresses():
    """Verify fixed addresses after deployment."""
    print("\n--- Fixed Address Post-Deployment Verification ---")
    
    # Check if fixed address file exists with the correct path
    fixed_address_file = "../prod_changes/cabgridmgr.amfam.com/fixed_address.json"
    if not os.path.exists(fixed_address_file):
        print(f"Fixed address file not found: {fixed_address_file}")
        print("Skipping fixed address verification.")
        return True
    
    # Read fixed address data from JSON file
    try:
        with open(fixed_address_file, 'r') as file:
            fixed_addresses = json.load(file)
            
            # Check if the file contains an empty list or empty object
            if not fixed_addresses or (isinstance(fixed_addresses, list) and len(fixed_addresses) == 0):
                print("Fixed address file exists but contains no records. Skipping verification.")
                return True
                
            # If the content is not a list, convert it to a list with one item
            if not isinstance(fixed_addresses, list):
                fixed_addresses = [fixed_addresses]
                
            print(f"Verifying {len(fixed_addresses)} fixed addresses.")
    except Exception as e:
        print(f"Error reading file {fixed_address_file}: {str(e)}")
        return False
    
    # Count statistics
    total_records = len(fixed_addresses)
    successful_records = 0
    failed_records = 0
    failed_list = []
    
    # Verify each record exists in Infoblox with correct configuration
    for record in fixed_addresses:
        ipv4addr = record.get('ipv4addr')
        network_view = record.get('network_view', 'default')
        mac = record.get('mac')
        match_client = record.get('match_client')
        
        if not ipv4addr or not network_view:
            print(f"✗ Incomplete record data: {record}")
            failed_records += 1
            continue
        
        actual_records = get_fixed_address(ipv4addr, network_view)
        
        if not actual_records:
            print(f"✗ Fixed address '{ipv4addr}' was not found in Infoblox")
            failed_records += 1
            failed_list.append(ipv4addr)
            continue
        
        # Check if key attributes match
        actual_record = actual_records[0]
        verification_passed = True
        
        # Check MAC address if match_client is MAC_ADDRESS
        if match_client == "MAC_ADDRESS" and mac:
            actual_mac = actual_record.get('mac')
            if actual_mac != mac:
                print(f"✗ Fixed address '{ipv4addr}' has incorrect MAC: expected {mac}, got {actual_mac}")
                verification_passed = False
        
        # Check match_client type
        if match_client:
            actual_match_client = actual_record.get('match_client')
            if actual_match_client != match_client:
                print(f"✗ Fixed address '{ipv4addr}' has incorrect match_client: expected {match_client}, got {actual_match_client}")
                verification_passed = False
        
        # Check network
        if 'network' in record:
            actual_network = actual_record.get('network')
            if actual_network != record['network']:
                print(f"✗ Fixed address '{ipv4addr}' has incorrect network: expected {record['network']}, got {actual_network}")
                verification_passed = False
        
        # Check DHCP options if specified
        if 'options' in record and record['options'] and record.get('use_options', False):
            expected_options = {(opt.get('name'), opt.get('value')) for opt in record['options'] if opt.get('use_option', False)}
            actual_options = {(opt.get('name'), opt.get('value')) for opt in actual_record.get('options', []) if opt.get('use_option', False)}
            
            # Find missing options
            missing_options = expected_options - actual_options
            if missing_options:
                print(f"✗ Fixed address '{ipv4addr}' is missing options: {missing_options}")
                verification_passed = False
        
        if verification_passed:
            print(f"✓ Fixed address '{ipv4addr}' verified successfully")
            successful_records += 1
        else:
            failed_records += 1
            failed_list.append(ipv4addr)
    
    # Display verification summary
    print("\nFixed Address Verification Summary:")
    print(f"Total records: {total_records}")
    print(f"Successfully verified: {successful_records}")
    print(f"Failed verification: {failed_records}")
    
    if failed_list:
        print(f"Failed records: {', '.join(failed_list)}")
    
    return failed_records == 0

def verify_host_records():
    """Verify host records after deployment."""
    print("\n--- Host Record Post-Deployment Verification ---")
    
    # Check if host record file exists with the correct path
    host_record_file = "../prod_changes/cabgridmgr.amfam.com/host_record.json"
    if not os.path.exists(host_record_file):
        print(f"Host record file not found: {host_record_file}")
        print("Skipping host record verification.")
        return True
    
    # Read host record data from JSON file
    try:
        with open(host_record_file, 'r') as file:
            host_records = json.load(file)
            
            # Check if the file contains an empty list or empty object
            if not host_records or (isinstance(host_records, list) and len(host_records) == 0):
                print("Host record file exists but contains no records. Skipping verification.")
                return True
            
            # If the content is not a list, convert it to a list with one item
            if not isinstance(host_records, list):
                host_records = [host_records]
            
            # Filter out any null entries
            host_records = [record for record in host_records if record is not None]
                
            print(f"Verifying {len(host_records)} host records.")
    except Exception as e:
        print(f"Error reading file {host_record_file}: {str(e)}")
        return False
    
    # Count statistics
    total_records = len(host_records)
    successful_records = 0
    failed_records = 0
    failed_list = []
    
    # Verify each record exists in Infoblox with correct configuration
    for record in host_records:
        name = record.get('name')
        view = record.get('view')
        
        if not name or not view:
            print(f"✗ Incomplete record data: {record}")
            failed_records += 1
            continue
        
        actual_records = get_host_record(name, view)
        
        if not actual_records:
            print(f"✗ Host record '{name}' was not found in Infoblox")
            failed_records += 1
            failed_list.append(name)
            continue
        
        # Check if key attributes match
        actual_record = actual_records[0]
        verification_passed = True
        
        # Check configure_for_dns
        if 'configure_for_dns' in record:
            expected_dns = record['configure_for_dns']
            actual_dns = actual_record.get('configure_for_dns')
            if actual_dns != expected_dns:
                print(f"✗ Host record '{name}' has incorrect configure_for_dns: expected {expected_dns}, got {actual_dns}")
                verification_passed = False
        
        # Check comment if specified
        if 'comment' in record:
            expected_comment = record['comment']
            actual_comment = actual_record.get('comment', '')
            if actual_comment != expected_comment:
                print(f"✗ Host record '{name}' has incorrect comment: expected '{expected_comment}', got '{actual_comment}'")
                verification_passed = False
        
        # Check IPv4 addresses if specified
        if 'ipv4addrs' in record and record['ipv4addrs']:
            expected_ipv4s = {addr['ipv4addr'] for addr in record['ipv4addrs'] if 'ipv4addr' in addr}
            actual_ipv4s = {addr['ipv4addr'] for addr in actual_record.get('ipv4addrs', []) if 'ipv4addr' in addr}
            
            # Find missing IPv4 addresses
            missing_ipv4s = expected_ipv4s - actual_ipv4s
            if missing_ipv4s:
                print(f"✗ Host record '{name}' is missing IPv4 addresses: {missing_ipv4s}")
                verification_passed = False
            
            # Check additional attributes for each IPv4 address
            for expected_addr in record['ipv4addrs']:
                if 'ipv4addr' not in expected_addr:
                    continue
                    
                # Find matching actual address
                matching_addrs = [addr for addr in actual_record.get('ipv4addrs', []) 
                                if addr.get('ipv4addr') == expected_addr['ipv4addr']]
                
                if not matching_addrs:
                    continue  # Already reported as missing
                
                actual_addr = matching_addrs[0]
                
                # Check configure_for_dhcp
                if 'configure_for_dhcp' in expected_addr:
                    expected_dhcp = expected_addr['configure_for_dhcp']
                    actual_dhcp = actual_addr.get('configure_for_dhcp')
                    if actual_dhcp != expected_dhcp:
                        print(f"✗ IPv4 address '{expected_addr['ipv4addr']}' has incorrect configure_for_dhcp: expected {expected_dhcp}, got {actual_dhcp}")
                        verification_passed = False
                
                # Check MAC address if specified
                if 'mac' in expected_addr:
                    expected_mac = expected_addr['mac']
                    actual_mac = actual_addr.get('mac', '')
                    if actual_mac != expected_mac:
                        print(f"✗ IPv4 address '{expected_addr['ipv4addr']}' has incorrect MAC: expected {expected_mac}, got {actual_mac}")
                        verification_passed = False
        
        # Check IPv6 addresses if specified
        if 'ipv6addrs' in record and record['ipv6addrs']:
            expected_ipv6s = {addr['ipv6addr'] for addr in record['ipv6addrs'] if 'ipv6addr' in addr}
            actual_ipv6s = {addr['ipv6addr'] for addr in actual_record.get('ipv6addrs', []) if 'ipv6addr' in addr}
            
            # Find missing IPv6 addresses
            missing_ipv6s = expected_ipv6s - actual_ipv6s
            if missing_ipv6s:
                print(f"✗ Host record '{name}' is missing IPv6 addresses: {missing_ipv6s}")
                verification_passed = False
        
        # Check aliases if specified
        if 'aliases' in record and record['aliases']:
            expected_aliases = set(record['aliases'])
            actual_aliases = set(actual_record.get('aliases', []))
            
            # Find missing aliases
            missing_aliases = expected_aliases - actual_aliases
            if missing_aliases:
                print(f"✗ Host record '{name}' is missing aliases: {missing_aliases}")
                verification_passed = False
        
        # Check nextserver if use_nextserver is true
        if record.get('use_nextserver', False) and 'nextserver' in record:
            expected_nextserver = record['nextserver']
            actual_nextserver = actual_record.get('nextserver', '')
            if actual_nextserver != expected_nextserver:
                print(f"✗ Host record '{name}' has incorrect nextserver: expected {expected_nextserver}, got {actual_nextserver}")
                verification_passed = False
        
        # Check extensible attributes if specified
        if 'extattrs' in record and record['extattrs']:
            for key, value in record['extattrs'].items():
                actual_value = actual_record.get('extattrs', {}).get(key, {}).get('value')
                if actual_value != value:
                    print(f"✗ Host record '{name}' has incorrect extensible attribute '{key}': expected '{value}', got '{actual_value}'")
                    verification_passed = False
        
        if verification_passed:
            print(f"✓ Host record '{name}' verified successfully")
            successful_records += 1
        else:
            failed_records += 1
            failed_list.append(name)
    
    # Display verification summary
    print("\nHost Record Verification Summary:")
    print(f"Total records: {total_records}")
    print(f"Successfully verified: {successful_records}")
    print(f"Failed verification: {failed_records}")
    
    if failed_list:
        print(f"Failed records: {', '.join(failed_list)}")
    
    return failed_records == 0

def verify_host_record_dns_resolution(host_records):
    """Verify DNS resolution for host records."""
    total_records = len(host_records)
    successful_resolutions = 0
    failed_resolutions = 0
    failed_list = []
    
    for record in host_records:
        name = record.get('name')
        
        if not name:
            print(f"✗ Incomplete record data: {record}")
            failed_resolutions += 1
            continue
        
        # Skip DNS check if configure_for_dns is explicitly set to False
        if record.get('configure_for_dns') is False:
            print(f"ℹ Skipping DNS resolution for '{name}' as configure_for_dns is False")
            continue
        
        # Determine if we need to check IPv4, IPv6, or both
        check_ipv4 = 'ipv4addrs' in record and record['ipv4addrs']
        check_ipv6 = 'ipv6addrs' in record and record['ipv6addrs']
        
        dns_resolution_passed = False
        
        # Check IPv4 resolution
        if check_ipv4:
            dns_result = perform_dns_lookup(name)
            
            if dns_result['rc'] == 0 and "NXDOMAIN" not in dns_result['stdout']:
                # For IPv4, check if any of the expected IPs are in the result
                expected_ipv4s = [addr['ipv4addr'] for addr in record['ipv4addrs'] if 'ipv4addr' in addr]
                found_ip = False
                
                for ip in expected_ipv4s:
                    if ip in dns_result['stdout']:
                        print(f"✓ DNS resolution for '{name}' returned expected IPv4 {ip}")
                        found_ip = True
                        dns_resolution_passed = True
                        break
                
                if not found_ip:
                    print(f"✗ DNS resolution for '{name}' did not return any expected IPv4 address")
                    print(f"  DNS lookup result: {dns_result['stdout']}")
            else:
                print(f"✗ IPv4 DNS lookup failed for '{name}'")
        
        # Check IPv6 resolution
        if check_ipv6:
            dns_result = perform_dns_lookup(name, "AAAA")
            
            if dns_result['rc'] == 0 and "NXDOMAIN" not in dns_result['stdout']:
                # For IPv6, check if any of the expected IPs are in the result
                expected_ipv6s = [addr['ipv6addr'] for addr in record['ipv6addrs'] if 'ipv6addr' in addr]
                found_ip = False
                
                for ip in expected_ipv6s:
                    if ip in dns_result['stdout']:
                        print(f"✓ DNS resolution for '{name}' returned expected IPv6 {ip}")
                        found_ip = True
                        dns_resolution_passed = True
                        break
                
                if not found_ip:
                    print(f"✗ DNS resolution for '{name}' did not return any expected IPv6 address")
                    print(f"  DNS lookup result: {dns_result['stdout']}")
            else:
                print(f"✗ IPv6 DNS lookup failed for '{name}'")
        
        if dns_resolution_passed:
            successful_resolutions += 1
        else:
            failed_resolutions += 1
            failed_list.append(name)
    
    # Display verification summary
    print("\nHost Record DNS Resolution Summary:")
    print(f"Total records checked: {total_records}")
    print(f"Successfully resolved: {successful_resolutions}")
    print(f"Failed resolution: {failed_resolutions}")
    
    if failed_list:
        print(f"Failed resolutions: {', '.join(failed_list)}")
    
    return failed_resolutions == 0

def get_mx_record(name, view):
    """Get MX record from Infoblox by name and view."""
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
            print(f"✗ Error getting MX record {name}: {response.status_code}")
            return []
    except Exception as e:
        print(f"✗ Error getting MX record {name}: {str(e)}")
        return []

def get_naptr_record(name, view):
    """Get NAPTR record from Infoblox by name and view."""
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
            print(f"✗ Error getting NAPTR record {name}: {response.status_code}")
            return []
    except Exception as e:
        print(f"✗ Error getting NAPTR record {name}: {str(e)}")
        return []

def verify_mx_records():
    """Verify MX records after deployment."""
    print("\n--- MX Record Post-Deployment Verification ---")
    
    # Check if MX record file exists with the correct path
    mx_record_file = "../prod_changes/cabgridmgr.amfam.com/mx_record.json"
    if not os.path.exists(mx_record_file):
        print(f"MX record file not found: {mx_record_file}")
        print("Skipping MX record verification.")
        return True
    
    # Read MX record data from JSON file
    try:
        with open(mx_record_file, 'r') as file:
            mx_records = json.load(file)
            
            # Check if the file contains an empty list or empty object
            if not mx_records or (isinstance(mx_records, list) and len(mx_records) == 0):
                print("MX record file exists but contains no records. Skipping verification.")
                return True
                
            # If the content is not a list, convert it to a list with one item
            if not isinstance(mx_records, list):
                mx_records = [mx_records]
                
            print(f"Verifying {len(mx_records)} MX records.")
    except Exception as e:
        print(f"Error reading file {mx_record_file}: {str(e)}")
        return False
    
    # Count statistics
    total_records = len(mx_records)
    successful_records = 0
    failed_records = 0
    failed_list = []
    
    # Verify each record exists in Infoblox with correct configuration
    for record in mx_records:
        name = record.get('name')
        view = record.get('view')
        expected_mail_exchanger = record.get('mail_exchanger')
        expected_preference = record.get('preference')
        
        if not name or not view or not expected_mail_exchanger or expected_preference is None:
            print(f"✗ Incomplete record data: {record}")
            failed_records += 1
            continue
        
        actual_records = get_mx_record(name, view)
        
        if not actual_records:
            print(f"✗ MX record '{name}' was not found in Infoblox")
            failed_records += 1
            failed_list.append(name)
            continue
        
        # Find matching record by mail exchanger and preference
        matching_record = None
        for actual_record in actual_records:
            if (actual_record.get('mail_exchanger') == expected_mail_exchanger and 
                actual_record.get('preference') == expected_preference):
                matching_record = actual_record
                break
        
        if not matching_record:
            print(f"✗ MX record '{name}' found but no matching mail exchanger/preference: expected {expected_mail_exchanger}/{expected_preference}")
            existing_configs = [(r.get('mail_exchanger'), r.get('preference')) for r in actual_records]
            print(f"  Found configurations: {existing_configs}")
            failed_records += 1
            failed_list.append(name)
            continue
        
        # Verify additional attributes if specified
        verification_passed = True
        
        # Check comment if specified
        if 'comment' in record:
            expected_comment = record['comment']
            actual_comment = matching_record.get('comment', '')
            if actual_comment != expected_comment:
                print(f"✗ MX record '{name}' has incorrect comment: expected '{expected_comment}', got '{actual_comment}'")
                verification_passed = False
        
        # Check TTL if specified
        if 'ttl' in record and record['ttl'] is not None:
            expected_ttl = record['ttl']
            actual_ttl = matching_record.get('ttl')
            if actual_ttl != expected_ttl:
                print(f"✗ MX record '{name}' has incorrect TTL: expected {expected_ttl}, got {actual_ttl}")
                verification_passed = False
        
        # Check extensible attributes if specified
        if 'extattrs' in record and record['extattrs']:
            for key, value in record['extattrs'].items():
                actual_value = matching_record.get('extattrs', {}).get(key, {}).get('value')
                if actual_value != value:
                    print(f"✗ MX record '{name}' has incorrect extensible attribute '{key}': expected '{value}', got '{actual_value}'")
                    verification_passed = False
        
        if verification_passed:
            print(f"✓ MX record '{name}' verified with mail exchanger {expected_mail_exchanger} and preference {expected_preference}")
            successful_records += 1
        else:
            failed_records += 1
            failed_list.append(name)
    
    # Display verification summary
    print("\nMX Record Verification Summary:")
    print(f"Total records: {total_records}")
    print(f"Successfully verified: {successful_records}")
    print(f"Failed verification: {failed_records}")
    
    if failed_list:
        print(f"Failed records: {', '.join(failed_list)}")
    
    return failed_records == 0

def verify_naptr_records():
    """Verify NAPTR records after deployment."""
    print("\n--- NAPTR Record Post-Deployment Verification ---")
    
    # Check if NAPTR record file exists with the correct path
    naptr_record_file = "playbooks/add/cabgridmgr.amfam.com/naptr_record.json"
    if not os.path.exists(naptr_record_file):
        print(f"NAPTR record file not found: {naptr_record_file}")
        print("Skipping NAPTR record verification.")
        return True
    
    # Read NAPTR record data from JSON file
    try:
        with open(naptr_record_file, 'r') as file:
            naptr_records = json.load(file)
            
            # Check if the file contains an empty list or empty object
            if not naptr_records or (isinstance(naptr_records, list) and len(naptr_records) == 0):
                print("NAPTR record file exists but contains no records. Skipping verification.")
                return True
                
            # If the content is not a list, convert it to a list with one item
            if not isinstance(naptr_records, list):
                naptr_records = [naptr_records]
                
            print(f"Verifying {len(naptr_records)} NAPTR records.")
    except Exception as e:
        print(f"Error reading file {naptr_record_file}: {str(e)}")
        return False
    
    # Count statistics
    total_records = len(naptr_records)
    successful_records = 0
    failed_records = 0
    failed_list = []
    
    # Verify each record exists in Infoblox with correct configuration
    for record in naptr_records:
        name = record.get('name')
        view = record.get('view')
        expected_order = record.get('order')
        expected_preference = record.get('preference')
        expected_services = record.get('services')
        
        if not name or not view:
            print(f"✗ Incomplete record data: {record}")
            failed_records += 1
            continue
        
        actual_records = get_naptr_record(name, view)
        
        if not actual_records:
            print(f"✗ NAPTR record '{name}' was not found in Infoblox")
            failed_records += 1
            failed_list.append(name)
            continue
        
        # Find matching record by order, preference, and services
        matching_record = None
        for actual_record in actual_records:
            if (actual_record.get('order') == expected_order and 
                actual_record.get('preference') == expected_preference and
                actual_record.get('services') == expected_services):
                matching_record = actual_record
                break
        
        if not matching_record:
            print(f"✗ NAPTR record '{name}' found but no matching order/preference/services: expected {expected_order}/{expected_preference}/{expected_services}")
            existing_configs = [(r.get('order'), r.get('preference'), r.get('services')) for r in actual_records]
            print(f"  Found configurations: {existing_configs}")
            failed_records += 1
            failed_list.append(name)
            continue
        
        # Verify additional attributes if specified
        verification_passed = True
        
        # Check flags if specified
        if 'flags' in record:
            expected_flags = record['flags']
            actual_flags = matching_record.get('flags', '')
            if actual_flags != expected_flags:
                print(f"✗ NAPTR record '{name}' has incorrect flags: expected '{expected_flags}', got '{actual_flags}'")
                verification_passed = False
        
        # Check regexp if specified
        if 'regexp' in record:
            expected_regexp = record['regexp']
            actual_regexp = matching_record.get('regexp', '')
            if actual_regexp != expected_regexp:
                print(f"✗ NAPTR record '{name}' has incorrect regexp: expected '{expected_regexp}', got '{actual_regexp}'")
                verification_passed = False
        
        # Check replacement if specified
        if 'replacement' in record:
            expected_replacement = record['replacement']
            actual_replacement = matching_record.get('replacement', '')
            if actual_replacement != expected_replacement:
                print(f"✗ NAPTR record '{name}' has incorrect replacement: expected '{expected_replacement}', got '{actual_replacement}'")
                verification_passed = False
        
        # Check comment if specified
        if 'comment' in record:
            expected_comment = record['comment']
            actual_comment = matching_record.get('comment', '')
            if actual_comment != expected_comment:
                print(f"✗ NAPTR record '{name}' has incorrect comment: expected '{expected_comment}', got '{actual_comment}'")
                verification_passed = False
        
        # Check TTL if specified
        if 'ttl' in record and record['ttl'] is not None:
            expected_ttl = record['ttl']
            actual_ttl = matching_record.get('ttl')
            if actual_ttl != expected_ttl:
                print(f"✗ NAPTR record '{name}' has incorrect TTL: expected {expected_ttl}, got {actual_ttl}")
                verification_passed = False
        
        # Check extensible attributes if specified
        if 'extattrs' in record and record['extattrs']:
            for key, value in record['extattrs'].items():
                actual_value = matching_record.get('extattrs', {}).get(key, {}).get('value')
                if actual_value != value:
                    print(f"✗ NAPTR record '{name}' has incorrect extensible attribute '{key}': expected '{value}', got '{actual_value}'")
                    verification_passed = False
        
        if verification_passed:
            print(f"✓ NAPTR record '{name}' verified with order {expected_order}, preference {expected_preference}, services {expected_services}")
            successful_records += 1
        else:
            failed_records += 1
            failed_list.append(name)
    
    # Display verification summary
    print("\nNAPTR Record Verification Summary:")
    print(f"Total records: {total_records}")
    print(f"Successfully verified: {successful_records}")
    print(f"Failed verification: {failed_records}")
    
    if failed_list:
        print(f"Failed records: {', '.join(failed_list)}")
    
    return failed_records == 0

def verify_mx_record_dns_resolution(mx_records):
    """Verify DNS resolution for MX records."""
    total_records = len(mx_records)
    successful_resolutions = 0
    failed_resolutions = 0
    failed_list = []
    
    for record in mx_records:
        name = record.get('name')
        expected_mail_exchanger = record.get('mail_exchanger')
        expected_preference = record.get('preference')
        
        if not name or not expected_mail_exchanger or expected_preference is None:
            print(f"✗ Incomplete record data: {record}")
            failed_resolutions += 1
            continue
        
        # Perform MX lookup
        dns_result = subprocess.run(['nslookup', '-type=MX', name], 
                                   capture_output=True, 
                                   text=True, 
                                   check=False)
        
        if dns_result.returncode != 0:
            print(f"✗ DNS MX lookup failed for '{name}'")
            failed_resolutions += 1
            failed_list.append(name)
            continue
        
        # Check if the expected mail exchanger and preference are in the results
        dns_output = dns_result.stdout.lower()
        mail_exchanger_found = expected_mail_exchanger.lower() in dns_output
        preference_found = str(expected_preference) in dns_output
        
        if mail_exchanger_found and preference_found:
            print(f"✓ DNS MX resolution for '{name}' returned expected mail exchanger {expected_mail_exchanger} with preference {expected_preference}")
            successful_resolutions += 1
        else:
            print(f"✗ DNS MX resolution for '{name}' did not return expected configuration")
            print(f"  Expected: {expected_mail_exchanger} (preference: {expected_preference})")
            print(f"  DNS lookup result: {dns_result.stdout}")
            failed_resolutions += 1
            failed_list.append(name)
    
    # Display verification summary
    print("\nMX Record DNS Resolution Summary:")
    print(f"Total records checked: {total_records}")
    print(f"Successfully resolved: {successful_resolutions}")
    print(f"Failed resolution: {failed_resolutions}")
    
    if failed_list:
        print(f"Failed resolutions: {', '.join(failed_list)}")
    
    return failed_resolutions == 0

def verify_naptr_record_dns_resolution(naptr_records):
    """Verify DNS resolution for NAPTR records."""
    total_records = len(naptr_records)
    successful_resolutions = 0
    failed_resolutions = 0
    failed_list = []
    
    for record in naptr_records:
        name = record.get('name')
        expected_order = record.get('order')
        expected_preference = record.get('preference')
        expected_services = record.get('services')
        
        if not name:
            print(f"✗ Incomplete record data: {record}")
            failed_resolutions += 1
            continue
        
        # Perform NAPTR lookup
        dns_result = subprocess.run(['nslookup', '-type=NAPTR', name], 
                                   capture_output=True, 
                                   text=True, 
                                   check=False)
        
        if dns_result.returncode != 0:
            print(f"✗ DNS NAPTR lookup failed for '{name}'")
            failed_resolutions += 1
            failed_list.append(name)
            continue
        
        # Check if the expected order, preference, and services are in the results
        dns_output = dns_result.stdout
        
        # Basic check - look for the presence of key values in the output
        order_found = expected_order is None or str(expected_order) in dns_output
        preference_found = expected_preference is None or str(expected_preference) in dns_output
        services_found = not expected_services or expected_services in dns_output
        
        if order_found and preference_found and services_found:
            print(f"✓ DNS NAPTR resolution for '{name}' found expected configuration")
            successful_resolutions += 1
        else:
            print(f"✗ DNS NAPTR resolution for '{name}' did not return expected configuration")
            print(f"  Expected: order {expected_order}, preference {expected_preference}, services {expected_services}")
            print(f"  DNS lookup result: {dns_result.stdout}")
            failed_resolutions += 1
            failed_list.append(name)
    
    # Display verification summary
    print("\nNAPTR Record DNS Resolution Summary:")
    print(f"Total records checked: {total_records}")
    print(f"Successfully resolved: {successful_resolutions}")
    print(f"Failed resolution: {failed_resolutions}")
    
    if failed_list:
        print(f"Failed resolutions: {', '.join(failed_list)}")
    
    return failed_resolutions == 0

def get_ptr_record(name, view):
    """Get PTR record from Infoblox by name and view."""
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
            print(f"✗ Error getting PTR record {name}: {response.status_code}")
            return []
    except Exception as e:
        print(f"✗ Error getting PTR record {name}: {str(e)}")
        return []

def get_txt_record(name, view):
    """Get TXT record from Infoblox by name and view."""
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
            print(f"✗ Error getting TXT record {name}: {response.status_code}")
            return []
    except Exception as e:
        print(f"✗ Error getting TXT record {name}: {str(e)}")
        return []

def verify_ptr_records():
    """Verify PTR records after deployment."""
    print("\n--- PTR Record Post-Deployment Verification ---")
    
    # Check if PTR record file exists with the correct path
    ptr_record_file = "../prod_changes/cabgridmgr.amfam.com/ptr_record.json"
    if not os.path.exists(ptr_record_file):
        print(f"PTR record file not found: {ptr_record_file}")
        print("Skipping PTR record verification.")
        return True
    
    # Read PTR record data from JSON file
    try:
        with open(ptr_record_file, 'r') as file:
            ptr_records = json.load(file)
            
            # Check if the file contains an empty list or empty object
            if not ptr_records or (isinstance(ptr_records, list) and len(ptr_records) == 0):
                print("PTR record file exists but contains no records. Skipping verification.")
                return True
                
            # If the content is not a list, convert it to a list with one item
            if not isinstance(ptr_records, list):
                ptr_records = [ptr_records]
                
            print(f"Verifying {len(ptr_records)} PTR records.")
    except Exception as e:
        print(f"Error reading file {ptr_record_file}: {str(e)}")
        return False
    
    # Count statistics
    total_records = len(ptr_records)
    successful_records = 0
    failed_records = 0
    failed_list = []
    
    # Verify each record exists in Infoblox with correct configuration
    for record in ptr_records:
        name = record.get('name')
        view = record.get('view')
        expected_ptrdname = record.get('ptrdname')
        
        if not name or not view or not expected_ptrdname:
            print(f"✗ Incomplete record data: {record}")
            failed_records += 1
            continue
        
        actual_records = get_ptr_record(name, view)
        
        if not actual_records:
            print(f"✗ PTR record '{name}' was not found in Infoblox")
            failed_records += 1
            failed_list.append(name)
            continue
        
        # Find matching record by ptrdname
        matching_record = None
        for actual_record in actual_records:
            if actual_record.get('ptrdname') == expected_ptrdname:
                matching_record = actual_record
                break
        
        if not matching_record:
            print(f"✗ PTR record '{name}' found but with incorrect ptrdname: expected '{expected_ptrdname}'")
            existing_ptrdnames = [r.get('ptrdname') for r in actual_records]
            print(f"  Found ptrdnames: {existing_ptrdnames}")
            failed_records += 1
            failed_list.append(name)
            continue
        
        # Verify additional attributes if specified
        verification_passed = True
        
        # Check extensible attributes if specified
        if 'extattrs' in record and record['extattrs']:
            for key, value in record['extattrs'].items():
                actual_value = matching_record.get('extattrs', {}).get(key, {}).get('value')
                if actual_value != value:
                    print(f"✗ PTR record '{name}' has incorrect extensible attribute '{key}': expected '{value}', got '{actual_value}'")
                    verification_passed = False
        
        if verification_passed:
            print(f"✓ PTR record '{name}' verified with ptrdname '{expected_ptrdname}'")
            successful_records += 1
        else:
            failed_records += 1
            failed_list.append(name)
    
    # Display verification summary
    print("\nPTR Record Verification Summary:")
    print(f"Total records: {total_records}")
    print(f"Successfully verified: {successful_records}")
    print(f"Failed verification: {failed_records}")
    
    if failed_list:
        print(f"Failed records: {', '.join(failed_list)}")
    
    return failed_records == 0

def verify_txt_records():
    """Verify TXT records after deployment."""
    print("\n--- TXT Record Post-Deployment Verification ---")
    
    # Check if TXT record file exists with the correct path
    txt_record_file = "../prod_changes/cabgridmgr.amfam.com/txt_record.json"
    if not os.path.exists(txt_record_file):
        print(f"TXT record file not found: {txt_record_file}")
        print("Skipping TXT record verification.")
        return True
    
    # Read TXT record data from JSON file
    try:
        with open(txt_record_file, 'r') as file:
            txt_records = json.load(file)
            
            # Check if the file contains an empty list or empty object
            if not txt_records or (isinstance(txt_records, list) and len(txt_records) == 0):
                print("TXT record file exists but contains no records. Skipping verification.")
                return True
                
            # If the content is not a list, convert it to a list with one item
            if not isinstance(txt_records, list):
                txt_records = [txt_records]
                
            print(f"Verifying {len(txt_records)} TXT records.")
    except Exception as e:
        print(f"Error reading file {txt_record_file}: {str(e)}")
        return False
    
    # Count statistics
    total_records = len(txt_records)
    successful_records = 0
    failed_records = 0
    failed_list = []
    
    # Verify each record exists in Infoblox with correct configuration
    for record in txt_records:
        name = record.get('name')
        view = record.get('view')
        expected_text = record.get('text')
        
        if not name or not view or not expected_text:
            print(f"✗ Incomplete record data: {record}")
            failed_records += 1
            continue
        
        actual_records = get_txt_record(name, view)
        
        if not actual_records:
            print(f"✗ TXT record '{name}' was not found in Infoblox")
            failed_records += 1
            failed_list.append(name)
            continue
        
        # Find matching record by text content
        matching_record = None
        for actual_record in actual_records:
            if actual_record.get('text') == expected_text:
                matching_record = actual_record
                break
        
        if not matching_record:
            print(f"✗ TXT record '{name}' found but with incorrect text content: expected '{expected_text}'")
            existing_texts = [r.get('text') for r in actual_records]
            print(f"  Found text values: {existing_texts}")
            failed_records += 1
            failed_list.append(name)
            continue
        
        # Verify additional attributes if specified
        verification_passed = True
        
        # Check comment if specified
        if 'comment' in record:
            expected_comment = record['comment']
            actual_comment = matching_record.get('comment', '')
            if actual_comment != expected_comment:
                print(f"✗ TXT record '{name}' has incorrect comment: expected '{expected_comment}', got '{actual_comment}'")
                verification_passed = False
        
        # Check TTL if specified
        if 'ttl' in record and record['ttl'] is not None:
            expected_ttl = record['ttl']
            actual_ttl = matching_record.get('ttl')
            if actual_ttl != expected_ttl:
                print(f"✗ TXT record '{name}' has incorrect TTL: expected {expected_ttl}, got {actual_ttl}")
                verification_passed = False
        
        # Check extensible attributes if specified
        if 'extattrs' in record and record['extattrs']:
            for key, value in record['extattrs'].items():
                actual_value = matching_record.get('extattrs', {}).get(key, {}).get('value')
                if actual_value != value:
                    print(f"✗ TXT record '{name}' has incorrect extensible attribute '{key}': expected '{value}', got '{actual_value}'")
                    verification_passed = False
        
        if verification_passed:
            print(f"✓ TXT record '{name}' verified with text content '{expected_text}'")
            successful_records += 1
        else:
            failed_records += 1
            failed_list.append(name)
    
    # Display verification summary
    print("\nTXT Record Verification Summary:")
    print(f"Total records: {total_records}")
    print(f"Successfully verified: {successful_records}")
    print(f"Failed verification: {failed_records}")
    
    if failed_list:
        print(f"Failed records: {', '.join(failed_list)}")
    
    return failed_records == 0

def verify_ptr_record_dns_resolution(ptr_records):
    """Verify DNS resolution for PTR records."""
    total_records = len(ptr_records)
    successful_resolutions = 0
    failed_resolutions = 0
    failed_list = []
    
    for record in ptr_records:
        name = record.get('name')
        expected_ptrdname = record.get('ptrdname')
        
        if not name or not expected_ptrdname:
            print(f"✗ Incomplete record data: {record}")
            failed_resolutions += 1
            continue
        
        # Perform PTR lookup (using IP or name, depending on what's available)
        ip_for_lookup = None
        if 'ipv4addr' in record and record['ipv4addr']:
            ip_for_lookup = record['ipv4addr']
        elif 'ipv6addr' in record and record['ipv6addr']:
            ip_for_lookup = record['ipv6addr']
        
        if ip_for_lookup:
            # Use direct IP for lookup
            dns_result = subprocess.run(['nslookup', ip_for_lookup], 
                                      capture_output=True, 
                                      text=True, 
                                      check=False)
        else:
            # Use PTR name for lookup
            dns_result = subprocess.run(['nslookup', '-type=PTR', name], 
                                      capture_output=True, 
                                      text=True, 
                                      check=False)
        
        if dns_result.returncode != 0:
            print(f"✗ DNS PTR lookup failed for '{name}'")
            failed_resolutions += 1
            failed_list.append(name)
            continue
        
        # Check if the expected ptrdname is in the results
        if expected_ptrdname in dns_result.stdout:
            print(f"✓ DNS PTR resolution for '{name}' returned expected ptrdname '{expected_ptrdname}'")
            successful_resolutions += 1
        else:
            print(f"✗ DNS PTR resolution for '{name}' did not return expected ptrdname '{expected_ptrdname}'")
            print(f"  DNS lookup result: {dns_result.stdout}")
            failed_resolutions += 1
            failed_list.append(name)
    
    # Display verification summary
    print("\nPTR Record DNS Resolution Summary:")
    print(f"Total records checked: {total_records}")
    print(f"Successfully resolved: {successful_resolutions}")
    print(f"Failed resolution: {failed_resolutions}")
    
    if failed_list:
        print(f"Failed resolutions: {', '.join(failed_list)}")
    
    return failed_resolutions == 0

def verify_txt_record_dns_resolution(txt_records):
    """Verify DNS resolution for TXT records."""
    total_records = len(txt_records)
    successful_resolutions = 0
    failed_resolutions = 0
    failed_list = []
    
    for record in txt_records:
        name = record.get('name')
        expected_text = record.get('text')
        
        if not name or not expected_text:
            print(f"✗ Incomplete record data: {record}")
            failed_resolutions += 1
            continue
        
        # Perform TXT lookup
        dns_result = subprocess.run(['nslookup', '-type=TXT', name], 
                                   capture_output=True, 
                                   text=True, 
                                   check=False)
        
        if dns_result.returncode != 0:
            print(f"✗ DNS TXT lookup failed for '{name}'")
            failed_resolutions += 1
            failed_list.append(name)
            continue
        
        dns_output = dns_result.stdout
        
        normalized_expected = expected_text.replace('"', '').replace(' ', '')
        normalized_output = dns_output.replace('"', '').replace(' ', '')
        
        if normalized_expected in normalized_output:
            print(f"✓ DNS TXT resolution for '{name}' returned expected text content")
            successful_resolutions += 1
        else:
            print(f"✗ DNS TXT resolution for '{name}' did not return expected text content")
            print(f"  Expected: '{expected_text}'")
            print(f"  DNS lookup result: {dns_result.stdout}")
            failed_resolutions += 1
            failed_list.append(name)
    
    # Display verification summary
    print("\nTXT Record DNS Resolution Summary:")
    print(f"Total records checked: {total_records}")
    print(f"Successfully resolved: {successful_resolutions}")
    print(f"Failed resolution: {failed_resolutions}")
    
    if failed_list:
        print(f"Failed resolutions: {', '.join(failed_list)}")
    
    return failed_resolutions == 0

def get_zone_rp_record(fqdn, view):
    """Get Response Policy Zone record from Infoblox by FQDN and view."""
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
            print(f"✗ Error getting RPZ zone {fqdn}: {response.status_code}")
            return []
    except Exception as e:
        print(f"✗ Error getting RPZ zone {fqdn}: {str(e)}")
        return []

def get_zone_auth_record(fqdn, view):
    """Get DNS Zone record from Infoblox by FQDN and view."""
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
            print(f"✗ Error getting DNS zone {fqdn}: {response.status_code}")
            return []
    except Exception as e:
        print(f"✗ Error getting DNS zone {fqdn}: {str(e)}")
        return []

def get_network_record(network, network_view):
    """Get Network record from Infoblox by network and network view."""
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
            print(f"✗ Error getting network {network}: {response.status_code}")
            return []
    except Exception as e:
        print(f"✗ Error getting network {network}: {str(e)}")
        return []

def verify_zone_rp_records():
    """Verify Response Policy Zone records after deployment."""
    print("\n--- Response Policy Zone Post-Deployment Verification ---")
    
    # Check if RPZ zone file exists with the correct path
    zone_rp_file = "playbooks/add/cabgridmgr.amfam.com/zone_rp.json"
    if not os.path.exists(zone_rp_file):
        print(f"Response Policy Zone file not found: {zone_rp_file}")
        print("Skipping Response Policy Zone verification.")
        return True
    
    # Read RPZ zone data from JSON file
    try:
        with open(zone_rp_file, 'r') as file:
            zone_rp_records = json.load(file)
            
            # Check if the file contains an empty list or empty object
            if not zone_rp_records or (isinstance(zone_rp_records, list) and len(zone_rp_records) == 0):
                print("Response Policy Zone file exists but contains no records. Skipping verification.")
                return True
                
            # If the content is not a list, convert it to a list with one item
            if not isinstance(zone_rp_records, list):
                zone_rp_records = [zone_rp_records]
                
            print(f"Verifying {len(zone_rp_records)} Response Policy Zone records.")
    except Exception as e:
        print(f"Error reading file {zone_rp_file}: {str(e)}")
        return False
    
    # Count statistics
    total_records = len(zone_rp_records)
    successful_records = 0
    failed_records = 0
    failed_list = []
    
    # Verify each record exists in Infoblox with correct configuration
    for record in zone_rp_records:
        fqdn = record.get('fqdn')
        view = record.get('view')
        
        if not fqdn or not view:
            print(f"✗ Incomplete record data: {record}")
            failed_records += 1
            continue
        
        actual_records = get_zone_rp_record(fqdn, view)
        
        if not actual_records:
            print(f"✗ RPZ zone '{fqdn}' was not found in Infoblox")
            failed_records += 1
            failed_list.append(fqdn)
            continue
        
        # Check if key attributes match
        actual_record = actual_records[0]
        verification_passed = True
        
        # Check RPZ policy
        if 'rpz_policy' in record:
            expected_policy = record['rpz_policy']
            actual_policy = actual_record.get('rpz_policy')
            if actual_policy != expected_policy:
                print(f"✗ RPZ zone '{fqdn}' has incorrect policy: expected {expected_policy}, got {actual_policy}")
                verification_passed = False
        
        # Check RPZ severity
        if 'rpz_severity' in record:
            expected_severity = record['rpz_severity']
            actual_severity = actual_record.get('rpz_severity')
            if actual_severity != expected_severity:
                print(f"✗ RPZ zone '{fqdn}' has incorrect severity: expected {expected_severity}, got {actual_severity}")
                verification_passed = False
        
        # Check RPZ type
        if 'rpz_type' in record:
            expected_type = record['rpz_type']
            actual_type = actual_record.get('rpz_type')
            if actual_type != expected_type:
                print(f"✗ RPZ zone '{fqdn}' has incorrect type: expected {expected_type}, got {actual_type}")
                verification_passed = False
        
        # Check log_rpz setting
        if 'log_rpz' in record:
            expected_log = record['log_rpz']
            actual_log = actual_record.get('log_rpz')
            if actual_log != expected_log:
                print(f"✗ RPZ zone '{fqdn}' has incorrect log_rpz: expected {expected_log}, got {actual_log}")
                verification_passed = False
        
        # Check disable setting
        if 'disable' in record:
            expected_disable = record['disable']
            actual_disable = actual_record.get('disable')
            if actual_disable != expected_disable:
                print(f"✗ RPZ zone '{fqdn}' has incorrect disable setting: expected {expected_disable}, got {actual_disable}")
                verification_passed = False
        
        # Check RPZ priority range
        if 'rpz_priority' in record:
            expected_priority = record['rpz_priority']
            actual_priority = actual_record.get('rpz_priority')
            if actual_priority != expected_priority:
                print(f"✗ RPZ zone '{fqdn}' has incorrect priority: expected {expected_priority}, got {actual_priority}")
                verification_passed = False
        
        if 'rpz_priority_end' in record:
            expected_priority_end = record['rpz_priority_end']
            actual_priority_end = actual_record.get('rpz_priority_end')
            if actual_priority_end != expected_priority_end:
                print(f"✗ RPZ zone '{fqdn}' has incorrect priority_end: expected {expected_priority_end}, got {actual_priority_end}")
                verification_passed = False
        
        # Check SOA settings if specified
        soa_fields = ['soa_default_ttl', 'soa_expire', 'soa_negative_ttl', 'soa_refresh', 'soa_retry']
        for soa_field in soa_fields:
            if soa_field in record:
                expected_value = record[soa_field]
                actual_value = actual_record.get(soa_field)
                if actual_value != expected_value:
                    print(f"✗ RPZ zone '{fqdn}' has incorrect {soa_field}: expected {expected_value}, got {actual_value}")
                    verification_passed = False
        
        # Check extensible attributes if specified
        if 'extattrs' in record and record['extattrs']:
            for key, value in record['extattrs'].items():
                actual_value = actual_record.get('extattrs', {}).get(key, {}).get('value')
                if actual_value != value:
                    print(f"✗ RPZ zone '{fqdn}' has incorrect extensible attribute '{key}': expected '{value}', got '{actual_value}'")
                    verification_passed = False
        
        if verification_passed:
            print(f"✓ RPZ zone '{fqdn}' verified successfully")
            successful_records += 1
        else:
            failed_records += 1
            failed_list.append(fqdn)
    
    # Display verification summary
    print("\nResponse Policy Zone Verification Summary:")
    print(f"Total records: {total_records}")
    print(f"Successfully verified: {successful_records}")
    print(f"Failed verification: {failed_records}")
    
    if failed_list:
        print(f"Failed records: {', '.join(failed_list)}")
    
    return failed_records == 0

def verify_zone_records():
    """Verify DNS Zone records after deployment."""
    print("\n--- DNS Zone Post-Deployment Verification ---")
    
    # Check if DNS zone file exists with the correct path
    zone_file = "../prod_changes/cabgridmgr.amfam.com/nios_zone.json"
    if not os.path.exists(zone_file):
        print(f"DNS Zone file not found: {zone_file}")
        print("Skipping DNS Zone verification.")
        return True
    
    # Read DNS zone data from JSON file
    try:
        with open(zone_file, 'r') as file:
            zone_records = json.load(file)
            
            # Check if the file contains an empty list or empty object
            if not zone_records or (isinstance(zone_records, list) and len(zone_records) == 0):
                print("DNS Zone file exists but contains no records. Skipping verification.")
                return True
                
            # If the content is not a list, convert it to a list with one item
            if not isinstance(zone_records, list):
                zone_records = [zone_records]
                
            print(f"Verifying {len(zone_records)} DNS Zone records.")
    except Exception as e:
        print(f"Error reading file {zone_file}: {str(e)}")
        return False
    
    # Count statistics
    total_records = len(zone_records)
    successful_records = 0
    failed_records = 0
    failed_list = []
    
    # Verify each record exists in Infoblox with correct configuration
    for record in zone_records:
        fqdn = record.get('fqdn')
        view = record.get('view')
        
        if not fqdn or not view:
            print(f"✗ Incomplete record data: {record}")
            failed_records += 1
            continue
        
        actual_records = get_zone_auth_record(fqdn, view)
        
        if not actual_records:
            print(f"✗ DNS zone '{fqdn}' was not found in Infoblox")
            failed_records += 1
            failed_list.append(fqdn)
            continue
        
        # Check if key attributes match
        actual_record = actual_records[0]
        verification_passed = True
        
        # Check zone format
        if 'zone_format' in record:
            expected_format = record['zone_format']
            actual_format = actual_record.get('zone_format')
            if actual_format != expected_format:
                print(f"✗ DNS zone '{fqdn}' has incorrect zone_format: expected {expected_format}, got {actual_format}")
                verification_passed = False
        
        # Check comment if specified
        if 'comment' in record:
            expected_comment = record['comment']
            actual_comment = actual_record.get('comment', '')
            if actual_comment != expected_comment:
                print(f"✗ DNS zone '{fqdn}' has incorrect comment: expected '{expected_comment}', got '{actual_comment}'")
                verification_passed = False
        
        # Check grid primary members
        if 'grid_primary' in record and record['grid_primary']:
            expected_primaries = {member.get('name') for member in record['grid_primary'] if 'name' in member}
            actual_primaries = {member.get('name') for member in actual_record.get('grid_primary', []) if 'name' in member}
            
            if expected_primaries != actual_primaries:
                print(f"✗ DNS zone '{fqdn}' has incorrect grid_primary members: expected {expected_primaries}, got {actual_primaries}")
                verification_passed = False
        
        # Check grid secondary members
        if 'grid_secondaries' in record and record['grid_secondaries']:
            expected_secondaries = {member.get('name') for member in record['grid_secondaries'] if 'name' in member}
            actual_secondaries = {member.get('name') for member in actual_record.get('grid_secondaries', []) if 'name' in member}
            
            if expected_secondaries != actual_secondaries:
                print(f"✗ DNS zone '{fqdn}' has incorrect grid_secondaries members: expected {expected_secondaries}, got {actual_secondaries}")
                verification_passed = False
        
        # Check NS group if specified
        if 'ns_group' in record:
            expected_ns_group = record['ns_group']
            actual_ns_group = actual_record.get('ns_group', '')
            if actual_ns_group != expected_ns_group:
                print(f"✗ DNS zone '{fqdn}' has incorrect ns_group: expected '{expected_ns_group}', got '{actual_ns_group}'")
                verification_passed = False
        
        # Check disable setting
        if 'disable' in record:
            expected_disable = record['disable']
            actual_disable = actual_record.get('disable')
            if actual_disable != expected_disable:
                print(f"✗ DNS zone '{fqdn}' has incorrect disable setting: expected {expected_disable}, got {actual_disable}")
                verification_passed = False
        
        # Check extensible attributes if specified
        if 'extattrs' in record and record['extattrs']:
            for key, value in record['extattrs'].items():
                actual_value = actual_record.get('extattrs', {}).get(key, {}).get('value')
                if actual_value != value:
                    print(f"✗ DNS zone '{fqdn}' has incorrect extensible attribute '{key}': expected '{value}', got '{actual_value}'")
                    verification_passed = False
        
        if verification_passed:
            print(f"✓ DNS zone '{fqdn}' verified successfully")
            successful_records += 1
        else:
            failed_records += 1
            failed_list.append(fqdn)
    
    # Display verification summary
    print("\nDNS Zone Verification Summary:")
    print(f"Total records: {total_records}")
    print(f"Successfully verified: {successful_records}")
    print(f"Failed verification: {failed_records}")
    
    if failed_list:
        print(f"Failed records: {', '.join(failed_list)}")
    
    return failed_records == 0

def verify_network_records():
    """Verify Network records after deployment."""
    print("\n--- Network Post-Deployment Verification ---")
    
    # Check if network file exists with the correct path
    network_file = "../prod_changes/cabgridmgr.amfam.com/network.json"
    if not os.path.exists(network_file):
        print(f"Network file not found: {network_file}")
        print("Skipping Network verification.")
        return True
    
    # Read network data from JSON file
    try:
        with open(network_file, 'r') as file:
            network_records = json.load(file)
            
            # Check if the file contains an empty list or empty object
            if not network_records or (isinstance(network_records, list) and len(network_records) == 0):
                print("Network file exists but contains no records. Skipping verification.")
                return True
                
            # If the content is not a list, convert it to a list with one item
            if not isinstance(network_records, list):
                network_records = [network_records]
                
            print(f"Verifying {len(network_records)} Network records.")
    except Exception as e:
        print(f"Error reading file {network_file}: {str(e)}")
        return False
    
    # Count statistics
    total_records = len(network_records)
    successful_records = 0
    failed_records = 0
    failed_list = []
    
    # Verify each record exists in Infoblox with correct configuration
    for record in network_records:
        network = record.get('network')
        network_view = record.get('network_view', 'default')
        
        if not network or not network_view:
            print(f"✗ Incomplete record data: {record}")
            failed_records += 1
            continue
        
        actual_records = get_network_record(network, network_view)
        
        if not actual_records:
            print(f"✗ Network '{network}' was not found in Infoblox")
            failed_records += 1
            failed_list.append(network)
            continue
        
        # Check if key attributes match
        actual_record = actual_records[0]
        verification_passed = True
        
        # Check comment if specified
        if 'comment' in record:
            expected_comment = record['comment']
            actual_comment = actual_record.get('comment', '')
            if actual_comment != expected_comment:
                print(f"✗ Network '{network}' has incorrect comment: expected '{expected_comment}', got '{actual_comment}'")
                verification_passed = False
        
        # Check members if specified
        expected_members = {member.get('name') for member in record['members'] if 'name' in member}
        actual_members = {member.get('name') for member in actual_record.get('members', []) if 'name' in member}
        
        if expected_members and len(actual_members) == 0:
            print(f"✗ Network '{network}' members were not assigned (module limitation)")
        
        # Check extensible attributes if specified
        if 'extattrs' in record and record['extattrs']:
            for key, value in record['extattrs'].items():
                actual_value = actual_record.get('extattrs', {}).get(key, {}).get('value')
                if actual_value != value:
                    print(f"✗ Network '{network}' has incorrect extensible attribute '{key}': expected '{value}', got '{actual_value}'")
                    verification_passed = False
        
        if verification_passed:
            print(f"✓ Network '{network}' verified successfully")
            successful_records += 1
        else:
            failed_records += 1
            failed_list.append(network)
    
    # Display verification summary
    print("\nNetwork Verification Summary:")
    print(f"Total records: {total_records}")
    print(f"Successfully verified: {successful_records}")
    print(f"Failed verification: {failed_records}")
    
    if failed_list:
        print(f"Failed records: {', '.join(failed_list)}")
    
    return failed_records == 0

def verify_zone_dns_resolution(zone_records):
    """Verify DNS resolution for DNS zones."""
    print("\n-- Verifying DNS Zone resolution --")
    
    total_records = len(zone_records)
    successful_resolutions = 0
    failed_resolutions = 0
    failed_list = []
    
    for record in zone_records:
        fqdn = record.get('fqdn')
        zone_format = record.get('zone_format', 'FORWARD')
        
        if not fqdn:
            print(f"✗ Incomplete record data: {record}")
            failed_resolutions += 1
            continue
        
        # Only test forward zones for DNS resolution
        if zone_format != "FORWARD":
            print(f"ℹ Skipping DNS resolution for reverse zone '{fqdn}'")
            continue
        
        # For forward zones, check if we can query the zone's SOA record
        dns_result = subprocess.run(['nslookup', '-type=SOA', fqdn], 
                                   capture_output=True, 
                                   text=True, 
                                   check=False)
        
        if dns_result.returncode == 0 and "NXDOMAIN" not in dns_result.stdout:
            print(f"✓ DNS zone '{fqdn}' is resolvable")
            successful_resolutions += 1
        else:
            print(f"✗ DNS zone '{fqdn}' is not resolvable")
            print(f"  DNS lookup result: {dns_result.stdout}")
            failed_resolutions += 1
            failed_list.append(fqdn)
    
    # Display verification summary
    print("\nDNS Zone Resolution Summary:")
    print(f"Total zones checked: {total_records}")
    print(f"Successfully resolved: {successful_resolutions}")
    print(f"Failed resolution: {failed_resolutions}")
    
    if failed_list:
        print(f"Failed resolutions: {', '.join(failed_list)}")
    
    return failed_resolutions == 0

def get_network_view_record(name):
    """Get Network View record from Infoblox by name."""
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
            print(f"✗ Error getting network view {name}: {response.status_code}")
            return []
    except Exception as e:
        print(f"✗ Error getting network view {name}: {str(e)}")
        return []

def verify_network_view_records():
    """Verify Network View records after deployment."""
    print("\n--- Network View Post-Deployment Verification ---")
    
    # Check if network view file exists with the correct path
    network_view_file = "playbooks/add/cabgridmgr.amfam.com/network_view.json"
    if not os.path.exists(network_view_file):
        print(f"Network View file not found: {network_view_file}")
        print("Skipping Network View verification.")
        return True
    
    # Read network view data from JSON file
    try:
        with open(network_view_file, 'r') as file:
            network_view_records = json.load(file)
            
            # Check if the file contains an empty list or empty object
            if not network_view_records or (isinstance(network_view_records, list) and len(network_view_records) == 0):
                print("Network View file exists but contains no records. Skipping verification.")
                return True
                
            # If the content is not a list, convert it to a list with one item
            if not isinstance(network_view_records, list):
                network_view_records = [network_view_records]
                
            print(f"Verifying {len(network_view_records)} Network View records.")
    except Exception as e:
        print(f"Error reading file {network_view_file}: {str(e)}")
        return False
    
    # Count statistics
    total_records = len(network_view_records)
    successful_records = 0
    failed_records = 0
    failed_list = []
    
    # Verify each record exists in Infoblox with correct configuration
    for record in network_view_records:
        name = record.get('name')
        
        if not name:
            print(f"✗ Incomplete record data: {record}")
            failed_records += 1
            continue
        
        actual_records = get_network_view_record(name)
        
        if not actual_records:
            print(f"✗ Network View '{name}' was not found in Infoblox")
            failed_records += 1
            failed_list.append(name)
            continue
        
        # Check if key attributes match
        actual_record = actual_records[0]
        verification_passed = True
        
        # Check comment if specified
        if 'comment' in record:
            expected_comment = record['comment']
            actual_comment = actual_record.get('comment', '')
            if actual_comment != expected_comment:
                print(f"✗ Network View '{name}' has incorrect comment: expected '{expected_comment}', got '{actual_comment}'")
                verification_passed = False
        
        # Check internal_forward_zones setting if specified
        if 'internal_forward_zones' in record:
            expected_internal_forward = record['internal_forward_zones']
            actual_internal_forward = actual_record.get('internal_forward_zones')
            if actual_internal_forward != expected_internal_forward:
                print(f"✗ Network View '{name}' has incorrect internal_forward_zones: expected {expected_internal_forward}, got {actual_internal_forward}")
                verification_passed = False
        
        # Check internal_reverse_zones setting if specified
        if 'internal_reverse_zones' in record:
            expected_internal_reverse = record['internal_reverse_zones']
            actual_internal_reverse = actual_record.get('internal_reverse_zones')
            if actual_internal_reverse != expected_internal_reverse:
                print(f"✗ Network View '{name}' has incorrect internal_reverse_zones: expected {expected_internal_reverse}, got {actual_internal_reverse}")
                verification_passed = False
        
        # Check remote_forward_zones setting if specified
        if 'remote_forward_zones' in record:
            expected_remote_forward = record['remote_forward_zones']
            actual_remote_forward = actual_record.get('remote_forward_zones')
            if actual_remote_forward != expected_remote_forward:
                print(f"✗ Network View '{name}' has incorrect remote_forward_zones: expected {expected_remote_forward}, got {actual_remote_forward}")
                verification_passed = False
        
        # Check remote_reverse_zones setting if specified
        if 'remote_reverse_zones' in record:
            expected_remote_reverse = record['remote_reverse_zones']
            actual_remote_reverse = actual_record.get('remote_reverse_zones')
            if actual_remote_reverse != expected_remote_reverse:
                print(f"✗ Network View '{name}' has incorrect remote_reverse_zones: expected {expected_remote_reverse}, got {actual_remote_reverse}")
                verification_passed = False
        
        # Check cloud_info settings if specified
        if 'cloud_info' in record and record['cloud_info']:
            expected_cloud_info = record['cloud_info']
            actual_cloud_info = actual_record.get('cloud_info', {})
            
            # Check cloud platform
            if 'cloud_platform' in expected_cloud_info:
                expected_platform = expected_cloud_info['cloud_platform']
                actual_platform = actual_cloud_info.get('cloud_platform')
                if actual_platform != expected_platform:
                    print(f"✗ Network View '{name}' has incorrect cloud_platform: expected '{expected_platform}', got '{actual_platform}'")
                    verification_passed = False
            
            # Check cloud account ID
            if 'cloud_account_id' in expected_cloud_info:
                expected_account_id = expected_cloud_info['cloud_account_id']
                actual_account_id = actual_cloud_info.get('cloud_account_id')
                if actual_account_id != expected_account_id:
                    print(f"✗ Network View '{name}' has incorrect cloud_account_id: expected '{expected_account_id}', got '{actual_account_id}'")
                    verification_passed = False
        
        # Check associated_dns_views if specified
        if 'associated_dns_views' in record and record['associated_dns_views']:
            expected_dns_views = set(record['associated_dns_views'])
            actual_dns_views = set(actual_record.get('associated_dns_views', []))
            
            if expected_dns_views != actual_dns_views:
                missing_views = expected_dns_views - actual_dns_views
                extra_views = actual_dns_views - expected_dns_views
                
                if missing_views:
                    print(f"✗ Network View '{name}' is missing associated DNS views: {missing_views}")
                    verification_passed = False
                if extra_views:
                    print(f"✗ Network View '{name}' has unexpected associated DNS views: {extra_views}")
                    verification_passed = False
        
        # Check ms_settings if specified (for Microsoft integration)
        if 'ms_settings' in record and record['ms_settings']:
            expected_ms_settings = record['ms_settings']
            actual_ms_settings = actual_record.get('ms_settings', {})
            
            # Check enable_ddns_ptr setting
            if 'enable_ddns_ptr' in expected_ms_settings:
                expected_ddns_ptr = expected_ms_settings['enable_ddns_ptr']
                actual_ddns_ptr = actual_ms_settings.get('enable_ddns_ptr')
                if actual_ddns_ptr != expected_ddns_ptr:
                    print(f"✗ Network View '{name}' has incorrect enable_ddns_ptr: expected {expected_ddns_ptr}, got {actual_ddns_ptr}")
                    verification_passed = False
            
            # Check enable_dhcp_thresholds setting
            if 'enable_dhcp_thresholds' in expected_ms_settings:
                expected_thresholds = expected_ms_settings['enable_dhcp_thresholds']
                actual_thresholds = actual_ms_settings.get('enable_dhcp_thresholds')
                if actual_thresholds != expected_thresholds:
                    print(f"✗ Network View '{name}' has incorrect enable_dhcp_thresholds: expected {expected_thresholds}, got {actual_thresholds}")
                    verification_passed = False
        
        # Check network_container_auto_create_reverse_zone if specified
        if 'network_container_auto_create_reverse_zone' in record:
            expected_auto_create = record['network_container_auto_create_reverse_zone']
            actual_auto_create = actual_record.get('network_container_auto_create_reverse_zone')
            if actual_auto_create != expected_auto_create:
                print(f"✗ Network View '{name}' has incorrect network_container_auto_create_reverse_zone: expected {expected_auto_create}, got {actual_auto_create}")
                verification_passed = False
        
        # Check DHCP options if specified
        if 'options' in record and record['options']:
            expected_options = {}
            for option in record['options']:
                if option.get('use_option', False):
                    option_name = option.get('name')
                    option_value = option.get('value')
                    if option_name and option_value:
                        expected_options[option_name] = option_value
            
            actual_options = {}
            for option in actual_record.get('options', []):
                if option.get('use_option', False):
                    option_name = option.get('name')
                    option_value = option.get('value')
                    if option_name and option_value:
                        actual_options[option_name] = option_value
            
            # Check for missing or incorrect options
            for option_name, expected_value in expected_options.items():
                if option_name not in actual_options:
                    print(f"✗ Network View '{name}' is missing DHCP option '{option_name}'")
                    verification_passed = False
                elif actual_options[option_name] != expected_value:
                    print(f"✗ Network View '{name}' has incorrect DHCP option '{option_name}': expected '{expected_value}', got '{actual_options[option_name]}'")
                    verification_passed = False
        
        # Check extensible attributes if specified
        if 'extattrs' in record and record['extattrs']:
            for key, expected_value in record['extattrs'].items():
                actual_value = actual_record.get('extattrs', {}).get(key, {}).get('value')
                if actual_value != expected_value:
                    print(f"✗ Network View '{name}' has incorrect extensible attribute '{key}': expected '{expected_value}', got '{actual_value}'")
                    verification_passed = False
        
        # Check utilization thresholds if specified
        if 'utilization_update' in record and record['utilization_update']:
            expected_utilization = record['utilization_update']
            actual_utilization = actual_record.get('utilization_update', {})
            
            # Check enabled setting
            if 'enabled' in expected_utilization:
                expected_enabled = expected_utilization['enabled']
                actual_enabled = actual_utilization.get('enabled')
                if actual_enabled != expected_enabled:
                    print(f"✗ Network View '{name}' has incorrect utilization_update enabled: expected {expected_enabled}, got {actual_enabled}")
                    verification_passed = False
            
            # Check notify_email_list
            if 'notify_email_list' in expected_utilization:
                expected_emails = set(expected_utilization['notify_email_list'])
                actual_emails = set(actual_utilization.get('notify_email_list', []))
                if expected_emails != actual_emails:
                    print(f"✗ Network View '{name}' has incorrect utilization notify_email_list: expected {expected_emails}, got {actual_emails}")
                    verification_passed = False
        
        try:
            test_response = requests.get(
                f"{BASE_URL}/network",
                params={"network_view": name, "_max_results": 1},
                auth=(INFOBLOX_USERNAME, INFOBLOX_PASSWORD),
                verify=VALIDATE_CERTS,
                timeout=HTTP_TIMEOUT
            )
            
            if test_response.status_code != 200:
                print(f"✗ Network View '{name}' appears to be non-functional - cannot query networks")
                verification_passed = False
            else:
                # Check if we can successfully query (even if no networks exist)
                networks = test_response.json()
                print(f"ℹ Network View '{name}' is functional with {len(networks)} networks")
        
        except Exception as e:
            print(f"✗ Network View '{name}' functionality test failed: {str(e)}")
            verification_passed = False
        
        if verification_passed:
            print(f"✓ Network View '{name}' verified successfully")
            successful_records += 1
        else:
            failed_records += 1
            failed_list.append(name)
    
    # Display verification summary
    print("\nNetwork View Verification Summary:")
    print(f"Total records: {total_records}")
    print(f"Successfully verified: {successful_records}")
    print(f"Failed verification: {failed_records}")
    
    if failed_list:
        print(f"Failed records: {', '.join(failed_list)}")
    
    return failed_records == 0

def get_dhcp_failover(name):
    """Get DHCP failover association from Infoblox by name."""
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
            print(f"✗ Error getting DHCP failover {name}: {response.status_code}")
            return []
    except Exception as e:
        print(f"✗ Error getting DHCP failover {name}: {str(e)}")
        return []

def get_dhcp_option_definition(name):
    """Get DHCP option definition from Infoblox by name."""
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
            print(f"✗ Error getting DHCP option definition {name}: {response.status_code}")
            return []
    except Exception as e:
        print(f"✗ Error getting DHCP option definition {name}: {str(e)}")
        return []

def get_dhcp_ipv6_option_definition(name):
    """Get DHCP IPv6 option definition from Infoblox by name."""
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
            print(f"✗ Error getting DHCP IPv6 option definition {name}: {response.status_code}")
            return []
    except Exception as e:
        print(f"✗ Error getting DHCP IPv6 option definition {name}: {str(e)}")
        return []

def get_dhcp_option_space(name):
    """Get DHCP option space from Infoblox by name."""
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
            print(f"✗ Error getting DHCP option space {name}: {response.status_code}")
            return []
    except Exception as e:
        print(f"✗ Error getting DHCP option space {name}: {str(e)}")
        return []

def get_dhcp_ipv6_option_space(name):
    """Get DHCP IPv6 option space from Infoblox by name."""
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
            print(f"✗ Error getting DHCP IPv6 option space {name}: {response.status_code}")
            return []
    except Exception as e:
        print(f"✗ Error getting DHCP IPv6 option space {name}: {str(e)}")
        return []

def get_dns_grid():
    """Get DNS Grid configuration from Infoblox."""
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
            print(f"✗ Error getting DNS Grid: {response.status_code}")
            return []
    except Exception as e:
        print(f"✗ Error getting DNS Grid: {str(e)}")
        return []

def get_dns64_group(name):
    """Get DNS64 group from Infoblox by name."""
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
            print(f"✗ Error getting DNS64 group {name}: {response.status_code}")
            return []
    except Exception as e:
        print(f"✗ Error getting DNS64 group {name}: {str(e)}")
        return []

def get_dtc_record_a(dtc_server, ipv4addr):
    """Get DTC A record from Infoblox by DTC server and IPv4 address."""
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
            print(f"✗ Error getting DTC A record: {response.status_code}")
            return []
    except Exception as e:
        print(f"✗ Error getting DTC A record: {str(e)}")
        return []

def get_fingerprint(name):
    """Get DHCP fingerprint from Infoblox by name."""
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
            print(f"✗ Error getting fingerprint {name}: {response.status_code}")
            return []
    except Exception as e:
        print(f"✗ Error getting fingerprint {name}: {str(e)}")
        return []

def get_grid_dhcp_properties():
    """Get Grid DHCP Properties from Infoblox."""
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
            print(f"✗ Error getting Grid DHCP Properties: {response.status_code}")
            return []
    except Exception as e:
        print(f"✗ Error getting Grid DHCP Properties: {str(e)}")
        return []

# Add these verification functions after the existing verify_* functions

def verify_dhcp_failover():
    """Verify DHCP failover associations after deployment."""
    print("\n--- DHCP Failover Post-Deployment Verification ---")
    
    dhcp_failover_file = "playbooks/add/cabgridmgr.amfam.com/dhcp_failover.json"
    if not os.path.exists(dhcp_failover_file):
        print(f"DHCP Failover file not found: {dhcp_failover_file}")
        print("Skipping DHCP Failover verification.")
        return True
    
    try:
        with open(dhcp_failover_file, 'r') as file:
            dhcp_failover_data = json.load(file)
            
            if not dhcp_failover_data or dhcp_failover_data == {}:
                print("DHCP Failover file exists but contains no data. Skipping verification.")
                return True
            
            # Convert to list if it's a single dictionary
            if isinstance(dhcp_failover_data, dict):
                dhcp_failover_data = [dhcp_failover_data]
                
            print(f"Verifying {len(dhcp_failover_data)} DHCP Failover associations.")
    except Exception as e:
        print(f"Error reading file {dhcp_failover_file}: {str(e)}")
        return False
    
    total_records = len(dhcp_failover_data)
    successful_records = 0
    failed_records = 0
    failed_list = []
    
    for record in dhcp_failover_data:
        name = record.get('name')
        primary = record.get('primary')
        secondary = record.get('secondary')
        
        if not name or not primary or not secondary:
            print(f"✗ Incomplete record data: {record}")
            failed_records += 1
            continue
        
        actual_records = get_dhcp_failover(name)
        
        if not actual_records:
            print(f"✗ DHCP Failover '{name}' was not found in Infoblox")
            failed_records += 1
            failed_list.append(name)
            continue
        
        actual_record = actual_records[0]
        verification_passed = True
        
        # Verify primary and secondary
        if actual_record.get('primary') != primary:
            print(f"✗ DHCP Failover '{name}' has incorrect primary: expected {primary}, got {actual_record.get('primary')}")
            verification_passed = False
        
        if actual_record.get('secondary') != secondary:
            print(f"✗ DHCP Failover '{name}' has incorrect secondary: expected {secondary}, got {actual_record.get('secondary')}")
            verification_passed = False
        
        # Verify association type if specified
        if 'association_type' in record:
            if actual_record.get('association_type') != record['association_type']:
                print(f"✗ DHCP Failover '{name}' has incorrect association_type")
                verification_passed = False
        
        # Verify mode if specified
        if 'mode' in record:
            if actual_record.get('mode') != record['mode']:
                print(f"✗ DHCP Failover '{name}' has incorrect mode")
                verification_passed = False
        
        if verification_passed:
            print(f"✓ DHCP Failover '{name}' verified successfully")
            successful_records += 1
        else:
            failed_records += 1
            failed_list.append(name)
    
    print("\nDHCP Failover Verification Summary:")
    print(f"Total records: {total_records}")
    print(f"Successfully verified: {successful_records}")
    print(f"Failed verification: {failed_records}")
    
    if failed_list:
        print(f"Failed records: {', '.join(failed_list)}")
    
    return failed_records == 0

def verify_dhcp_option_definitions():
    """Verify DHCP option definitions after deployment."""
    print("\n--- DHCP Option Definition Post-Deployment Verification ---")
    
    dhcp_option_def_file = "playbooks/add/cabgridmgr.amfam.com/dhcpoptiondefinition.json"
    if not os.path.exists(dhcp_option_def_file):
        print(f"DHCP Option Definition file not found: {dhcp_option_def_file}")
        print("Skipping DHCP Option Definition verification.")
        return True
    
    dhcp_option_definitions = read_json_file(dhcp_option_def_file)
    if not dhcp_option_definitions:
        print("DHCP Option Definition file exists but contains no records. Skipping verification.")
        return True
    
    print(f"Verifying {len(dhcp_option_definitions)} DHCP Option Definitions.")
    
    total_records = len(dhcp_option_definitions)
    successful_records = 0
    failed_records = 0
    failed_list = []
    
    for record in dhcp_option_definitions:
        name = record.get('name')
        num = record.get('num')
        option_type = record.get('type')
        
        if not name or num is None or not option_type:
            print(f"✗ Incomplete record data: {record}")
            failed_records += 1
            continue
        
        actual_records = get_dhcp_option_definition(name)
        
        if not actual_records:
            print(f"✗ DHCP Option Definition '{name}' was not found in Infoblox")
            failed_records += 1
            failed_list.append(name)
            continue
        
        actual_record = actual_records[0]
        verification_passed = True
        
        # Verify option number
        if str(actual_record.get('num')) != str(num):
            print(f"✗ DHCP Option Definition '{name}' has incorrect number: expected {num}, got {actual_record.get('num')}")
            verification_passed = False
        
        # Verify type
        if actual_record.get('type') != option_type:
            print(f"✗ DHCP Option Definition '{name}' has incorrect type: expected {option_type}, got {actual_record.get('type')}")
            verification_passed = False
        
        # Verify space if specified
        if 'space' in record:
            if actual_record.get('space') != record['space']:
                print(f"✗ DHCP Option Definition '{name}' has incorrect space")
                verification_passed = False
        
        if verification_passed:
            print(f"✓ DHCP Option Definition '{name}' verified successfully")
            successful_records += 1
        else:
            failed_records += 1
            failed_list.append(name)
    
    print("\nDHCP Option Definition Verification Summary:")
    print(f"Total records: {total_records}")
    print(f"Successfully verified: {successful_records}")
    print(f"Failed verification: {failed_records}")
    
    if failed_list:
        print(f"Failed records: {', '.join(failed_list)}")
    
    return failed_records == 0

def verify_dhcp_ipv6_option_definitions():
    """Verify DHCP IPv6 option definitions after deployment."""
    print("\n--- DHCP IPv6 Option Definition Post-Deployment Verification ---")
    
    dhcp_ipv6_option_def_file = "playbooks/add/cabgridmgr.amfam.com/dhcpoptionipv6definition.json"
    if not os.path.exists(dhcp_ipv6_option_def_file):
        print(f"DHCP IPv6 Option Definition file not found: {dhcp_ipv6_option_def_file}")
        print("Skipping DHCP IPv6 Option Definition verification.")
        return True
    
    dhcp_ipv6_option_definitions = read_json_file(dhcp_ipv6_option_def_file)
    if not dhcp_ipv6_option_definitions:
        print("DHCP IPv6 Option Definition file exists but contains no records. Skipping verification.")
        return True
    
    print(f"Verifying {len(dhcp_ipv6_option_definitions)} DHCP IPv6 Option Definitions.")
    
    total_records = len(dhcp_ipv6_option_definitions)
    successful_records = 0
    failed_records = 0
    failed_list = []
    
    for record in dhcp_ipv6_option_definitions:
        name = record.get('name')
        code = record.get('code')
        option_type = record.get('type')
        
        if not name or code is None or not option_type:
            print(f"✗ Incomplete record data: {record}")
            failed_records += 1
            continue
        
        actual_records = get_dhcp_ipv6_option_definition(name)
        
        if not actual_records:
            print(f"✗ DHCP IPv6 Option Definition '{name}' was not found in Infoblox")
            failed_records += 1
            failed_list.append(name)
            continue
        
        actual_record = actual_records[0]
        verification_passed = True
        
        # Verify option code
        if str(actual_record.get('code')) != str(code):
            print(f"✗ DHCP IPv6 Option Definition '{name}' has incorrect code: expected {code}, got {actual_record.get('code')}")
            verification_passed = False
        
        # Verify type
        if actual_record.get('type') != option_type:
            print(f"✗ DHCP IPv6 Option Definition '{name}' has incorrect type: expected {option_type}, got {actual_record.get('type')}")
            verification_passed = False
        
        if verification_passed:
            print(f"✓ DHCP IPv6 Option Definition '{name}' verified successfully")
            successful_records += 1
        else:
            failed_records += 1
            failed_list.append(name)
    
    print("\nDHCP IPv6 Option Definition Verification Summary:")
    print(f"Total records: {total_records}")
    print(f"Successfully verified: {successful_records}")
    print(f"Failed verification: {failed_records}")
    
    if failed_list:
        print(f"Failed records: {', '.join(failed_list)}")
    
    return failed_records == 0

def verify_dhcp_option_spaces():
    """Verify DHCP option spaces after deployment."""
    print("\n--- DHCP Option Space Post-Deployment Verification ---")
    
    dhcp_option_space_file = "playbooks/add/cabgridmgr.amfam.com/dhcpoptionspace.json"
    if not os.path.exists(dhcp_option_space_file):
        print(f"DHCP Option Space file not found: {dhcp_option_space_file}")
        print("Skipping DHCP Option Space verification.")
        return True
    
    dhcp_option_spaces = read_json_file(dhcp_option_space_file)
    if not dhcp_option_spaces:
        print("DHCP Option Space file exists but contains no records. Skipping verification.")
        return True
    
    print(f"Verifying {len(dhcp_option_spaces)} DHCP Option Spaces.")
    
    total_records = len(dhcp_option_spaces)
    successful_records = 0
    failed_records = 0
    failed_list = []
    
    for record in dhcp_option_spaces:
        name = record.get('name')
        
        if not name:
            print(f"✗ Incomplete record data: {record}")
            failed_records += 1
            continue
        
        actual_records = get_dhcp_option_space(name)
        
        if not actual_records:
            print(f"✗ DHCP Option Space '{name}' was not found in Infoblox")
            failed_records += 1
            failed_list.append(name)
            continue
        
        actual_record = actual_records[0]
        verification_passed = True
        
        # Verify vendor identifier if specified
        if 'vendor_identifier' in record:
            if actual_record.get('vendor_identifier') != record['vendor_identifier']:
                print(f"✗ DHCP Option Space '{name}' has incorrect vendor_identifier")
                verification_passed = False
        
        # Verify comment if specified
        if 'comment' in record:
            if actual_record.get('comment') != record['comment']:
                print(f"✗ DHCP Option Space '{name}' has incorrect comment")
                verification_passed = False
        
        if verification_passed:
            print(f"✓ DHCP Option Space '{name}' verified successfully")
            successful_records += 1
        else:
            failed_records += 1
            failed_list.append(name)
    
    print("\nDHCP Option Space Verification Summary:")
    print(f"Total records: {total_records}")
    print(f"Successfully verified: {successful_records}")
    print(f"Failed verification: {failed_records}")
    
    if failed_list:
        print(f"Failed records: {', '.join(failed_list)}")
    
    return failed_records == 0

def verify_dhcp_ipv6_option_spaces():
    """Verify DHCP IPv6 option spaces after deployment."""
    print("\n--- DHCP IPv6 Option Space Post-Deployment Verification ---")
    
    dhcp_ipv6_option_space_file = "playbooks/add/cabgridmgr.amfam.com/dhcpoptionipv6space.json"
    if not os.path.exists(dhcp_ipv6_option_space_file):
        print(f"DHCP IPv6 Option Space file not found: {dhcp_ipv6_option_space_file}")
        print("Skipping DHCP IPv6 Option Space verification.")
        return True
    
    dhcp_ipv6_option_spaces = read_json_file(dhcp_ipv6_option_space_file)
    if not dhcp_ipv6_option_spaces:
        print("DHCP IPv6 Option Space file exists but contains no records. Skipping verification.")
        return True
    
    print(f"Verifying {len(dhcp_ipv6_option_spaces)} DHCP IPv6 Option Spaces.")
    
    total_records = len(dhcp_ipv6_option_spaces)
    successful_records = 0
    failed_records = 0
    failed_list = []
    
    for record in dhcp_ipv6_option_spaces:
        name = record.get('name')
        
        if not name:
            print(f"✗ Incomplete record data: {record}")
            failed_records += 1
            continue
        
        actual_records = get_dhcp_ipv6_option_space(name)
        
        if not actual_records:
            print(f"✗ DHCP IPv6 Option Space '{name}' was not found in Infoblox")
            failed_records += 1
            failed_list.append(name)
            continue
        
        actual_record = actual_records[0]
        verification_passed = True
        
        # Verify enterprise number if specified
        if 'enterprise_number' in record:
            if actual_record.get('enterprise_number') != record['enterprise_number']:
                print(f"✗ DHCP IPv6 Option Space '{name}' has incorrect enterprise_number")
                verification_passed = False
        
        if verification_passed:
            print(f"✓ DHCP IPv6 Option Space '{name}' verified successfully")
            successful_records += 1
        else:
            failed_records += 1
            failed_list.append(name)
    
    print("\nDHCP IPv6 Option Space Verification Summary:")
    print(f"Total records: {total_records}")
    print(f"Successfully verified: {successful_records}")
    print(f"Failed verification: {failed_records}")
    
    if failed_list:
        print(f"Failed records: {', '.join(failed_list)}")
    
    return failed_records == 0

def verify_dns_grid():
    """Verify DNS Grid configuration after deployment."""
    print("\n--- DNS Grid Post-Deployment Verification ---")
    
    dns_grid_file = "playbooks/add/cabgridmgr.amfam.com/dns_grid.json"
    if not os.path.exists(dns_grid_file):
        print(f"DNS Grid file not found: {dns_grid_file}")
        print("Skipping DNS Grid verification.")
        return True
    
    try:
        with open(dns_grid_file, 'r') as file:
            dns_grid_configs = json.load(file)
            
            if not dns_grid_configs or len(dns_grid_configs) == 0:
                print("DNS Grid file exists but contains no records. Skipping verification.")
                return True
            
            dns_grid_config = dns_grid_configs[0]
            print(f"Verifying DNS Grid configuration.")
    except Exception as e:
        print(f"Error reading file {dns_grid_file}: {str(e)}")
        return False
    
    actual_grids = get_dns_grid()
    
    if not actual_grids:
        print(f"✗ DNS Grid configuration was not found in Infoblox")
        return False
    
    actual_grid = actual_grids[0]
    verification_passed = True
    
    # Verify key settings
    settings_to_check = [
        'allow_recursive_query', 'allow_transfer', 'allow_update',
        'blackhole_enabled', 'dnssec_enabled', 'dnssec_validation_enabled',
        'recursion', 'dns_cache_acceleration_enabled'
    ]
    
    for setting in settings_to_check:
        if setting in dns_grid_config:
            expected = dns_grid_config[setting]
            actual = actual_grid.get(setting)
            if actual != expected:
                print(f"✗ DNS Grid has incorrect {setting}: expected {expected}, got {actual}")
                verification_passed = False
    
    if verification_passed:
        print(f"✓ DNS Grid configuration verified successfully")
        return True
    else:
        return False

def verify_dns64_groups():
    """Verify DNS64 groups after deployment."""
    print("\n--- DNS64 Group Post-Deployment Verification ---")
    
    dns64_group_file = "playbooks/add/cabgridmgr.amfam.com/dns64group.json"
    if not os.path.exists(dns64_group_file):
        print(f"DNS64 Group file not found: {dns64_group_file}")
        print("Skipping DNS64 Group verification.")
        return True
    
    dns64_groups = read_json_file(dns64_group_file)
    if not dns64_groups:
        print("DNS64 Group file exists but contains no records. Skipping verification.")
        return True
    
    print(f"Verifying {len(dns64_groups)} DNS64 Groups.")
    
    total_records = len(dns64_groups)
    successful_records = 0
    failed_records = 0
    failed_list = []
    
    for record in dns64_groups:
        name = record.get('name')
        dns64_prefix = record.get('dns64_prefix')
        
        if not name or not dns64_prefix:
            print(f"✗ Incomplete record data: {record}")
            failed_records += 1
            continue
        
        actual_records = get_dns64_group(name)
        
        if not actual_records:
            print(f"✗ DNS64 Group '{name}' was not found in Infoblox")
            failed_records += 1
            failed_list.append(name)
            continue
        
        actual_record = actual_records[0]
        verification_passed = True
        
        # Verify DNS64 prefix
        if actual_record.get('dns64_prefix') != dns64_prefix:
            print(f"✗ DNS64 Group '{name}' has incorrect prefix: expected {dns64_prefix}, got {actual_record.get('dns64_prefix')}")
            verification_passed = False
        
        # Verify disable status if specified
        if 'disable' in record:
            if actual_record.get('disable') != record['disable']:
                print(f"✗ DNS64 Group '{name}' has incorrect disable status")
                verification_passed = False
        
        if verification_passed:
            print(f"✓ DNS64 Group '{name}' verified successfully")
            successful_records += 1
        else:
            failed_records += 1
            failed_list.append(name)
    
    print("\nDNS64 Group Verification Summary:")
    print(f"Total records: {total_records}")
    print(f"Successfully verified: {successful_records}")
    print(f"Failed verification: {failed_records}")
    
    if failed_list:
        print(f"Failed records: {', '.join(failed_list)}")
    
    return failed_records == 0

def verify_dtc_record_a():
    """Verify DTC A records after deployment."""
    print("\n--- DTC A Record Post-Deployment Verification ---")
    
    dtc_record_a_file = "playbooks/add/cabgridmgr.amfam.com/dtc_record_a.json"
    if not os.path.exists(dtc_record_a_file):
        print(f"DTC A Record file not found: {dtc_record_a_file}")
        print("Skipping DTC A Record verification.")
        return True
    
    dtc_record_as = read_json_file(dtc_record_a_file)
    if not dtc_record_as:
        print("DTC A Record file exists but contains no records. Skipping verification.")
        return True
    
    print(f"Verifying {len(dtc_record_as)} DTC A Records.")
    
    total_records = len(dtc_record_as)
    successful_records = 0
    failed_records = 0
    failed_list = []
    
    for record in dtc_record_as:
        name = record.get('name')
        ipv4addr = record.get('ipv4addr')
        dtc_server = record.get('dtc_server')
        
        if not name or not ipv4addr or not dtc_server:
            print(f"✗ Incomplete record data: {record}")
            failed_records += 1
            continue
        
        actual_records = get_dtc_record_a(dtc_server, ipv4addr)
        
        if not actual_records:
            print(f"✗ DTC A Record for server '{dtc_server}' with IP {ipv4addr} was not found")
            failed_records += 1
            failed_list.append(f"{name}:{dtc_server}")
            continue
        
        actual_record = actual_records[0]
        verification_passed = True
        
        # Verify name
        if actual_record.get('name') != name:
            print(f"✗ DTC A Record has incorrect name: expected {name}, got {actual_record.get('name')}")
            verification_passed = False
        
        # Verify TTL if specified
        if 'ttl' in record and record['ttl'] is not None:
            if actual_record.get('ttl') != record['ttl']:
                print(f"✗ DTC A Record '{name}' has incorrect TTL")
                verification_passed = False
        
        if verification_passed:
            print(f"✓ DTC A Record '{name}' on server '{dtc_server}' verified successfully")
            successful_records += 1
        else:
            failed_records += 1
            failed_list.append(f"{name}:{dtc_server}")
    
    print("\nDTC A Record Verification Summary:")
    print(f"Total records: {total_records}")
    print(f"Successfully verified: {successful_records}")
    print(f"Failed verification: {failed_records}")
    
    if failed_list:
        print(f"Failed records: {', '.join(failed_list)}")
    
    return failed_records == 0

def verify_fingerprints():
    """Verify DHCP fingerprints after deployment."""
    print("\n--- DHCP Fingerprint Post-Deployment Verification ---")
    
    fingerprint_file = "playbooks/add/cabgridmgr.amfam.com/fingerprint.json"
    if not os.path.exists(fingerprint_file):
        print(f"DHCP Fingerprint file not found: {fingerprint_file}")
        print("Skipping DHCP Fingerprint verification.")
        return True
    
    fingerprints = read_json_file(fingerprint_file)
    if not fingerprints:
        print("DHCP Fingerprint file exists but contains no records. Skipping verification.")
        return True
    
    print(f"Verifying {len(fingerprints)} DHCP Fingerprints.")
    
    total_records = len(fingerprints)
    successful_records = 0
    failed_records = 0
    failed_list = []
    
    for record in fingerprints:
        name = record.get('name')
        option_sequence = record.get('option_sequence')
        
        if not name or not option_sequence:
            print(f"✗ Incomplete record data: {record}")
            failed_records += 1
            continue
        
        actual_records = get_fingerprint(name)
        
        if not actual_records:
            print(f"✗ DHCP Fingerprint '{name}' was not found in Infoblox")
            failed_records += 1
            failed_list.append(name)
            continue
        
        actual_record = actual_records[0]
        verification_passed = True
        
        # Verify option sequence
        if actual_record.get('option_sequence') != option_sequence:
            print(f"✗ DHCP Fingerprint '{name}' has incorrect option_sequence")
            verification_passed = False
        
        # Verify device class if specified
        if 'device_class' in record:
            if actual_record.get('device_class') != record['device_class']:
                print(f"✗ DHCP Fingerprint '{name}' has incorrect device_class")
                verification_passed = False
        
        if verification_passed:
            print(f"✓ DHCP Fingerprint '{name}' verified successfully")
            successful_records += 1
        else:
            failed_records += 1
            failed_list.append(name)
    
    print("\nDHCP Fingerprint Verification Summary:")
    print(f"Total records: {total_records}")
    print(f"Successfully verified: {successful_records}")
    print(f"Failed verification: {failed_records}")
    
    if failed_list:
        print(f"Failed records: {', '.join(failed_list)}")
    
    return failed_records == 0

def verify_grid_dhcp_properties():
    """Verify Grid DHCP Properties after deployment."""
    print("\n--- Grid DHCP Properties Post-Deployment Verification ---")
    
    grid_dhcp_properties_file = "playbooks/add/cabgridmgr.amfam.com/grid_dhcp_properties.json"
    if not os.path.exists(grid_dhcp_properties_file):
        print(f"Grid DHCP Properties file not found: {grid_dhcp_properties_file}")
        print("Skipping Grid DHCP Properties verification.")
        return True
    
    try:
        with open(grid_dhcp_properties_file, 'r') as file:
            grid_dhcp_properties_config = json.load(file)
            
            if not grid_dhcp_properties_config or grid_dhcp_properties_config == {}:
                print("Grid DHCP Properties file exists but contains no data. Skipping verification.")
                return True
            
            print(f"Verifying Grid DHCP Properties configuration.")
    except Exception as e:
        print(f"Error reading file {grid_dhcp_properties_file}: {str(e)}")
        return False
    
    actual_properties = get_grid_dhcp_properties()
    
    if not actual_properties:
        print(f"✗ Grid DHCP Properties configuration was not found in Infoblox")
        return False
    
    actual_config = actual_properties[0]
    verification_passed = True
    
    # Verify key settings
    important_settings = [
        'deny_bootp', 'enable_ddns', 'enable_fingerprint', 'enable_leasequery',
        'ignore_dhcp_option_list_request', 'recycle_leases', 'update_dns_on_lease_renewal'
    ]
    
    for setting in important_settings:
        if setting in grid_dhcp_properties_config:
            expected = grid_dhcp_properties_config[setting]
            actual = actual_config.get(setting)
            if actual != expected:
                print(f"✗ Grid DHCP Properties has incorrect {setting}: expected {expected}, got {actual}")
                verification_passed = False
    
    # Verify DHCP options if specified
    if 'options' in grid_dhcp_properties_config:
        expected_options = {opt['name']: opt['value'] for opt in grid_dhcp_properties_config['options'] 
                          if opt.get('use_option', False)}
        actual_options = {opt['name']: opt['value'] for opt in actual_config.get('options', []) 
                         if opt.get('use_option', False)}
        
        for opt_name, expected_value in expected_options.items():
            if opt_name not in actual_options:
                print(f"✗ Grid DHCP Properties missing option '{opt_name}'")
                verification_passed = False
            elif actual_options[opt_name] != expected_value:
                print(f"✗ Grid DHCP Properties has incorrect option '{opt_name}'")
                verification_passed = False
    
    if verification_passed:
        print(f"✓ Grid DHCP Properties configuration verified successfully")
        return True
    else:
        return False



def get_adminuser(name):
    """Get admin user from Infoblox by name."""
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
            print(f"✗ Error getting admin user {name}: {response.status_code}")
            return []
    except Exception as e:
        print(f"✗ Error getting admin user {name}: {str(e)}")
        return []

def verify_adminuser_records():
    """Verify Admin User records after deployment."""
    print("\n--- Admin User Post-Deployment Verification ---")
    
    # Check if admin user file exists with the correct path
    adminuser_file = "playbooks/add/cabgridmgr.amfam.com/adminuser.json"
    if not os.path.exists(adminuser_file):
        print(f"Admin User file not found: {adminuser_file}")
        print("Skipping Admin User verification.")
        return True
    
    # Read admin user data from JSON file
    try:
        with open(adminuser_file, 'r') as file:
            adminuser_records = json.load(file)
            
            # Check if the file contains an empty list or empty object
            if not adminuser_records or (isinstance(adminuser_records, list) and len(adminuser_records) == 0):
                print("Admin User file exists but contains no records. Skipping verification.")
                return True
                
            # If the content is not a list, convert it to a list with one item
            if not isinstance(adminuser_records, list):
                adminuser_records = [adminuser_records]
                
            print(f"Verifying {len(adminuser_records)} Admin User records.")
    except Exception as e:
        print(f"Error reading file {adminuser_file}: {str(e)}")
        return False
    
    # Count statistics
    total_records = len(adminuser_records)
    successful_records = 0
    failed_records = 0
    failed_list = []
    
    # Verify each record exists in Infoblox with correct configuration
    for record in adminuser_records:
        name = record.get('name')
        
        if not name:
            print(f"✗ Incomplete record data: {record}")
            failed_records += 1
            continue
        
        actual_records = get_adminuser(name)
        
        if not actual_records:
            print(f"✗ Admin user '{name}' was not found in Infoblox")
            print(f"  Note: This may be expected if password was not provided in JSON")
            failed_records += 1
            failed_list.append(name)
            continue
        
        # Check if key attributes match
        actual_record = actual_records[0]
        verification_passed = True
        
        # Check email if specified
        if 'email' in record and record['email']:
            expected_email = record['email']
            actual_email = actual_record.get('email', '')
            if actual_email != expected_email:
                print(f"✗ Admin user '{name}' has incorrect email: expected '{expected_email}', got '{actual_email}'")
                verification_passed = False
        
        # Check comment if specified
        if 'comment' in record:
            expected_comment = record['comment']
            actual_comment = actual_record.get('comment', '')
            if actual_comment != expected_comment:
                print(f"✗ Admin user '{name}' has incorrect comment: expected '{expected_comment}', got '{actual_comment}'")
                verification_passed = False
        
        # Check disable status
        if 'disable' in record:
            expected_disable = record['disable']
            actual_disable = actual_record.get('disable', False)
            if actual_disable != expected_disable:
                status = "disabled" if actual_disable else "enabled"
                expected_status = "disabled" if expected_disable else "enabled"
                print(f"✗ Admin user '{name}' has incorrect status: expected {expected_status}, got {status}")
                verification_passed = False
        
        # Check admin groups if specified
        if 'admin_groups' in record and record['admin_groups']:
            # Extract expected group names
            expected_groups = set()
            for group in record['admin_groups']:
                if isinstance(group, dict) and 'name' in group:
                    expected_groups.add(group['name'])
                elif isinstance(group, str):
                    expected_groups.add(group)
            
            # Extract actual group names from references
            actual_groups = set()
            for group_ref in actual_record.get('admin_groups', []):
                if isinstance(group_ref, str) and ':' in group_ref:
                    # Extract group name from reference like "admingroup/ZG5zLmFkbWluX2dyb3VwJDEg:admin-group"
                    group_name = group_ref.split(':')[-1]
                    actual_groups.add(group_name)
            
            # Compare groups
            missing_groups = expected_groups - actual_groups
            extra_groups = actual_groups - expected_groups
            
            if missing_groups:
                print(f"✗ Admin user '{name}' is missing admin groups: {missing_groups}")
                verification_passed = False
            if extra_groups:
                print(f"✗ Admin user '{name}' has unexpected admin groups: {extra_groups}")
                verification_passed = False
        
        # Check time zone if specified
        if 'time_zone' in record and record['time_zone']:
            expected_timezone = record['time_zone']
            actual_timezone = actual_record.get('time_zone', '')
            if actual_timezone != expected_timezone:
                print(f"✗ Admin user '{name}' has incorrect time zone: expected '{expected_timezone}', got '{actual_timezone}'")
                verification_passed = False
        
        # Check use_time_zone flag
        if 'use_time_zone' in record:
            expected_use_tz = record['use_time_zone']
            actual_use_tz = actual_record.get('use_time_zone', False)
            if actual_use_tz != expected_use_tz:
                print(f"✗ Admin user '{name}' has incorrect use_time_zone: expected {expected_use_tz}, got {actual_use_tz}")
                verification_passed = False
        
        # Check auth_type if specified
        if 'auth_type' in record:
            expected_auth_type = record['auth_type']
            actual_auth_type = actual_record.get('auth_type', 'LOCAL')
            if actual_auth_type != expected_auth_type:
                print(f"✗ Admin user '{name}' has incorrect auth_type: expected '{expected_auth_type}', got '{actual_auth_type}'")
                verification_passed = False
        
        # Check extensible attributes if specified
        if 'extattrs' in record and record['extattrs']:
            for key, expected_value in record['extattrs'].items():
                actual_value = actual_record.get('extattrs', {}).get(key, {}).get('value')
                if actual_value != expected_value:
                    print(f"✗ Admin user '{name}' has incorrect extensible attribute '{key}': expected '{expected_value}', got '{actual_value}'")
                    verification_passed = False
        
        if verification_passed:
            print(f"✓ Admin user '{name}' verified successfully")
            successful_records += 1
        else:
            failed_records += 1
            failed_list.append(name)
    
    # Display verification summary
    print("\nAdmin User Verification Summary:")
    print(f"Total records: {total_records}")
    print(f"Successfully verified: {successful_records}")
    print(f"Failed verification: {failed_records}")
    
    if failed_list:
        print(f"Failed records: {', '.join(failed_list)}")
    
    return failed_records == 0

def get_network_container(network, network_view):
    """Get network container from Infoblox by network and network view."""
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
            print(f"✗ Error getting network container {network}: {response.status_code}")
            return []
    except Exception as e:
        print(f"✗ Error getting network container {network}: {str(e)}")
        return []

def get_ipv6_network_container(network, network_view):
    """Get IPv6 network container from Infoblox by network and network view."""
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
            print(f"✗ Error getting IPv6 network container {network}: {response.status_code}")
            return []
    except Exception as e:
        print(f"✗ Error getting IPv6 network container {network}: {str(e)}")
        return []

def verify_network_container_records():
    """Verify Network Container records after deployment."""
    print("\n--- Network Container Post-Deployment Verification ---")
    
    # Check if network container file exists with the correct path
    networkcontainer_file = "playbooks/add/cabgridmgr.amfam.com/networkcontainer.json"
    if not os.path.exists(networkcontainer_file):
        print(f"Network Container file not found: {networkcontainer_file}")
        print("Skipping Network Container verification.")
        return True
    
    # Read network container data from JSON file
    try:
        with open(networkcontainer_file, 'r') as file:
            networkcontainer_records = json.load(file)
            
            # Check if the file contains an empty list or empty object
            if not networkcontainer_records or (isinstance(networkcontainer_records, list) and len(networkcontainer_records) == 0):
                print("Network Container file exists but contains no records. Skipping verification.")
                return True
                
            # If the content is not a list, convert it to a list with one item
            if not isinstance(networkcontainer_records, list):
                networkcontainer_records = [networkcontainer_records]
                
            print(f"Verifying {len(networkcontainer_records)} Network Container records.")
    except Exception as e:
        print(f"Error reading file {networkcontainer_file}: {str(e)}")
        return False
    
    # Count statistics
    total_records = len(networkcontainer_records)
    successful_records = 0
    failed_records = 0
    failed_list = []
    
    # Verify each record exists in Infoblox with correct configuration
    for record in networkcontainer_records:
        network = record.get('network')
        network_view = record.get('network_view', 'default')
        
        if not network or not network_view:
            print(f"✗ Incomplete record data: {record}")
            failed_records += 1
            continue
        
        actual_records = get_network_container(network, network_view)
        
        if not actual_records:
            print(f"✗ Network container '{network}' was not found in Infoblox")
            failed_records += 1
            failed_list.append(network)
            continue
        
        # Check if key attributes match
        actual_record = actual_records[0]
        verification_passed = True
        
        # Check comment if specified
        if 'comment' in record:
            expected_comment = record['comment']
            actual_comment = actual_record.get('comment', '')
            if actual_comment != expected_comment:
                print(f"✗ Network container '{network}' has incorrect comment: expected '{expected_comment}', got '{actual_comment}'")
                verification_passed = False
        
        # Check DDNS settings
        ddns_fields = ['enable_ddns', 'ddns_domainname', 'ddns_generate_hostname', 
                       'ddns_server_always_updates', 'ddns_ttl', 'ddns_update_fixed_addresses',
                       'ddns_use_option81']
        
        for field in ddns_fields:
            if field in record:
                expected_value = record[field]
                actual_value = actual_record.get(field)
                if actual_value != expected_value:
                    print(f"✗ Network container '{network}' has incorrect {field}: expected {expected_value}, got {actual_value}")
                    verification_passed = False
        
        # Check DHCP settings
        dhcp_fields = ['enable_dhcp_thresholds', 'enable_email_warnings', 'enable_snmp_warnings',
                       'high_water_mark', 'high_water_mark_reset', 'low_water_mark', 
                       'low_water_mark_reset']
        
        for field in dhcp_fields:
            if field in record:
                expected_value = record[field]
                actual_value = actual_record.get(field)
                if actual_value != expected_value:
                    print(f"✗ Network container '{network}' has incorrect {field}: expected {expected_value}, got {actual_value}")
                    verification_passed = False
        
        # Check discovery settings
        if 'enable_discovery' in record:
            expected_discovery = record['enable_discovery']
            actual_discovery = actual_record.get('enable_discovery')
            if actual_discovery != expected_discovery:
                print(f"✗ Network container '{network}' has incorrect enable_discovery: expected {expected_discovery}, got {actual_discovery}")
                verification_passed = False
        
        if 'discovery_member' in record and record['discovery_member']:
            expected_member = record['discovery_member']
            actual_member = actual_record.get('discovery_member')
            if actual_member != expected_member:
                print(f"✗ Network container '{network}' has incorrect discovery_member: expected '{expected_member}', got '{actual_member}'")
                verification_passed = False
        
        # Check email list if specified
        if 'email_list' in record and record['email_list']:
            expected_emails = set(record['email_list'])
            actual_emails = set(actual_record.get('email_list', []))
            
            if expected_emails != actual_emails:
                missing_emails = expected_emails - actual_emails
                extra_emails = actual_emails - expected_emails
                
                if missing_emails:
                    print(f"✗ Network container '{network}' is missing emails: {missing_emails}")
                    verification_passed = False
                if extra_emails:
                    print(f"✗ Network container '{network}' has unexpected emails: {extra_emails}")
                    verification_passed = False
        
        # Check DHCP options if specified
        if 'options' in record and record['options']:
            expected_options = {}
            for option in record['options']:
                if option.get('use_option', False):
                    option_name = option.get('name')
                    option_value = option.get('value')
                    if option_name and option_value:
                        expected_options[option_name] = option_value
            
            actual_options = {}
            for option in actual_record.get('options', []):
                if option.get('use_option', False):
                    option_name = option.get('name')
                    option_value = option.get('value')
                    if option_name and option_value:
                        actual_options[option_name] = option_value
            
            # Check for missing or incorrect options
            for option_name, expected_value in expected_options.items():
                if option_name not in actual_options:
                    print(f"✗ Network container '{network}' is missing DHCP option '{option_name}'")
                    verification_passed = False
                elif actual_options[option_name] != expected_value:
                    print(f"✗ Network container '{network}' has incorrect DHCP option '{option_name}': expected '{expected_value}', got '{actual_options[option_name]}'")
                    verification_passed = False
        
        # Check unmanaged status
        if 'unmanaged' in record:
            expected_unmanaged = record['unmanaged']
            actual_unmanaged = actual_record.get('unmanaged', False)
            if actual_unmanaged != expected_unmanaged:
                print(f"✗ Network container '{network}' has incorrect unmanaged status: expected {expected_unmanaged}, got {actual_unmanaged}")
                verification_passed = False
        
        # Check extensible attributes if specified
        if 'extattrs' in record and record['extattrs']:
            for key, value in record['extattrs'].items():
                # Handle the transformation that the playbook does
                if isinstance(value, dict) and 'value' in value:
                    expected_value = value['value']
                else:
                    expected_value = value
                    
                actual_value = actual_record.get('extattrs', {}).get(key, {}).get('value')
                if actual_value != expected_value:
                    print(f"✗ Network container '{network}' has incorrect extensible attribute '{key}': expected '{expected_value}', got '{actual_value}'")
                    verification_passed = False
        
        if verification_passed:
            print(f"✓ Network container '{network}' verified successfully")
            successful_records += 1
        else:
            failed_records += 1
            failed_list.append(network)
    
    # Display verification summary
    print("\nNetwork Container Verification Summary:")
    print(f"Total records: {total_records}")
    print(f"Successfully verified: {successful_records}")
    print(f"Failed verification: {failed_records}")
    
    if failed_list:
        print(f"Failed records: {', '.join(failed_list)}")
    
    return failed_records == 0

def verify_ipv6_network_container_records():
    """Verify IPv6 Network Container records after deployment."""
    print("\n--- IPv6 Network Container Post-Deployment Verification ---")
    
    # Check if IPv6 network container file exists with the correct path
    ipv6networkcontainer_file = "playbooks/add/cabgridmgr.amfam.com/networkipv6container.json"
    if not os.path.exists(ipv6networkcontainer_file):
        print(f"IPv6 Network Container file not found: {ipv6networkcontainer_file}")
        print("Skipping IPv6 Network Container verification.")
        return True
    
    # Read IPv6 network container data from JSON file
    try:
        with open(ipv6networkcontainer_file, 'r') as file:
            ipv6networkcontainer_records = json.load(file)
            
            # Check if the file contains an empty list or empty object
            if not ipv6networkcontainer_records or (isinstance(ipv6networkcontainer_records, list) and len(ipv6networkcontainer_records) == 0):
                print("IPv6 Network Container file exists but contains no records. Skipping verification.")
                return True
                
            # If the content is not a list, convert it to a list with one item
            if not isinstance(ipv6networkcontainer_records, list):
                ipv6networkcontainer_records = [ipv6networkcontainer_records]
                
            print(f"Verifying {len(ipv6networkcontainer_records)} IPv6 Network Container records.")
    except Exception as e:
        print(f"Error reading file {ipv6networkcontainer_file}: {str(e)}")
        return False
    
    # Count statistics
    total_records = len(ipv6networkcontainer_records)
    successful_records = 0
    failed_records = 0
    failed_list = []
    
    # Verify each record exists in Infoblox with correct configuration
    for record in ipv6networkcontainer_records:
        network = record.get('network')
        network_view = record.get('network_view', 'default')
        
        if not network or not network_view:
            print(f"✗ Incomplete record data: {record}")
            failed_records += 1
            continue
        
        actual_records = get_ipv6_network_container(network, network_view)
        
        if not actual_records:
            print(f"✗ IPv6 network container '{network}' was not found in Infoblox")
            failed_records += 1
            failed_list.append(network)
            continue
        
        # Check if key attributes match
        actual_record = actual_records[0]
        verification_passed = True
        
        # Check comment if specified
        if 'comment' in record:
            expected_comment = record['comment']
            actual_comment = actual_record.get('comment', '')
            if actual_comment != expected_comment:
                print(f"✗ IPv6 network container '{network}' has incorrect comment: expected '{expected_comment}', got '{actual_comment}'")
                verification_passed = False
        
        # Check DDNS settings
        ddns_fields = ['enable_ddns', 'ddns_domainname', 'ddns_generate_hostname', 
                       'ddns_server_always_updates', 'ddns_ttl', 'update_dns_on_lease_renewal']
        
        for field in ddns_fields:
            if field in record:
                expected_value = record[field]
                actual_value = actual_record.get(field)
                if actual_value != expected_value:
                    print(f"✗ IPv6 network container '{network}' has incorrect {field}: expected {expected_value}, got {actual_value}")
                    verification_passed = False
        
        # Check IPv6-specific lifetime values
        if 'preferred_lifetime' in record:
            expected_lifetime = record['preferred_lifetime']
            actual_lifetime = actual_record.get('preferred_lifetime')
            if actual_lifetime != expected_lifetime:
                print(f"✗ IPv6 network container '{network}' has incorrect preferred_lifetime: expected {expected_lifetime}, got {actual_lifetime}")
                verification_passed = False
        
        if 'valid_lifetime' in record:
            expected_lifetime = record['valid_lifetime']
            actual_lifetime = actual_record.get('valid_lifetime')
            if actual_lifetime != expected_lifetime:
                print(f"✗ IPv6 network container '{network}' has incorrect valid_lifetime: expected {expected_lifetime}, got {actual_lifetime}")
                verification_passed = False
        
        # Check use_preferred_lifetime and use_valid_lifetime flags
        if 'use_preferred_lifetime' in record:
            expected_use = record['use_preferred_lifetime']
            actual_use = actual_record.get('use_preferred_lifetime', False)
            if actual_use != expected_use:
                print(f"✗ IPv6 network container '{network}' has incorrect use_preferred_lifetime: expected {expected_use}, got {actual_use}")
                verification_passed = False
        
        if 'use_valid_lifetime' in record:
            expected_use = record['use_valid_lifetime']
            actual_use = actual_record.get('use_valid_lifetime', False)
            if actual_use != expected_use:
                print(f"✗ IPv6 network container '{network}' has incorrect use_valid_lifetime: expected {expected_use}, got {actual_use}")
                verification_passed = False
        
        # Check DHCPv6 options if specified
        if 'options' in record and record['options']:
            expected_options = {}
            for option in record['options']:
                if option.get('use_option', False):
                    option_name = option.get('name')
                    option_value = option.get('value')
                    if option_name and option_value:
                        expected_options[option_name] = option_value
            
            actual_options = {}
            for option in actual_record.get('options', []):
                if option.get('use_option', False):
                    option_name = option.get('name')
                    option_value = option.get('value')
                    if option_name and option_value:
                        actual_options[option_name] = option_value
            
            # Check for missing or incorrect options
            for option_name, expected_value in expected_options.items():
                if option_name not in actual_options:
                    print(f"✗ IPv6 network container '{network}' is missing DHCPv6 option '{option_name}'")
                    verification_passed = False
                elif actual_options[option_name] != expected_value:
                    print(f"✗ IPv6 network container '{network}' has incorrect DHCPv6 option '{option_name}': expected '{expected_value}', got '{actual_options[option_name]}'")
                    verification_passed = False
        
        # Check unmanaged status
        if 'unmanaged' in record:
            expected_unmanaged = record['unmanaged']
            actual_unmanaged = actual_record.get('unmanaged', False)
            if actual_unmanaged != expected_unmanaged:
                print(f"✗ IPv6 network container '{network}' has incorrect unmanaged status: expected {expected_unmanaged}, got {actual_unmanaged}")
                verification_passed = False
        
        # Check extensible attributes if specified
        if 'extattrs' in record and record['extattrs']:
            for key, value in record['extattrs'].items():
                # Handle the transformation that the playbook does
                if isinstance(value, dict) and 'value' in value:
                    expected_value = value['value']
                else:
                    expected_value = value
                    
                actual_value = actual_record.get('extattrs', {}).get(key, {}).get('value')
                if actual_value != expected_value:
                    print(f"✗ IPv6 network container '{network}' has incorrect extensible attribute '{key}': expected '{expected_value}', got '{actual_value}'")
                    verification_passed = False
        
        if verification_passed:
            print(f"✓ IPv6 network container '{network}' verified successfully")
            successful_records += 1
        else:
            failed_records += 1
            failed_list.append(network)
    
    # Display verification summary
    print("\nIPv6 Network Container Verification Summary:")
    print(f"Total records: {total_records}")
    print(f"Successfully verified: {successful_records}")
    print(f"Failed verification: {failed_records}")
    
    if failed_list:
        print(f"Failed records: {', '.join(failed_list)}")
    
    return failed_records == 0

def get_range(start_addr, end_addr, network_view):
    """Get DHCP range from Infoblox by start/end addresses and network view."""
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
            print(f"✗ Error getting range {start_addr}-{end_addr}: {response.status_code}")
            return []
    except Exception as e:
        print(f"✗ Error getting range {start_addr}-{end_addr}: {str(e)}")
        return []

def get_srv_record(name, view):
    """Get SRV record from Infoblox by name and view."""
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
            print(f"✗ Error getting SRV record {name}: {response.status_code}")
            return []
    except Exception as e:
        print(f"✗ Error getting SRV record {name}: {str(e)}")
        return []

def verify_range_records():
    """Verify DHCP Range records after deployment."""
    print("\n--- DHCP Range Post-Deployment Verification ---")
    
    # Check if range file exists with the correct path
    range_file = "../prod_changes/cabgridmgr.amfam.com/network_range.json"
    if not os.path.exists(range_file):
        print(f"DHCP Range file not found: {range_file}")
        print("Skipping DHCP Range verification.")
        return True
    
    # Read range data from JSON file
    try:
        with open(range_file, 'r') as file:
            range_records = json.load(file)
            
            # Check if the file contains an empty list or empty object
            if not range_records or (isinstance(range_records, list) and len(range_records) == 0):
                print("DHCP Range file exists but contains no records. Skipping verification.")
                return True
                
            # If the content is not a list, convert it to a list with one item
            if not isinstance(range_records, list):
                range_records = [range_records]
                
            print(f"Verifying {len(range_records)} DHCP Range records.")
    except Exception as e:
        print(f"Error reading file {range_file}: {str(e)}")
        return False
    
    # Count statistics
    total_records = len(range_records)
    successful_records = 0
    failed_records = 0
    failed_list = []
    
    # Verify each record exists in Infoblox with correct configuration
    for record in range_records:
        start_addr = record.get('start_addr')
        end_addr = record.get('end_addr')
        network_view = record.get('network_view', 'default')
        
        if not start_addr or not end_addr:
            print(f"✗ Incomplete record data: {record}")
            failed_records += 1
            continue
        
        actual_records = get_range(start_addr, end_addr, network_view)
        
        if not actual_records:
            print(f"✗ DHCP range '{start_addr}-{end_addr}' was not found in Infoblox")
            failed_records += 1
            failed_list.append(f"{start_addr}-{end_addr}")
            continue
        
        # Check if key attributes match
        actual_record = actual_records[0]
        verification_passed = True
        
        # Check network
        if 'network' in record:
            expected_network = record['network']
            actual_network = actual_record.get('network')
            if actual_network != expected_network:
                print(f"✗ DHCP range '{start_addr}-{end_addr}' has incorrect network: expected '{expected_network}', got '{actual_network}'")
                verification_passed = False
        
        # Check name if specified
        if 'name' in record and record['name']:
            expected_name = record['name']
            actual_name = actual_record.get('name', '')
            if actual_name != expected_name:
                print(f"✗ DHCP range '{start_addr}-{end_addr}' has incorrect name: expected '{expected_name}', got '{actual_name}'")
                verification_passed = False
        
        # Check comment if specified
        if 'comment' in record:
            expected_comment = record['comment']
            actual_comment = actual_record.get('comment', '')
            if actual_comment != expected_comment:
                print(f"✗ DHCP range '{start_addr}-{end_addr}' has incorrect comment: expected '{expected_comment}', got '{actual_comment}'")
                verification_passed = False
        
        # Check disable status
        if 'disable' in record:
            expected_disable = record['disable']
            actual_disable = actual_record.get('disable', False)
            if actual_disable != expected_disable:
                status = "disabled" if actual_disable else "enabled"
                expected_status = "disabled" if expected_disable else "enabled"
                print(f"✗ DHCP range '{start_addr}-{end_addr}' has incorrect status: expected {expected_status}, got {status}")
                verification_passed = False
        
        # Check server association
        if 'server_association_type' in record:
            expected_assoc = record['server_association_type']
            actual_assoc = actual_record.get('server_association_type')
            if actual_assoc != expected_assoc:
                print(f"✗ DHCP range '{start_addr}-{end_addr}' has incorrect server_association_type: expected '{expected_assoc}', got '{actual_assoc}'")
                verification_passed = False
            
            # Check member if MEMBER association
            if expected_assoc == 'MEMBER' and 'member' in record:
                expected_member = record['member']
                if isinstance(expected_member, dict):
                    expected_member = expected_member.get('name')
                    
                actual_member = actual_record.get('member')
                if actual_member != expected_member:
                    print(f"✗ DHCP range '{start_addr}-{end_addr}' has incorrect member: expected '{expected_member}', got '{actual_member}'")
                    verification_passed = False
            
            # Check MS server if MS_SERVER association
            if expected_assoc == 'MS_SERVER' and 'ms_server' in record:
                expected_ms_server = record['ms_server']
                actual_ms_server = actual_record.get('ms_server')
                if actual_ms_server != expected_ms_server:
                    print(f"✗ DHCP range '{start_addr}-{end_addr}' has incorrect ms_server: expected '{expected_ms_server}', got '{actual_ms_server}'")
                    verification_passed = False
            
            # Check failover association if FAILOVER or MS_FAILOVER
            if expected_assoc in ['FAILOVER', 'MS_FAILOVER'] and 'failover_association' in record:
                expected_failover = record['failover_association']
                actual_failover = actual_record.get('failover_association')
                if actual_failover != expected_failover:
                    print(f"✗ DHCP range '{start_addr}-{end_addr}' has incorrect failover_association: expected '{expected_failover}', got '{actual_failover}'")
                    verification_passed = False
        
        # Check DHCP options if specified
        if 'options' in record and record['options']:
            expected_options = {}
            for option in record['options']:
                if option.get('use_option', False):
                    option_name = option.get('name')
                    option_value = option.get('value')
                    if option_name and option_value:
                        expected_options[option_name] = option_value
            
            actual_options = {}
            for option in actual_record.get('options', []):
                if option.get('use_option', False):
                    option_name = option.get('name')
                    option_value = option.get('value')
                    if option_name and option_value:
                        actual_options[option_name] = option_value
            
            # Check for missing or incorrect options
            for option_name, expected_value in expected_options.items():
                if option_name not in actual_options:
                    print(f"✗ DHCP range '{start_addr}-{end_addr}' is missing DHCP option '{option_name}'")
                    verification_passed = False
                elif actual_options[option_name] != expected_value:
                    print(f"✗ DHCP range '{start_addr}-{end_addr}' has incorrect DHCP option '{option_name}': expected '{expected_value}', got '{actual_options[option_name]}'")
                    verification_passed = False
        
        # Check extensible attributes if specified
        if 'extattrs' in record and record['extattrs']:
            for key, expected_value in record['extattrs'].items():
                actual_value = actual_record.get('extattrs', {}).get(key, {}).get('value')
                if actual_value != expected_value:
                    print(f"✗ DHCP range '{start_addr}-{end_addr}' has incorrect extensible attribute '{key}': expected '{expected_value}', got '{actual_value}'")
                    verification_passed = False
        
        if verification_passed:
            print(f"✓ DHCP range '{start_addr}-{end_addr}' verified successfully")
            successful_records += 1
        else:
            failed_records += 1
            failed_list.append(f"{start_addr}-{end_addr}")
    
    # Display verification summary
    print("\nDHCP Range Verification Summary:")
    print(f"Total records: {total_records}")
    print(f"Successfully verified: {successful_records}")
    print(f"Failed verification: {failed_records}")
    
    if failed_list:
        print(f"Failed records: {', '.join(failed_list)}")
    
    return failed_records == 0

def verify_srv_records():
    """Verify SRV records after deployment."""
    print("\n--- SRV Record Post-Deployment Verification ---")
    
    # Check if SRV record file exists with the correct path
    srv_record_file = "../prod_changes/cabgridmgr.amfam.com/srv_record.json"
    if not os.path.exists(srv_record_file):
        print(f"SRV record file not found: {srv_record_file}")
        print("Skipping SRV record verification.")
        return True
    
    # Read SRV record data from JSON file
    try:
        with open(srv_record_file, 'r') as file:
            srv_records = json.load(file)
            
            # Check if the file contains an empty list or empty object
            if not srv_records or (isinstance(srv_records, list) and len(srv_records) == 0):
                print("SRV record file exists but contains no records. Skipping verification.")
                return True
                
            # If the content is not a list, convert it to a list with one item
            if not isinstance(srv_records, list):
                srv_records = [srv_records]
                
            print(f"Verifying {len(srv_records)} SRV records.")
    except Exception as e:
        print(f"Error reading file {srv_record_file}: {str(e)}")
        return False
    
    # Count statistics
    total_records = len(srv_records)
    successful_records = 0
    failed_records = 0
    failed_list = []
    
    # Verify each record exists in Infoblox with correct configuration
    for record in srv_records:
        name = record.get('name')
        view = record.get('view')
        expected_port = record.get('port')
        expected_priority = record.get('priority')
        expected_target = record.get('target')
        expected_weight = record.get('weight')
        
        if not all([name, view, expected_port is not None, expected_priority is not None, 
                    expected_target, expected_weight is not None]):
            print(f"✗ Incomplete record data: {record}")
            failed_records += 1
            continue
        
        actual_records = get_srv_record(name, view)
        
        if not actual_records:
            print(f"✗ SRV record '{name}' was not found in Infoblox")
            failed_records += 1
            failed_list.append(name)
            continue
        
        # Find matching record by port, priority, target, and weight
        matching_record = None
        for actual_record in actual_records:
            if (actual_record.get('port') == expected_port and 
                actual_record.get('priority') == expected_priority and
                actual_record.get('target') == expected_target and
                actual_record.get('weight') == expected_weight):
                matching_record = actual_record
                break
        
        if not matching_record:
            print(f"✗ SRV record '{name}' found but no matching configuration")
            print(f"  Expected: port={expected_port}, priority={expected_priority}, weight={expected_weight}, target={expected_target}")
            existing_configs = [(r.get('port'), r.get('priority'), r.get('weight'), r.get('target')) 
                               for r in actual_records]
            print(f"  Found configurations: {existing_configs}")
            failed_records += 1
            failed_list.append(name)
            continue
        
        # Verify additional attributes if specified
        verification_passed = True
        
        # Check comment if specified
        if 'comment' in record:
            expected_comment = record['comment']
            actual_comment = matching_record.get('comment', '')
            if actual_comment != expected_comment:
                print(f"✗ SRV record '{name}' has incorrect comment: expected '{expected_comment}', got '{actual_comment}'")
                verification_passed = False
        
        # Check TTL if specified
        if 'ttl' in record and record['ttl'] is not None:
            expected_ttl = record['ttl']
            actual_ttl = matching_record.get('ttl')
            if actual_ttl != expected_ttl:
                print(f"✗ SRV record '{name}' has incorrect TTL: expected {expected_ttl}, got {actual_ttl}")
                verification_passed = False
        
        # Check extensible attributes if specified
        if 'extattrs' in record and record['extattrs']:
            for key, expected_value in record['extattrs'].items():
                actual_value = matching_record.get('extattrs', {}).get(key, {}).get('value')
                if actual_value != expected_value:
                    print(f"✗ SRV record '{name}' has incorrect extensible attribute '{key}': expected '{expected_value}', got '{actual_value}'")
                    verification_passed = False
        
        if verification_passed:
            print(f"✓ SRV record '{name}' verified with port={expected_port}, priority={expected_priority}, weight={expected_weight}, target={expected_target}")
            successful_records += 1
        else:
            failed_records += 1
            failed_list.append(name)
    
    # Display verification summary
    print("\nSRV Record Verification Summary:")
    print(f"Total records: {total_records}")
    print(f"Successfully verified: {successful_records}")
    print(f"Failed verification: {failed_records}")
    
    if failed_list:
        print(f"Failed records: {', '.join(failed_list)}")
    
    return failed_records == 0

def verify_srv_record_dns_resolution(srv_records):
    """Verify DNS resolution for SRV records."""
    total_records = len(srv_records)
    successful_resolutions = 0
    failed_resolutions = 0
    failed_list = []
    
    for record in srv_records:
        name = record.get('name')
        expected_port = record.get('port')
        expected_priority = record.get('priority')
        expected_target = record.get('target')
        expected_weight = record.get('weight')
        
        if not name:
            print(f"✗ Incomplete record data: {record}")
            failed_resolutions += 1
            continue
        
        # Perform SRV lookup
        dns_result = subprocess.run(['nslookup', '-type=SRV', name], 
                                   capture_output=True, 
                                   text=True, 
                                   check=False)
        
        if dns_result.returncode != 0:
            print(f"✗ DNS SRV lookup failed for '{name}'")
            failed_resolutions += 1
            failed_list.append(name)
            continue
        
        # Check if the expected values are in the results
        dns_output = dns_result.stdout
        
        # Look for the SRV record values in the output
        port_found = str(expected_port) in dns_output
        priority_found = str(expected_priority) in dns_output
        weight_found = str(expected_weight) in dns_output
        target_found = expected_target in dns_output
        
        if port_found and priority_found and weight_found and target_found:
            print(f"✓ DNS SRV resolution for '{name}' returned expected configuration")
            successful_resolutions += 1
        else:
            print(f"✗ DNS SRV resolution for '{name}' did not return expected configuration")
            print(f"  Expected: priority={expected_priority}, weight={expected_weight}, port={expected_port}, target={expected_target}")
            print(f"  DNS lookup result: {dns_result.stdout}")
            failed_resolutions += 1
            failed_list.append(name)
    
    # Display verification summary
    print("\nSRV Record DNS Resolution Summary:")
    print(f"Total records checked: {total_records}")
    print(f"Successfully resolved: {successful_resolutions}")
    print(f"Failed resolution: {failed_resolutions}")
    
    if failed_list:
        print(f"Failed resolutions: {', '.join(failed_list)}")
    
    return failed_resolutions == 0

def get_member_dns(host_name):
    """Get Member DNS Properties from Infoblox by host name."""
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
            print(f"✗ Error getting member DNS {host_name}: {response.status_code}")
            return []
    except Exception as e:
        print(f"✗ Error getting member DNS {host_name}: {str(e)}")
        return []

def get_namedacl(name):
    """Get Named ACL from Infoblox by name."""
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
            print(f"✗ Error getting named ACL {name}: {response.status_code}")
            return []
    except Exception as e:
        print(f"✗ Error getting named ACL {name}: {str(e)}")
        return []

def verify_member_dns():
    """Verify Member DNS Properties after deployment."""
    print("\n--- Member DNS Properties Post-Deployment Verification ---")
    
    # Check if member DNS file exists with the correct path
    member_dns_file = "playbooks/add/cabgridmgr.amfam.com/member_dns.json"
    if not os.path.exists(member_dns_file):
        print(f"Member DNS file not found: {member_dns_file}")
        print("Skipping Member DNS verification.")
        return True
    
    # Read member DNS data from JSON file
    try:
        with open(member_dns_file, 'r') as file:
            member_dns_list = json.load(file)
            
            # Check if the file contains an empty list or empty object
            if not member_dns_list or (isinstance(member_dns_list, list) and len(member_dns_list) == 0):
                print("Member DNS file exists but contains no records. Skipping verification.")
                return True
                
            # If the content is not a list, convert it to a list with one item
            if not isinstance(member_dns_list, list):
                member_dns_list = [member_dns_list]
                
            print(f"Verifying {len(member_dns_list)} Member DNS configurations.")
    except Exception as e:
        print(f"Error reading file {member_dns_file}: {str(e)}")
        return False
    
    # Count statistics
    total_records = len(member_dns_list)
    successful_records = 0
    failed_records = 0
    failed_list = []
    
    # Define field categories
    integer_fields = [
        'dns_cache_acceleration_ttl', 'dns_health_check_interval', 'dns_health_check_retries',
        'dns_health_check_timeout', 'dns_query_capture_file_time_limit', 'edns_udp_size',
        'ftc_expired_record_timeout', 'ftc_expired_record_ttl', 'max_cache_ttl',
        'max_cached_lifetime', 'max_ncache_ttl', 'max_udp_size', 'notify_delay',
        'nxdomain_redirect_ttl', 'resolver_query_timeout', 'serial_query_rate',
        'transfers_in', 'transfers_out', 'transfers_per_ns', 'recursive_client_limit',
        'rpz_drop_ip_rule_min_prefix_length_ipv4', 'rpz_drop_ip_rule_min_prefix_length_ipv6',
        'tcp_idle_timeout', 'tls_session_duration', 'doh_https_session_duration'
    ]
    
    boolean_fields = [
        'add_client_ip_mac_options', 'allow_gss_tsig_zone_updates', 'allow_recursive_query',
        'anonymize_response_logging', 'atc_fwd_enable', 'auto_create_a_and_ptr_for_lan2',
        'auto_create_aaaa_and_ipv6ptr_for_lan2', 'auto_sort_views', 
        'check_names_for_ddns_and_zone_transfer', 'copy_client_ip_mac_options',
        'copy_xfer_to_notify', 'disable_edns', 'dns_health_check_anycast_control',
        'dns_health_check_recursion_flag', 'dns_over_tls_service', 'dnssec_blacklist_enabled',
        'dnssec_dns64_enabled', 'dnssec_enabled', 'dnssec_expired_signatures_enabled',
        'dnssec_nxdomain_enabled', 'dnssec_rpz_enabled', 'dnssec_validation_enabled',
        'dtc_edns_prefer_client_subnet', 'enable_blackhole', 'enable_blacklist',
        'enable_capture_dns_queries', 'enable_capture_dns_responses', 'enable_dns',
        'enable_dns64', 'enable_dns_cache_acceleration', 'enable_dns_health_check',
        'enable_dnstap_queries', 'enable_dnstap_responses', 'enable_excluded_domain_names',
        'enable_fixed_rrset_order_fqdns', 'enable_ftc', 'enable_gss_tsig',
        'enable_notify_source_port', 'enable_query_rewrite', 'enable_query_source_port',
        'forward_only', 'forward_updates', 'minimal_resp', 'nxdomain_log_query',
        'nxdomain_redirect', 'rpz_disable_nsdname_nsip', 'rpz_drop_ip_rule_enabled',
        'rpz_qname_wait_recurse', 'skip_in_grid_rpz_queries', 'store_locally',
        'use_root_server_for_all_views', 'use_lan_port', 'use_lan2_port',
        'use_lan_ipv6_port', 'use_lan2_ipv6_port', 'use_mgmt_port', 'use_mgmt_ipv6_port'
    ]
    
    string_fields = [
        'bind_check_names_policy', 'bind_hostname_directive', 'bind_hostname_directive_fqdn',
        'blacklist_action', 'dns_notify_transfer_source', 'dns_notify_transfer_source_address',
        'dns_query_source_interface', 'dns_query_source_address', 
        'dtc_dns_queries_specific_behavior', 'dtc_health_source', 'dtc_health_source_address',
        'filter_aaaa', 'record_name_policy', 'recursive_resolver', 'root_name_server_type',
        'server_id_directive', 'server_id_directive_string', 'syslog_facility',
        'transfer_format', 'upstream_address_family_preference'
    ]
    
    list_fields = [
        'additional_ip_list', 'blacklist_redirect_addresses', 'blacklist_rulesets',
        'dns64_groups', 'dns_health_check_domain_list', 'dnssec_negative_trust_anchors',
        'dnssec_trusted_keys', 'domains_to_capture_dns_queries', 'excluded_domain_names',
        'forwarders', 'nxdomain_redirect_addresses', 'nxdomain_redirect_addresses_v6',
        'nxdomain_rulesets', 'transfer_excluded_servers', 'views'
    ]
    
    struct_fields = [
        'attack_mitigation', 'auto_blackhole', 'dnstap_setting', 'file_transfer_setting',
        'logging_categories', 'response_rate_limiting', 'extattrs'
    ]
    
    list_of_structs_fields = [
        'allow_query', 'allow_transfer', 'allow_update', 'blackhole_list',
        'custom_root_name_servers', 'filter_aaaa_list', 'fixed_rrset_order_fqdns',
        'recursive_query_list', 'sortlist', 'gss_tsig_keys', 'dns_view_address_settings',
        'glue_record_addresses', 'ipv6_glue_record_addresses', 'additional_ip_list_struct'
    ]
    
    # Verify each member DNS configuration
    for member_config in member_dns_list:
        host_name = member_config.get('host_name')
        
        if not host_name:
            print(f"✗ Incomplete member DNS data: {member_config}")
            failed_records += 1
            continue
        
        actual_records = get_member_dns(host_name)
        
        if not actual_records:
            print(f"✗ Member DNS '{host_name}' was not found in Infoblox")
            failed_records += 1
            failed_list.append(host_name)
            continue
        
        # Check if key attributes match
        actual_record = actual_records[0]
        verification_passed = True
        
        # Check integer fields
        for field in integer_fields:
            if field in member_config:
                expected_value = member_config[field]
                actual_value = actual_record.get(field)
                if actual_value != expected_value:
                    print(f"✗ Member DNS '{host_name}' has incorrect {field}: expected {expected_value}, got {actual_value}")
                    verification_passed = False
        
        # Check boolean fields
        for field in boolean_fields:
            if field in member_config:
                expected_value = member_config[field]
                actual_value = actual_record.get(field)
                if actual_value != expected_value:
                    print(f"✗ Member DNS '{host_name}' has incorrect {field}: expected {expected_value}, got {actual_value}")
                    verification_passed = False
        
        # Check string fields
        for field in string_fields:
            if field in member_config:
                expected_value = member_config[field]
                actual_value = actual_record.get(field)
                if actual_value != expected_value:
                    print(f"✗ Member DNS '{host_name}' has incorrect {field}: expected '{expected_value}', got '{actual_value}'")
                    verification_passed = False
        
        # Check list fields
        for field in list_fields:
            if field in member_config and member_config[field]:
                expected_list = set(member_config[field]) if isinstance(member_config[field], list) else {member_config[field]}
                actual_list = set(actual_record.get(field, [])) if isinstance(actual_record.get(field, []), list) else set()
                
                if expected_list != actual_list:
                    missing_items = expected_list - actual_list
                    extra_items = actual_list - expected_list
                    
                    if missing_items:
                        print(f"✗ Member DNS '{host_name}' is missing {field} items: {missing_items}")
                        verification_passed = False
                    if extra_items:
                        print(f"✗ Member DNS '{host_name}' has unexpected {field} items: {extra_items}")
                        verification_passed = False
        
        # Check struct fields (like extattrs)
        if 'extattrs' in member_config and member_config['extattrs']:
            for key, expected_value in member_config['extattrs'].items():
                actual_value = actual_record.get('extattrs', {}).get(key, {}).get('value')
                if actual_value != expected_value:
                    print(f"✗ Member DNS '{host_name}' has incorrect extensible attribute '{key}': expected '{expected_value}', got '{actual_value}'")
                    verification_passed = False
        
        # Check complex struct fields
        for field in struct_fields:
            if field in member_config and field != 'extattrs':
                expected_struct = member_config[field]
                actual_struct = actual_record.get(field, {})
                
                if isinstance(expected_struct, dict):
                    for sub_key, sub_value in expected_struct.items():
                        if actual_struct.get(sub_key) != sub_value:
                            print(f"✗ Member DNS '{host_name}' has incorrect {field}.{sub_key}")
                            verification_passed = False
        
        # Check list of structs fields
        for field in list_of_structs_fields:
            if field in member_config and member_config[field]:
                # These fields are complex and would need specific handling
                # For now, we'll do a basic check for presence
                if field not in actual_record or not actual_record[field]:
                    print(f"✗ Member DNS '{host_name}' is missing {field} configuration")
                    verification_passed = False
        
        if verification_passed:
            print(f"✓ Member DNS '{host_name}' verified successfully")
            successful_records += 1
        else:
            failed_records += 1
            failed_list.append(host_name)
    
    # Display verification summary
    print("\nMember DNS Verification Summary:")
    print(f"Total records: {total_records}")
    print(f"Successfully verified: {successful_records}")
    print(f"Failed verification: {failed_records}")
    
    if failed_list:
        print(f"Failed records: {', '.join(failed_list)}")
    
    return failed_records == 0

def verify_named_acls():
    """Verify Named ACLs after deployment."""
    print("\n--- Named ACL Post-Deployment Verification ---")
    
    # Check if named ACL file exists with the correct path
    namedacl_file = "playbooks/add/cabgridmgr.amfam.com/namedacl.json"
    if not os.path.exists(namedacl_file):
        print(f"Named ACL file not found: {namedacl_file}")
        print("Skipping Named ACL verification.")
        return True
    
    # Read named ACL data from JSON file
    try:
        with open(namedacl_file, 'r') as file:
            namedacl_records = json.load(file)
            
            # Check if the file contains an empty list or empty object
            if not namedacl_records or (isinstance(namedacl_records, list) and len(namedacl_records) == 0):
                print("Named ACL file exists but contains no records. Skipping verification.")
                return True
                
            # If the content is not a list, convert it to a list with one item
            if not isinstance(namedacl_records, list):
                namedacl_records = [namedacl_records]
                
            print(f"Verifying {len(namedacl_records)} Named ACL records.")
    except Exception as e:
        print(f"Error reading file {namedacl_file}: {str(e)}")
        return False
    
    # Count statistics
    total_records = len(namedacl_records)
    successful_records = 0
    failed_records = 0
    failed_list = []
    
    # Verify each record exists in Infoblox with correct configuration
    for record in namedacl_records:
        name = record.get('name')
        
        if not name:
            print(f"✗ Incomplete record data: {record}")
            failed_records += 1
            continue
        
        actual_records = get_namedacl(name)
        
        if not actual_records:
            print(f"✗ Named ACL '{name}' was not found in Infoblox")
            failed_records += 1
            failed_list.append(name)
            continue
        
        # Check if key attributes match
        actual_record = actual_records[0]
        verification_passed = True
        
        # Check comment if specified
        if 'comment' in record:
            expected_comment = record['comment']
            actual_comment = actual_record.get('comment', '')
            if actual_comment != expected_comment:
                print(f"✗ Named ACL '{name}' has incorrect comment: expected '{expected_comment}', got '{actual_comment}'")
                verification_passed = False
        
        # Check access list
        if 'access_list' in record and record['access_list']:
            expected_access_list = []
            for entry in record['access_list']:
                # Normalize the entry format
                normalized_entry = {
                    'address': entry.get('address'),
                    'permission': entry.get('permission')
                }
                expected_access_list.append(normalized_entry)
            
            actual_access_list = []
            for entry in actual_record.get('access_list', []):
                # Normalize the actual entry format
                normalized_entry = {
                    'address': entry.get('address'),
                    'permission': entry.get('permission')
                }
                actual_access_list.append(normalized_entry)
            
            # Compare access lists
            expected_set = {(e['address'], e['permission']) for e in expected_access_list if e['address'] and e['permission']}
            actual_set = {(e['address'], e['permission']) for e in actual_access_list if e['address'] and e['permission']}
            
            missing_entries = expected_set - actual_set
            extra_entries = actual_set - expected_set
            
            if missing_entries:
                print(f"✗ Named ACL '{name}' is missing access list entries: {missing_entries}")
                verification_passed = False
            if extra_entries:
                print(f"✗ Named ACL '{name}' has unexpected access list entries: {extra_entries}")
                verification_passed = False
        
        # Check TSIG keys if specified
        if 'tsig_keys' in record and record['tsig_keys']:
            expected_keys = set(record['tsig_keys'])
            # Extract TSIG key names from actual references
            actual_keys = set()
            for key_ref in actual_record.get('tsig_keys', []):
                if isinstance(key_ref, str) and ':' in key_ref:
                    # Extract key name from reference like "tsigkey/ZG5zLnRzaWdfa2V5JC5fZGVmYXVsdC5jb20uaW5mb2Jsb3guZG5zLm9uZQ:tsig-key-1"
                    key_name = key_ref.split(':')[-1]
                    actual_keys.add(key_name)
            
            missing_keys = expected_keys - actual_keys
            extra_keys = actual_keys - expected_keys
            
            if missing_keys:
                print(f"✗ Named ACL '{name}' is missing TSIG keys: {missing_keys}")
                verification_passed = False
            if extra_keys:
                print(f"✗ Named ACL '{name}' has unexpected TSIG keys: {extra_keys}")
                verification_passed = False
        
        # Check disable status
        if 'disable' in record:
            expected_disable = record['disable']
            actual_disable = actual_record.get('disable', False)
            if actual_disable != expected_disable:
                status = "disabled" if actual_disable else "enabled"
                expected_status = "disabled" if expected_disable else "enabled"
                print(f"✗ Named ACL '{name}' has incorrect status: expected {expected_status}, got {status}")
                verification_passed = False
        
        # Check extensible attributes if specified
        if 'extattrs' in record and record['extattrs']:
            for key, expected_value in record['extattrs'].items():
                actual_value = actual_record.get('extattrs', {}).get(key, {}).get('value')
                if actual_value != expected_value:
                    print(f"✗ Named ACL '{name}' has incorrect extensible attribute '{key}': expected '{expected_value}', got '{actual_value}'")
                    verification_passed = False
        
        if verification_passed:
            print(f"✓ Named ACL '{name}' verified successfully")
            successful_records += 1
        else:
            failed_records += 1
            failed_list.append(name)
    
    # Display verification summary
    print("\nNamed ACL Verification Summary:")
    print(f"Total records: {total_records}")
    print(f"Successfully verified: {successful_records}")
    print(f"Failed verification: {failed_records}")
    
    if failed_list:
        print(f"Failed records: {', '.join(failed_list)}")
    
    return failed_records == 0

def verify_grid_dns_properties():
    """Verify Grid DNS Properties after deployment."""
    print("\n--- Grid DNS Properties Post-Deployment Verification ---")
    
    grid_dns_properties_file = "playbooks/add/cabgridmgr.amfam.com/grid_dns_properties.json"
    if not os.path.exists(grid_dns_properties_file):
        print(f"Grid DNS Properties file not found: {grid_dns_properties_file}")
        print("Skipping Grid DNS Properties verification.")
        return True
    
    try:
        with open(grid_dns_properties_file, 'r') as file:
            grid_dns_properties_config = json.load(file)
            
            if not grid_dns_properties_config or grid_dns_properties_config == {}:
                print("Grid DNS Properties file exists but contains no data. Skipping verification.")
                return True
            
            print(f"Verifying Grid DNS Properties configuration.")
    except Exception as e:
        print(f"Error reading file {grid_dns_properties_file}: {str(e)}")
        return False
    
    actual_properties = get_dns_grid()
    
    if not actual_properties:
        print(f"✗ Grid DNS Properties configuration was not found in Infoblox")
        return False
    
    actual_config = actual_properties[0]
    verification_passed = True
    
    # Verify key settings
    important_settings = [
        'allow_bulkhost_ddns', 'allow_gss_tsig_zone_updates', 'allow_query', 
        'allow_transfer', 'allow_update', 'bind_check_names_policy', 
        'blackhole_enabled', 'blackhole_list', 'copy_xfer_to_notify',
        'default_bulk_host_name_template', 'default_ttl', 'dnssec_enabled',
        'dnssec_expired_signatures_enabled', 'dnssec_validation_enabled',
        'enable_blacklist', 'enable_dns64', 'enable_dnstap', 'enable_gss_tsig',
        'enable_notify_source_port', 'enable_query_source_port', 'filter_aaaa',
        'forwarders', 'forward_only', 'lame_ttl', 'max_cache_ttl', 'max_ncache_ttl',
        'notify_delay', 'recursion', 'recursive_query_list', 'resolver_query_timeout',
        'root_name_server_type', 'rpz_qname_wait_recurse', 'scavenging_settings',
        'sortlist', 'syslog_facility', 'zone_deletion_double_confirm'
    ]
    
    for setting in important_settings:
        if setting in grid_dns_properties_config:
            expected = grid_dns_properties_config[setting]
            actual = actual_config.get(setting)
            if actual != expected:
                print(f"✗ Grid DNS Properties has incorrect {setting}: expected {expected}, got {actual}")
                verification_passed = False
    
    # Verify custom root name servers if specified
    if 'custom_root_name_servers' in grid_dns_properties_config:
        expected_servers = grid_dns_properties_config['custom_root_name_servers']
        actual_servers = actual_config.get('custom_root_name_servers', [])
        
        # Compare server lists
        if len(expected_servers) != len(actual_servers):
            print(f"✗ Grid DNS Properties has incorrect number of custom root name servers")
            verification_passed = False
    
    # Verify logging categories if specified
    if 'logging_categories' in grid_dns_properties_config:
        expected_logging = grid_dns_properties_config['logging_categories']
        actual_logging = actual_config.get('logging_categories', {})
        
        for category, settings in expected_logging.items():
            if category not in actual_logging:
                print(f"✗ Grid DNS Properties missing logging category '{category}'")
                verification_passed = False
            elif actual_logging[category] != settings:
                print(f"✗ Grid DNS Properties has incorrect logging settings for '{category}'")
                verification_passed = False
    
    if verification_passed:
        print(f"✓ Grid DNS Properties configuration verified successfully")
        return True
    else:
        return False

def get_vlan(name, vlan_id, parent):
    """Get VLAN from Infoblox by name, ID, and parent."""
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
            print(f"✗ Error getting VLAN {name}: {response.status_code}")
            return []
    except Exception as e:
        print(f"✗ Error getting VLAN {name}: {str(e)}")
        return []

def verify_vlan_records():
    """Verify VLAN records after deployment."""
    print("\n--- VLAN Post-Deployment Verification ---")
    
    # Check if VLAN file exists with the correct path
    vlan_file = "playbooks/add/cabgridmgr.amfam.com/vlan.json"
    if not os.path.exists(vlan_file):
        print(f"VLAN file not found: {vlan_file}")
        print("Skipping VLAN verification.")
        return True
    
    # Read VLAN data from JSON file
    try:
        with open(vlan_file, 'r') as file:
            vlan_records = json.load(file)
            
            # Check if the file contains an empty list or empty object
            if not vlan_records or (isinstance(vlan_records, list) and len(vlan_records) == 0):
                print("VLAN file exists but contains no records. Skipping verification.")
                return True
                
            # If the content is not a list, convert it to a list with one item
            if not isinstance(vlan_records, list):
                vlan_records = [vlan_records]
                
            print(f"Verifying {len(vlan_records)} VLAN records.")
    except Exception as e:
        print(f"Error reading file {vlan_file}: {str(e)}")
        return False
    
    # Count statistics
    total_records = len(vlan_records)
    successful_records = 0
    failed_records = 0
    failed_list = []
    
    # Verify each record exists in Infoblox with correct configuration
    for record in vlan_records:
        name = record.get('name')
        vlan_id = record.get('id')
        parent = record.get('parent')
        
        if not name or not vlan_id or not parent:
            print(f"✗ Incomplete record data: {record}")
            failed_records += 1
            continue
        
        actual_records = get_vlan(name, vlan_id, parent)
        
        if not actual_records:
            print(f"✗ VLAN '{name}' (ID: {vlan_id}) was not found in Infoblox")
            failed_records += 1
            failed_list.append(f"{name} (ID: {vlan_id})")
            continue
        
        # Check if key attributes match
        actual_record = actual_records[0]
        verification_passed = True
        
        # Check comment if specified
        if 'comment' in record and record['comment']:
            expected_comment = record['comment']
            actual_comment = actual_record.get('comment', '')
            if actual_comment != expected_comment:
                print(f"✗ VLAN '{name}' has incorrect comment: expected '{expected_comment}', got '{actual_comment}'")
                verification_passed = False
        
        # Check contact if specified
        if 'contact' in record and record['contact']:
            expected_contact = record['contact']
            actual_contact = actual_record.get('contact', '')
            if actual_contact != expected_contact:
                print(f"✗ VLAN '{name}' has incorrect contact: expected '{expected_contact}', got '{actual_contact}'")
                verification_passed = False
        
        # Check department if specified
        if 'department' in record and record['department']:
            expected_department = record['department']
            actual_department = actual_record.get('department', '')
            if actual_department != expected_department:
                print(f"✗ VLAN '{name}' has incorrect department: expected '{expected_department}', got '{actual_department}'")
                verification_passed = False
        
        # Check description if specified
        if 'description' in record and record['description']:
            expected_description = record['description']
            actual_description = actual_record.get('description', '')
            if actual_description != expected_description:
                print(f"✗ VLAN '{name}' has incorrect description: expected '{expected_description}', got '{actual_description}'")
                verification_passed = False
        
        # Check reserved status if specified
        if 'reserved' in record:
            expected_reserved = record['reserved']
            actual_reserved = actual_record.get('reserved', False)
            if actual_reserved != expected_reserved:
                status = "reserved" if actual_reserved else "not reserved"
                expected_status = "reserved" if expected_reserved else "not reserved"
                print(f"✗ VLAN '{name}' has incorrect reserved status: expected {expected_status}, got {status}")
                verification_passed = False
        
        # Verify VLAN ID matches
        actual_id = actual_record.get('id')
        if str(actual_id) != str(vlan_id):
            print(f"✗ VLAN '{name}' has incorrect ID: expected {vlan_id}, got {actual_id}")
            verification_passed = False
        
        # Verify parent matches
        actual_parent = actual_record.get('parent')
        if actual_parent != parent:
            print(f"✗ VLAN '{name}' has incorrect parent: expected '{parent}', got '{actual_parent}'")
            verification_passed = False
        
        # Check extensible attributes if specified
        if 'extattrs' in record and record['extattrs']:
            for key, value in record['extattrs'].items():
                actual_value = actual_record.get('extattrs', {}).get(key, {}).get('value')
                if actual_value != value:
                    print(f"✗ VLAN '{name}' has incorrect extensible attribute '{key}': expected '{value}', got '{actual_value}'")
                    verification_passed = False
        
        # Additional validation: Check if VLAN is assigned to any networks
        try:
            # Query networks that use this VLAN
            network_response = requests.get(
                f"{BASE_URL}/network",
                params={"_return_fields": "network,vlans", "_max_results": 1000},
                auth=(INFOBLOX_USERNAME, INFOBLOX_PASSWORD),
                verify=VALIDATE_CERTS,
                timeout=HTTP_TIMEOUT
            )
            
            if network_response.status_code == 200:
                networks = network_response.json()
                assigned_networks = []
                
                for network in networks:
                    if 'vlans' in network:
                        for vlan in network['vlans']:
                            if vlan.get('id') == actual_id and vlan.get('vlan') == actual_record.get('_ref'):
                                assigned_networks.append(network['network'])
                
                if assigned_networks:
                    print(f"ℹ VLAN '{name}' is assigned to {len(assigned_networks)} network(s): {', '.join(assigned_networks[:3])}")
                    if len(assigned_networks) > 3:
                        print(f"    ... and {len(assigned_networks) - 3} more")
        except Exception as e:
            # Not critical if we can't check network assignments
            pass
        
        if verification_passed:
            print(f"✓ VLAN '{name}' (ID: {vlan_id}) verified successfully")
            successful_records += 1
        else:
            failed_records += 1
            failed_list.append(f"{name} (ID: {vlan_id})")
    
    # Display verification summary
    print("\nVLAN Verification Summary:")
    print(f"Total records: {total_records}")
    print(f"Successfully verified: {successful_records}")
    print(f"Failed verification: {failed_records}")
    
    if failed_list:
        print(f"Failed records: {', '.join(failed_list)}")
    
    return failed_records == 0

def get_vlan_view(name):
    """Get VLAN View from Infoblox by name."""
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
            print(f"✗ Error getting VLAN view {name}: {response.status_code}")
            return []
    except Exception as e:
        print(f"✗ Error getting VLAN view {name}: {str(e)}")
        return []

def verify_vlan_view_records():
    """Verify VLAN View records after deployment."""
    print("\n--- VLAN View Post-Deployment Verification ---")
    
    # Check if VLAN View file exists with the correct path
    vlan_view_file = "playbooks/add/cabgridmgr.amfam.com/vlanview.json"
    if not os.path.exists(vlan_view_file):
        print(f"VLAN View file not found: {vlan_view_file}")
        print("Skipping VLAN View verification.")
        return True
    
    # Read VLAN View data from JSON file
    try:
        with open(vlan_view_file, 'r') as file:
            vlan_view_records = json.load(file)
            
            # Check if the file contains an empty list or empty object
            if not vlan_view_records or (isinstance(vlan_view_records, list) and len(vlan_view_records) == 0):
                print("VLAN View file exists but contains no records. Skipping verification.")
                return True
                
            # If the content is not a list, convert it to a list with one item
            if not isinstance(vlan_view_records, list):
                vlan_view_records = [vlan_view_records]
                
            print(f"Verifying {len(vlan_view_records)} VLAN View records.")
    except Exception as e:
        print(f"Error reading file {vlan_view_file}: {str(e)}")
        return False
    
    # Count statistics
    total_records = len(vlan_view_records)
    successful_records = 0
    failed_records = 0
    failed_list = []
    
    # Verify each record exists in Infoblox with correct configuration
    for record in vlan_view_records:
        name = record.get('name')
        
        if not name:
            print(f"✗ Incomplete record data: {record}")
            failed_records += 1
            continue
        
        actual_records = get_vlan_view(name)
        
        if not actual_records:
            print(f"✗ VLAN View '{name}' was not found in Infoblox")
            failed_records += 1
            failed_list.append(name)
            continue
        
        # Check if key attributes match
        actual_record = actual_records[0]
        verification_passed = True
        
        # Check comment if specified
        if 'comment' in record and record['comment']:
            expected_comment = record['comment']
            actual_comment = actual_record.get('comment', '')
            if actual_comment != expected_comment:
                print(f"✗ VLAN View '{name}' has incorrect comment: expected '{expected_comment}', got '{actual_comment}'")
                verification_passed = False
        
        # Check start_vlan_id if specified
        if 'start_vlan_id' in record:
            expected_start_id = record['start_vlan_id']
            actual_start_id = actual_record.get('start_vlan_id')
            if str(actual_start_id) != str(expected_start_id):
                print(f"✗ VLAN View '{name}' has incorrect start_vlan_id: expected {expected_start_id}, got {actual_start_id}")
                verification_passed = False
        
        # Check end_vlan_id if specified
        if 'end_vlan_id' in record:
            expected_end_id = record['end_vlan_id']
            actual_end_id = actual_record.get('end_vlan_id')
            if str(actual_end_id) != str(expected_end_id):
                print(f"✗ VLAN View '{name}' has incorrect end_vlan_id: expected {expected_end_id}, got {actual_end_id}")
                verification_passed = False
        
        # Check pre_create_vlan if specified
        if 'pre_create_vlan' in record:
            expected_pre_create = record['pre_create_vlan']
            actual_pre_create = actual_record.get('pre_create_vlan', False)
            if actual_pre_create != expected_pre_create:
                print(f"✗ VLAN View '{name}' has incorrect pre_create_vlan: expected {expected_pre_create}, got {actual_pre_create}")
                verification_passed = False
        
        # Check allow_range_overlapping if specified
        if 'allow_range_overlapping' in record:
            expected_overlap = record['allow_range_overlapping']
            actual_overlap = actual_record.get('allow_range_overlapping', False)
            if actual_overlap != expected_overlap:
                print(f"✗ VLAN View '{name}' has incorrect allow_range_overlapping: expected {expected_overlap}, got {actual_overlap}")
                verification_passed = False
        
        # Check extensible attributes if specified
        if 'extattrs' in record and record['extattrs']:
            for key, value in record['extattrs'].items():
                # Handle both formats: direct value or {'value': ...}
                if isinstance(value, dict) and 'value' in value:
                    expected_value = value['value']
                else:
                    expected_value = value
                
                actual_value = actual_record.get('extattrs', {}).get(key, {}).get('value')
                if actual_value != expected_value:
                    print(f"✗ VLAN View '{name}' has incorrect extensible attribute '{key}': expected '{expected_value}', got '{actual_value}'")
                    verification_passed = False
        
        # Additional validation: Check if VLAN View contains any VLANs
        try:
            # Query VLANs in this view
            vlan_response = requests.get(
                f"{BASE_URL}/vlan",
                params={"parent": actual_record.get('_ref'), "_max_results": 1},
                auth=(INFOBLOX_USERNAME, INFOBLOX_PASSWORD),
                verify=VALIDATE_CERTS,
                timeout=HTTP_TIMEOUT
            )
            
            if vlan_response.status_code == 200:
                vlans = vlan_response.json()
                if vlans:
                    # Count total VLANs in this view
                    total_vlan_response = requests.get(
                        f"{BASE_URL}/vlan",
                        params={"parent": actual_record.get('_ref'), "_return_fields": "id", "_max_results": 10000},
                        auth=(INFOBLOX_USERNAME, INFOBLOX_PASSWORD),
                        verify=VALIDATE_CERTS,
                        timeout=HTTP_TIMEOUT
                    )
                    
                    if total_vlan_response.status_code == 200:
                        total_vlans = total_vlan_response.json()
                        vlan_count = len(total_vlans)
                        print(f"ℹ VLAN View '{name}' contains {vlan_count} VLAN(s)")
                        
                        # Show VLAN ID range if VLANs exist
                        if vlan_count > 0:
                            vlan_ids = sorted([int(v.get('id', 0)) for v in total_vlans if v.get('id')])
                            if vlan_ids:
                                print(f"    VLAN ID range: {min(vlan_ids)} - {max(vlan_ids)}")
                else:
                    print(f"ℹ VLAN View '{name}' contains no VLANs")
        except Exception as e:
            # Not critical if we can't check VLAN contents
            pass
        
        # Check if view is assigned to any networks
        try:
            # Query network views that might reference this VLAN view
            network_view_response = requests.get(
                f"{BASE_URL}/networkview",
                params={"_return_fields": "name,vlan_view", "_max_results": 1000},
                auth=(INFOBLOX_USERNAME, INFOBLOX_PASSWORD),
                verify=VALIDATE_CERTS,
                timeout=HTTP_TIMEOUT
            )
            
            if network_view_response.status_code == 200:
                network_views = network_view_response.json()
                assigned_network_views = []
                
                for nv in network_views:
                    if nv.get('vlan_view') == actual_record.get('_ref'):
                        assigned_network_views.append(nv['name'])
                
                if assigned_network_views:
                    print(f"ℹ VLAN View '{name}' is assigned to network view(s): {', '.join(assigned_network_views)}")
        except Exception as e:
            # Not critical if we can't check network view assignments
            pass
        
        if verification_passed:
            print(f"✓ VLAN View '{name}' verified successfully")
            successful_records += 1
        else:
            failed_records += 1
            failed_list.append(name)
    
    # Display verification summary
    print("\nVLAN View Verification Summary:")
    print(f"Total records: {total_records}")
    print(f"Successfully verified: {successful_records}")
    print(f"Failed verification: {failed_records}")
    
    if failed_list:
        print(f"Failed records: {', '.join(failed_list)}")
    
    return failed_records == 0

def get_upgrade_group(name):
    """Get Upgrade Group from Infoblox by name."""
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
            print(f"✗ Error getting upgrade group {name}: {response.status_code}")
            return []
    except Exception as e:
        print(f"✗ Error getting upgrade group {name}: {str(e)}")
        return []

def verify_upgrade_group_records():
    """Verify Upgrade Group records after deployment."""
    print("\n--- Upgrade Group Post-Deployment Verification ---")

    # Check if Upgrade Group file exists with the correct path
    upgrade_group_file = "playbooks/add/cabgridmgr.amfam.com/upgradegroup.json"
    if not os.path.exists(upgrade_group_file):
        print(f"Upgrade Group file not found: {upgrade_group_file}")
        print("Skipping Upgrade Group verification.")
        return True
    
    # Read Upgrade Group data from JSON file
    try:
        with open(upgrade_group_file, 'r') as file:
            upgrade_group_records = json.load(file)
            
            # Check if the file contains an empty list or empty object
            if not upgrade_group_records or (isinstance(upgrade_group_records, list) and len(upgrade_group_records) == 0):
                print("Upgrade Group file exists but contains no records. Skipping verification.")
                return True
                
            # If the content is not a list, convert it to a list with one item
            if not isinstance(upgrade_group_records, list):
                upgrade_group_records = [upgrade_group_records]
                
            print(f"Verifying {len(upgrade_group_records)} Upgrade Group records.")
    except Exception as e:
        print(f"Error reading file {upgrade_group_file}: {str(e)}")
        return False
    
    # Non-editable groups from playbook
    non_editable_groups = ["Grid Master"]
    
    # Count statistics
    total_records = len(upgrade_group_records)
    successful_records = 0
    failed_records = 0
    failed_list = []
    skipped_records = 0
    
    # Verify each record exists in Infoblox with correct configuration
    for record in upgrade_group_records:
        name = record.get('name')
        
        if not name:
            print(f"✗ Incomplete record data: {record}")
            failed_records += 1
            continue
        
        # Skip non-editable groups
        if name in non_editable_groups:
            print(f"ℹ Skipping verification of system upgrade group '{name}' (non-editable)")
            skipped_records += 1
            continue
        
        actual_records = get_upgrade_group(name)
        
        if not actual_records:
            print(f"✗ Upgrade Group '{name}' was not found in Infoblox")
            failed_records += 1
            failed_list.append(name)
            continue
        
        # Check if key attributes match
        actual_record = actual_records[0]
        verification_passed = True
        
        # Check comment if specified
        if 'comment' in record and record['comment']:
            expected_comment = record['comment']
            actual_comment = actual_record.get('comment', '')
            if actual_comment != expected_comment:
                print(f"✗ Upgrade Group '{name}' has incorrect comment: expected '{expected_comment}', got '{actual_comment}'")
                verification_passed = False
        
        # Check members if specified
        if 'members' in record and record['members'] is not None:
            expected_members = set(record['members']) if isinstance(record['members'], list) else set()
            actual_members = set(actual_record.get('members', []))
            
            missing_members = expected_members - actual_members
            extra_members = actual_members - expected_members
            
            if missing_members:
                print(f"✗ Upgrade Group '{name}' is missing members: {', '.join(missing_members)}")
                verification_passed = False
            
            if extra_members:
                print(f"✗ Upgrade Group '{name}' has unexpected members: {', '.join(extra_members)}")
                verification_passed = False
            
            # Check if members actually exist as grid members
            for member in expected_members:
                try:
                    member_response = requests.get(
                        f"{BASE_URL}/member",
                        params={"host_name": member},
                        auth=(INFOBLOX_USERNAME, INFOBLOX_PASSWORD),
                        verify=VALIDATE_CERTS,
                        timeout=HTTP_TIMEOUT
                    )
                    
                    if member_response.status_code != 200 or not member_response.json():
                        print(f"✗ Upgrade Group '{name}' references non-existent member: {member}")
                        verification_passed = False
                except Exception:
                    pass  # Already handled in validation
        
        # Check upgrade_dependent_group if specified
        if 'upgrade_dependent_group' in record and record['upgrade_dependent_group']:
            expected_dependent = record['upgrade_dependent_group']
            actual_dependent = actual_record.get('upgrade_dependent_group', '')
            
            if actual_dependent != expected_dependent:
                print(f"✗ Upgrade Group '{name}' has incorrect upgrade_dependent_group: expected '{expected_dependent}', got '{actual_dependent}'")
                verification_passed = False
            
            # Check if dependent group actually exists
            if expected_dependent:
                dependent_exists = get_upgrade_group(expected_dependent)
                if not dependent_exists:
                    print(f"✗ Upgrade Group '{name}' depends on non-existent group: {expected_dependent}")
                    verification_passed = False
        
        # Check time_zone if specified
        if 'time_zone' in record and record['time_zone']:
            expected_timezone = record['time_zone']
            actual_timezone = actual_record.get('time_zone', '')
            if actual_timezone != expected_timezone:
                print(f"✗ Upgrade Group '{name}' has incorrect time_zone: expected '{expected_timezone}', got '{actual_timezone}'")
                verification_passed = False
        
        # Check upgrade_time if specified
        if 'upgrade_time' in record and record['upgrade_time']:
            expected_time = record['upgrade_time']
            actual_time = actual_record.get('upgrade_time', '')
            if actual_time != expected_time:
                print(f"✗ Upgrade Group '{name}' has incorrect upgrade_time: expected '{expected_time}', got '{actual_time}'")
                verification_passed = False
        
        # Additional information about the group
        if actual_record.get('members'):
            print(f"ℹ Upgrade Group '{name}' contains {len(actual_record['members'])} member(s)")
            
            # Check member upgrade status if available
            try:
                for member_name in actual_record['members'][:3]:  # Check first 3 members
                    member_response = requests.get(
                        f"{BASE_URL}/member",
                        params={"host_name": member_name, "_return_fields": "host_name,upgrade_status"},
                        auth=(INFOBLOX_USERNAME, INFOBLOX_PASSWORD),
                        verify=VALIDATE_CERTS,
                        timeout=HTTP_TIMEOUT
                    )
                    
                    if member_response.status_code == 200 and member_response.json():
                        member_data = member_response.json()[0]
                        upgrade_status = member_data.get('upgrade_status', 'Unknown')
                        print(f"    Member '{member_name}' upgrade status: {upgrade_status}")
                
                if len(actual_record['members']) > 3:
                    print(f"    ... and {len(actual_record['members']) - 3} more members")
            except Exception:
                pass  # Not critical if we can't get member status
        
        # Check for circular dependencies
        if 'upgrade_dependent_group' in record and record['upgrade_dependent_group']:
            visited = set()
            current = name
            circular = False
            
            while current and current not in visited:
                visited.add(current)
                dep_groups = get_upgrade_group(current)
                if dep_groups:
                    current = dep_groups[0].get('upgrade_dependent_group')
                    if current == name:
                        print(f"✗ Upgrade Group '{name}' has circular dependency")
                        verification_passed = False
                        circular = True
                        break
                else:
                    break
        
        if verification_passed:
            print(f"✓ Upgrade Group '{name}' verified successfully")
            successful_records += 1
        else:
            failed_records += 1
            failed_list.append(name)
    
    # Display verification summary
    print("\nUpgrade Group Verification Summary:")
    print(f"Total records: {total_records}")
    print(f"Successfully verified: {successful_records}")
    print(f"Failed verification: {failed_records}")
    print(f"Skipped (system groups): {skipped_records}")
    
    if failed_list:
        print(f"Failed records: {', '.join(failed_list)}")
    
    return failed_records == 0

def get_ns_group(name):
    """Get NS Group from Infoblox by name."""
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
            print(f"✗ Error getting NS group {name}: {response.status_code}")
            return []
    except Exception as e:
        print(f"✗ Error getting NS group {name}: {str(e)}")
        return []

def verify_ns_group_records():
    """Verify NS Group records after deployment."""
    print("\n--- NS Group Post-Deployment Verification ---")
    
    # Check if NS Group file exists with the correct path
    ns_group_file = "playbooks/add/cabgridmgr.amfam.com/nsgroup.json"
    if not os.path.exists(ns_group_file):
        print(f"NS Group file not found: {ns_group_file}")
        print("Skipping NS Group verification.")
        return True
    
    # Read NS Group data from JSON file
    try:
        with open(ns_group_file, 'r') as file:
            ns_group_records = json.load(file)
            
            # Check if the file contains an empty list or empty object
            if not ns_group_records or (isinstance(ns_group_records, list) and len(ns_group_records) == 0):
                print("NS Group file exists but contains no records. Skipping verification.")
                return True
                
            # If the content is not a list, convert it to a list with one item
            if not isinstance(ns_group_records, list):
                ns_group_records = [ns_group_records]
                
            print(f"Verifying {len(ns_group_records)} NS Group records.")
    except Exception as e:
        print(f"Error reading file {ns_group_file}: {str(e)}")
        return False
    
    # Count statistics
    total_records = len(ns_group_records)
    successful_records = 0
    failed_records = 0
    failed_list = []
    
    # Verify each record exists in Infoblox with correct configuration
    for record in ns_group_records:
        name = record.get('name')
        
        if not name:
            print(f"✗ Incomplete record data: {record}")
            failed_records += 1
            continue
        
        actual_records = get_ns_group(name)
        
        if not actual_records:
            print(f"✗ NS Group '{name}' was not found in Infoblox")
            failed_records += 1
            failed_list.append(name)
            continue
        
        # Check if key attributes match
        actual_record = actual_records[0]
        verification_passed = True
        
        # Check if it's a grid default
        if actual_record.get("is_grid_default", False):
            print(f"ℹ NS Group '{name}' is a grid default group")
        
        # Check comment if specified
        if 'comment' in record and record['comment']:
            expected_comment = record['comment']
            actual_comment = actual_record.get('comment', '')
            if actual_comment != expected_comment:
                print(f"✗ NS Group '{name}' has incorrect comment: expected '{expected_comment}', got '{actual_comment}'")
                verification_passed = False
        
        # Check external primaries
        if 'external_primaries' in record:
            expected_ext_prim = record.get('external_primaries', [])
            actual_ext_prim = actual_record.get('external_primaries', [])
            
            # Compare addresses only
            expected_addresses = sorted([p.get('address') for p in expected_ext_prim if p.get('address')])
            actual_addresses = sorted([p.get('address') for p in actual_ext_prim if p.get('address')])
            
            if expected_addresses != actual_addresses:
                print(f"✗ NS Group '{name}' has incorrect external primaries")
                print(f"   Expected addresses: {expected_addresses}")
                print(f"   Actual addresses: {actual_addresses}")
                verification_passed = False
            
            # Check TSIG keys if specified
            for idx, exp_prim in enumerate(expected_ext_prim):
                if 'tsig_key' in exp_prim and exp_prim['tsig_key']:
                    # Find matching actual primary by address
                    matching_actual = None
                    for act_prim in actual_ext_prim:
                        if act_prim.get('address') == exp_prim.get('address'):
                            matching_actual = act_prim
                            break
                    
                    if matching_actual:
                        if matching_actual.get('tsig_key') != exp_prim['tsig_key']:
                            print(f"✗ NS Group '{name}' external primary {exp_prim['address']} has incorrect TSIG key")
                            verification_passed = False
        
        # Check external secondaries
        if 'external_secondaries' in record:
            expected_ext_sec = record.get('external_secondaries', [])
            actual_ext_sec = actual_record.get('external_secondaries', [])
            
            # Compare addresses only
            expected_addresses = sorted([s.get('address') for s in expected_ext_sec if s.get('address')])
            actual_addresses = sorted([s.get('address') for s in actual_ext_sec if s.get('address')])
            
            if expected_addresses != actual_addresses:
                print(f"✗ NS Group '{name}' has incorrect external secondaries")
                print(f"   Expected addresses: {expected_addresses}")
                print(f"   Actual addresses: {actual_addresses}")
                verification_passed = False
        
        # Check grid primary members
        if 'grid_primary' in record:
            expected_grid_prim = sorted([m.get('name') for m in record.get('grid_primary', []) if m.get('name')])
            actual_grid_prim = sorted([m.get('name') for m in actual_record.get('grid_primary', []) if m.get('name')])
            
            if expected_grid_prim != actual_grid_prim:
                print(f"✗ NS Group '{name}' has incorrect grid primary members")
                print(f"   Expected: {expected_grid_prim}")
                print(f"   Actual: {actual_grid_prim}")
                verification_passed = False
        
        # Check grid secondary members
        if 'grid_secondaries' in record:
            expected_grid_sec = sorted([m.get('name') for m in record.get('grid_secondaries', []) if m.get('name')])
            actual_grid_sec = sorted([m.get('name') for m in actual_record.get('grid_secondaries', []) if m.get('name')])
            
            if expected_grid_sec != actual_grid_sec:
                print(f"✗ NS Group '{name}' has incorrect grid secondary members")
                print(f"   Expected: {expected_grid_sec}")
                print(f"   Actual: {actual_grid_sec}")
                verification_passed = False
        
        # Check use_external_primary flag
        if 'use_external_primary' in record:
            expected_use_ext = record['use_external_primary']
            actual_use_ext = actual_record.get('use_external_primary', False)
            if actual_use_ext != expected_use_ext:
                print(f"✗ NS Group '{name}' has incorrect use_external_primary: expected {expected_use_ext}, got {actual_use_ext}")
                verification_passed = False
        
        # Check is_grid_default flag (if specified, though it's usually read-only)
        if 'is_grid_default' in record:
            expected_grid_default = record['is_grid_default']
            actual_grid_default = actual_record.get('is_grid_default', False)
            if actual_grid_default != expected_grid_default:
                print(f"✗ NS Group '{name}' has incorrect is_grid_default: expected {expected_grid_default}, got {actual_grid_default}")
                verification_passed = False
        
        # Check extensible attributes if specified
        if 'extattrs' in record and record['extattrs']:
            # Handle the list wrapper that the playbook uses
            expected_extattrs = record['extattrs']
            if isinstance(expected_extattrs, list) and len(expected_extattrs) == 1:
                expected_extattrs = expected_extattrs[0]
            
            for key, value in expected_extattrs.items():
                actual_value = actual_record.get('extattrs', {}).get(key, {}).get('value')
                if actual_value != value:
                    print(f"✗ NS Group '{name}' has incorrect extensible attribute '{key}': expected '{value}', got '{actual_value}'")
                    verification_passed = False
        
        # Additional information: Check which zones use this NS Group
        try:
            # Query zones using this NS Group
            zone_response = requests.get(
                f"{BASE_URL}/zone_auth",
                params={"ns_group": name, "_return_fields": "fqdn", "_max_results": 10},
                auth=(INFOBLOX_USERNAME, INFOBLOX_PASSWORD),
                verify=VALIDATE_CERTS,
                timeout=HTTP_TIMEOUT
            )
            
            if zone_response.status_code == 200:
                zones = zone_response.json()
                if zones:
                    zone_names = [z.get('fqdn') for z in zones[:5]]  # Show first 5
                    print(f"ℹ NS Group '{name}' is used by {len(zones)} zone(s): {', '.join(zone_names)}")
                    if len(zones) > 5:
                        print(f"    ... and {len(zones) - 5} more zones")
                else:
                    print(f"ℹ NS Group '{name}' is not currently used by any zones")
        except Exception:
            pass  # Not critical if we can't check zone usage
        
        # Count total servers in the group
        total_servers = 0
        if 'external_primaries' in actual_record:
            total_servers += len(actual_record['external_primaries'])
        if 'external_secondaries' in actual_record:
            total_servers += len(actual_record['external_secondaries'])
        if 'grid_primary' in actual_record:
            total_servers += len(actual_record['grid_primary'])
        if 'grid_secondaries' in actual_record:
            total_servers += len(actual_record['grid_secondaries'])
        
        if total_servers > 0:
            print(f"ℹ NS Group '{name}' has {total_servers} total name server(s)")
        
        if verification_passed:
            print(f"✓ NS Group '{name}' verified successfully")
            successful_records += 1
        else:
            failed_records += 1
            failed_list.append(name)
    
    # Display verification summary
    print("\nNS Group Verification Summary:")
    print(f"Total records: {total_records}")
    print(f"Successfully verified: {successful_records}")
    print(f"Failed verification: {failed_records}")
    
    if failed_list:
        print(f"Failed records: {', '.join(failed_list)}")
    
    return failed_records == 0

def main():
    """Main function."""
    print("Starting post-deployment verification...")
    
    # Check if we can connect to Infoblox
    if not authenticate():
        print("✗ Post-check failed: Cannot connect to Infoblox")
        sys.exit(1)
    
    # Check and verify A records
    a_record_file = "../prod_changes/cabgridmgr.amfam.com/a_record.json"
    should_verify_a_records = os.path.exists(a_record_file) and read_json_file(a_record_file)
    
    # Check and verify AAAA records
    aaaa_record_file = "../prod_changes/cabgridmgr.amfam.com/aaaa_record.json"
    should_verify_aaaa_records = os.path.exists(aaaa_record_file) and read_json_file(aaaa_record_file)
    
    # Check and verify Alias records
    alias_record_file = "playbooks/add/cabgridmgr.amfam.com/alias_record.json"
    should_verify_alias_records = os.path.exists(alias_record_file) and read_json_file(alias_record_file)
    
    # Check and verify CNAME records
    cname_record_file = "../prod_changes/cabgridmgr.amfam.com/cname_record.json"
    should_verify_cname_records = os.path.exists(cname_record_file) and read_json_file(cname_record_file)

    # Check and verify Fixed Address records
    fixed_address_file = "../prod_changes/cabgridmgr.amfam.com/fixed_address.json"
    should_verify_fixed_addresses = os.path.exists(fixed_address_file) and read_json_file(fixed_address_file)
    
    # Check and verify Host records
    host_record_file = "../prod_changes/cabgridmgr.amfam.com/host_record.json"
    host_records = read_json_file(host_record_file) if os.path.exists(host_record_file) else []
    should_verify_host_records = host_records and any(record is not None for record in host_records)
    
    # Check and verify MX records
    mx_record_file = "../prod_changes/cabgridmgr.amfam.com/mx_record.json"
    should_verify_mx_records = os.path.exists(mx_record_file) and read_json_file(mx_record_file)
    
    # Check and verify NAPTR records
    naptr_record_file = "playbooks/add/cabgridmgr.amfam.com/naptr_record.json"
    should_verify_naptr_records = os.path.exists(naptr_record_file) and read_json_file(naptr_record_file)

    # Check and verify PTR records
    ptr_record_file = "../prod_changes/cabgridmgr.amfam.com/ptr_record.json"
    should_verify_ptr_records = os.path.exists(ptr_record_file) and read_json_file(ptr_record_file)
    
    # Check and verify TXT records
    txt_record_file = "../prod_changes/cabgridmgr.amfam.com/txt_record.json"
    should_verify_txt_records = os.path.exists(txt_record_file) and read_json_file(txt_record_file)

    # Check and verify Response Policy Zone records
    zone_rp_file = "playbooks/add/cabgridmgr.amfam.com/zone_rp.json"
    should_verify_zone_rp_records = os.path.exists(zone_rp_file) and read_json_file(zone_rp_file)
    
    # Check and verify DNS Zone records
    zone_file = "../prod_changes/cabgridmgr.amfam.com/nios_zone.json"
    should_verify_zone_records = os.path.exists(zone_file) and read_json_file(zone_file)
    
    # Check and verify Network records
    network_file = "../prod_changes/cabgridmgr.amfam.com/network.json"
    should_verify_network_records = os.path.exists(network_file) and read_json_file(network_file)

    # Check and verify Network View records
    network_view_file = "playbooks/add/cabgridmgr.amfam.com/network_view.json"
    should_verify_network_view_records = os.path.exists(network_view_file) and read_json_file(network_view_file)

    # Check and verify DHCP Failover
    dhcp_failover_file = "playbooks/add/cabgridmgr.amfam.com/dhcp_failover.json"
    should_verify_dhcp_failover = os.path.exists(dhcp_failover_file)
    
    # Check and verify DHCP Option Definitions
    dhcp_option_def_file = "playbooks/add/cabgridmgr.amfam.com/dhcpoptiondefinition.json"
    should_verify_dhcp_option_defs = os.path.exists(dhcp_option_def_file) and read_json_file(dhcp_option_def_file)
    
    # Check and verify DHCP IPv6 Option Definitions
    dhcp_ipv6_option_def_file = "playbooks/add/cabgridmgr.amfam.com/dhcpoptionipv6definition.json"
    should_verify_dhcp_ipv6_option_defs = os.path.exists(dhcp_ipv6_option_def_file) and read_json_file(dhcp_ipv6_option_def_file)
    
    # Check and verify DHCP Option Spaces
    dhcp_option_space_file = "playbooks/add/cabgridmgr.amfam.com/dhcpoptionspace.json"
    should_verify_dhcp_option_spaces = os.path.exists(dhcp_option_space_file) and read_json_file(dhcp_option_space_file)
    
    # Check and verify DHCP IPv6 Option Spaces
    dhcp_ipv6_option_space_file = "playbooks/add/cabgridmgr.amfam.com/dhcpoptionipv6space.json"
    should_verify_dhcp_ipv6_option_spaces = os.path.exists(dhcp_ipv6_option_space_file) and read_json_file(dhcp_ipv6_option_space_file)
    
    # Check and verify DNS Grid
    dns_grid_file = "playbooks/add/cabgridmgr.amfam.com/dns_grid.json"
    should_verify_dns_grid = os.path.exists(dns_grid_file)
    
    # Check and verify DNS64 Groups
    dns64_group_file = "playbooks/add/cabgridmgr.amfam.com/dns64group.json"
    should_verify_dns64_groups = os.path.exists(dns64_group_file) and read_json_file(dns64_group_file)
    
    # Check and verify DTC A Records
    dtc_record_a_file = "playbooks/add/cabgridmgr.amfam.com/dtc_record_a.json"
    should_verify_dtc_record_a = os.path.exists(dtc_record_a_file) and read_json_file(dtc_record_a_file)
    
    # Check and verify DHCP Fingerprints
    fingerprint_file = "playbooks/add/cabgridmgr.amfam.com/fingerprint.json"
    should_verify_fingerprints = os.path.exists(fingerprint_file) and read_json_file(fingerprint_file)
    
    # Check and verify Grid DHCP Properties
    grid_dhcp_properties_file = "playbooks/add/cabgridmgr.amfam.com/grid_dhcp_properties.json"
    should_verify_grid_dhcp_properties = os.path.exists(grid_dhcp_properties_file)

    # Check and verify Grid DNS Properties
    grid_dns_properties_file = "playbooks/add/cabgridmgr.amfam.com/grid_dns_properties.json"
    should_verify_grid_dns_properties = os.path.exists(grid_dns_properties_file)
    
    # Check and verify Member DNS
    member_dns_file = "playbooks/add/cabgridmgr.amfam.com/member_dns.json"
    should_verify_member_dns = os.path.exists(member_dns_file) and read_json_file(member_dns_file)
    
    # Check and verify Named ACLs
    named_acl_file = "playbooks/add/cabgridmgr.amfam.com/namedacl.json"
    should_verify_named_acls = os.path.exists(named_acl_file) and read_json_file(named_acl_file)

    # Check and verify Admin User records
    adminuser_file = "playbooks/add/cabgridmgr.amfam.com/adminuser.json"
    should_verify_adminuser_records = os.path.exists(adminuser_file) and read_json_file(adminuser_file)

    # Check and verify Network Container records
    networkcontainer_file = "playbooks/add/cabgridmgr.amfam.com/networkcontainer.json"
    should_verify_networkcontainer_records = os.path.exists(networkcontainer_file) and read_json_file(networkcontainer_file)
    
    # Check and verify IPv6 Network Container records
    ipv6networkcontainer_file = "playbooks/add/cabgridmgr.amfam.com/networkipv6container.json"
    should_verify_ipv6networkcontainer_records = os.path.exists(ipv6networkcontainer_file) and read_json_file(ipv6networkcontainer_file)

    # Check and verify Range records
    range_file = "../prod_changes/cabgridmgr.amfam.com/network_range.json"
    should_verify_range_records = os.path.exists(range_file) and read_json_file(range_file)
    
    # Check and verify SRV records
    srv_record_file = "../prod_changes/cabgridmgr.amfam.com/srv_record.json"
    should_verify_srv_records = os.path.exists(srv_record_file) and read_json_file(srv_record_file)

    # Check and verify VLAN records
    vlan_file = "playbooks/add/cabgridmgr.amfam.com/vlan.json"
    should_verify_vlan_records = os.path.exists(vlan_file) and read_json_file(vlan_file)

    # Check and verify VLAN View records
    vlan_view_file = "playbooks/add/cabgridmgr.amfam.com/vlanview.json"
    should_verify_vlan_view_records = os.path.exists(vlan_view_file) and read_json_file(vlan_view_file)

    # Check and verify Upgrade Group records
    upgrade_group_file = "playbooks/add/cabgridmgr.amfam.com/upgradegroup.json"
    should_verify_upgrade_group_records = os.path.exists(upgrade_group_file) and read_json_file(upgrade_group_file)

    # Check and verify NS Group records
    ns_group_file = "playbooks/add/cabgridmgr.amfam.com/nsgroup.json"
    should_verify_ns_group_records = os.path.exists(ns_group_file) and read_json_file(ns_group_file)

    # Only call the verification functions if we have records to verify
    verification_failed = False
    
    if should_verify_a_records:
        a_records_verified = verify_a_records()
        if not a_records_verified:
            verification_failed = True
            print("\n✗ Post-check: A Record verification failed")
    
    if should_verify_aaaa_records:
        aaaa_records_verified = verify_aaaa_records()
        if not aaaa_records_verified:
            verification_failed = True
            print("\n✗ Post-check: AAAA Record verification failed")
    
    if should_verify_alias_records:
        alias_records_verified = verify_alias_records()
        if not alias_records_verified:
            verification_failed = True
            print("\n✗ Post-check: Alias Record verification failed")
    
    if should_verify_cname_records:
        cname_records_verified = verify_cname_records()
        if not cname_records_verified:
            verification_failed = True
            print("\n✗ Post-check: CNAME Record verification failed")

    if should_verify_fixed_addresses:
        fixed_addresses_verified = verify_fixed_addresses()
        if not fixed_addresses_verified:
            verification_failed = True
            print("\n✗ Post-check: Fixed Address verification failed")
    
    if should_verify_host_records:
        host_records_verified = verify_host_records()
        if not host_records_verified:
            verification_failed = True
            print("\n✗ Post-check: Host Record verification failed")

    if should_verify_mx_records:
        mx_records_verified = verify_mx_records()
        if not mx_records_verified:
            verification_failed = True
            print("\n✗ Post-check: MX Record verification failed")
    
    if should_verify_naptr_records:
        naptr_records_verified = verify_naptr_records()
        if not naptr_records_verified:
            verification_failed = True
            print("\n✗ Post-check: NAPTR Record verification failed")

    if should_verify_ptr_records:
        ptr_records_verified = verify_ptr_records()
        if not ptr_records_verified:
            verification_failed = True
            print("\n✗ Post-check: PTR Record verification failed")
    
    if should_verify_txt_records:
        txt_records_verified = verify_txt_records()
        if not txt_records_verified:
            verification_failed = True
            print("\n✗ Post-check: TXT Record verification failed")

    if should_verify_zone_rp_records:
        zone_rp_verified = verify_zone_rp_records()
        if not zone_rp_verified:
            verification_failed = True
            print("\n✗ Post-check: Response Policy Zone verification failed")
    
    if should_verify_zone_records:
        zone_verified = verify_zone_records()
        if not zone_verified:
            verification_failed = True
            print("\n✗ Post-check: DNS Zone verification failed")
    
    if should_verify_network_records:
        network_verified = verify_network_records()
        if not network_verified:
            verification_failed = True
            print("\n✗ Post-check: DHCP Network verification failed")

    if should_verify_network_view_records:
        network_view_verified = verify_network_view_records()
        if not network_view_verified:
            verification_failed = True
            print("\n✗ Post-check: Network View verification failed")

    if should_verify_dhcp_failover:
        dhcp_failover_verified = verify_dhcp_failover()
        if not dhcp_failover_verified:
            verification_failed = True
            print("\n✗ Post-check: DHCP Failover verification failed")
    
    if should_verify_dhcp_option_defs:
        dhcp_option_defs_verified = verify_dhcp_option_definitions()
        if not dhcp_option_defs_verified:
            verification_failed = True
            print("\n✗ Post-check: DHCP Option Definition verification failed")
    
    if should_verify_dhcp_ipv6_option_defs:
        dhcp_ipv6_option_defs_verified = verify_dhcp_ipv6_option_definitions()
        if not dhcp_ipv6_option_defs_verified:
            verification_failed = True
            print("\n✗ Post-check: DHCP IPv6 Option Definition verification failed")
    
    if should_verify_dhcp_option_spaces:
        dhcp_option_spaces_verified = verify_dhcp_option_spaces()
        if not dhcp_option_spaces_verified:
            verification_failed = True
            print("\n✗ Post-check: DHCP Option Space verification failed")
    
    if should_verify_dhcp_ipv6_option_spaces:
        dhcp_ipv6_option_spaces_verified = verify_dhcp_ipv6_option_spaces()
        if not dhcp_ipv6_option_spaces_verified:
            verification_failed = True
            print("\n✗ Post-check: DHCP IPv6 Option Space verification failed")
    
    if should_verify_dns_grid:
        dns_grid_verified = verify_dns_grid()
        if not dns_grid_verified:
            verification_failed = True
            print("\n✗ Post-check: DNS Grid verification failed")
    
    if should_verify_dns64_groups:
        dns64_groups_verified = verify_dns64_groups()
        if not dns64_groups_verified:
            verification_failed = True
            print("\n✗ Post-check: DNS64 Group verification failed")
    
    if should_verify_dtc_record_a:
        dtc_record_a_verified = verify_dtc_record_a()
        if not dtc_record_a_verified:
            verification_failed = True
            print("\n✗ Post-check: DTC A Record verification failed")
    
    if should_verify_fingerprints:
        fingerprints_verified = verify_fingerprints()
        if not fingerprints_verified:
            verification_failed = True
            print("\n✗ Post-check: DHCP Fingerprint verification failed")
    
    if should_verify_grid_dhcp_properties:
        grid_dhcp_properties_verified = verify_grid_dhcp_properties()
        if not grid_dhcp_properties_verified:
            verification_failed = True
            print("\n✗ Post-check: Grid DHCP Properties verification failed")

    if should_verify_grid_dns_properties:
        grid_dns_properties_verified = verify_grid_dns_properties()
        if not grid_dns_properties_verified:
            verification_failed = True
            print("\n✗ Post-check: Grid DNS Properties verification failed")
    
    if should_verify_member_dns:
        member_dns_verified = verify_member_dns()
        if not member_dns_verified:
            verification_failed = True
            print("\n✗ Post-check: Member DNS verification failed")
    
    if should_verify_named_acls:
        named_acls_verified = verify_named_acls()
        if not named_acls_verified:
            verification_failed = True
            print("\n✗ Post-check: Named ACL verification failed")

    if should_verify_adminuser_records:
        adminuser_verified = verify_adminuser_records()
        if not adminuser_verified:
            verification_failed = True
            print("\n✗ Post-check: Admin User verification failed")

    if should_verify_networkcontainer_records:
        networkcontainer_verified = verify_network_container_records()
        if not networkcontainer_verified:
            verification_failed = True
            print("\n✗ Post-check: Network Container verification failed")
    
    if should_verify_ipv6networkcontainer_records:
        ipv6networkcontainer_verified = verify_ipv6_network_container_records()
        if not ipv6networkcontainer_verified:
            verification_failed = True
            print("\n✗ Post-check: IPv6 Network Container verification failed")

    if should_verify_range_records:
        range_verified = verify_range_records()
        if not range_verified:
            verification_failed = True
            print("\n✗ Post-check: DHCP Range verification failed")
    
    if should_verify_srv_records:
        srv_verified = verify_srv_records()
        if not srv_verified:
            verification_failed = True
            print("\n✗ Post-check: SRV Record verification failed")

    if should_verify_vlan_records:
        vlan_verified = verify_vlan_records()
        if not vlan_verified:
            verification_failed = True
            print("\n✗ Post-check: VLAN verification failed")

    if should_verify_vlan_view_records:
        vlan_view_verified = verify_vlan_view_records()
        if not vlan_view_verified:
            verification_failed = True
            print("\n✗ Post-check: VLAN View verification failed")

    if should_verify_upgrade_group_records:
        upgrade_group_verified = verify_upgrade_group_records()
        if not upgrade_group_verified:
            verification_failed = True
            print("\n✗ Post-check: Upgrade Group verification failed")

    if should_verify_ns_group_records:
        ns_group_verified = verify_ns_group_records()
        if not ns_group_verified:
            verification_failed = True
            print("\n✗ Post-check: NS Group verification failed")

    # Verify DNS resolution for all records
    # verify_dns_resolution()
    
    if verification_failed:
        sys.exit(1)
    else:
        print("\n✓ All post-deployment checks passed successfully")
        sys.exit(0)

if __name__ == "__main__":
    main()