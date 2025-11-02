"""
Configuration management for SonarQube Exporter
"""

import os
from typing import List


class Config:
    """Configuration class with environment variable support"""
    
    # SonarQube Connection
    SONARQUBE_SERVER: str = os.getenv('SONARQUBE_SERVER', 'http://localhost:9000')
    SONARQUBE_TOKEN: str = os.getenv('SONARQUBE_TOKEN', '')
    SONARQUBE_VERIFY_SSL: bool = os.getenv('SONARQUBE_VERIFY_SSL', 'true').lower() == 'true'
    SONARQUBE_CA_CERT: str = os.getenv('SONARQUBE_CA_CERT', '')
    
    # Exporter Settings
    EXPORTER_PORT: int = int(os.getenv('EXPORTER_PORT', '8198'))
    SCRAPE_INTERVAL: int = int(os.getenv('SCRAPE_INTERVAL', '60'))
    REQUEST_TIMEOUT: int = int(os.getenv('REQUEST_TIMEOUT', '30'))
    
    # Rate Limiting (Enterprise 2025: 600 requests/min)
    RATE_LIMIT_REQUESTS_PER_MINUTE: int = int(os.getenv('RATE_LIMIT_REQUESTS_PER_MINUTE', '500'))
    RATE_LIMIT_DELAY: float = float(os.getenv('RATE_LIMIT_DELAY', '0.12'))  # 60/500 = 0.12s
    RETRY_ATTEMPTS: int = int(os.getenv('RETRY_ATTEMPTS', '3'))
    RETRY_BACKOFF_SECONDS: int = int(os.getenv('RETRY_BACKOFF_SECONDS', '2'))
    
    # Pagination
    MAX_PROJECTS: int = int(os.getenv('MAX_PROJECTS', '0'))  # 0 = all
    PAGE_SIZE: int = int(os.getenv('PAGE_SIZE', '100'))
    MAX_CONCURRENT_REQUESTS: int = int(os.getenv('MAX_CONCURRENT_REQUESTS', '5'))
    
    # Enterprise Features
    INCLUDE_ENTERPRISE_FEATURES: bool = os.getenv('INCLUDE_ENTERPRISE_FEATURES', 'true').lower() == 'true'
    INCLUDE_BRANCHES: bool = os.getenv('INCLUDE_BRANCHES', 'true').lower() == 'true'
    INCLUDE_APPLICATIONS: bool = os.getenv('INCLUDE_APPLICATIONS', 'true').lower() == 'true'
    INCLUDE_PORTFOLIOS: bool = os.getenv('INCLUDE_PORTFOLIOS', 'true').lower() == 'true'
    INCLUDE_QUALITY_PROFILES: bool = os.getenv('INCLUDE_QUALITY_PROFILES', 'false').lower() == 'true'
    
    # RBAC Settings
    ENABLE_RBAC: bool = os.getenv('ENABLE_RBAC', 'true').lower() == 'true'
    RBAC_CACHE_TTL: int = int(os.getenv('RBAC_CACHE_TTL', '300'))  # 5 minutes
    
    # Metrics to collect (can be customized)
    METRICS_TO_COLLECT: List[str] = [
        'ncloc', 'bugs', 'vulnerabilities', 'code_smells',
        'coverage', 'duplicated_lines_density', 'complexity',
        'security_rating', 'reliability_rating', 'sqale_rating',
        'alert_status', 'security_hotspots', 'security_review_rating',
        'new_bugs', 'new_vulnerabilities', 'new_code_smells',
        'new_coverage', 'new_duplicated_lines_density',
        'new_security_rating', 'new_reliability_rating', 'new_maintainability_rating'
    ]
    
    # Logging
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')
    
    def __init__(self):
        self.validate()
    
    def validate(self):
        """Validate required configuration"""
        if not self.SONARQUBE_SERVER:
            raise ValueError("SONARQUBE_SERVER is required")
        
        if not self.SONARQUBE_TOKEN:
            raise ValueError("SONARQUBE_TOKEN is required")
        
        if not self.SONARQUBE_SERVER.startswith(('http://', 'https://')):
            raise ValueError("SONARQUBE_SERVER must start with http:// or https://")
        
        # Remove trailing slash from server URL
        self.SONARQUBE_SERVER = self.SONARQUBE_SERVER.rstrip('/')
