"""
The sanitizer is the only thing standing between model output and a public
page, so it gets the most direct tests in this app.
"""
from django.test import SimpleTestCase

from apps.ai_assistant.sanitizer import sanitize_page_html


class SanitizerTests(SimpleTestCase):
    def test_strips_script_tags(self):
        html, changed = sanitize_page_html(
            '<section><h1>Hi</h1><script>alert(1)</script></section>'
        )
        self.assertNotIn('<script', html)
        self.assertNotIn('alert(1)', html)
        self.assertIn('<h1>Hi</h1>', html)
        self.assertTrue(changed)

    def test_strips_inline_event_handlers(self):
        html, changed = sanitize_page_html(
            '<section><img src="https://x.test/a.png" alt="a" onerror="steal()"></section>'
        )
        self.assertNotIn('onerror', html)
        self.assertNotIn('steal()', html)
        self.assertIn('src="https://x.test/a.png"', html)
        self.assertTrue(changed)

    def test_strips_javascript_urls(self):
        html, changed = sanitize_page_html('<a href="javascript:alert(1)">Click</a>')
        self.assertNotIn('javascript:', html)
        self.assertIn('Click', html)
        self.assertTrue(changed)

    def test_strips_iframes(self):
        html, changed = sanitize_page_html(
            '<section><iframe src="https://evil.test"></iframe></section>'
        )
        self.assertNotIn('<iframe', html)
        self.assertTrue(changed)

    def test_strips_data_urls(self):
        """data: can carry scriptable SVG, so it is not an allowed scheme."""
        html, _ = sanitize_page_html(
            '<img src="data:image/svg+xml;base64,PHN2Zz48L3N2Zz4=" alt="x">'
        )
        self.assertNotIn('data:image', html)

    def test_keeps_legitimate_page_structure(self):
        source = (
            '<section class="py-16 px-4">'
            '<div class="max-w-6xl mx-auto">'
            '<h1 class="text-4xl font-bold">Build something</h1>'
            '<p class="text-gray-600">Supporting copy.</p>'
            '<a href="https://example.test/signup" class="rounded-lg">Get started</a>'
            '<i class="fas fa-check"></i>'
            '<img src="https://placehold.co/1200x800" alt="Replace this image">'
            '</div></section>'
        )
        html, changed = sanitize_page_html(source)

        self.assertFalse(changed)
        for fragment in [
            'class="py-16 px-4"',
            'max-w-6xl mx-auto',
            'text-4xl font-bold',
            'https://example.test/signup',
            'fas fa-check',
            'alt="Replace this image"',
        ]:
            self.assertIn(fragment, html)

    def test_keeps_the_form_slot_marker(self):
        """The builder relies on this marker to show where a form belongs."""
        html, _ = sanitize_page_html(
            '<div data-form-slot="true" class="border-dashed">Drop your form here</div>'
        )
        self.assertIn('data-form-slot', html)

    def test_empty_input(self):
        self.assertEqual(sanitize_page_html(''), ('', False))

    def test_report_flag_is_false_for_clean_markup(self):
        """Normalisation alone must not be reported as 'we changed your page'."""
        _, changed = sanitize_page_html('<section><p>Plain and clean.</p></section>')
        self.assertFalse(changed)
