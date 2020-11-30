from showdown.battle import Battle
from showdown.engine.objects import StateMutator
from showdown.battle_bots.helpers import format_decision
from showdown.engine.find_state_instructions import get_all_state_instructions
from showdown.engine.select_best_move import pick_safest
from showdown.engine.evaluate import evaluate

import random
import copy
import itertools
import math

MAX_DEPTH = 50
TUNABLE_CONSTANT = 2 

class MonteCarloTree():

    def __init__(self, state, depth=MAX_DEPTH):
        self.state = state
        #self.mutator = StateMutator(state)
        self.wins = 0
        self.total = 0
        self.max_depth = depth

        user_options, opponent_options = self.state.get_all_options()
        self.transitions = list(itertools.product(user_options, opponent_options))
        self.children = {} #map from transition (our_move, opponent_move) to {mutator instruction: MonteCarloTree}

    def win_rate(self):
        return self.wins / self.total

    def evaluate(self):
        number_of_opponent_reserve_revealed = len(self.state.opponent.reserve) + 1
        opponent_alive_reserves_count = len([p for p in self.state.opponent.reserve.values() if p.hp > 0]) + (6-number_of_opponent_reserve_revealed)
    
        score = 0
        score += self.evaluate_pokemon(self.state.self.active)
        for pkmn in self.state.self.reserve.values():
            score += self.evaluate_pokemon(pkmn)

        score -= self.evaluate_pokemon(self.state.opponent.active)
        for pkmn in self.state.opponent.reserve.values():
            score -= self.evaluate_pokemon(pkmn)

        for _ in range(opponent_alive_reserves_count):
            score -= 100

        return score

    def evaluate_pokemon(self, pkmn):
        if pkmn.hp <= 0:
            return 0
        return 100 * (float(pkmn.hp) / pkmn.maxhp)
 
    def sample(self, depth=0):
        self.total += 1

        if depth == self.max_depth:
            return self.evaluate() >= 0

        winner = self.state.battle_is_finished()
        if winner:
            if winner == 1: #we won
                self.wins += 1
                return True
            else:
                return False
            
        if len(self.children.keys()) == len(self.transitions):
            next_child = self.get_highest_ucb()
            playout_successful = next_child.sample(depth + 1)
        else:
            unexplored_transitions = list(self.transitions - self.children.keys())
            chosen_transition = random.choice(unexplored_transitions)
            next_child = self.generate_next_child(chosen_transition)
            self.children[chosen_transition] = next_child
            playout_successful = next_child.sample(depth + 1)

        if playout_successful: #backprop via boolean return of child
            self.wins += 1
            return True

        return False

    def generate_next_child(self, chosen_transition):
        mutator = StateMutator(copy.deepcopy(self.state))
        state_instructions = get_all_state_instructions(mutator, chosen_transition[0], chosen_transition[1])
        possible_instrucitons = [i.instructions for i in state_instructions]
        weights = [i.percentage for i in state_instructions]
        choice = random.choices(possible_instrucitons, weights=weights)[0]
        mutator.apply(choice)
        return MonteCarloTree(mutator.state)

    def run(self, times):
        for sample in range(times):
            self.sample()
            if sample % 50 == 0:
                print("[DEBUG]: ran ", sample, "/", times, " samples") 
        #run should return child node with most wins

    def get_child_from_move(self, our_move, opponent_move):
        return self.children[(our_move, opponent_move)]

    def get_best_move(self):
        payoff_matrix = {}
        for transition, child in self.children.items():
            if transition[0] not in payoff_matrix.keys():
                payoff_matrix[transition[0]] = [child.win_rate()]
            else:
                payoff_matrix[transition[0]].append(child.win_rate())

        # check for highest minimum win rate
        dominant_move = None
        dominant_winrate = None
        for move, winrates in payoff_matrix.items():
            min_winrate = min(winrates)
            if dominant_winrate is None or min_winrate > dominant_winrate:
                dominant_move = move
                dominant_winrate = min_winrate
        
        return dominant_move, dominant_winrate
    
    def get_highest_ucb(self):
        best_child = None
        best_child_weight = 0
        for move, child in self.children.items():
            w = child.win_rate() + math.sqrt(TUNABLE_CONSTANT * math.log(self.total) / child.total)
            if best_child is None or w > best_child_weight:
                best_child = child
                best_child_weight = w        
        return best_child

    def pretty_print(self, depth=0):
        for move, child in self.children.items():
            print("Move: " + str(move) + " WINS: " + str(child.wins) + " TOTAL: " + str(child.total))

class BattleBot(Battle):
    def __init__(self, *args, **kwargs):
        super(BattleBot, self).__init__(*args, **kwargs)
        self.battle_trees = {} # battle -> tree

    def find_best_move(self):
        # get possible game configurations
        battles = self.prepare_battles(join_moves_together=True) 

        all_scores = dict()
        for i, b in enumerate(battles):
            mctree = MonteCarloTree(b.create_state())
            mctree.run(350)
            mctree.pretty_print()

            move, score = mctree.get_best_move()
            print("SCORE PRINTED: " + str(score))
            if move in all_scores.keys():
                all_scores[move].append(score)
            else:
                all_scores[move] = [score]
        
        averages = { move: sum(scores)/len(scores) for move, scores in all_scores.items()}
        bot_choice = max(averages, key=averages.get)


        print("OUR MOVE:" + str(bot_choice) + " PROJECTED WINRATE: " + str(averages[bot_choice]))
        return format_decision(self, bot_choice)