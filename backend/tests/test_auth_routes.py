import pytest
from fastapi import HTTPException
from app.api.routes.auth import register, login
from app.schemas.auth import UserRegister, UserLogin
from app.models import User, Role, UserRole
from app.core.security import get_password_hash, verify_password


class FakeQuery:
    def __init__(self, items):
        self.items = items

    def filter(self, *args, **kwargs):
        # Extremely simplified filter matching email
        return self

    def first(self):
        return self.items[0] if self.items else None


class FakeAuthSession:
    def __init__(self):
        self.added = []
        self.committed = False
        self.flushed = False
        self.refreshed = None
        self.users = []
        self.roles = []
        self.user_roles = []

    def query(self, model):
        if model is User:
            return FakeQuery(self.users)
        if model is Role:
            return FakeQuery(self.roles)
        if model is UserRole:
            return FakeQuery(self.user_roles)
        return FakeQuery([])

    def add(self, instance):
        self.added.append(instance)
        if isinstance(instance, User):
            self.users.append(instance)
            if not instance.id:
                from uuid import uuid4
                instance.id = uuid4()
        elif isinstance(instance, Role):
            self.roles.append(instance)
            if not instance.id:
                from uuid import uuid4
                instance.id = uuid4()
        elif isinstance(instance, UserRole):
            self.user_roles.append(instance)

    def flush(self):
        self.flushed = True

    def commit(self):
        self.committed = True

    def refresh(self, instance):
        self.refreshed = instance


def test_register_creates_user_with_hashed_password():
    session = FakeAuthSession()
    # Ensure role analyst/admin are returned as not existing yet
    session.roles = []

    request = UserRegister(
        email="test-analyst@example.com",
        password="securepassword123",
        display_name="Test Analyst"
    )

    response = register(request, session)

    assert response.access_token is not None
    assert response.email == "test-analyst@example.com"
    assert response.display_name == "Test Analyst"
    assert "analyst" in response.roles
    assert "admin" in response.roles
    assert session.committed is True

    # Check password hashing
    user = session.users[0]
    assert user.email == "test-analyst@example.com"
    assert verify_password("securepassword123", user.password_hash) is True


def test_register_rejects_duplicate_email():
    session = FakeAuthSession()
    # Pre-populate existing user
    existing_user = User(
        email="test-analyst@example.com",
        password_hash=get_password_hash("password123"),
        display_name="Existing"
    )
    session.users = [existing_user]

    request = UserRegister(
        email="test-analyst@example.com",
        password="securepassword123",
        display_name="Test Analyst"
    )

    with pytest.raises(HTTPException) as exc_info:
        register(request, session)

    assert exc_info.value.status_code == 400
    assert "already registered" in exc_info.value.detail


def test_login_successful_with_correct_credentials():
    session = FakeAuthSession()
    user = User(
        email="test-analyst@example.com",
        password_hash=get_password_hash("securepassword123"),
        display_name="Test Analyst",
        is_active=True
    )
    # Mock user roles
    role_admin = Role(name="admin", description="Admin")
    role_analyst = Role(name="analyst", description="Analyst")
    user.roles = [
        UserRole(user=user, role=role_admin),
        UserRole(user=user, role=role_analyst)
    ]
    session.users = [user]

    request = UserLogin(
        email="test-analyst@example.com",
        password="securepassword123"
    )

    response = login(request, session)

    assert response.access_token is not None
    assert response.email == "test-analyst@example.com"
    assert response.display_name == "Test Analyst"
    assert "admin" in response.roles
    assert "analyst" in response.roles


def test_login_rejects_incorrect_password():
    session = FakeAuthSession()
    user = User(
        email="test-analyst@example.com",
        password_hash=get_password_hash("securepassword123"),
        display_name="Test Analyst",
        is_active=True
    )
    session.users = [user]

    request = UserLogin(
        email="test-analyst@example.com",
        password="wrongpassword"
    )

    with pytest.raises(HTTPException) as exc_info:
        login(request, session)

    assert exc_info.value.status_code == 401
    assert "Invalid email or password" in exc_info.value.detail
