from showdown.battle import Battle
from showdown.engine.objects import StateMutator
from showdown.battle_bots.helpers import format_decision

MAX_DEPTH = 200
TUNABLE_CONSTANT = 2 

class MonteCarloTree():

    def __init__(self, battle, depth=MAX_DEPTH):
        self.battle = battle
        self.mutator = StateMutator(state)
        self.children = {} #map from (our_move, opponent_move) to MonteCarloTree
        self.wins = 0
        self.total = 0

        user_options, opponent_options = self.battle.get_all_options()

        self.transitions = itertools 
    def win_rate(self):
        return self.wins / self.total

    def sample(self):
        self.total += 1
        self.mutator.

    def run(self, times):
        for i in range(times):
            self.sample()
        #run should return child node with most wins

    def get_child_from_move(our_move, opponent_move):
        return self.children[(our_move, opponent_move)]

    def get_best_move():
    
    def get_highest_ucb(self):
        best_child = None
        best_child_weight = 0
        for move, child in self.children.items():
            w = child.win_rate() + math.sqrt(TUNABLE_CONSTANT * math.log(self.total) / child.total)
            if best_child is None or w > best_child_weight:
                best_child = child
                best_child_weight = w        
        return best_child

# function MCTS_sample(state)
#     state.visits += 1
#     if all children of state expanded:
#         next_state = UCB_sample(state)
#         winner = MCTS_sample(next_state)
#     else:
#         if some children of state expanded:
#             next_state = expand(random unexpanded child)
#         else:
#             next_state = state
#         winner = random_playout(next_state)
#     update_value(state, winner)

# function UCB_sample(state):
#     weights = []
#     for child of state:
#         w = child.value + C * sqrt(ln(state.visits) / child.visits)
#         weights.append(w)
#     distribution = [w / sum(weights) for w in weights]
#     return child sampled according to distribution

# function random_playout(state):
#     if is_terminal(state):
#         return winner
#     else: return random_playout(random_move(state))

# function expand(state):
#     state.visits = 1
#     state.value = 0

# function update_value(state, winner):
#     # Depends on the application. The following would work for hex.
#     if winner == state.turn:
#         state.value += 1
#     else:
#         state.value -= 1



class BattleBot(Battle):
    def __init__(self, *args, **kwargs):
        super(BattleBot, self).__init__(*args, **kwargs)

    def find_best_move(self):
        battles = self.prepare_battles(join_moves_together=True) 



        best_move = None
        return format_decision(self, best_move)