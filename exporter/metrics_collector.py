"""
Standard metrics collector for all SonarQube editions
"""

import logging
from prometheus_client.core import GaugeMetricFamily
from typing import List

logger = logging.getLogger(__name__)


class MetricsCollector:
    """Collects standard SonarQube metrics"""
    
    def __init__(self, sonar_client):
        self.sonar_client = sonar_client
        
        # Metric definitions
        self.metric_definitions = {
            'ncloc': ('Lines of Code', 'Size'),
            'bugs': ('Bugs', 'Reliability'),
            'vulnerabilities': ('Vulnerabilities', 'Security'),
            'code_smells': ('Code Smells', 'Maintainability'),
            'coverage': ('Coverage', 'Coverage'),
            'duplicated_lines_density': ('Duplicated Lines (%)', 'Duplications'),
            'complexity': ('Cyclomatic Complexity', 'Complexity'),
            'cognitive_complexity': ('Cognitive Complexity', 'Complexity'),
            'security_rating': ('Security Rating', 'Security'),
            'reliability_rating': ('Reliability Rating', 'Reliability'),
            'sqale_rating': ('Maintainability Rating', 'Maintainability'),
            'alert_status': ('Quality Gate Status', 'Releasability'),
            'security_hotspots': ('Security Hotspots', 'SecurityReview'),
            'security_review_rating': ('Security Review Rating', 'SecurityReview'),
            'new_bugs': ('New Bugs', 'Reliability'),
            'new_vulnerabilities': ('New Vulnerabilities', 'Security'),
            'new_code_smells': ('New Code Smells', 'Maintainability'),
            'new_coverage': ('Coverage on New Code', 'Coverage'),
            'new_duplicated_lines_density': ('Duplicated Lines (%) on New Code', 'Duplications'),
        }
    
    def describe(self):
        """Describe all metrics (required by Prometheus)"""
        for metric_key, (help_text, domain) in self.metric_definitions.items():
            yield GaugeMetricFamily(
                metric_key,
                help_text,
                labels=['project_key', 'project_name', 'domain', 'organization']
            )
    
    def collect(self):
        """Collect metrics from SonarQube"""
        try:
            # Get all projects
            projects = self.sonar_client.get_all_projects()
            logger.info(f"Collecting metrics for {len(projects)} projects")
            
            # Collect metrics for each project
            metrics_data = {}
            for project in projects:
                project_key = project['key']
                project_name = project.get('name', project_key)
                organization = project.get('organization', 'default')
                
                try:
                    # Get measures
                    metric_keys = list(self.metric_definitions.keys())
                    result = self.sonar_client.get_measures(project_key, metric_keys)
                    
                    # Process measures
                    measures = result.get('component', {}).get('measures', [])
                    for measure in measures:
                        metric_key = measure['metric']
                        value = measure.get('value', measure.get('period', {}).get('value', 0))
                        
                        # Handle alert_status (convert to numeric)
                        if metric_key == 'alert_status':
                            value = 1 if value == 'ERROR' else 0
                        
                        # Convert to float
                        try:
                            value = float(value)
                        except (ValueError, TypeError):
                            continue
                        
                        # Store metric
                        if metric_key not in metrics_data:
                            help_text, domain = self.metric_definitions[metric_key]
                            metrics_data[metric_key] = GaugeMetricFamily(
                                metric_key,
                                help_text,
                                labels=['project_key', 'project_name', 'domain', 'organization']
                            )
                        
                        metrics_data[metric_key].add_metric(
                            [project_key, project_name, self.metric_definitions[metric_key][1], organization],
                            value
                        )
                
                except Exception as e:
                    logger.error(f"Failed to collect metrics for {project_key}: {e}")
                    continue
            
            # Yield all collected metrics
            for metric in metrics_data.values():
                yield metric
        
        except Exception as e:
            logger.error(f"Failed to collect metrics: {e}")
