from unittest import TestCase
from exo import apps, extensions, components, uses


class TestApp(TestCase):
    def create_app(self, *args, **kwargs):
        return apps.App(*args, **kwargs)

    def test_instantiation(self):
        self.create_app()

    def test_add_extension(self):
        class TestExtension(extensions.Extension):
            loaded = False

            def __init__(self):
                TestExtension.loaded = True

        app = self.create_app()
        app.add_extension(TestExtension)

        self.assertTrue(TestExtension.loaded, "The extension was not loaded")

    def test_add_extension_init(self):
        class TestExtension(extensions.Extension):
            loaded = False

            def __init__(self):
                TestExtension.loaded = True

        app = self.create_app(extensions=[TestExtension])

        self.assertTrue(TestExtension.loaded, "The extension was not loaded")

    def test_run(self):
        app = self.create_app()

        self.assertIsNone(app.run(), "Run returned something")

    def test_add_component_runs(self):
        class TestComponent(components.Component):
            ran = False

            def run(self, result):
                TestComponent.ran = True

        app = self.create_app()
        app.add_component(TestComponent)

        self.assertFalse(TestComponent.ran, "Component ran too early")
        app.run()
        self.assertTrue(TestComponent.ran, "Component didn't run")

    def test_add_component_init_runs(self):
        class TestComponent(components.Component):
            ran = False

            def run(self, result):
                TestComponent.ran = True

        app = self.create_app(components=[TestComponent])

        self.assertFalse(TestComponent.ran, "Component ran too early")
        app.run()
        self.assertTrue(TestComponent.ran, "Component didn't run")

    def test_result_change(self):
        class TestComponent(components.Component):
            sentinel = object()

            def run(self, result):
                return TestComponent.sentinel

        app = self.create_app(components=[TestComponent])

        self.assertIs(app.run(), TestComponent.sentinel, "Result value was not changed")

    def test_extensions_adding_components(self):
        @uses(app="app")
        class TestExtension(extensions.Extension):
            def __init__(self):
                self.app.add_component(TestComponent)

        class TestComponent(components.Component):
            sentinel = object()

            def run(self, result):
                return TestComponent.sentinel

        app = self.create_app(extensions=[TestExtension])

        self.assertIs(app.run(), TestComponent.sentinel, "The component was not run")

    def test_components_can_access_env(self):
        @uses(app="app")
        class TestComponent(components.Component):
            def run(self, result):
                return self.app

        app = self.create_app(components=[TestComponent])
        app.sentinel = object()

        self.assertIs(
            app.run(),
            app,
            "The component did not have access to the correct environment",
        )

    def test_extensions_only_instantiate_at_app_create(self):
        class TestExtension(extensions.Extension):
            ...

        @uses(ext="TestExtension")
        class TestComponent(components.Component):
            def run(self, result):
                return self.ext

        app = self.create_app(extensions=[TestExtension], components=[TestComponent])

        run1 = app.run()
        run2 = app.run()

        self.assertIsInstance(
            run1, extensions.Extension, "The extension was not returned"
        )
        self.assertIs(run1, run2, "The extension was re-instantiated between runs")
