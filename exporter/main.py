#!/usr/bin/env python3
"""
SonarQube Prometheus Exporter for Enterprise 2025
Main entry point for the exporter
"""

import os
import sys
import time
import signal
import logging
from prometheus_client import start_http_server, REGISTRY
from prometheus_client.core import GaugeMetricFamily

from config import Config
from sonar_client import SonarQubeClient
from metrics_collector import MetricsCollector
from enterprise_collector import EnterpriseCollector
from rbac_handler import RBACHandler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SonarQubeExporter:
    """Main exporter class"""
    
    def __init__(self, config):
        self.config = config
        self.running = True
        
        # Initialize SonarQube client
        self.sonar_client = SonarQubeClient(
            server_url=config.SONARQUBE_SERVER,
            token=config.SONARQUBE_TOKEN,
            verify_ssl=config.SONARQUBE_VERIFY_SSL,
            timeout=config.REQUEST_TIMEOUT
        )
        
        # Initialize collectors
        self.metrics_collector = MetricsCollector(self.sonar_client)
        self.enterprise_collector = EnterpriseCollector(self.sonar_client)
        
        # Initialize RBAC handler
        self.rbac_handler = RBACHandler(self.sonar_client)
        
        # Register collectors
        REGISTRY.register(self.metrics_collector)
        if config.INCLUDE_ENTERPRISE_FEATURES:
            REGISTRY.register(self.enterprise_collector)
    
    def health_check(self):
        """Perform health check"""
        try:
            status = self.sonar_client.get_system_status()
            return status.get('status') == 'UP'
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False
    
    def validate_connection(self):
        """Validate connection to SonarQube"""
        logger.info(f"Connecting to SonarQube at {self.config.SONARQUBE_SERVER}")
        
        try:
            # Test authentication
            status = self.sonar_client.get_system_status()
            version = status.get('version', 'unknown')
            
            logger.info(f"✓ Successfully connected to SonarQube {version}")
            
            # Check Enterprise edition
            edition = self.sonar_client.get_edition()
            if edition in ['ENTERPRISE', 'DATACENTER']:
                logger.info(f"✓ Detected SonarQube {edition} Edition")
            else:
                logger.warning(f"⚠ Running on {edition} edition - some Enterprise features may not be available")
            
            # Validate token permissions
            permissions = self.rbac_handler.get_token_permissions()
            logger.info(f"✓ Token permissions: {', '.join(permissions)}")
            
            return True
            
        except Exception as e:
            logger.error(f"✗ Failed to connect to SonarQube: {e}")
            return False
    
    def run(self):
        """Run the exporter"""
        # Validate connection first
        if not self.validate_connection():
            logger.error("Exiting due to connection failure")
            sys.exit(1)
        
        # Start HTTP server
        port = self.config.EXPORTER_PORT
        logger.info(f"Starting exporter on port {port}")
        start_http_server(port)
        logger.info(f"✓ Exporter started on http://0.0.0.0:{port}/metrics")
        
        # Keep running
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Shutting down...")
            self.running = False
    
    def shutdown(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, shutting down...")
        self.running = False


def main():
    """Main entry point"""
    # Load configuration
    config = Config()
    
    # Create exporter
    exporter = SonarQubeExporter(config)
    
    # Setup signal handlers
    signal.signal(signal.SIGTERM, exporter.shutdown)
    signal.signal(signal.SIGINT, exporter.shutdown)
    
    # Run exporter
    exporter.run()


if __name__ == '__main__':
    main()
