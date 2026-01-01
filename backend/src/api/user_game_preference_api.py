from flask import jsonify
from sqlalchemy import and_, or_

from src.app.db import db
from src.app.models import Game, User, UserGamePreference

def get_user_games(user_id):
    games = UserGamePreference.query.filter_by(user_id=user_id).all()
    return [Game.query.get_or_404(game.game_id).game_name for game in games]

def add_preference(user_id, game_name):
    game_name = game_name.title()
    user = User.query.filter_by(id=user_id).first()
    if not user:
        raise ValueError("User not found.")
    if not user.verified:
        raise ValueError(
            f"{user.username}, you must verify your email before you can choose your game preferences."
        )
    game = Game.query.filter_by(game_name=game_name).first()
    if not game:
        raise ValueError("Game not found.")
    if UserGamePreference.query.filter(
        and_(UserGamePreference.user_id == user_id, UserGamePreference.game_id == game.id)
    ).first():
        return f"You have already added '{game_name}' to your game preferences.", 200
    new_preference = UserGamePreference(user_id=user_id, game_id=game.id)
    db.session.add(new_preference)
    db.session.commit()
    return jsonify(new_preference.to_dict()), 201

def put_games(user_id, games):
    current_games =  UserGamePreference.query.filter_by(user_id=user_id).all()
    deleted = []
    added = []
    for game in current_games:
        game_name = Game.query.get_or_404(game.game_id).game_name
        if game_name in games:
            games.remove(game_name)
        else:
            deleted.append(game_name)
            print("deleted ", game_name)
            db.session.delete(game)
    for game in games:
        game_id = Game.query.filter_by(game_name=game).first().id
        new_preference = UserGamePreference(user_id=user_id, game_id=game_id)
        db.session.add(new_preference)
        added.append(game)
        print("added ", game)
    db.session.commit()
    return added, deleted