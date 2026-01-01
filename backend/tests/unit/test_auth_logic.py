def test_login_invalid_password(client):
    """Test that login fails with wrong password."""

    user_data = {
        "Email": "auth_test@example.com",
        "Username": "AuthTest",
        "Password": "Str0ng!PassX9",
        "DiscordUsername": "Test#0000"
    }

    # Create user
    client.post("/api/users/signup", json=user_data)

    # Manually verify user
    from src.app.models import User, db
    user = User.query.filter_by(email="auth_test@example.com").first()
    assert user is not None

    user.verified = True
    db.session.commit()

    # Attempt login with wrong password
    response = client.post("/api/users/login", json={
        "Email": "auth_test@example.com",
        "Password": "WRONGPASSWORD"
    })

    assert response.status_code == 401

    # ✅ Assert semantic meaning from JSON, not exact phrasing
    data = response.get_json()
    assert data is not None
    assert "message" in data

    msg = data["message"].lower()
    assert "password" in msg
    assert "email" in msg