"""
One module per sidebar menu.

Every path here matches an entry in ``js/core/api.js::endpoints`` exactly, so
the client and the server can be read side by side. Order the router mounts
with the literal paths that would otherwise be swallowed by a path parameter,
e.g. ``/clients/export`` must be declared before ``/clients/{id}``.
"""