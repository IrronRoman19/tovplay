# from flask import jsonify, Blueprint, request
# from src.app.models import UserAvailability, db
#
#
# game_bp = Blueprint('platform', __name__)
#
# @game_bp.route('/api/all-games', methods=['GET'])
# def get_games():
#     # get all available games on the platform
#
#     return jsonify({"games": [game.to_dict() for game in games]}), 200
