from bson import ObjectId
from models.entity import User
from pymongo.collection import Collection


def get_user(user_id: str, users_collection: Collection) -> User | None:
    doc = users_collection.find_one({"_id": ObjectId(user_id)})
    if not doc:
        return None
    return User.model_validate(doc)


def create_user(user: User, users_collection: Collection) -> User:
    doc = user.model_dump(by_alias=True, exclude_none=True)
    result = users_collection.insert_one(doc)
    doc["_id"] = result.inserted_id
    return User.model_validate(doc)


def check_user_exists(email: str, users_collection: Collection) -> bool:
    return users_collection.find_one({"user_email": email}) is not None


def update_user(user_id: str, update_data: dict, users_collection: Collection) -> User | None:
    result = users_collection.find_one_and_update(
        {"_id": ObjectId(user_id)},
        {"$set": update_data},
        return_document=True,
    )
    if not result:
        return None
    return User.model_validate(result)


def list_users(users_collection: Collection) -> list[User]:
    return [User.model_validate(doc) for doc in users_collection.find()]


def delete_user(user_id: str, users_collection: Collection) -> bool:
    result = users_collection.delete_one({"_id": ObjectId(user_id)})
    return result.deleted_count > 0
