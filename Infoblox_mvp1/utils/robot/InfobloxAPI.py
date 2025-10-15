#!/usr/bin/env python3
"""
Robot Framework library for direct Infoblox API interactions.
This library provides low-level keywords to interact with Infoblox WAPI.
"""

import os
import re
import json
import subprocess
from ipaddress import IPv4Address, IPv6Address, IPv4Network, IPv6Network
import requests
import urllib3
from robot.api.deco import keyword
from robot.api import logger

# Disable SSL warnings for self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class InfobloxAPI:
    """Robot Framework library for Infoblox WAPI interactions."""

    ROBOT_LIBRARY_SCOPE = 'SUITE'

    def __init__(self):
        """Initialize the library."""
        self.grid_host = None
        self.base_url = None
        self.username = None
        self.password = None
        self.wapi_version = "2.13.4"
        self.timeout = 999999
        self.verify_certs = False

    @keyword('Connect To Infoblox Grid')
    def connect_to_infoblox_grid(self, grid_host, username=None, password=None):
        """Connect to Infoblox Grid Manager.

        Args:
            grid_host: Grid hostname or IP
            username: Infoblox username (defaults to env var infoblox_username)
            password: Infoblox password (defaults to env var infoblox_password)
        """
        self.grid_host = grid_host
        self.base_url = f"https://{grid_host}/wapi/v{self.wapi_version}"

        self.username = username or os.environ.get("infoblox_username")
        self.password = password or os.environ.get("infoblox_password")

        if not self.username or not self.password:
            raise Exception("Infoblox credentials not provided. Set infoblox_username and infoblox_password environment variables.")

        logger.info(f"Connected to Infoblox Grid: {grid_host}")

    @keyword('Test Infoblox Connection')
    def test_infoblox_connection(self):
        """Test connection to Infoblox Grid.

        Returns:
            bool: True if connection successful
        """
        try:
            response = requests.get(
                f"{self.base_url}/grid",
                auth=(self.username, self.password),
                verify=self.verify_certs,
                timeout=self.timeout
            )

            if response.status_code == 200:
                logger.info("✓ Successfully connected to Infoblox Grid")
                return True
            else:
                raise Exception(f"Connection failed with status code: {response.status_code}")
        except Exception as e:
            raise Exception(f"Failed to connect to Infoblox: {str(e)}")

    @keyword('Get A Records')
    def get_a_records(self, name=None, view=None, ipv4addr=None):
        """Get A records from Infoblox.

        Args:
            name: Record name (optional)
            view: DNS view (optional)
            ipv4addr: IPv4 address (optional)

        Returns:
            list: List of A records
        """
        params = {}
        if name:
            params['name'] = name
        if view:
            params['view'] = view
        if ipv4addr:
            params['ipv4addr'] = ipv4addr

        response = requests.get(
            f"{self.base_url}/record:a",
            params=params,
            auth=(self.username, self.password),
            verify=self.verify_certs,
            timeout=self.timeout
        )

        if response.status_code == 200:
            records = response.json()
            logger.info(f"Found {len(records)} A record(s)")
            return records
        else:
            raise Exception(f"Failed to get A records: {response.status_code}")

    @keyword('Get AAAA Records')
    def get_aaaa_records(self, name=None, view=None, ipv6addr=None):
        """Get AAAA records from Infoblox.

        Args:
            name: Record name (optional)
            view: DNS view (optional)
            ipv6addr: IPv6 address (optional)

        Returns:
            list: List of AAAA records
        """
        params = {}
        if name:
            params['name'] = name
        if view:
            params['view'] = view
        if ipv6addr:
            params['ipv6addr'] = ipv6addr

        response = requests.get(
            f"{self.base_url}/record:aaaa",
            params=params,
            auth=(self.username, self.password),
            verify=self.verify_certs,
            timeout=self.timeout
        )

        if response.status_code == 200:
            records = response.json()
            logger.info(f"Found {len(records)} AAAA record(s)")
            return records
        else:
            raise Exception(f"Failed to get AAAA records: {response.status_code}")

    @keyword('Get CNAME Records')
    def get_cname_records(self, name=None, view=None):
        """Get CNAME records from Infoblox.

        Args:
            name: Record name (optional)
            view: DNS view (optional)

        Returns:
            list: List of CNAME records
        """
        params = {}
        if name:
            params['name'] = name
        if view:
            params['view'] = view

        response = requests.get(
            f"{self.base_url}/record:cname",
            params=params,
            auth=(self.username, self.password),
            verify=self.verify_certs,
            timeout=self.timeout
        )

        if response.status_code == 200:
            records = response.json()
            logger.info(f"Found {len(records)} CNAME record(s)")
            return records
        else:
            raise Exception(f"Failed to get CNAME records: {response.status_code}")

    @keyword('Get Networks')
    def get_networks(self, network=None, network_view=None):
        """Get networks from Infoblox.

        Args:
            network: Network CIDR (optional)
            network_view: Network view (optional)

        Returns:
            list: List of networks
        """
        params = {}
        if network:
            params['network'] = network
        if network_view:
            params['network_view'] = network_view

        response = requests.get(
            f"{self.base_url}/network",
            params=params,
            auth=(self.username, self.password),
            verify=self.verify_certs,
            timeout=self.timeout
        )

        if response.status_code == 200:
            records = response.json()
            logger.info(f"Found {len(records)} network(s)")
            return records
        else:
            raise Exception(f"Failed to get networks: {response.status_code}")

    @keyword('Get DNS Zones')
    def get_dns_zones(self, fqdn=None, view=None):
        """Get DNS zones from Infoblox.

        Args:
            fqdn: Zone FQDN (optional)
            view: DNS view (optional)

        Returns:
            list: List of zones
        """
        params = {}
        if fqdn:
            params['fqdn'] = fqdn
        if view:
            params['view'] = view

        response = requests.get(
            f"{self.base_url}/zone_auth",
            params=params,
            auth=(self.username, self.password),
            verify=self.verify_certs,
            timeout=self.timeout
        )

        if response.status_code == 200:
            zones = response.json()
            logger.info(f"Found {len(zones)} DNS zone(s)")
            return zones
        else:
            raise Exception(f"Failed to get DNS zones: {response.status_code}")

    @keyword('Get Grid Members')
    def get_grid_members(self, host_name=None):
        """Get Grid Members from Infoblox.

        Args:
            host_name: Member hostname (optional)

        Returns:
            list: List of grid members
        """
        params = {}
        if host_name:
            params['host_name'] = host_name

        response = requests.get(
            f"{self.base_url}/member",
            params=params,
            auth=(self.username, self.password),
            verify=self.verify_certs,
            timeout=self.timeout
        )

        if response.status_code == 200:
            members = response.json()
            logger.info(f"Found {len(members)} grid member(s)")
            return members
        else:
            raise Exception(f"Failed to get grid members: {response.status_code}")

    @keyword('Get Network Views')
    def get_network_views(self, name=None):
        """Get network views from Infoblox.

        Args:
            name: Network view name (optional)

        Returns:
            list: List of network views
        """
        params = {}
        if name:
            params['name'] = name

        response = requests.get(
            f"{self.base_url}/networkview",
            params=params,
            auth=(self.username, self.password),
            verify=self.verify_certs,
            timeout=self.timeout
        )

        if response.status_code == 200:
            views = response.json()
            logger.info(f"Found {len(views)} network view(s)")
            return views
        else:
            raise Exception(f"Failed to get network views: {response.status_code}")

    @keyword('Validate IPv4 Address')
    def validate_ipv4_address(self, ip_address):
        """Validate IPv4 address format.

        Args:
            ip_address: IPv4 address string

        Returns:
            bool: True if valid IPv4 address
        """
        try:
            IPv4Address(ip_address)
            logger.info(f"✓ Valid IPv4 address: {ip_address}")
            return True
        except ValueError as e:
            raise Exception(f"Invalid IPv4 address '{ip_address}': {str(e)}")

    @keyword('Validate IPv6 Address')
    def validate_ipv6_address(self, ip_address):
        """Validate IPv6 address format.

        Args:
            ip_address: IPv6 address string

        Returns:
            bool: True if valid IPv6 address
        """
        try:
            IPv6Address(ip_address)
            logger.info(f"✓ Valid IPv6 address: {ip_address}")
            return True
        except ValueError as e:
            raise Exception(f"Invalid IPv6 address '{ip_address}': {str(e)}")

    @keyword('Validate Network CIDR')
    def validate_network_cidr(self, network):
        """Validate network CIDR format.

        Args:
            network: Network in CIDR notation (e.g., 192.168.1.0/24)

        Returns:
            bool: True if valid network CIDR
        """
        try:
            # Try IPv4 first
            IPv4Network(network, strict=True)
            logger.info(f"✓ Valid IPv4 network: {network}")
            return True
        except ValueError:
            try:
                # Try IPv6
                IPv6Network(network, strict=True)
                logger.info(f"✓ Valid IPv6 network: {network}")
                return True
            except ValueError as e:
                raise Exception(f"Invalid network CIDR '{network}': {str(e)}")

    @keyword('Extract Parent Domain')
    def extract_parent_domain(self, fqdn):
        """Extract parent domain from FQDN.

        Args:
            fqdn: Fully qualified domain name

        Returns:
            str: Parent domain
        """
        parts = fqdn.split('.')
        if len(parts) > 1:
            parent = '.'.join(parts[1:])
            logger.info(f"Parent domain of '{fqdn}': {parent}")
            return parent
        return fqdn

    @keyword('Perform DNS Lookup')
    def perform_dns_lookup(self, domain, record_type='A'):
        """Perform DNS lookup using nslookup.

        Args:
            domain: Domain name to lookup
            record_type: Record type (A, AAAA, CNAME, etc.)

        Returns:
            dict: Result with rc, stdout, stderr
        """
        try:
            if record_type == 'AAAA':
                cmd = ['nslookup', '-type=AAAA', domain]
            else:
                cmd = ['nslookup', domain]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False
            )

            logger.info(f"DNS lookup for {domain} (type: {record_type})")

            return {
                'rc': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr
            }
        except Exception as e:
            raise Exception(f"DNS lookup failed for {domain}: {str(e)}")

    @keyword('Load JSON Records')
    def load_json_records(self, file_path):
        """Load records from JSON file.

        Args:
            file_path: Path to JSON file

        Returns:
            list: List of records
        """
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)

            # Ensure data is a list
            if not isinstance(data, list):
                data = [data]

            logger.info(f"Loaded {len(data)} record(s) from {file_path}")
            return data
        except FileNotFoundError:
            raise Exception(f"File not found: {file_path}")
        except json.JSONDecodeError as e:
            raise Exception(f"Invalid JSON in file {file_path}: {str(e)}")
        except Exception as e:
            raise Exception(f"Error reading file {file_path}: {str(e)}")
