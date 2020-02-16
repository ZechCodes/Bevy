from unittest import TestCase
from exo.exo import Exo
from exo.app import ExoApp
import asyncio


class TestExoApp(TestCase):
    def test_run(self):
        class Extension(Exo):
            async def run(self):
                return "Hello"

        class ExtensionB(Exo):
            async def run(self):
                return "World"

        loop = asyncio.get_event_loop()
        app = ExoApp([ExtensionB, Extension])

        self.assertTrue(hasattr(app, "extensions"))
        self.assertTrue(hasattr(app, "run"))
        self.assertEqual(len(app.extensions._extensions), 2)
        self.assertIs(app.extensions, app.run.extensions)
        self.assertEqual(
            "Hello World", " ".join(sorted(loop.run_until_complete(app.run())))
        )
