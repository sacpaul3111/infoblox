#!/usr/bin/env python3
"""
Robot Framework library to track and display test execution counts.
"""

import os
import json
from datetime import datetime
from robot.api.deco import keyword
from robot.api import logger


class ExecutionCounter:
    """Library to track test execution counts across runs."""

    ROBOT_LIBRARY_SCOPE = 'SUITE'

    def __init__(self):
        """Initialize the execution counter."""
        self.counter_file = None
        self.counter_data = {}

    @keyword('Initialize Execution Counter')
    def initialize_execution_counter(self, counter_file_path):
        """Initialize the execution counter with a file path.

        Args:
            counter_file_path: Path to the JSON file storing execution counts
        """
        self.counter_file = counter_file_path

        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(counter_file_path), exist_ok=True)

        # Load existing counter data
        if os.path.exists(counter_file_path):
            try:
                with open(counter_file_path, 'r') as f:
                    self.counter_data = json.load(f)
                logger.info(f"Loaded execution counter from: {counter_file_path}")
            except Exception as e:
                logger.warn(f"Failed to load counter file: {e}")
                self.counter_data = {}
        else:
            self.counter_data = {}
            logger.info(f"Created new execution counter: {counter_file_path}")

    @keyword('Increment Test Execution Count')
    def increment_test_execution_count(self, test_name):
        """Increment the execution count for a specific test.

        Args:
            test_name: Name of the test

        Returns:
            int: New execution count
        """
        if test_name not in self.counter_data:
            self.counter_data[test_name] = {
                'count': 0,
                'first_run': datetime.now().isoformat(),
                'last_run': None,
                'history': []
            }

        self.counter_data[test_name]['count'] += 1
        self.counter_data[test_name]['last_run'] = datetime.now().isoformat()
        self.counter_data[test_name]['history'].append({
            'timestamp': datetime.now().isoformat(),
            'run_number': self.counter_data[test_name]['count']
        })

        # Keep only last 50 runs in history
        if len(self.counter_data[test_name]['history']) > 50:
            self.counter_data[test_name]['history'] = self.counter_data[test_name]['history'][-50:]

        count = self.counter_data[test_name]['count']
        logger.info(f"Test '{test_name}' execution count: {count}")

        return count

    @keyword('Get Test Execution Count')
    def get_test_execution_count(self, test_name):
        """Get the execution count for a specific test.

        Args:
            test_name: Name of the test

        Returns:
            int: Execution count (0 if never run)
        """
        if test_name in self.counter_data:
            count = self.counter_data[test_name]['count']
            logger.info(f"Test '{test_name}' has been executed {count} times")
            return count
        else:
            logger.info(f"Test '{test_name}' has never been executed")
            return 0

    @keyword('Get Total Test Executions')
    def get_total_test_executions(self):
        """Get the total number of test executions across all tests.

        Returns:
            int: Total execution count
        """
        total = sum(test['count'] for test in self.counter_data.values())
        logger.info(f"Total test executions: {total}")
        return total

    @keyword('Save Execution Counter')
    def save_execution_counter(self):
        """Save the execution counter to the file."""
        if not self.counter_file:
            logger.warn("Counter file not initialized")
            return False

        try:
            with open(self.counter_file, 'w') as f:
                json.dump(self.counter_data, f, indent=2)
            logger.info(f"Saved execution counter to: {self.counter_file}")
            return True
        except Exception as e:
            logger.error(f"Failed to save counter file: {e}")
            return False

    @keyword('Log Execution Statistics')
    def log_execution_statistics(self):
        """Log execution statistics for all tests."""
        if not self.counter_data:
            logger.info("No execution statistics available")
            return

        logger.info("=" * 80)
        logger.info("TEST EXECUTION STATISTICS")
        logger.info("=" * 80)

        total_tests = len(self.counter_data)
        total_runs = sum(test['count'] for test in self.counter_data.values())

        logger.info(f"Total unique tests: {total_tests}")
        logger.info(f"Total test executions: {total_runs}")
        logger.info("")

        # Sort by execution count
        sorted_tests = sorted(
            self.counter_data.items(),
            key=lambda x: x[1]['count'],
            reverse=True
        )

        logger.info("Test execution counts:")
        for test_name, data in sorted_tests:
            logger.info(f"  • {test_name}: {data['count']} runs")
            if data['last_run']:
                try:
                    last_run_dt = datetime.fromisoformat(data['last_run'])
                    logger.info(f"    Last run: {last_run_dt.strftime('%Y-%m-%d %H:%M:%S')}")
                except:
                    pass

        logger.info("=" * 80)

    @keyword('Record Test Execution')
    def record_test_execution(self, test_name):
        """Record a test execution (increment and save).

        This is a convenience keyword that increments the count and saves the file.

        Args:
            test_name: Name of the test

        Returns:
            int: New execution count
        """
        count = self.increment_test_execution_count(test_name)
        self.save_execution_counter()

        logger.info(f"📊 Test '{test_name}' - Execution #{count}")

        return count
