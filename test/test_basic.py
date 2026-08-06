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


class TestCategoryCopySql:
    """
    Tests for the SQL that copies a word's row into a second category.

    The column list is read from the database catalog at runtime rather than
    hardcoded, because words has grown by self-migration (image_file,
    image_file_2, ipa and the four SRS columns). These tests pin the rules that
    decide what travels with the copy.
    """

    ALL_COLUMNS = [
        'id', 'word', 'translation', 'category', 'example_sentence',
        'created_at', 'updated_at', 'image_file', 'image_file_2', 'ipa',
        'review_count', 'last_reviewed', 'next_review_date', 'srs_interval',
    ]

    def test_content_columns_are_copied(self):
        """The word's actual content travels with the copy"""
        from app import build_category_copy_sql
        sql = build_category_copy_sql(self.ALL_COLUMNS)
        for column in ('word', 'translation', 'ipa', 'example_sentence'):
            assert f'`{column}`' in sql

    def test_review_state_is_copied(self):
        """The copy inherits the review count and the SRS schedule"""
        from app import build_category_copy_sql
        sql = build_category_copy_sql(self.ALL_COLUMNS)
        for column in ('review_count', 'last_reviewed', 'next_review_date', 'srs_interval'):
            assert f'`{column}`' in sql

    def test_images_are_copied(self):
        """Both image slots travel with the copy"""
        from app import build_category_copy_sql
        sql = build_category_copy_sql(self.ALL_COLUMNS)
        assert '`image_file`' in sql
        assert '`image_file_2`' in sql

    def test_id_is_not_copied(self):
        """The new row must get its own id"""
        from app import build_category_copy_sql
        assert '`id`' not in build_category_copy_sql(self.ALL_COLUMNS)

    def test_timestamps_are_not_copied(self):
        """The copy is new, so it gets fresh created_at and updated_at"""
        from app import build_category_copy_sql
        sql = build_category_copy_sql(self.ALL_COLUMNS)
        assert '`created_at`' not in sql
        assert '`updated_at`' not in sql

    def test_category_is_inserted_but_not_selected(self):
        """
        category is named in the INSERT list but comes from a placeholder, never
        from the source row - substituting it is the whole point of the copy.
        """
        from app import build_category_copy_sql
        sql = build_category_copy_sql(self.ALL_COLUMNS)
        insert_list, select_list = _split_copy_sql(sql)
        assert '`category`' in insert_list
        assert '`category`' not in select_list
        assert select_list.split(',')[0].strip() == '%s'

    def test_exactly_two_placeholders(self):
        """One for the new category, one for the source row id"""
        from app import build_category_copy_sql
        assert build_category_copy_sql(self.ALL_COLUMNS).count('%s') == 2

    def test_insert_and_select_lists_are_the_same_length(self):
        """A mismatch here is a runtime error MySQL would only catch in production"""
        from app import build_category_copy_sql
        insert_list, select_list = _split_copy_sql(
            build_category_copy_sql(self.ALL_COLUMNS)
        )
        assert len(insert_list.split(',')) == len(select_list.split(','))

    def test_copies_a_column_it_has_never_heard_of(self):
        """A column added by a future migration is copied without a code change"""
        from app import build_category_copy_sql
        sql = build_category_copy_sql(self.ALL_COLUMNS + ['some_future_column'])
        assert '`some_future_column`' in sql

    def test_selects_by_id(self):
        """The source row is identified by id"""
        from app import build_category_copy_sql
        assert build_category_copy_sql(self.ALL_COLUMNS).endswith('WHERE id = %s')

    def test_every_column_is_backtick_quoted(self):
        """Catalog names are interpolated, so they are quoted regardless"""
        from app import build_category_copy_sql
        insert_list, _ = _split_copy_sql(build_category_copy_sql(self.ALL_COLUMNS))
        for name in insert_list.split(','):
            assert name.strip().startswith('`')
            assert name.strip().endswith('`')

    def test_nothing_to_copy_raises(self):
        """
        A misread catalog must fail loudly rather than insert a row with no
        word and no translation.
        """
        import pytest as _pytest
        from app import build_category_copy_sql
        with _pytest.raises(ValueError):
            build_category_copy_sql(['id', 'category', 'created_at', 'updated_at'])

    def test_empty_column_list_raises(self):
        """Same for a catalog read that returned nothing at all"""
        import pytest as _pytest
        from app import build_category_copy_sql
        with _pytest.raises(ValueError):
            build_category_copy_sql([])


def _split_copy_sql(sql):
    """Return the INSERT column list and the SELECT expression list of a copy statement"""
    insert_list = sql[sql.index('(') + 1:sql.index(')')]
    select_list = sql[sql.index('SELECT ') + len('SELECT '):sql.index(' FROM ')]
    return insert_list, select_list


class TestAddCategoryRoute:
    """Tests for the add-to-category endpoint's registration"""

    def test_add_category_route_is_registered(self):
        """POST /api/words/<id>/categories should exist"""
        from app import app
        matches = [
            rule for rule in app.url_map.iter_rules()
            if 'POST' in rule.methods and str(rule).endswith('/categories')
        ]
        assert matches, 'POST /api/words/<id>/categories is not registered'

    def test_add_category_route_takes_a_word_id(self):
        """The route should carry the id of the word being copied"""
        from app import app
        matches = [
            str(rule) for rule in app.url_map.iter_rules()
            if 'POST' in rule.methods and str(rule).endswith('/categories')
        ]
        assert any('word_id' in rule for rule in matches)

    def test_move_route_still_exists(self):
        """Add is a separate verb; Move must be untouched"""
        from app import app
        matches = [
            rule for rule in app.url_map.iter_rules()
            if 'PUT' in rule.methods and str(rule).endswith('/category')
        ]
        assert matches, 'PUT /api/words/<id>/category disappeared'


class TestSharedWriteScope:
    """
    Tests that the writes which should reach every category actually do.

    words holds one row per word-and-category pair. Translation, IPA and image
    removal already write WHERE word; upload and the two review paths used to
    write WHERE id, so a word in two categories would drift apart.
    """

    def _source(self):
        from app import app
        with open(os.path.join(app.root_path, 'app.py'), encoding='utf-8') as f:
            return f.read()

    def _function_body(self, name):
        """Return the source of one top-level function"""
        source = self._source()
        start = source.index(f'def {name}(')
        rest = source[start + 1:]
        end = rest.find('\n@app.route')
        return rest if end == -1 else rest[:end]

    def test_image_upload_writes_every_row_sharing_the_word(self):
        """An image added from one category must show up in the others"""
        body = self._function_body('upload_word_image')
        assert 'UPDATE words SET {column} = %s WHERE word = %s' in body

    def test_review_counter_writes_every_row_sharing_the_word(self):
        """Reviewing a word reviews it everywhere it is filed"""
        body = self._function_body('increment_review_counter')
        update = body[body.index('UPDATE words'):]
        assert 'WHERE word = %s' in update[:update.index('"""')]

    def test_flashcard_srs_writes_every_row_sharing_the_word(self):
        """Answering a flashcard reschedules every copy of the word"""
        body = self._function_body('submit_quiz_result')
        assert 'SET next_review_date = %s, srs_interval = %s, updated_at = NOW()' in body
        update = body[body.index('SET next_review_date'):]
        assert 'WHERE word = %s' in update[:update.index('"""')]


class TestWordCategoryDisplay:
    """
    Tests for the row of category pills under the word.

    The row is informational: it shows every category the word is filed under,
    styled like the search-result pill.
    """

    def _index_html(self):
        from app import app
        with open(os.path.join(app.root_path, 'templates', 'index.html'), encoding='utf-8') as f:
            return f.read()

    def test_index_has_word_categories_row(self):
        """The word card should carry the pill row's container"""
        assert 'wordCategories' in self._index_html()

    def test_row_sits_between_word_content_and_history(self):
        """
        Position is part of the request: below word-content, above the History
        dropdown. Asserting it stops the row drifting elsewhere in the card
        during an unrelated edit.
        """
        markup = self._index_html()
        content = markup.index('class="word-content"')
        row = markup.index('id="wordCategories"')
        history = markup.index('history-dropdown-container')
        assert content < row < history

    def test_browse_response_carries_categories(self):
        """
        The list travels with the word, so navigating does not cost an extra
        round trip per arrow-key press.
        """
        from app import app
        with open(os.path.join(app.root_path, 'app.py'), encoding='utf-8') as f:
            source = f.read()
        start = source.index('def get_word_by_category(')
        body = source[start:source.index('\n@app.route', start)]
        assert 'word["categories"]' in body

    def test_categories_are_looked_up_by_word_text(self):
        """
        Categories belong to the spelling, not to the row being viewed - the
        whole point is to find that word's other rows.
        """
        from app import app
        with open(os.path.join(app.root_path, 'app.py'), encoding='utf-8') as f:
            source = f.read()
        start = source.index('def get_word_by_category(')
        body = source[start:source.index('\n@app.route', start)]
        query_at = body.index('SELECT DISTINCT category')
        assert 'WHERE word = %s' in body[query_at:query_at + 200]

    def test_pill_style_exists(self):
        """The pill needs its own class rather than borrowing the search one"""
        from app import app
        with open(os.path.join(app.root_path, 'static', 'css', 'style.css'), encoding='utf-8') as f:
            css = f.read()
        assert '.word-category-tag' in css

    def test_pill_does_not_hardcode_the_dark_mode_navy(self):
        """
        .search-result-category hardcodes #1e3a5f, which all but vanishes on the
        dark-mode background. The new pill must not inherit that mistake.
        """
        from app import app
        with open(os.path.join(app.root_path, 'static', 'css', 'style.css'), encoding='utf-8') as f:
            css = f.read()
        rule_at = css.index('.word-category-tag')
        rule = css[rule_at:css.index('}', rule_at)]
        assert '#1e3a5f' not in rule
        assert 'var(--text-primary)' in rule

    def test_category_names_are_escaped(self):
        """
        Category names come from the Add New Word modal and from XML import, so
        they are rendered through escapeHTML() as search results are.
        """
        from app import app
        with open(os.path.join(app.root_path, 'static', 'js', 'app.js'), encoding='utf-8') as f:
            js = f.read()
        start = js.index('function renderWordCategories(')
        body = js[start:js.index('\n}', start)]
        assert 'escapeHTML(' in body


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

    def test_index_has_add_category_button(self):
        """Word actions row should contain the add-to-category button"""
        from app import app
        template_path = os.path.join(app.root_path, 'templates', 'index.html')
        with open(template_path, encoding='utf-8') as f:
            markup = f.read()
        assert 'addCategoryBtn' in markup

    def test_index_has_toast(self):
        """The page should carry the toast element"""
        from app import app
        template_path = os.path.join(app.root_path, 'templates', 'index.html')
        with open(template_path, encoding='utf-8') as f:
            markup = f.read()
        assert 'id="toast"' in markup

    def test_move_button_survives(self):
        """Add sits beside Move; it does not replace it"""
        from app import app
        template_path = os.path.join(app.root_path, 'templates', 'index.html')
        with open(template_path, encoding='utf-8') as f:
            markup = f.read()
        assert 'moveCategoryBtn' in markup

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
