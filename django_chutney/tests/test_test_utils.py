# Third Party
from django.http import HttpResponse
from django.test import Client, TestCase
from django.test.utils import override_settings
from django.urls import path
from django.utils.datastructures import MultiValueDict

# Django Chutney
from django_chutney.test_utils import FormHelper


_LAST_SUBMISSION = {
    "method": None,
    "data": MultiValueDict(),
}


def _reset_last_submission():
    _LAST_SUBMISSION["method"] = None
    _LAST_SUBMISSION["data"].clear()


def submit_form_view(request):
    """View to submit a form."""
    data = request.POST if request.method == "POST" else request.GET
    _LAST_SUBMISSION["data"].update(data)
    _LAST_SUBMISSION["method"] = request.method
    return HttpResponse("OK")


urlpatterns = [
    path("my-view/", submit_form_view),
]


class HelperTestCase(FormHelper, TestCase):
    """An example test case which we use to test FormHelper."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # This doesn't get set up for us unless we actually run a test via this class
        self.client = Client()


@override_settings(ROOT_URLCONF=__name__)
class FormHelperTestCase(TestCase):
    """Test the FormHelper class."""

    def setUp(self):
        """Set up the test case."""
        _reset_last_submission()

    def _get_form_response(self, html: str):
        """Get a response from a form page."""
        request = {
            # This is what a Django TestCase.client.get() sets as `response.request`
            "PATH_INFO": "/my-view/",
            "REQUEST_METHOD": "GET",
            "SERVER_PORT": "80",
            "wsgi.url_scheme": "http",
            "QUERY_STRING": "",
        }
        # Wrap the HTML so that the <form> is *within* the html and can be selected
        html = f"<html><body>{html}</body></html>"
        response = HttpResponse(html)
        response.request = request
        return response

    def _get_submitted_data(self, form_html: str, data: dict = None):
        """Given the HTML of a form, and data to submit, return the data that `submit_form` submits."""
        data = data or {}
        form_response = self._get_form_response(form_html)
        helper = HelperTestCase()
        response = helper.submit_form(form_response, "form", data)
        self.assertIn(response.status_code, (200, 302), response.content.decode("utf8"))
        submitted_data = _LAST_SUBMISSION["data"].copy()
        return submitted_data

    def assert_data_equal(self, submitted_data: MultiValueDict, expected_data: dict):
        """Assert that the submitted data is equal to the expected data."""
        self.assertEqual(sorted(submitted_data.keys()), sorted(expected_data.keys()))
        for key, expected_value in expected_data.items():
            if isinstance(expected_value, list):
                submitted_value = submitted_data.getlist(key)
            else:
                submitted_value = submitted_data[key]
            self.assertEqual(submitted_value, expected_value, msg=f"Mismatch for field '{key}'.")

    def test_submits_via_correct_form_method(self):
        """Test that the submit_form method submits via the correct form method."""
        form_html = """
            <form method="post">
                <input type="text" name="my-text">
            </form>
        """
        submitted_data = self._get_submitted_data(form_html, {"my-text": "my value"})
        self.assertEqual(_LAST_SUBMISSION["method"], "POST")
        self.assert_data_equal(submitted_data, {"my-text": "my value"})

    def test_submits_supplied_data(self):
        """Test that the submit_form method submits the supplied data."""
        form_html = """
            <form method="post">
                <input type="text" name="my-text">
                <textarea name="my-textarea"></textarea>
                <select name="my-select">
                    <option value="select1">Value 1</option>
                    <option value="select2">Value 2</option>
                </select>
                <input type="checkbox" name="my-checkbox" value="checkbox1">
                <input type="checkbox" name="my-checkbox" value="checkbox2">
                <input type="radio" name="my-radio" value="radio1">
                <input type="radio" name="my-radio" value="radio2">
            </form>
        """
        form_data = {
            "my-text": "my value",
            "my-textarea": "my textarea value",
            "my-select": "select1",
            "my-checkbox": "checkbox1",
            "my-radio": "radio1",
        }
        submitted_data = self._get_submitted_data(form_html, form_data)
        self.assert_data_equal(submitted_data, form_data)

    def test_submits_default_values(self):
        """Test that the submit_form method submits all the default values for the form."""
        form_html = """
            <form method="post">
                <input type="hidden" name="my-hidden" value="hidden-value">
                <input type="text" name="my-text" value="text-value">
                <input type="checkbox" name="my-checkbox" value="checkbox-value" checked>
                <input type="checkbox" name="my-checkbox" value="non-checked-value">
                <input type="radio" name="my-radio" value="radio-value" checked>
                <input type="radio" name="my-radio" value="non-checked-value">
                <textarea name="my-textarea">textarea-value</textarea>
                <select name="my-select">
                    <option value="select-value" selected>Selected value</option>
                    <option value="non-selected-value">Non-selected value</option>
                </select>
                <select name="my-select-multiple" multiple>
                    <option value="select-value-1" selected>Selected value 1</option>
                    <option value="select-value-2" selected>Selected value 2</option>
                    <option value="non-selected-value-1">Non-selected value 1</option>
                    <option value="non-selected-value-2">Non-selected value 2</option>
                </select>
            </form>
        """
        submitted_data = self._get_submitted_data(form_html, {})
        expected_data = {
            "my-hidden": "hidden-value",
            "my-text": "text-value",
            "my-checkbox": ["checkbox-value"],
            "my-radio": "radio-value",
            "my-textarea": "textarea-value",
            "my-select": "select-value",
            "my-select-multiple": ["select-value-1", "select-value-2"],
        }
        self.assert_data_equal(submitted_data, expected_data)

    def test_default_submit_button_value_is_submitted(self):
        """If there's only one submit button, and it has a name and value, that value should be submitted."""
        form_html = """
            <form method="post">
                <button type="submit" name="my-submit" value="submit-value">Submit</button>
            </form>
        """
        submitted_data = self._get_submitted_data(form_html, {})
        self.assertEqual(submitted_data["my-submit"], "submit-value")

        # The same should apply for an <input type="submit" />
        form_html = """
            <form method="post">
                <input type="submit" name="my-submit" value="submit-value">
            </form>
        """
        submitted_data = self._get_submitted_data(form_html, {})
        self.assertEqual(submitted_data["my-submit"], "submit-value")

    def test_multiple_submit_buttons_require_an_explicit_value(self):
        """If there are multiple submit buttons, none of them should be submitted."""
        form_html = """
            <form method="post">
                <button type="submit" name="my-submit" value="submit-value-1">Submit</button>
                <button type="submit" name="my-submit" value="submit-value-2">Submit</button>
            </form>
        """
        self.assertRaises(ValueError, self._get_submitted_data, form_html, {})
        # Submitting with an explicit value should work
        submitted_data = self._get_submitted_data(form_html, {"my-submit": "submit-value-1"})
        self.assert_data_equal(submitted_data, {"my-submit": "submit-value-1"})

    def test_disabled_fields_are_not_submitted(self):
        """Test that disabled fields are not - and cannot be - submitted."""
        form_html = """
            <form method="post">
                <input type="text" name="disabled-text" value="disabled-value" disabled>
                <input type="hidden" name="disabled-hidden" value="disabled-value" disabled>
                <input type="checkbox" name="disabled-checkbox" value="disabled-value" disabled checked>
                <input type="radio" name="disabled-radio" value="disabled-value" disabled checked>
                <textarea name="disabled-textarea" value="disabled-value" disabled></textarea>
                <select name="disabled-select" disabled>
                    <option value="select-value" selected>Selected value</option>
                    <option value="non-selected-value">Non-selected value</option>
                </select>
            </form>
        """
        submitted_data = self._get_submitted_data(form_html, {})
        self.assertEqual(submitted_data, {})
        # Submitting with a value should raise a ValueError
        for field in (
            "disabled-text",
            "disabled-hidden",
            "disabled-checkbox",
            "disabled-radio",
            "disabled-textarea",
            "disabled-select",
        ):
            self.assertRaises(ValueError, self._get_submitted_data, form_html, {field: "my value"})

    def test_readonly_fields_are_not_editable(self):
        """Test that readonly fields can't have their values changed."""
        form_html = """
            <form method="post">
                <input type="text" name="readonly-text" value="readonly-value" readonly>
                <input type="hidden" name="readonly-hidden" value="readonly-value" readonly>
                <input type="checkbox" name="readonly-checkbox" value="readonly-value" readonly checked>
                <input type="radio" name="readonly-radio" value="readonly-value" readonly checked>
                <textarea name="readonly-textarea" readonly>readonly-value</textarea>
                <select name="readonly-select" readonly>
                    <option value="readonly-value" selected>Selected value</option>
                    <option value="non-selected-value">Non-selected value</option>
                </select>
            </form>
        """
        expected_data = {
            "readonly-text": "readonly-value",
            "readonly-hidden": "readonly-value",
            "readonly-checkbox": ["readonly-value"],
            "readonly-radio": "readonly-value",
            "readonly-textarea": "readonly-value",
            "readonly-select": "readonly-value",
        }
        submitted_data = self._get_submitted_data(form_html, {})
        self.assert_data_equal(submitted_data, expected_data)
        # Submitting with a value should raise a ValueError
        for field in expected_data.keys():
            with self.assertRaises(ValueError, msg=f"Readonly field '{field}' should not be editable."):
                self._get_submitted_data(form_html, {field: "my value"})

    def test_raises_error_for_multiple_incompatible_inputs(self):
        """Test that an error is raised if there are multiple inputs with the same name but different types."""
        form_html = """
            <form method="post">
                <input type="text" name="my-text" value="text-value">
                <input type="checkbox" name="my-text" value="checkbox-value" checked>
            </form>
        """
        self.assertRaises(ValueError, self._get_submitted_data, form_html, {})
