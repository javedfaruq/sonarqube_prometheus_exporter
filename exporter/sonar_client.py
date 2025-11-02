"""
SonarQube API Client with Enterprise 2025 support
"""

import time
import logging
import requests
from typing import Dict, List, Optional, Any
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter

logger = logging.getLogger(__name__)


class SonarQubeClient:
    """SonarQube API client with retry logic and rate limiting"""
    
    def __init__(self, server_url: str, token: str, verify_ssl: bool = True, timeout: int = 30):
        self.server_url = server_url.rstrip('/')
        self.token = token
        self.verify_ssl = verify_ssl
        self.timeout = timeout
        self.session = self._create_session()
        
        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 0.12  # ~500 requests/minute
    
    def _create_session(self) -> requests.Session:
        """Create session with retry logic"""
        session = requests.Session()
        
        # Configure retries
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST"]
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        # Set authentication header
        session.headers.update({
            'Authorization': f'Bearer {self.token}',
            'Accept': 'application/json'
        })
        
        return session
    
    def _rate_limit(self):
        """Enforce rate limiting"""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_request_interval:
            time.sleep(self.min_request_interval - elapsed)
        self.last_request_time = time.time()
    
    def _request(self, method: str, endpoint: str, params: Dict = None, retry: int = 3) -> Dict:
        """Make API request with rate limiting and error handling"""
        self._rate_limit()
        
        url = f"{self.server_url}{endpoint}"
        
        try:
            response = self.session.request(
                method=method,
                url=url,
                params=params,
                timeout=self.timeout,
                verify=self.verify_ssl
            )
            
            # Handle rate limiting
            if response.status_code == 429:
                if retry > 0:
                    wait_time = int(response.headers.get('Retry-After', 60))
                    logger.warning(f"Rate limited, waiting {wait_time} seconds...")
                    time.sleep(wait_time)
                    return self._request(method, endpoint, params, retry - 1)
                else:
                    raise Exception("Rate limit exceeded, max retries reached")
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {method} {url} - {e}")
            if retry > 0:
                time.sleep(2)
                return self._request(method, endpoint, params, retry - 1)
            raise
    
    def get(self, endpoint: str, params: Dict = None) -> Dict:
        """GET request"""
        return self._request('GET', endpoint, params)
    
    # System APIs
    def get_system_status(self) -> Dict:
        """Get system status"""
        return self.get('/api/system/status')
    
    def get_system_health(self) -> Dict:
        """Get system health (Enterprise)"""
        return self.get('/api/system/health')
    
    def get_edition(self) -> str:
        """Get SonarQube edition"""
        try:
            status = self.get_system_status()
            return status.get('edition', 'COMMUNITY')
        except:
            return 'UNKNOWN'
    
    # Project APIs
    def get_projects(self, page: int = 1, page_size: int = 100) -> Dict:
        """Get all projects with pagination"""
        return self.get('/api/projects/search', {
            'p': page,
            'ps': page_size
        })
    
    def get_all_projects(self, max_projects: int = 0) -> List[Dict]:
        """Get all projects (handles pagination)"""
        projects = []
        page = 1
        page_size = 100
        
        while True:
            result = self.get_projects(page, page_size)
            projects.extend(result.get('components', []))
            
            # Check if we've retrieved all projects
            total = result.get('paging', {}).get('total', 0)
            if len(projects) >= total:
                break
            
            # Check max_projects limit
            if max_projects > 0 and len(projects) >= max_projects:
                projects = projects[:max_projects]
                break
            
            page += 1
        
        logger.info(f"Retrieved {len(projects)} projects")
        return projects
    
    # Measures APIs
    def get_measures(self, component_key: str, metric_keys: List[str], branch: str = None) -> Dict:
        """Get measures for a component"""
        params = {
            'component': component_key,
            'metricKeys': ','.join(metric_keys)
        }
        
        if branch:
            params['branch'] = branch
        
        return self.get('/api/measures/component', params)
    
    # Branch APIs (all editions in 2025)
    def get_branches(self, project_key: str) -> List[Dict]:
        """Get branches for a project"""
        try:
            result = self.get('/api/project_branches/list', {'project': project_key})
            return result.get('branches', [])
        except Exception as e:
            logger.warning(f"Failed to get branches for {project_key}: {e}")
            return []
    
    # Application APIs (Enterprise only)
    def get_applications(self) -> List[Dict]:
        """Get all applications (Enterprise feature)"""
        try:
            result = self.get('/api/applications/search')
            return result.get('applications', [])
        except Exception as e:
            logger.warning(f"Failed to get applications (may not be Enterprise): {e}")
            return []
    
    # Portfolio APIs (Enterprise only)
    def get_portfolios(self) -> List[Dict]:
        """Get all portfolios/views (Enterprise feature)"""
        try:
            result = self.get('/api/views/search')
            return result.get('views', [])
        except Exception as e:
            logger.warning(f"Failed to get portfolios (may not be Enterprise): {e}")
            return []
    
    # Quality Gate APIs
    def get_quality_gate_status(self, project_key: str, branch: str = None) -> Dict:
        """Get quality gate status for a project"""
        params = {'projectKey': project_key}
        if branch:
            params['branch'] = branch
        
        try:
            return self.get('/api/qualitygates/project_status', params)
        except Exception as e:
            logger.warning(f"Failed to get quality gate for {project_key}: {e}")
            return {}
    
    # User Permissions APIs (for RBAC)
    def get_user_permissions(self, user_login: str) -> Dict:
        """Get user permissions"""
        try:
            return self.get('/api/permissions/users', {'q': user_login})
        except Exception as e:
            logger.warning(f"Failed to get permissions for user {user_login}: {e}")
            return {}
    
    def get_project_permissions(self, project_key: str) -> Dict:
        """Get permissions for a project"""
        try:
            return self.get('/api/permissions/search_project_permissions', {'projectKey': project_key})
        except Exception as e:
            logger.warning(f"Failed to get permissions for project {project_key}: {e}")
            return {}
    
    # Token validation
    def validate_token(self) -> Dict:
        """Validate current token and get permissions"""
        try:
            # Get current user
            result = self.get('/api/authentication/validate')
            return result
        except Exception as e:
            logger.error(f"Token validation failed: {e}")
            return {'valid': False}
