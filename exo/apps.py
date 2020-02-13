from __future__ import annotations
from abc import ABC, abstractmethod
from exo.components import ExoComponent
from exo.extensions import ExoExtension
from exo.repositories import ExoRepository, Repository
from typing import Any, Awaitable, Dict, Iterable, Sequence, Tuple, Type, TypeVar
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

    def run(self, *args, **kwargs) -> Any:
        component_repo, scoped_repo = self._build_run_environment(*args, **kwargs)
        self._create_components(component_repo, scoped_repo)
        return self._run_components(component_repo, *args, **kwargs)

    def _build_environment(
        self, context: Type, _: Tuple, values: Dict[str, Any]
    ) -> None:
        self._repository.set("app", self, instantiate=False)
        self._repository.set("env", context(**values), instantiate=False)

    def _build_run_environment(self, *_, **__) -> Tuple[ExoRepository, ExoRepository]:
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

    def _run_components(
        self, components: Iterable[ExoComponent], *args, **kwargs
    ) -> Any:
        return AppRunner(
            [component.run(None, *args, **kwargs) for component in components]
        )


class AppRunner:
    def __init__(self, tasks: Sequence[Awaitable]):
        self._results = []
        self._tasks = tasks

    def __await__(self):
        return self.execute().__await__()

    async def execute(self):
        await asyncio.gather(*[self._runner(task) for task in self._tasks])
        return self._results[-1] if self._results else None

    async def _runner(self, awaitable: Awaitable):
        self._save_result(await awaitable)

    def _save_result(self, result: Any):
        self._results.append(result)
