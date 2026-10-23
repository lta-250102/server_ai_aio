"""Database helpers.

Thin wrappers around PyMongo operations for the ``users`` collection.
All functions operate on plain ``Collection`` objects passed by the caller,
making testing straightforward.
"""

from .user import (
    check_user_exists,
    create_user,
    delete_user,
    get_user,
    list_users,
    update_user,
)
