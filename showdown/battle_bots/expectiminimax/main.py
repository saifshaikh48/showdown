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

DEPTH = 2

def get_dominant_move(payoff_matrix):
    """
    Finds the dominant move in a payoff matrix.
    Returns the move and expectiminimax value associated
    {Move: [Double]} -> Move, Double
    """

    dominant_move = None
    dominant_value = None
    for move, values in payoff_matrix.items():
        min_value = min(values)
        if dominant_value is None or min_value > dominant_value:
            dominant_move = move
            dominant_value = min_value
    
    return dominant_move, dominant_value

def generate_payoff_matrix(value_map):
    """
    Takes in a dictionary of transition to expectiminimax value and converts
    it to a payoff matrix.
    {Transition: Double} -> {Move: [Double]}
    """
    payoff_matrix = {}
    for transition, value in value_map.items():
        if transition[0] not in payoff_matrix.keys():
            payoff_matrix[transition[0]] = [value]
        else:
            payoff_matrix[transition[0]].append(value)
    
    return payoff_matrix


def calculate_value(state, transition, depth):
    """
    Takes in the current state, a specific transition (pair of our move and opponent move), 
    and estimates the value associated with applying this transition at current search depth, 
    taking into account the probability of this transition occuring
    """
    state_instructions = get_all_state_instructions(StateMutator(state), transition[0], transition[1])

    total_value = 0

    for instruction in state_instructions:
        mutator = StateMutator(copy.deepcopy(state))
        mutator.apply(instruction.instructions)
        value = expectiminimax(mutator.state, depth)
        total_value += value * instruction.percentage
    
    return total_value

def expectiminimax(state, depth):
    """
    Returns the expectiminimax value of a state down to a certain depth according to
    some evaluation function. Recurs by calling calculate_value on possible transitions.
    The calculate_value function acts as the algorithm's "chance node."  
    """
    if depth == 0:
        return evaluate(state)

    winner = state.battle_is_finished()
    if winner:
        if winner == 1: #we won
            return 10000
        else:
            return -10000

    else:
        user_options, opponent_options = state.get_all_options()
        transitions = list(itertools.product(user_options, opponent_options))
        value_of_transisitons = {}
        for transition in transitions:
            value_of_transisitons[transition] = calculate_value(state, transition, depth - 1)

        move, value = get_dominant_move(generate_payoff_matrix(value_of_transisitons))

        return value

def get_value_map(battle, depth):
    """
    Returns a dictionary of transistions to expectiminimax values at a certain depth for
    a single possible hidden state of the partially observable game. 
    """
    state = battle.create_state()
    user_options, opponent_options = state.get_all_options()
    transitions = list(itertools.product(user_options, opponent_options))
    value_of_transisitons = {}
    for transition in transitions:
        value_of_transisitons[transition] = calculate_value(state, transition, depth - 1)

    return value_of_transisitons

def get_best_move(value_maps):
    """
    Looks across all possible hidden states of the partially observable game and selects
    the dominant move.
    """
    payoff_matrix = {}
    for value_map in value_maps:
        for transition, value in value_map.items():
            if transition[0] not in payoff_matrix.keys():
                payoff_matrix[transition[0]] = [value]
            else:
                payoff_matrix[transition[0]].append(value)
    
    return get_dominant_move(payoff_matrix)


class BattleBot(Battle):
    '''expectiminimax'''

    def __init__(self, *args, **kwargs):
        super(BattleBot, self).__init__(*args, **kwargs)

    def find_best_move(self):
        """
        Looks for the best move across the possible battles the bot could be in.
        Possible battles include variations in the sets of moves the opponents
        pokemon can make that is hidden from the bot.

        This function finds the best move to make based on the expeciminimax algorithm.
        """
        battles = self.prepare_battles(join_moves_together=True)
        value_maps = []

        for b in battles:
            value_maps.append(get_value_map(b, DEPTH))

        best_move, value = get_best_move(value_maps)
        return format_decision(self, best_move)