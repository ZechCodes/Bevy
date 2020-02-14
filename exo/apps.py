from __future__ import annotations
from abc import ABC, abstractmethod
from exo.components import ExoComponent
from exo.extensions import ExoExtension
from exo.repositories import ExoRepository, Repository
from typing import (
    Any,
    Awaitable,
    Callable,
    Coroutine,
    Dict,
    Iterable,
    Sequence,
    Tuple,
    Type,
    TypeVar,
)
import asyncio


ExoApp = TypeVar("ExoApp", bound="AbstractApp")


class AbstractApp(ABC):
    @abstractmethod
    def add_component(self, component: Type[ExoComponent]) -> ExoApp:
        return self

    @abstractmethod
    def add_extension(self, extension: Type[ExoExtension]) -> ExoApp:
        return self

    @abstractmethod
    async def run(self, *args, **kwargs) -> Any:
        return


class App(AbstractApp):
    def __init__(
        self,
        *args,
        components: Sequence[Type[ExoComponent]] = tuple(),
        environment: Type = dict,
        extensions: Sequence[Type[ExoExtension]] = tuple(),
        repository: Type[ExoRepository] = Repository,
        **kwargs
    ):
        self._components = set()
        self._extensions = set()
        self._repository = repository()

        self._build_environment(environment, args, kwargs)
        self._load_extensions(extensions)
        self._load_components(components)

    def add_extension(self, extension: Type[ExoExtension]) -> ExoApp:
        """ Adds an extension instance to the app repository. Extensions will
        exist for the lifetime of the app instance. """
        self._extensions.add(
            self._repository.get(extension.__name__, default=extension)
        )
        return self

    def add_component(self, component: Type[ExoComponent]):
        """ Adds a component to the app which will be instantiated when the app
        run method is called. Component instances will only exist during the
        app run event, they will also be given a reduced scope repository that
        is the state object for the run event. """
        self._components.add(component)

    @property
    def run(self) -> Any:
        """ Creates an app runner that executes the run method on all of the
        registered components. The components will all be instantiated with a
        scope that will exist only within this call. """
        component_repo, scoped_repo = self._build_run_environment()
        self._create_components(component_repo, scoped_repo)
        return self._run_components(component_repo)

    def _build_environment(
        self, context: Type, _: Tuple, values: Dict[str, Any]
    ) -> None:
        self._repository.set("app", self, instantiate=False)
        self._repository.set("env", context(**values), instantiate=False)

    def _build_run_environment(self) -> Tuple[ExoRepository, ExoRepository]:
        component_repo = self._repository.create_child()
        scoped_repo = component_repo.create_child()
        scoped_repo.set(
            "components", component_repo, instantiate=False, repository=scoped_repo
        )
        return component_repo, scoped_repo

    def _create_components(self, repository: ExoRepository, scope: ExoRepository):
        for component in self._components:
            repository.set(component.__name__, component, repository=scope)

    def _load_components(self, components: Sequence[Type[ExoComponent]]) -> None:
        for component in components:
            self.add_component(component)

    def _load_extensions(self, extensions: Sequence[Type[ExoExtension]]) -> None:
        for extension in extensions:
            self.add_extension(extension)

    def _run_components(self, components: Iterable[ExoComponent]) -> Any:
        return AppRunner([component.run for component in components])


class AppRunner:
    """ Runs components and gives some use methods for getting the result
    you're after. """

    def __init__(self, tasks: Sequence[Coroutine]):
        self._queue = asyncio.Queue()
        self._done = asyncio.Event()
        self._running = asyncio.Event()
        self._new_result = asyncio.Event()
        self._tasks = tasks
        self._last_result = None

    @property
    def done(self) -> bool:
        """ Whether all components have run and returned. """
        return self._done.is_set()

    @property
    def running(self) -> bool:
        """ Whether any components are still running. """
        return self._running.is_set()

    def __await__(self):
        return self.execute().__await__()

    def __call__(self, *args, **kwargs) -> Awaitable:
        return self.execute(*args, **kwargs)

    def __aiter__(self) -> AppRunner:
        self._run()
        return self

    async def __anext__(self) -> Any:
        if not self.done and self._queue.empty():
            await self._new_result.wait()

        if self.done and self._queue.empty():
            raise StopAsyncIteration

        return self._queue.get_nowait()

    async def execute(self, *args, **kwargs) -> Any:
        """ Allows for arguments to be passed into the component run methods.
        This functions the same as awaiting the runner and only returns the
        last value received."""
        self._run(*args, **kwargs)
        await self._done.wait()
        return self._last_result

    async def flatten(self, *args, **kwargs) -> Sequence[Any]:
        """ Runs all components and returns a list of all the values they
        returned. """
        self._run(*args, **kwargs)
        return [result async for result in self]

    async def reduce(self, func: Callable[[any, any], any], *args, **kwargs) -> Any:
        """ Applies a function to two return values until there are no
        components left to return, returns the final value given by the
        function. """
        self._run(*args, **kwargs)
        values = []
        async for result in self:
            values.append(result)
            if len(values) == 2:
                values = [func(*values)]
        return values[0] if values else None

    def _run(self, *args, **kwargs):
        """ Runs the executor, setting the running event before creating the
        event loop task. """
        if not self.running and not self.done:
            self._running.set()
            asyncio.create_task(self._executor(*args, **kwargs))

    async def _executor(self, *args, **kwargs):
        """ Awaits all of the components calling them with the provided
        arguments and wrapping them in a runner that will notify the app runner
        when the component has finished. """
        await asyncio.gather(
            *[self._runner(task(*args, **kwargs)) for task in self._tasks]
        )
        self._running.clear()
        self._done.set()
        self._new_result.set()

    async def _runner(self, awaitable: Awaitable):
        """ Component runner that saves the returned value and clears the
        new result event. """
        self._save_result(await awaitable)
        self._new_result.clear()

    def _save_result(self, result: Any):
        """ Saves a return and sets the new result event. """
        self._queue.put_nowait(result)
        self._new_result.set()
        self._last_result = result
