from showdown.battle import Battle
from showdown.engine.objects import StateMutator
from showdown.battle_bots.helpers import format_decision
from showdown.engine.find_state_instructions import get_all_state_instructions
from showdown.engine.select_best_move import pick_safest

import random
import copy
import itertools
import math

MAX_DEPTH = 200
TUNABLE_CONSTANT = 2 

class MonteCarloTree():

    def __init__(self, battle, state, depth=MAX_DEPTH):
        self.battle = battle
        self.state = state
        #self.mutator = StateMutator(state)
        self.wins = 0
        self.total = 0

        user_options, opponent_options = self.battle.get_all_options()
        self.transitions = list(itertools.product(user_options, opponent_options))
        self.children = {} #map from transition (our_move, opponent_move) to MonteCarloTree

    def win_rate(self):
        return self.wins / self.total

    # TODO add accumulator to reach depth
    def sample(self):
        self.total += 1
        next_child = self

        winner = self.state.battle_is_finished()
        if winner:
            if winner == 1: #we won
                self.wins += 1
                return True
            else:
                return False
            
        if len(self.children.keys()) == len(self.transitions):
            next_child = self.get_highest_ucb()
            playout_successful = next_child.sample()
            
        else:
            unexplored_transitions = list(self.transitions - self.children.keys())
            chosen_transition = random.choice(unexplored_transitions)
            next_child = self.generate_next_child(chosen_transition)
            self.children[chosen_transition] = next_child
            playout_successful = next_child.sample()

        if playout_successful: #backprop via boolean return of child
            self.wins += 1
            return True

        return False


    def generate_next_child(self, chosen_transition):
        mutator = StateMutator(self.state)
        state_instructions = get_all_state_instructions(mutator, chosen_transition[0], chosen_transition[1])
        #TODO choose a random insturction
        #for instructions in state_instructions:
        mutator.apply(random.choice(state_instructions).instructions)
        return MonteCarloTree(self.battle, mutator.state)

    def run(self, times):
        for i in range(times):
            self.sample()
        #run should return child node with most wins

    def get_child_from_move(self, our_move, opponent_move):
        return self.children[(our_move, opponent_move)]

    def get_best_move(self):
        winrates = {move: child.win_rate() for move, child in self.children }
        best_move = None
        best_winrate = 0
        for move, winrate in winrates.items():
            if winrate > best_winrate:
                best_winrate = winrate
                best_move = move

        return best_move, best_winrate
    
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
        self.battle_trees = {} # battle -> tree

    def find_best_move(self):
        # get possible game configurations
        battles = self.prepare_battles(join_moves_together=True) 

        # loop thru battles and construct montecarlo trees for each one
        # TODO: find way to hash battles so that we can know which battles to go back into

        all_scores = dict()
        trees = []
        for i, b in enumerate(battles):
            mctree = MonteCarloTree(b, b.create_state())
            mctree.run(100)
            trees.append(mctree)
            move, score = mctree.get_best_move()
            all_scores[move] = score
        
        decision, payoff = pick_safest(all_scores)
        bot_choice = decision[0]

        return format_decision(self, bot_choice)