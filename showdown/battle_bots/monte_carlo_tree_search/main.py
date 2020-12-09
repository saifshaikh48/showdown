from showdown.battle import Battle
from showdown.engine.objects import StateMutator
from showdown.battle_bots.helpers import format_decision
from showdown.engine.find_state_instructions import get_all_state_instructions
from showdown.engine.select_best_move import pick_safest
from showdown.engine.evaluate import evaluate
import logging

import random
import copy
import itertools
import math

MAX_DEPTH = 15
TUNABLE_CONSTANT = 2 
SAMPLE_COUNT = 3000

BLACKLISTED_MOVES = set(['voltswitch', 'uturn', 'outrage'])
def get_transitions(state):
    user_options, opponent_options = state.get_all_options()
    user_options = list(set(user_options) - BLACKLISTED_MOVES)
    return list(itertools.product(user_options, opponent_options))

class MonteCarloTree():
    """
    Object representing a node in a monte carlo tree
    Instance Variables:
        - state: represenation of the current battle including all pokemon's updated health, environment information, etc.
        - wins: the number of playouts in this tree's children that resulted in a "win" based on the evaluation function
        - total: the total number of playouts resulting from this tree and it's children
        - max_depth: how deep to explore this MC tree's child nodes
        - transitions: set of all possible moves, combining our move and opponent move possibilities
        - children: this node's children based on chosen transitions to explore
    """

    def __init__(self, state):
        self.state = state
        self.wins = 0
        self.total = 0

        self.transitions = get_transitions(state)
        self.children = {} #map from transition (our_move, opponent_move) -> MonteCarloTree

    def win_rate(self):
        """
        Returns the number of wins divided by the total number of playouts
        """
        return self.wins / self.total
 
    def sample(self, initial_position, depth=0):
        """
        Selects a new node to add to a montecarlo search tree. If a there are unexplored
        transitions it opts to randomly choose one of those first. Otherwise, it 
        recurs on its child node with highest UCB value. Once the node is selected a
        random playout is run. If the result  of the playout is a win or leads to
        a favorable position, then a win is back propagated up the tree.
        """
        self.total += 1

        if depth == MAX_DEPTH:
            if evaluate(self.state) >= initial_position:
                self.wins += 1
                return True
            else:
                return False

        winner = self.state.battle_is_finished()
        if winner:
            if winner == 1:
                self.wins += 1
                return True
            else:
                return False
        
        if len(self.children.keys()) == len(self.transitions):
            # there are no unexplored transitions
            next_child = self.get_highest_ucb()
            playout_successful = next_child.sample(initial_position, depth + 1)
        else:
            # generate a new node for a random unexplored transition
            unexplored_transitions = list(self.transitions - self.children.keys())
            chosen_transition = random.choice(unexplored_transitions)
            next_child = self.generate_next_child(chosen_transition)
            self.children[chosen_transition] = next_child
            playout_successful = next_child.random_playout(initial_position, depth + 1)

        if playout_successful: #backprop via boolean return of child
            self.wins += 1
            return True

        return False

    def random_playout(self, initial_position, depth):
        """
        Random playout of from this node. If max depth is reached then
        the evaluation function of the state is compared against initial_position.
        If the evaluation of the state is better than the initial position, it is
        counted as win, since the bot position was improved.
        """
        self.total += 1

        mutator = StateMutator(copy.deepcopy(self.state))
        while True:
            if depth == MAX_DEPTH:
                if evaluate(mutator.state) >= initial_position:
                    self.wins += 1
                    return True
                else:
                    return False

            winner = mutator.state.battle_is_finished()
            if winner:
                if winner == 1:
                    self.wins += 1
                    return True
                else:
                    return False

            transition = random.choice(get_transitions(mutator.state))
            state_instructions = get_all_state_instructions(mutator, transition[0], transition[1])
            possible_instrucitons = [i.instructions for i in state_instructions]
            weights = [i.percentage for i in state_instructions]
            choice = random.choices(possible_instrucitons, weights=weights)[0]
            mutator.apply(choice)

            depth += 1
            

    def generate_next_child(self, chosen_transition):
        """
        Generates a child node by choosing the most likely mutation instructions
        (instructions are potential results of a transition) of the given transition.
        Params:
            - chosen_transition: the pair of (our move : opponent move) to apply
        """
        mutator = StateMutator(copy.deepcopy(self.state))
        state_instructions = get_all_state_instructions(mutator, chosen_transition[0], chosen_transition[1])
        choice = max(state_instructions, key=lambda i : i.percentage).instructions
        mutator.apply(choice)
        return MonteCarloTree(mutator.state)

    def run(self, times):
        """
        Top level function that samples the tree the given number of times
        Params:
            - times: number of times to sample this tree
        """
        for sample in range(times):
            self.sample(evaluate(self.state))
            # if DEBUG and sample % 50 == 0:
            #     print("[DEBUG]: ran ", sample, "/", times, " samples") 

    def get_best_move(self):
        """
            Returns the move (that we could make) with the highest win rate 
            throughout this state and child playouts, resulting in a dominant playing strategy
        """
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
        """
            Returns the child node with the highest UCB.
        """
        best_child = None
        best_child_weight = 0
        for move, child in self.children.items():
            w = child.win_rate() + math.sqrt(TUNABLE_CONSTANT * math.log(self.total) / child.total)
            if best_child is None or w > best_child_weight:
                best_child = child
                best_child_weight = w        
        return best_child

    def pretty_print(self, depth=0):
        """
        Debug helper, prints the wins/total for each transition of a node.
        """
        for move, child in self.children.items():
            print("Move: " + str(move) + " WINS: " + str(child.wins) + " TOTAL: " + str(child.total))


class BattleBot(Battle):
    '''monte_carlo_tree_search'''
    
    def __init__(self, *args, **kwargs):
        super(BattleBot, self).__init__(*args, **kwargs)

    def find_best_move_for_battle(self, battle):
        """
        Returns the best move after sampling a monte carlo tree with the
        state of the given battle
        """
        mctree = MonteCarloTree(battle.create_state())
        mctree.run(SAMPLE_COUNT)
        #mctree.pretty_print()

        return mctree.get_best_move()

    def find_best_move(self):
        """
        Looks for the best move across the possible battles the bot could be in.
        Possible battles include variations in the sets of moves the opponents
        pokemon can make that is hidden from the bot.

        This library updates the possible battles on each turn and each battle
        is equally likely in random battles, so we are hopeful and chose the move 
        with the highest average winrate across the trees.
        """
        battles = self.prepare_battles(join_moves_together=True)

        all_scores = dict()
        for _, b in enumerate(battles):
            move, score = self.find_best_move_for_battle(b)
            if move in all_scores.keys():
                all_scores[move].append(score)
            else:
                all_scores[move] = [score]
        
        averages = { move: sum(scores)/len(scores) for move, scores in all_scores.items()}
        bot_choice = max(averages, key=averages.get)

        # if DEBUG:
        #     print("OUR MOVE:" + str(bot_choice) + " PROJECTED WINRATE: " + str(averages[bot_choice]))

        return format_decision(self, bot_choice)