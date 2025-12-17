# Standard Library
from __future__ import annotations
from dataclasses import dataclass, field
from urllib import parse
import re

# Third Party
from bs4 import BeautifulSoup, Tag


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

        form_spec = self.get_form_spec(form)

        # Build default data from the form fields as a starting point
        data_to_submit = {}
        for key, field_spec in form_spec.items():
            if field_spec.should_auto_include:
                data_to_submit[key] = field_spec.default_value

        # Get the default submit button, if there's only one submit button
        require_explicit_submit_button_value = False
        submit_button_names = set()
        submit_button_specs = [spec for spec in form_spec.values() if spec.type == "submit"]
        possible_submit_button_values = set()
        for spec in submit_button_specs:
            for value in spec.allowed_values:
                possible_submit_button_values.add(value)
        if len(possible_submit_button_values) == 1:
            button_spec = submit_button_specs[0]
            if button_spec.default_value:
                data_to_submit[button_spec.name] = button_spec.default_value
        elif len(possible_submit_button_values) > 1:
            require_explicit_submit_button_value = True
            submit_button_names = {spec.name for spec in submit_button_specs}

        # Validate that the supplied data values are allowed, and build the final data to submit.
        for key, value in data.items():
            # All HTTP GET/POST values are strings. Although Django allows submitting of multiple values in a list
            if isinstance(value, (list, tuple, set)):
                value = [str(v) for v in value]
            else:
                value = str(value)

            if key not in form_spec:
                raise ValueError(
                    f"'{key}' is not an allowed key for the form '{form_selector}'. "
                    f"Allowed keys are: {', '.join(form_spec.keys())}."
                )
            form_spec[key].validate_value(value)
            data_to_submit[key] = value

        if require_explicit_submit_button_value:
            have_explicit_value = False
            for name in submit_button_names:
                if data_to_submit.get(name) is not None:
                    have_explicit_value = True
                    break
            if not have_explicit_value:
                raise ValueError(
                    f"Form '{form_selector}' has multiple submit buttons. You must specify a value for one of them."
                )
        # Submit the form with our data
        action = form.get("action") or response.request["PATH_INFO"]
        method = form.get("method", "get").lower()
        if method not in ("get", "post"):
            raise ValueError(f"Form '{form_selector}' has a method of '{method}'. Must be 'get' or 'post'.")
        return getattr(self.client, method)(action, data=data_to_submit)

    def get_form_spec(self, form: BeautifulSoup) -> dict[str, FieldSpec]:
        """Get the specification of the form fields for a form."""
        inputs = form.select("input")
        textareas = form.select("textarea")
        selects = form.select("select")
        submit_buttons = form.select("button[type='submit']")

        # Look at what fields are in the form to work out what data keys are allowed and what the
        # allowed values for selects/radio buttons are. Does not yet support validation of 'range'
        # inputs.

        form_spec: dict[str, FieldSpec] = {}

        for input_ in inputs:
            name = input_.get("name")
            typ = input_.get("type", "text")
            value = input_.get("value", "")
            if typ == "radio":
                if get_boolean_attribute(input_, "checked"):
                    default_value = value
                else:
                    default_value = None
            elif typ == "checkbox":
                if get_boolean_attribute(input_, "checked"):
                    default_value = [value]
                else:
                    default_value = []
            else:
                default_value = value
            if name:
                if name not in form_spec:
                    form_spec[name] = FieldSpec(
                        name=name,
                        type=typ,
                        disabled=get_boolean_attribute(input_, "disabled"),
                        readonly=get_boolean_attribute(input_, "readonly"),
                        default_value=default_value,
                        allowed_multiple=typ == "checkbox",
                        allowed_values=[value],  # Only relevant for checkbox/radio/submit
                    )
                elif typ != form_spec[name].type:
                    raise ValueError(f"Multiple different input types ({typ}, {form_spec[name]}) for field '{name}'.")
                elif typ in ("radio", "checkbox", "submit"):
                    # This could be a susequent input for a set of radio buttons or checkboxes, or alternative submit button
                    form_spec[name].allowed_values.append(value)
                    if typ == "checkbox" and get_boolean_attribute(input_, "checked"):
                        form_spec[name].default_value += default_value
                elif typ != "reset":
                    raise ValueError(f"Multiple {typ} inputs for field '{name}'.")

        for textarea in textareas:
            name = textarea.get("name")
            if name:
                if name not in form_spec:
                    form_spec[name] = FieldSpec(
                        name=name,
                        type="textarea",
                        disabled=get_boolean_attribute(textarea, "disabled"),
                        readonly=get_boolean_attribute(textarea, "readonly"),
                        default_value=textarea.text,
                    )
                else:
                    raise ValueError(f"Multiple different textarea fields for field '{name}'.")

        for select in selects:
            name = select.get("name")
            if name:
                if name not in form_spec:
                    field_spec = FieldSpec(
                        name=name,
                        type="select",
                        disabled=get_boolean_attribute(select, "disabled"),
                        readonly=get_boolean_attribute(select, "readonly"),
                        allowed_multiple=get_boolean_attribute(select, "multiple"),
                        default_value=[] if get_boolean_attribute(select, "multiple") else None,
                    )
                    form_spec[name] = field_spec
                    for option in select.select("option"):
                        value = option.get("value") or option.text
                        field_spec.allowed_values.append(value)
                        selected = get_boolean_attribute(option, "selected")
                        if selected and field_spec.default_value and not field_spec.allowed_multiple:
                            raise ValueError(f"Field '{name}' has got multiple pre-selected options.")
                        if selected:
                            if field_spec.allowed_multiple:
                                field_spec.default_value.append(value)
                            else:
                                field_spec.default_value = value
                else:
                    raise ValueError(f"Multiple different select fields for field '{name}'.")

        for button in submit_buttons:
            name = button.get("name")
            value = button.get("value", "")
            if name:
                if name not in form_spec:
                    form_spec[name] = FieldSpec(
                        name=name,
                        type="submit",
                        default_value=value,
                        allowed_values=[value],
                    )
                else:
                    # It's allowed to have multiple submit buttons with the same name, and one value
                    # must then be specified when submitting the form.
                    form_spec[name].allowed_values.append(value)
                    # If there are multiple buttons with the same name, there's no explicit default
                    form_spec[name].default_value = None
        return form_spec


@dataclass
class FieldSpec:
    """Specification of a form field."""

    name: str  # Duplication of the dict keys, but helps with error messages.
    type: str
    disabled: bool = False
    readonly: bool = False
    default_value: str | list[str] | None = None
    allowed_values: list[str] = field(default_factory=list)
    allowed_multiple: bool = False

    @property
    def editable(self) -> bool:
        return self.type not in ("hidden", "submit", "image", "reset") and not self.disabled and not self.readonly

    @property
    def should_auto_include(self) -> bool:
        return self.default_value is not None and self.type not in ("submit", "reset") and not self.disabled

    @property
    def should_restrict_value(self) -> bool:
        return self.type in ("checkbox", "radio", "select", "submit")

    def validate_value(self, value: str | list[str]) -> None:
        if self.disabled:
            raise ValueError(f"Field '{self.name}' is disabled. You can't submit a value for it.")
        if self.readonly and value != self.default_value:
            raise ValueError(f"Field '{self.name}' is readonly; its value is fixed to {self.default_value}.")
        if isinstance(value, str):
            if not self.should_restrict_value:
                return
            if value not in self.allowed_values:
                raise ValueError(f"'{value}' is not an allowed value for field '{self.name}'.")
        elif isinstance(value, (list, tuple, set)):
            if not self.allowed_multiple:
                raise ValueError(f"Field '{self.name}' ({self.type}) is not allowed to have multiple values.")
            for val in value:
                if val not in self.allowed_values:
                    raise ValueError(f"'{val}' is not an allowed value for {self.type} field '{self.name}'.")


def get_boolean_attribute(tag: Tag, attribute: str) -> bool:
    # Not sure if this is quite correct, so might need tweaking
    return tag.get(attribute, False) is not False
