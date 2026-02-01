"""
BKDict - Basic Tests (No Database Required)
These tests verify core Flask application functionality without database connections.

Test Coverage:
- Application initialization and configuration
- Route definitions and accessibility  
- Template rendering
- Static file configuration
- Utility function behavior
"""

import pytest
import os
import sys

# Skip database initialization for CI tests
os.environ['SKIP_DB'] = 'true'

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestAppInitialization:
    """Tests for application startup and configuration"""
    
    def test_app_creates_successfully(self):
        """Flask app should initialize without errors"""
        from app import app
        assert app is not None
        
    def test_app_is_flask_instance(self):
        """App should be a Flask instance"""
        from flask import Flask
        from app import app
        assert isinstance(app, Flask)
        
    def test_config_loads(self):
        """Configuration should load without errors"""
        from config import Config
        assert Config is not None
        

class TestRouteDefinitions:
    """Tests to verify all routes are properly defined"""
    
    @pytest.fixture
    def app(self):
        from app import app
        app.config['TESTING'] = True
        return app
    
    @pytest.fixture
    def client(self, app):
        return app.test_client()
    
    def test_index_route_exists(self, client):
        """Main index route should be accessible"""
        # Will redirect to login if password protected, both are valid responses
        response = client.get('/')
        assert response.status_code in [200, 302]
        
    def test_login_route_exists(self, client):
        """Login route should be accessible"""
        response = client.get('/login')
        assert response.status_code in [200, 302]
        
    def test_quiz_route_exists(self, client):
        """Quiz route should be accessible"""
        response = client.get('/quiz')
        assert response.status_code in [200, 302]
        
    def test_favicon_route_exists(self, client):
        """Favicon route should be accessible"""
        response = client.get('/favicon.ico')
        # 200 if found, 404 if not present (both acceptable)
        assert response.status_code in [200, 404]


class TestStaticFiles:
    """Tests for static file configuration"""
    
    def test_static_folder_exists(self):
        """Static folder should exist"""
        from app import app
        static_path = os.path.join(app.root_path, 'static')
        assert os.path.isdir(static_path)
        
    def test_css_folder_exists(self):
        """CSS folder should exist in static"""
        from app import app
        css_path = os.path.join(app.root_path, 'static', 'css')
        assert os.path.isdir(css_path)
        
    def test_js_folder_exists(self):
        """JavaScript folder should exist in static"""
        from app import app
        js_path = os.path.join(app.root_path, 'static', 'js')
        assert os.path.isdir(js_path)
        
    def test_main_stylesheet_exists(self):
        """Main CSS file should exist"""
        from app import app
        style_path = os.path.join(app.root_path, 'static', 'css', 'style.css')
        assert os.path.isfile(style_path)
        
    def test_main_js_exists(self):
        """Main JavaScript file should exist"""
        from app import app
        js_path = os.path.join(app.root_path, 'static', 'js', 'app.js')
        assert os.path.isfile(js_path)


class TestTemplates:
    """Tests for template files"""
    
    def test_templates_folder_exists(self):
        """Templates folder should exist"""
        from app import app
        template_path = os.path.join(app.root_path, 'templates')
        assert os.path.isdir(template_path)
        
    def test_index_template_exists(self):
        """Index template should exist"""
        from app import app
        template_path = os.path.join(app.root_path, 'templates', 'index.html')
        assert os.path.isfile(template_path)
        
    def test_login_template_exists(self):
        """Login template should exist"""
        from app import app
        template_path = os.path.join(app.root_path, 'templates', 'login.html')
        assert os.path.isfile(template_path)
        
    def test_quiz_template_exists(self):
        """Quiz template should exist"""
        from app import app
        template_path = os.path.join(app.root_path, 'templates', 'quiz.html')
        assert os.path.isfile(template_path)


class TestUtilities:
    """Tests for utility functions"""
    
    def test_allowed_file_accepts_xml(self):
        """allowed_file should accept XML files (per config)"""
        from app import allowed_file
        assert allowed_file('test.xml') == True
        assert allowed_file('vocabulary.xml') == True
        
    def test_allowed_file_rejects_invalid(self):
        """allowed_file should reject non-allowed files"""
        from app import allowed_file
        assert allowed_file('test.exe') == False
        assert allowed_file('test.py') == False
        assert allowed_file('noextension') == False
        assert allowed_file('test.txt') == False


class TestEnvironmentDetection:
    """Tests for environment detection logic"""
    
    def test_inject_env_info_returns_dict(self):
        """inject_env_info should return a dictionary"""
        from app import inject_env_info
        result = inject_env_info()
        assert isinstance(result, dict)
        assert 'env_type' in result
        
    def test_env_type_is_string(self):
        """env_type should be a string"""
        from app import inject_env_info
        result = inject_env_info()
        assert isinstance(result['env_type'], str)
        assert len(result['env_type']) > 0
