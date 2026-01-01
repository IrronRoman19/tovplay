import pytest
from src.app.routes.signup_signin import signup_user
from src.app.models import User

def test_signup_success_flow(app, mock_users):
    data = mock_users["valid_user"]

    with app.app_context():
        new_user = signup_user(data)

        assert new_user.email == data["Email"].lower()
        assert new_user.username == data["Username"]

        saved_user = User.query.filter_by(email=data["Email"].lower()).first()
        assert saved_user is not None
        assert saved_user.discord_username == data["DiscordUsername"]

def test_signup_invalid_password(app, mock_users):
    data = mock_users["invalid_password"]

    with app.app_context():
        with pytest.raises(ValueError) as excinfo:
            signup_user(data)

        assert "Password" in str(excinfo.value)