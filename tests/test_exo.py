from unittest import TestCase
import exo.page
from exo.exo import Exo
from exo.exceptions import AppMustUseExoSubclass


class Test(TestCase):
    def test_extension_loading(self):
        class App(Exo):
            ...

        app = App()

        self.assertTrue(
            hasattr(app, "__repositories__"),
            "Metaclass failed to create any repositories for the app",
        )
        self.assertTrue(
            hasattr(app, "Page"),
            "Page extension registration class failed to associate with the app",
        )

    def test_base_Exo_class(self):
        with self.assertRaises(
            AppMustUseExoSubclass,
            msg="Should not be possible to instantiate the base Exo class",
        ):
            Exo()

    def test_extension_subclassing(self):
        class EmptyApp(Exo):
            ...

        class App(Exo):
            ...

        class MyPage(App.Page):
            pass

        self.assertIn(
            "MyPage",
            App.__repositories__["Page"].registry,
            "The page class was not added to the page repository for App",
        )

        self.assertNotIn(
            "MyPage",
            EmptyApp.__repositories__["Page"].registry,
            "The page class was added to the page repository for EmptyApp",
        )

        self.assertIsInstance(
            MyPage(),
            exo.page.Page,
            "The page is not a subclass of the exo.page.Page class",
        )
