# ranking/ranking_system.py

import random

class RankingSystem:
    def __init__(self):
        self.rankings = {}
        self.comparisons = []

    def initialize(self, albums):
        """Initialize the ranking system with albums and default scores"""
        self.rankings = {album_id: 1000 for album_id in albums}
        self.comparisons = self._generate_comparisons(albums)

    def _generate_comparisons(self, albums):
        """Generate random pairwise comparisons"""
        pairs = []
        for i in range(len(albums)):
            for j in range(i + 1, len(albums)):
                pairs.append((albums[i], albums[j]))
        random.shuffle(pairs)
        return pairs

    def record_result(self, winner_id, loser_id):
        """Apply simple Elo-like adjustment to the rankings"""
        k = 30
        winner_rating = self.rankings[winner_id]
        loser_rating = self.rankings[loser_id]

        expected_winner = 1 / (1 + 10 ** ((loser_rating - winner_rating) / 400))
        expected_loser = 1 - expected_winner

        self.rankings[winner_id] += int(k * (1 - expected_winner))
        self.rankings[loser_id] += int(k * (0 - expected_loser))

    def get_sorted_rankings(self):
        return sorted(self.rankings.items(), key=lambda x: x[1], reverse=True)

    def remaining_comparisons(self):
        return self.comparisons