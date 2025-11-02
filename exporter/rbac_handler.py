"""
RBAC Handler for SonarQube permissions integration
Maps SonarQube permissions to Grafana dashboard access
"""

import logging
import time
from typing import Dict, List, Set
from functools import lru_cache

logger = logging.getLogger(__name__)


class RBACHandler:
    """Handle RBAC integration with SonarQube"""
    
    def __init__(self, sonar_client):
        self.sonar_client = sonar_client
        self.cache_ttl = 300  # 5 minutes
        self.permission_cache = {}
    
    def get_token_permissions(self) -> Set[str]:
        """Get permissions for the current token"""
        try:
            validation = self.sonar_client.validate_token()
            if validation.get('valid'):
                # Try to infer permissions based on successful API calls
                permissions = set()
                
                # Test various permissions
                try:
                    self.sonar_client.get_projects(page_size=1)
                    permissions.add('Browse')
                except:
                    pass
                
                try:
                    self.sonar_client.get_system_status()
                    permissions.add('Administer')
                except:
                    pass
                
                return permissions
            
            return set()
        
        except Exception as e:
            logger.error(f"Failed to get token permissions: {e}")
            return set()
    
    @lru_cache(maxsize=1000)
    def get_project_permissions(self, project_key: str) -> Dict[str, List[str]]:
        """Get permissions for a specific project (cached)"""
        try:
            result = self.sonar_client.get_project_permissions(project_key)
            
            # Parse permissions by user/group
            permissions_map = {}
            
            for user_perm in result.get('users', []):
                user_login = user_perm['login']
                permissions_map[user_login] = user_perm.get('permissions', [])
            
            return permissions_map
        
        except Exception as e:
            logger.error(f"Failed to get permissions for {project_key}: {e}")
            return {}
    
    def get_user_accessible_projects(self, user_login: str) -> List[str]:
        """Get list of projects accessible by user"""
        try:
            all_projects = self.sonar_client.get_all_projects()
            accessible_projects = []
            
            for project in all_projects:
                project_key = project['key']
                permissions = self.get_project_permissions(project_key)
                
                # Check if user has any permission on this project
                if user_login in permissions:
                    accessible_projects.append(project_key)
            
            return accessible_projects
        
        except Exception as e:
            logger.error(f"Failed to get accessible projects for {user_login}: {e}")
            return []
    
    def generate_grafana_rbac_config(self) -> Dict:
        """
        Generate Grafana RBAC configuration based on SonarQube permissions
        This creates a mapping for Grafana dashboard variables
        """
        try:
            projects = self.sonar_client.get_all_projects()
            
            rbac_config = {
                'version': '1.0',
                'projects': {},
                'portfolios': {},
                'roles': {
                    'viewer': {
                        'sonarqube_permission': 'Browse',
                        'grafana_permission': 'Viewer'
                    },
                    'admin': {
                        'sonarqube_permission': 'Administer',
                        'grafana_permission': 'Admin'
                    }
                }
            }
            
            # Map projects
            for project in projects:
                project_key = project['key']
                permissions = self.get_project_permissions(project_key)
                
                rbac_config['projects'][project_key] = {
                    'name': project.get('name', project_key),
                    'users': list(permissions.keys()),
                    'visibility': 'private' if permissions else 'public'
                }
            
            # Map portfolios (Enterprise)
            try:
                portfolios = self.sonar_client.get_portfolios()
                for portfolio in portfolios:
                    portfolio_key = portfolio['key']
                    rbac_config['portfolios'][portfolio_key] = {
                        'name': portfolio.get('name', portfolio_key),
                        'sub_portfolios': portfolio.get('subViews', [])
                    }
            except:
                pass
            
            return rbac_config
        
        except Exception as e:
            logger.error(f"Failed to generate RBAC config: {e}")
            return {}
