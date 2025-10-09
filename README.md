# Django Chutney
Tasty accompaniments to go with the Django web framework

My personal collection of miscellaneous useful bits of code for use in Django projects.

## Installation

`pip install django-chutney`


## Usage

The library is intended to be a pick and mix bucket from which you can choose to use whichever bits you want.


## Test cases

Handy test cases for testing HTML pages and forms.

These require BeautifulSoup to be installed:
```
pip install beautifulsoup4>=4
```

```python
from django_chutney.test.testcases import FormTestCase, SoupCase

class MyTestCase(SoupSoup):

    def test_page(self):
        response = self.client.get(reverse("my_view"))
        soup = self.soup(response)
        # Test that a link to a specific URL exists, with order-insensitive query params
        self.assert_link_in_soup(soup, "https://www.thing.com/?unordered=query&params=value")


class MyFormTestCase(FormTestCase):

    def test_form_page(self):
        page_response = self.client.get(reverse("my_view"))
        # Submit a form to the page, with automatic checking that the values you're submitting are
        # possible values for a browser to submit based on the HTML of the form in the page.
        # Also submits hidden values that are in the form, even if you don't specific them.
        data = {"field1": "some-value"}
        post_response = self.submit_form(response, "#my-form", data)
        self.assertEqual(post_response.status_code, 302)
```


## Template tags & filters

```html
{% load chutney_tags %}
<p>
    Use a variable in the template as a key/attribute to extract an item from a dict/object:
</p>
<p>
    {{ my_dict|get:my_var }}
</p>
```