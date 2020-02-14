from unittest import TestCase
from exo import apps, extensions, components, uses
import asyncio


class TestApp(TestCase):
    def create_app(self, *args, **kwargs):
        return apps.App(*args, **kwargs)

    def run_app(self, coro, loop=None):
        loop = loop if loop else asyncio.get_event_loop()
        return loop.run_until_complete(coro)

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

        self.assertIsNone(self.run_app(app.run()), "Run returned something")

    def test_add_component_runs(self):
        class TestComponent(components.Component):
            ran = False

            async def run(self):
                TestComponent.ran = True

        app = self.create_app()
        app.add_component(TestComponent)

        self.assertFalse(TestComponent.ran, "Component ran too early")
        self.run_app(app.run())
        self.assertTrue(TestComponent.ran, "Component didn't run")

    def test_add_component_init_runs(self):
        class TestComponent(components.Component):
            ran = False

            async def run(self):
                TestComponent.ran = True

        app = self.create_app(components=[TestComponent])

        self.assertFalse(TestComponent.ran, "Component ran too early")
        self.run_app(app.run())
        self.assertTrue(TestComponent.ran, "Component didn't run")

    def test_result_change(self):
        class TestComponent(components.Component):
            sentinel = object()

            async def run(self):
                return TestComponent.sentinel

        app = self.create_app(components=[TestComponent])

        self.assertIs(
            self.run_app(app.run()),
            TestComponent.sentinel,
            "Result value was not changed",
        )

    def test_extensions_adding_components(self):
        @uses(app="app")
        class TestExtension(extensions.Extension):
            def __init__(self):
                self.app.add_component(TestComponent)

        class TestComponent(components.Component):
            sentinel = object()

            async def run(self):
                return TestComponent.sentinel

        app = self.create_app(extensions=[TestExtension])

        self.assertIs(
            self.run_app(app.run()), TestComponent.sentinel, "The component was not run"
        )

    def test_components_can_access_env(self):
        @uses(app="app")
        class TestComponent(components.Component):
            async def run(self):
                return self.app

        app = self.create_app(components=[TestComponent])
        app.sentinel = object()

        self.assertIs(
            self.run_app(app.run()),
            app,
            "The component did not have access to the correct environment",
        )

    def test_extensions_only_instantiate_at_app_create(self):
        class TestExtension(extensions.Extension):
            ...

        @uses(ext="TestExtension")
        class TestComponent(components.Component):
            async def run(self):
                return self.ext

        app = self.create_app(extensions=[TestExtension], components=[TestComponent])

        run1 = self.run_app(app.run())
        run2 = self.run_app(app.run())

        self.assertIsInstance(
            run1, extensions.Extension, "The extension was not returned"
        )
        self.assertIs(run1, run2, "The extension was re-instantiated between runs")

    def test_run_flatten(self):
        class TestComponent(components.Component):
            async def run(self):
                ...

        class TestComponentB(components.Component):
            async def run(self):
                ...

        app = self.create_app(components=[TestComponent, TestComponentB])

        loop = asyncio.get_event_loop()
        self.assertEqual(
            len(self.run_app(app.run.flatten(), loop=loop)),
            2,
            "Not all results were returned",
        )

    def test_run_reduce(self):
        class TestComponent(components.Component):
            async def run(self):
                await asyncio.sleep(0.01)
                return 2

        class TestComponentB(components.Component):
            async def run(self):
                return 1

        app = self.create_app(components=[TestComponent, TestComponentB])

        def reduce(value_1, value_2):
            return value_1 - value_2

        loop = asyncio.get_event_loop()
        self.assertEqual(
            self.run_app(app.run.reduce(reduce), loop=loop),
            -1,
            "Not all results were returned",
        )

    def test_run_stream(self):
        class TestComponent(components.Component):
            async def run(self):
                await asyncio.sleep(0.01)
                return 2

        class TestComponentB(components.Component):
            async def run(self):
                return 1

        app = self.create_app(components=[TestComponent, TestComponentB])

        async def testing():
            results = []
            async for result in app.run:
                results.append(result)
            return results

        self.assertEqual(
            self.run_app(testing()), [1, 2], "Results were not streamed correctly"
        )
