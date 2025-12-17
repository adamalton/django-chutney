# Django Chutney
Tasty accompaniments to go with the Django web framework

My personal collection of miscellaneous useful bits of code for use in Django projects.

## Installation

`pip install django-chutney`


## Usage

The library is intended to be a pick and mix bucket from which you can choose to use whichever bits you want.


## Test case helpers

These require BeautifulSoup to be installed:
```
pip install beautifulsoup4>=4
```

### FormHelper

This provides functionality to allow you to test HTML forms in a way that's more accurate than the
standard approach with `django.test.Client`.

A common approach to testing form submissions to Django views is to submit a dict of data to the view,
but simply doing that doesn't check that the HTML form you're rendering actually allows those values
to be submitted. For example, your test case might submit a value for a field which isn't an option
in the rendered `<select>`. This approach also means that you may not be submitting values which would
be automatically submitted by a web browser, such as hidden fields.

`django_chutney.test_utils.FormHelper` provides a way for a test case to to submit a form while
checking that the values you're submitting are actually value that the browser would allow a user
to submit. It also automatically submits the values of any hidden inputs the form.



```python
from django.test import TestCase
from django_chutney.test_utils import FormHelper

class MyFormTestCase(TestCase, FormHelper):

    def test_form_page(self):
        page_response = self.client.get(reverse("my_view"))
        # Submit a form to the page, with automatic checking that the values you're submitting are
        # possible values for a browser to submit based on the HTML of the form in the page.
        # Also submits hidden values that are in the form, even if you don't specific them.
        data = {"field1": "some-value"}
        post_response = self.submit_form(response, "#my-form", data)
        self.assertEqual(post_response.status_code, 302)
```

### SoupHelper

This class provides additional helper methods for testing pages using
[BeautifulSoup](https://www.crummy.com/software/BeautifulSoup/bs4/doc/).

#### `assert_link_in_soup(url: str, soup: bs4.BeautifulSoup)`

Tests that the given URL appears in a link (`<a/>` tag) in the given soup, while being order-insensitive
about the order of query params.

### `assert_text_in_soup(text, soup, tag: str | None = None, exact=False)`

Tests that the given text appears in the soup, optionally inside the given type of tag.
If `exact` is `True` then the tag must contain _only_ the given text.

### `find_element_containing_text(soup, text, tax=None, exact=False) -> bs4.BeautifulSoup | None`

Similar to `assert_text_in_soup`, but returns the first found element which matches.


```python
from django.test import TestCase
from django_chutney.test_utils import SoupHelper

class MyTestCase(TestCase, SoupHelper):

    def test_page(self):
        response = self.client.get(reverse("my_view"))
        soup = self.soup(response)
        # Test that a link to a specific URL exists, with order-insensitive query params
        self.assert_link_in_soup("https://www.thing.com/?unordered=query&params=value", soup)
        self.assert_text_in_soup("Hello", soup)
        table_row = self.find_element_containing_text("John Smith")
        # The table row should contain a link to the user's profile
        self.assert_link_in_soup("/user/profile/{john_smith.pk}/", table_row)

```


## Template tags & filters

### `get` filter

Allows you to use a variable in the template as a key to extra an item from a dict to to extract
an attribute value from an object.

In Django templates, doing `{{obj.my_key}}` will try to do `obj["my_key"]`. So you can't use a
variable to supply the key.

This filter allows you to do `{{obj|get:my_var}}`, which will do `obj[my_var]` instead.

```html
{% load chutney_tags %}
<p>
    {{ my_dict|get:my_var }}
</p>
```