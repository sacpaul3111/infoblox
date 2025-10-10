#!/usr/bin/env python3
"""
Save test execution metadata for use in execution report generation.
This script is called during pre-check and post-check stages to save
pipeline metadata alongside test results.
"""

import json
import os
import sys
from datetime import datetime


def save_metadata(output_dir, pipeline_id, grid_host, operation, record_type):
    """Save metadata to JSON file in the history directory.

    Args:
        output_dir: Directory where history files are stored
        pipeline_id: CI pipeline ID
        grid_host: Infoblox grid hostname
        operation: Operation type (add/delete)
        record_type: Record type (a_record/cname_record/network)
    """
    # Create history directory if it doesn't exist
    history_dir = os.path.join(output_dir, 'history')
    os.makedirs(history_dir, exist_ok=True)

    # Generate timestamp for filename
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    # Create metadata dictionary
    metadata = {
        'pipeline_id': pipeline_id,
        'grid_host': grid_host,
        'operation': operation,
        'record_type': record_type,
        'timestamp': datetime.now().isoformat()
    }

    # Save metadata file
    metadata_file = os.path.join(history_dir, f'metadata_{timestamp}.json')

    try:
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        print(f"[OK] Metadata saved: {metadata_file}")
        return metadata_file
    except Exception as e:
        print(f"[ERROR] Failed to save metadata: {e}")
        return None


def main():
    """Main execution function."""
    if len(sys.argv) < 6:
        print("Usage: save_test_metadata.py <output_dir> <pipeline_id> <grid_host> <operation> <record_type>")
        print("\nExample:")
        print("  save_test_metadata.py infoblox_mvp1/robot_reports/pre_check 12345 cabgridmgr.amfam.com add a_record")
        return 1

    output_dir = sys.argv[1]
    pipeline_id = sys.argv[2]
    grid_host = sys.argv[3]
    operation = sys.argv[4]
    record_type = sys.argv[5]

    print(f"Saving test metadata:")
    print(f"  Output dir: {output_dir}")
    print(f"  Pipeline ID: {pipeline_id}")
    print(f"  Grid Host: {grid_host}")
    print(f"  Operation: {operation}")
    print(f"  Record Type: {record_type}")

    metadata_file = save_metadata(output_dir, pipeline_id, grid_host, operation, record_type)

    if metadata_file:
        print("[OK] Test metadata saved successfully")
        return 0
    else:
        print("[ERROR] Failed to save test metadata")
        return 1


if __name__ == "__main__":
    sys.exit(main())
