from opentracing import ScopeManager  # noqa:F401

from ddtrace._trace.provider import BaseContextProvider  # noqa:F401


# DEV: If `asyncio` or `gevent` are unavailable we do not throw an error,
#    `context_provider` will just not be set and we'll get an `AttributeError` instead


def get_context_provider_for_scope_manager(scope_manager):
    # type: (ScopeManager) -> BaseContextProvider
    """Returns the context_provider to use with a given scope_manager."""

    scope_manager_type = type(scope_manager).__name__

    # avoid having to import scope managers which may not be compatible
    # with the version of python being used
    if scope_manager_type == "AsyncioScopeManager":
        import ddtrace.contrib.asyncio

        dd_context_provider = ddtrace.contrib.asyncio.context_provider  # type: BaseContextProvider
    elif scope_manager_type == "GeventScopeManager":
        import ddtrace.contrib.gevent

        dd_context_provider = ddtrace.contrib.gevent.context_provider
    else:
        from ddtrace._trace.provider import DefaultContextProvider

        dd_context_provider = DefaultContextProvider()

    _patch_scope_manager(scope_manager, dd_context_provider)

    return dd_context_provider


def _patch_scope_manager(scope_manager, context_provider):
    # type: (ScopeManager, BaseContextProvider) -> None
    """
    Patches a scope manager so that any time a span is activated
    it'll also activate the underlying ddcontext with the underlying
    datadog context provider.

    This allows opentracing users to rely on ddtrace.contrib patches and
    have them parent correctly.

    :param scope_manager: Something that implements `opentracing.ScopeManager`
    :param context_provider: Something that implements `datadog.provider.BaseContextProvider`
    """
    if getattr(scope_manager, "_datadog_patch", False):
        return
    scope_manager._datadog_patch = True

    old_method = scope_manager.activate

    def _patched_activate(*args, **kwargs):
        otspan = kwargs.get("span", args[0])
        context_provider.activate(otspan._dd_context)
        return old_method(*args, **kwargs)

    scope_manager.activate = _patched_activate
