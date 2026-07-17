from django.test import TestCase

<<<<<<< HEAD

class SmokeTest(TestCase):
    def test_root_url_resolves(self):
        response = self.client.get("/")
        # Expect 200 or 302 depending on auth/redirects; assert no server error
        self.assertLess(response.status_code, 500)
=======
# Create your tests here.
>>>>>>> 5815f15 (Initial project commit)
