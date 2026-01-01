from flask import Blueprint, jsonify

from ..models import Game

game_bp = Blueprint("game", __name__)


@game_bp.route("/", methods=["GET"])
def get_games():
    games = Game.query.all()
    return jsonify([game.to_dict() for game in games]), 200


@game_bp.route("/<uuid:game_id>", methods=["GET"])
def get_game_by_id(game_id):
    # TODO: Added the endpoint so that requests sent from the dashboard will get resolved correctly,
    #  until /game_requests/ returns the game name instead of the UUID
    game = Game.query.get_or_404(game_id)
    return jsonify(game.to_dict()), 200


@game_bp.route("/<game_name>", methods=["GET"])
def get_game(game_name):
    game = Game.query.filter_by(game_name=game_name).first()
    return jsonify(game.to_dict()), 200
