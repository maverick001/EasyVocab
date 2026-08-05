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

    def test_index_has_remove_screenshot_button(self):
        """Add New Word modal should contain the remove image button"""
        from app import app
        template_path = os.path.join(app.root_path, 'templates', 'index.html')
        with open(template_path, encoding='utf-8') as f:
            markup = f.read()
        assert 'removeScreenshotBtn' in markup

    def test_index_has_attach_screenshot_button(self):
        """Add New Word modal should contain the attach image button"""
        from app import app
        template_path = os.path.join(app.root_path, 'templates', 'index.html')
        with open(template_path, encoding='utf-8') as f:
            markup = f.read()
        assert 'attachScreenshotBtn' in markup


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


class TestSecondImageColumn:
    """Tests for the image_file_2 self-migration"""

    def test_ensure_image_file_2_column_exists(self):
        """The migration function should be defined"""
        import app as app_module
        assert hasattr(app_module, 'ensure_image_file_2_column')

    def test_ensure_image_file_2_column_is_callable(self):
        """The migration function should be callable"""
        import app as app_module
        assert callable(app_module.ensure_image_file_2_column)


class TestImageSlotParsing:
    """Tests for interpreting the 'slot' field of an image upload"""

    def test_absent_slot_defaults_to_one(self):
        """A request with no slot field targets slot 1"""
        from app import parse_image_slot
        assert parse_image_slot(None) == 1

    def test_empty_slot_defaults_to_one(self):
        """An empty slot field targets slot 1"""
        from app import parse_image_slot
        assert parse_image_slot('') == 1

    def test_slot_one_accepted(self):
        """Slot 1 is accepted"""
        from app import parse_image_slot
        assert parse_image_slot('1') == 1

    def test_slot_two_accepted(self):
        """Slot 2 is accepted"""
        from app import parse_image_slot
        assert parse_image_slot('2') == 2

    def test_integer_input_accepted(self):
        """An int is accepted as well as a string"""
        from app import parse_image_slot
        assert parse_image_slot(2) == 2

    def test_zero_rejected(self):
        """Slot 0 is out of range"""
        from app import parse_image_slot
        assert parse_image_slot('0') is None

    def test_three_rejected(self):
        """Slot 3 is out of range - two images is a hard cap"""
        from app import parse_image_slot
        assert parse_image_slot('3') is None

    def test_non_numeric_rejected(self):
        """A non-numeric slot is rejected rather than raising"""
        from app import parse_image_slot
        assert parse_image_slot('abc') is None


class TestImageRemovalSql:
    """Tests for the SQL that empties a slot and restores compaction"""

    def test_slot_one_pulls_slot_two_down(self):
        """Removing slot 1 must move slot 2 into it, not just blank slot 1"""
        from app import build_image_removal_sql
        sql = build_image_removal_sql(1)
        assert 'image_file = image_file_2' in sql
        assert 'image_file_2 = NULL' in sql

    def test_slot_two_clears_only_slot_two(self):
        """Removing slot 2 must leave slot 1 alone"""
        from app import build_image_removal_sql
        sql = build_image_removal_sql(2)
        assert 'image_file_2 = NULL' in sql
        assert 'image_file = image_file_2' not in sql

    def test_slot_one_targets_all_rows_sharing_the_word(self):
        """Removal is shared across categories, as translation and ipa are"""
        from app import build_image_removal_sql
        assert build_image_removal_sql(1).endswith('WHERE word = %s')

    def test_slot_two_targets_all_rows_sharing_the_word(self):
        """Removal is shared across categories, as translation and ipa are"""
        from app import build_image_removal_sql
        assert build_image_removal_sql(2).endswith('WHERE word = %s')

    def test_statements_carry_exactly_one_placeholder(self):
        """Only the word text is parameterised; the slot is never interpolated"""
        from app import build_image_removal_sql
        assert build_image_removal_sql(1).count('%s') == 1
        assert build_image_removal_sql(2).count('%s') == 1


class TestImageDeleteRoute:
    """Tests for the image removal endpoint's registration"""

    def test_delete_image_route_is_registered(self):
        """DELETE /api/words/<id>/image/<slot> should exist"""
        from app import app
        matches = [
            rule for rule in app.url_map.iter_rules()
            if 'DELETE' in rule.methods and '/image/' in str(rule)
        ]
        assert matches, 'DELETE /api/words/<id>/image/<slot> is not registered'

    def test_delete_image_route_takes_a_slot(self):
        """The route should carry both a word id and a slot"""
        from app import app
        matches = [
            str(rule) for rule in app.url_map.iter_rules()
            if 'DELETE' in rule.methods and '/image/' in str(rule)
        ]
        assert any('word_id' in rule and 'slot' in rule for rule in matches)


class TestImageDisplayModalMarkup:
    """Tests for the two-image display modal markup"""

    def test_index_has_image_scroll_pane(self):
        """Display modal should contain the scrolling image pane"""
        from app import app
        template_path = os.path.join(app.root_path, 'templates', 'index.html')
        with open(template_path, encoding='utf-8') as f:
            markup = f.read()
        assert 'imageScrollPane' in markup

    def test_index_has_add_another_image_button(self):
        """Display modal footer should contain the add button"""
        from app import app
        template_path = os.path.join(app.root_path, 'templates', 'index.html')
        with open(template_path, encoding='utf-8') as f:
            markup = f.read()
        assert 'addAnotherImageBtn' in markup


# Ids that document.getElementById() in app.js legitimately looks up even
# though they are absent from templates/index.html. The failure mode
# TestElementIdConsistency guards against is an *unguarded* lookup at
# startup (e.g. Elements.changeImageBtn.addEventListener(...) throwing on
# null and breaking the whole app). Neither entry below is that case, so
# each is allowlisted individually with the reason. Do not broaden this
# beyond the two known cases -- a new missing id should fail the test and
# get its own deliberate decision.
IDS_NOT_IN_INDEX_TEMPLATE = {
    # Created at runtime by app.js itself (assigned into
    # Elements.searchResultsList.innerHTML in displaySearchResults()), then
    # looked up a tick later with a null guard. It genuinely exists in the
    # DOM when queried; the static template just isn't where it's defined.
    'addSearchWordBtn',
    # Pre-existing dead code: id="positionInfo" was removed from
    # templates/index.html before this branch existed. The lookup is
    # unconditional at cacheElements() time, but the only use site is
    # guarded (`if (Elements.positionInfo) { ... }`), so it cannot throw.
    # Left in place deliberately -- removing it is out of scope here.
    'positionInfo',
}


class TestElementIdConsistency:
    """
    Guards against the class of bug Task 7 introduced by hand: an id removed
    from templates/index.html while static/js/app.js still looks it up
    unconditionally at startup. That leaves Elements.<name> null, and the
    very next .addEventListener(...) on it throws and breaks the whole app.

    Every document.getElementById('...') literal in app.js must reference an
    id that actually exists in templates/index.html, except for the
    documented, individually-justified exceptions in
    IDS_NOT_IN_INDEX_TEMPLATE.
    """

    def test_every_getelementbyid_target_exists_in_index_html(self):
        """Every id app.js looks up by document.getElementById must exist in index.html"""
        import re
        from app import app

        js_path = os.path.join(app.root_path, 'static', 'js', 'app.js')
        with open(js_path, encoding='utf-8') as f:
            js_source = f.read()

        html_path = os.path.join(app.root_path, 'templates', 'index.html')
        with open(html_path, encoding='utf-8') as f:
            html_source = f.read()

        js_ids = set(re.findall(r"""document\.getElementById\(\s*['"]([^'"]+)['"]\s*\)""", js_source))
        html_ids = set(re.findall(r"""\bid=["']([^"']+)["']""", html_source))

        missing = js_ids - html_ids - IDS_NOT_IN_INDEX_TEMPLATE
        assert not missing, (
            "app.js calls document.getElementById() with ids that do not exist "
            f"in templates/index.html: {sorted(missing)}"
        )
