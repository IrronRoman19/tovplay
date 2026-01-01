from sqlalchemy import func
from uuid import uuid4

def test_matchmaking_sanity_flow(client):
    """
    SANITY CHECK: Full Matchmaking Lifecycle
    """

    suffix = uuid4().hex[:8]  # unique per test run

    print("\n[Step 1] Creating Players...")
    player_a = {
        "Email": f"sanityA_{suffix}@test.com",
        "Username": f"SanityA_{suffix}",
        "Password": "Str0ng!PassX9",
        "DiscordUsername": f"SanityA_{suffix}#1234",
    }
    player_b = {
        "Email": f"sanityB_{suffix}@test.com",
        "Username": f"SanityB_{suffix}",
        "Password": "Str0ng!PassX9",
        "DiscordUsername": f"SanityB_{suffix}#1234",
    }

    # --- REGISTER (must be 201; if it's 400, you're hitting an existing unverified user) ---
    resp_a = client.post("/api/users/signup", json=player_a)
    assert resp_a.status_code == 201, f"Reg A failed: {resp_a.text}"

    resp_b = client.post("/api/users/signup", json=player_b)
    assert resp_b.status_code == 201, f"Reg B failed: {resp_b.text}"

    # --- MANUAL VERIFICATION + LOWERCASE ASSERT ---
    from src.app.models import User, db

    sanity_a = User.query.filter(func.lower(User.email) == player_a["Email"].lower()).first()
    assert sanity_a is not None, "User A not found in DB after signup"
    assert sanity_a.email == player_a["Email"].lower(), f"User A email not stored lowercased: {sanity_a.email}"
    sanity_a.verified = True

    sanity_b = User.query.filter(func.lower(User.email) == player_b["Email"].lower()).first()
    assert sanity_b is not None, "User B not found in DB after signup"
    assert sanity_b.email == player_b["Email"].lower(), f"User B email not stored lowercased: {sanity_b.email}"
    sanity_b.verified = True

    db.session.commit()

    # --- LOGIN ---
    login_a = client.post("/api/users/login", json={
        "Email": player_a["Email"],
        "Password": player_a["Password"],
    })
    assert login_a.status_code == 200, f"Login A failed: {login_a.text}"
    token_a = login_a.json.get("jwt_token")
    assert token_a, f"Login A missing jwt_token: {login_a.text}"

    login_b = client.post("/api/users/login", json={
        "Email": player_b["Email"],
        "Password": player_b["Password"],
    })
    assert login_b.status_code == 200, f"Login B failed: {login_b.text}"
    token_b = login_b.json.get("jwt_token")
    assert token_b, f"Login B missing jwt_token: {login_b.text}"

    headers_b = {"Authorization": f"Bearer {token_b}"}

    # --- SET AVAILABILITY ---
    resp_avail = client.post(
        "/api/availability/",
        json={"slots": {"Monday-18:00": True}, "is_recurring": True},
        headers=headers_b,
    )
    assert resp_avail.status_code in (200, 201), f"Availability failed: {resp_avail.text}"

    print("[Success] Sanity Flow Complete!")