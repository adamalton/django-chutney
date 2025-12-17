# Standard Library
from urllib import parse
import re

# Third Party
from bs4 import BeautifulSoup


class SoupHelper:
    """Mixin for TestCase classes which provides helper methods for testing pages using BeautifulSoup."""

    def soup(self, response):
        return BeautifulSoup(response.content.decode("utf8"), features="html.parser")

    def assert_text_in_soup(self, text, soup, tag=None, exact=False):
        """Assert that the given text is in the given soup, optionally within a specific tag.
        If exact is True, the text must be the only content of the soup element.
        """
        search = text if exact else re.compile(re.escape(text))
        # Case when the text we're searching for is the only content of the soup
        if exact:
            if soup.text == search:
                return
        elif search.search(soup.text):
            return
        # Case when the text is somewhere within a child element in the soup
        element = soup.find(tag or True, string=search)
        self.assertIsNotNone(element, msg=f"Couldn't find text '{text}' in HTML:\n{soup.prettify()}")

    def assert_link_in_soup(self, url, soup):
        """Assert that there's at least one <a/> with the given URL (or equivalent URL with the query
        params in a different order) as its href in the given soup element.
        """
        parsed = parse.urlparse(url)
        expected_path = parsed.path
        expected_query = parse.parse_qs(parsed.query)
        for link in soup.select("a"):
            parsed = parse.urlparse(link.get("href", ""))
            if parsed.path == expected_path and parse.parse_qs(parsed.query) == expected_query:
                return
        self.fail(f"Link with href '{url}' not found in HTML:\n{soup.prettify()}")

    def find_element_containing_text(self, soup, text, tag=None, exact=False):
        """Find an element in the given soup that contains the given text."""
        for element in soup.find_all(tag or True):
            if text in element.text:
                if tag and element.name != tag:
                    continue
                if exact and element.text == text:
                    return element
                return element


class FormHelper:
    """Mixin for TestCase classes which provides helper methods for testing HTML forms."""

    def submit_form(self, response, form_selector: str, data: dict = None):
        """Given a CSS selector and data to submit, extract the <form/> element from the page,
        check that the fields for the data keys exist in the form, submit the form data (along
        with any default values in the form) and return the response.
        """
        data = data or {}
        content = response.content.decode("utf8")
        soup = BeautifulSoup(content, features="html.parser")
        form = soup.select_one(form_selector)
        self.assertIsNotNone(form, msg=f"Couldn't find form '{form_selector}' in content:\n{content}")
        inputs = form.select("input")
        textareas = form.select("textarea")
        selects = form.select("select")

        # Look at what fields are in the form to work out what data keys are allowed and what the
        # allowed values for selects/radio buttons are. Does not yet support validation of 'range'
        # inputs.
        data_to_submit = {}
        allowed_keys = set()
        allowed_value_restrictions = {}
        fixed_values = {}
        for input_ in inputs:
            name = input_.get("name")
            if name:
                allowed_keys.add(name)
                typ = input_.get("type")
                value = input_.get("value")
                if value:
                    if typ in ("text", "email", "number"):
                        data_to_submit[name] = value
                    elif typ == "hidden":
                        data_to_submit[name] = value
                        fixed_values[name] = value
                    elif typ in ["checkbox", "radio"]:
                        allowed_value_restrictions.setdefault(name, []).append(value)
                        if input_.get("checked"):
                            data_to_submit[name] = value

        for textarea in textareas:
            name = textarea.get("name")
            if name:
                allowed_keys.add(name)
                data_to_submit[name] = textarea.text

        for select in selects:
            name = select.get("name")
            if name:
                allowed_keys.add(name)
                allowed_value_restrictions.setdefault(name, [])
                for option in select.select("option"):
                    value = option.get("value")
                    if value:
                        allowed_value_restrictions[name].append(value)
                        if option.get("selected"):
                            data_to_submit[name] = value

        # Validate that the supplied data values are allowed, and build the final data to submit.
        for key, value in data.items():
            value = str(value)  # All HTTP GET/POST values are strings
            if key not in allowed_keys:
                raise ValueError(
                    f"'{key}' is not an allowed key for the form '{form_selector}'. "
                    f"Allowed keys are: {', '.join(allowed_keys)}."
                )
            if key in allowed_value_restrictions:
                allowed_values = allowed_value_restrictions[key]
                # Support the submission of multiple values for the same key
                values_to_test = value if isinstance(value, (list, tuple, set)) else [value]
                for val in values_to_test:
                    if val not in allowed_values:
                        raise ValueError(
                            f"'{val} is not an allowed value for field '{key}'. "
                            f"Allowed values are: {', '.join(allowed_values)}."
                        )
            if key in fixed_values:
                raise ValueError(
                    f"Form field '{key}' has a fixed value of '{fixed_values[key]}'. You can't specify a value for it."
                )
            data_to_submit[key] = value

        # Submit the form with our data
        action = form.get("action") or response.request["PATH_INFO"]
        method = form.get("method", "get").lower()
        if method not in ("get", "post"):
            raise ValueError(f"Form '{form_selector}' has a method of '{method}'. Must be 'get' or 'post'.")
        return getattr(self.client, method)(action, data=data_to_submit)
