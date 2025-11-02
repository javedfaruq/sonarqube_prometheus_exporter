"""
Enterprise-specific metrics collector
Collects portfolios, applications, and advanced branch metrics
"""

import logging
from prometheus_client.core import GaugeMetricFamily
from typing import List, Dict

logger = logging.getLogger(__name__)


class EnterpriseCollector:
    """Collects Enterprise edition metrics"""
    
    def __init__(self, sonar_client):
        self.sonar_client = sonar_client
    
    def describe(self):
        """Describe Enterprise metrics"""
        yield GaugeMetricFamily(
            'portfolio_ncloc',
            'Portfolio Lines of Code',
            labels=['portfolio_key', 'portfolio_name']
        )
        yield GaugeMetricFamily(
            'portfolio_bugs',
            'Portfolio Bugs',
            labels=['portfolio_key', 'portfolio_name']
        )
        yield GaugeMetricFamily(
            'portfolio_vulnerabilities',
            'Portfolio Vulnerabilities',
            labels=['portfolio_key', 'portfolio_name']
        )
        yield GaugeMetricFamily(
            'portfolio_coverage',
            'Portfolio Coverage',
            labels=['portfolio_key', 'portfolio_name']
        )
        yield GaugeMetricFamily(
            'portfolio_reliability_rating',
            'Portfolio Reliability Rating',
            labels=['portfolio_key', 'portfolio_name']
        )
        yield GaugeMetricFamily(
            'portfolio_security_rating',
            'Portfolio Security Rating',
            labels=['portfolio_key', 'portfolio_name']
        )
        yield GaugeMetricFamily(
            'portfolio_maintainability_rating',
            'Portfolio Maintainability Rating',
            labels=['portfolio_key', 'portfolio_name']
        )
        
        # Application metrics
        yield GaugeMetricFamily(
            'application_ncloc',
            'Application Lines of Code',
            labels=['application_key', 'application_name']
        )
        yield GaugeMetricFamily(
            'application_bugs',
            'Application Bugs',
            labels=['application_key', 'application_name']
        )
        
        # Branch metrics
        yield GaugeMetricFamily(
            'branch_bugs',
            'Branch Bugs',
            labels=['project_key', 'branch_name', 'branch_type']
        )
    
    def collect(self):
        """Collect Enterprise metrics"""
        try:
            # Collect portfolio metrics
            for metric in self._collect_portfolio_metrics():
                yield metric
            
            # Collect application metrics
            for metric in self._collect_application_metrics():
                yield metric
            
            # Collect branch metrics
            for metric in self._collect_branch_metrics():
                yield metric
        
        except Exception as e:
            logger.error(f"Failed to collect Enterprise metrics: {e}")
    
    def _collect_portfolio_metrics(self):
        """Collect portfolio metrics"""
        portfolios = self.sonar_client.get_portfolios()
        logger.info(f"Collecting metrics for {len(portfolios)} portfolios")
        
        metrics = {
            'ncloc': GaugeMetricFamily('portfolio_ncloc', 'Portfolio Lines of Code', labels=['portfolio_key', 'portfolio_name']),
            'bugs': GaugeMetricFamily('portfolio_bugs', 'Portfolio Bugs', labels=['portfolio_key', 'portfolio_name']),
            'vulnerabilities': GaugeMetricFamily('portfolio_vulnerabilities', 'Portfolio Vulnerabilities', labels=['portfolio_key', 'portfolio_name']),
            'coverage': GaugeMetricFamily('portfolio_coverage', 'Portfolio Coverage', labels=['portfolio_key', 'portfolio_name']),
            'reliability_rating': GaugeMetricFamily('portfolio_reliability_rating', 'Portfolio Reliability Rating', labels=['portfolio_key', 'portfolio_name']),
            'security_rating': GaugeMetricFamily('portfolio_security_rating', 'Portfolio Security Rating', labels=['portfolio_key', 'portfolio_name']),
            'sqale_rating': GaugeMetricFamily('portfolio_maintainability_rating', 'Portfolio Maintainability Rating', labels=['portfolio_key', 'portfolio_name']),
        }
        
        for portfolio in portfolios:
            portfolio_key = portfolio['key']
            portfolio_name = portfolio.get('name', portfolio_key)
            
            try:
                result = self.sonar_client.get_measures(portfolio_key, list(metrics.keys()))
                measures = result.get('component', {}).get('measures', [])
                
                for measure in measures:
                    metric_key = measure['metric']
                    value = float(measure.get('value', 0))
                    
                    if metric_key in metrics:
                        metrics[metric_key].add_metric([portfolio_key, portfolio_name], value)
            
            except Exception as e:
                logger.error(f"Failed to get portfolio metrics for {portfolio_key}: {e}")
        
        for metric in metrics.values():
            yield metric
    
    def _collect_application_metrics(self):
        """Collect application metrics"""
        applications = self.sonar_client.get_applications()
        logger.info(f"Collecting metrics for {len(applications)} applications")
        
        metrics = {
            'ncloc': GaugeMetricFamily('application_ncloc', 'Application Lines of Code', labels=['application_key', 'application_name']),
            'bugs': GaugeMetricFamily('application_bugs', 'Application Bugs', labels=['application_key', 'application_name']),
        }
        
        for app in applications:
            app_key = app['key']
            app_name = app.get('name', app_key)
            
            try:
                result = self.sonar_client.get_measures(app_key, list(metrics.keys()))
                measures = result.get('component', {}).get('measures', [])
                
                for measure in measures:
                    metric_key = measure['metric']
                    value = float(measure.get('value', 0))
                    
                    if metric_key in metrics:
                        metrics[metric_key].add_metric([app_key, app_name], value)
            
            except Exception as e:
                logger.error(f"Failed to get application metrics for {app_key}: {e}")
        
        for metric in metrics.values():
            yield metric
    
    def _collect_branch_metrics(self):
        """Collect branch-level metrics"""
        projects = self.sonar_client.get_all_projects()
        
        branch_bugs = GaugeMetricFamily('branch_bugs', 'Branch Bugs', labels=['project_key', 'branch_name', 'branch_type'])
        
        for project in projects[:10]:  # Limit to first 10 projects for performance
            project_key = project['key']
            
            try:
                branches = self.sonar_client.get_branches(project_key)
                
                for branch in branches:
                    branch_name = branch['name']
                    branch_type = branch.get('type', 'BRANCH')
                    
                    result = self.sonar_client.get_measures(project_key, ['bugs'], branch=branch_name)
                    measures = result.get('component', {}).get('measures', [])
                    
                    for measure in measures:
                        if measure['metric'] == 'bugs':
                            value = float(measure.get('value', 0))
                            branch_bugs.add_metric([project_key, branch_name, branch_type], value)
            
            except Exception as e:
                logger.error(f"Failed to get branch metrics for {project_key}: {e}")
        
        yield branch_bugs
