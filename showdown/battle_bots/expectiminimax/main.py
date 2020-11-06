from showdown.battle import Battle

from showdown.battle_bots.helpers import format_decision


class BattleBot(Battle):
    def __init__(self, *args, **kwargs):
        super(BattleBot, self).__init__(*args, **kwargs)

    def find_best_move(self):
        best_move = None
        return format_decision(self, best_move)