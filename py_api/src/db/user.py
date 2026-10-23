"""MongoDB user operations.

Every function accepts a ``Collection`` object so that the caller controls
which database / collection is used.  This keeps persistence logic
independent of application configuration.
"""

from bson import ObjectId
from pymongo.collection import Collection

from models.entity import User


def get_user(user_id: str, users_collection: Collection) -> User | None:
    """Return a :class:`~models.entity.User` for *user_id*, or ``None``."""
    doc = users_collection.find_one({"_id": ObjectId(user_id)})
    if not doc:
        return None
    return User.model_validate(doc)


def create_user(user: User, users_collection: Collection) -> User:
    """Insert *user* into the database and return the populated entity."""
    doc = user.model_dump(by_alias=True, exclude_none=True)
    result = users_collection.insert_one(doc)
    doc["_id"] = result.inserted_id
    return User.model_validate(doc)


def check_user_exists(email: str, users_collection: Collection) -> bool:
    """Return ``True`` when a user with *email* already exists."""
    return users_collection.find_one({"user_email": email}) is not None


def update_user(
    user_id: str,
    update_data: dict,
    users_collection: Collection,
) -> User | None:
    """Apply a partial update (*update_data*) to the user identified by *user_id*.

    Returns the updated :class:`~models.entity.User` or ``None`` if not found.
    """
    result = users_collection.find_one_and_update(
        {"_id": ObjectId(user_id)},
        {"$set": update_data},
        return_document=True,
    )
    if not result:
        return None
    return User.model_validate(result)


def list_users(users_collection: Collection) -> list[User]:
    """Return every user in the collection."""
    return [User.model_validate(doc) for doc in users_collection.find()]


def delete_user(user_id: str, users_collection: Collection) -> bool:
    """Delete the user identified by *user_id*.  Returns ``True`` if a document was removed."""
    result = users_collection.delete_one({"_id": ObjectId(user_id)})
    return result.deleted_count > 0
