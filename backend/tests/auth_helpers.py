from __future__ import annotations

from types import SimpleNamespace

from app.api.dependencies import get_current_user, get_current_workspace

TEST_USER = SimpleNamespace(
    id="user_test",
    email="tester@example.com",
    display_name="Test User",
)
TEST_WORKSPACE = SimpleNamespace(
    id="ws_test",
    name="Test User Personal",
    is_personal=True,
    role="owner",
)


def install_auth_overrides(app):
    async def override_current_user():
        return TEST_USER

    async def override_current_workspace():
        return TEST_WORKSPACE

    app.dependency_overrides[get_current_user] = override_current_user
    app.dependency_overrides[get_current_workspace] = override_current_workspace
    return TEST_USER, TEST_WORKSPACE
