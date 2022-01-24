# REFERENCE: OPENAI BASELINES
# (https://github.com/openai/baselines)

import numpy as np
import random
from src.value_function.segment_tree import MinSegmentTree, SumSegmentTree
from src.value_function.experience import *


class ReplayBuffer(object):
    def __init__(self, size: int):
        """Create Replay buffer.

        Parameters
        ----------
        size: int
            Max number of transitions to store in the buffer. When the buffer
            overflows the old memories are dropped.
        """
        self._storage = []
        self._maxsize = size
        self._next_idx = 0

    def __len__(self):
        return len(self._storage)

    def add(self, experience: Experience):
        if self._next_idx >= len(self._storage):
            self._storage.append(experience)
        else:
            self._storage[self._next_idx] = experience
        self._next_idx = (self._next_idx + 1) % self._maxsize

    def _encode_sample(self, idxes: list[int]) -> list[Experience]:
        return [self._storage[i] for i in idxes]

    def sample(self, batch_size: int) -> list[Experience]:
        """Sample a batch of experiences.

        Parameters
        ----------
        batch_size: int
            How many transitions to sample.

        Returns
        -------
        sampled_experiences: list[Experience]
            batch of experiences
        """
        idxes = [random.randint(0, len(self._storage) - 1) for _ in range(batch_size)]
        return self._encode_sample(idxes)


class PrioritizedReplayBuffer(ReplayBuffer):
    def __init__(self, size: int, alpha: float = 0.6):
        """Create Prioritized Replay buffer.

        Parameters
        ----------
        size: int
            Max number of transitions to store in the buffer. When the buffer
            overflows the old memories are dropped.
        alpha: float
            how much prioritization is used
            (0 - no prioritization, 1 - full prioritization)

        See Also
        --------
        ReplayBuffer.__init__
        """
        super(PrioritizedReplayBuffer, self).__init__(size)
        assert alpha >= 0
        self._alpha = alpha

        it_capacity = 1
        while it_capacity < size:
            it_capacity *= 2

        self._it_sum = SumSegmentTree(it_capacity)
        self._it_min = MinSegmentTree(it_capacity)
        self._max_priority = 1.0

    def add(self, experience: Experience):
        """See ReplayBuffer.store_effect"""
        idx = self._next_idx
        super().add(experience)
        priority_alpha = self._max_priority ** self._alpha
        self._it_sum[idx] = priority_alpha
        self._it_min[idx] = priority_alpha

    def _sample_proportional(self, batch_size: int) -> list[int]:
        res = []
        p_total = self._it_sum.sum(0, len(self._storage) - 1)
        every_range_len = p_total / batch_size
        for i in range(batch_size):
            mass = random.random() * every_range_len + i * every_range_len
            idx = self._it_sum.find_prefixsum_idx(mass)
            res.append(idx)
        return res

    def sample(self, batch_size: int, beta: float = 0.4) -> tuple[list[Experience], list[float], list[int]]:
        """Sample a batch of experiences.
        compared to ReplayBuffer.sample
        it also returns importance weights and idxes
        of sampled experiences.

        Parameters
        ----------
        batch_size: int
            How many transitions to sample.
        beta: float
            To what degree to use importance weights
            (0 - no corrections, 1 - full correction)

        Returns
        -------
        sampled_experiences: list[Experience]
            batch of experiences
        weights: list[float]
            denoting importance weight of each sampled transition
        idxes: list[int]
            indexes in buffer of sampled experiences
        """
        assert beta > 0

        idxes = self._sample_proportional(batch_size)

        weights = []
        p_min = self._it_min.min() / self._it_sum.sum()
        max_weight = (p_min * len(self._storage)) ** (-beta)

        for idx in idxes:
            p_sample = self._it_sum[idx] / self._it_sum.sum()
            weight = (p_sample * len(self._storage)) ** (-beta)
            weights.append(weight / max_weight)
        sampled_experiences = self._encode_sample(idxes)
        return sampled_experiences, weights, idxes

    def update_priorities(self, idxes: list[int], priorities: list[float]):
        """Update priorities of sampled transitions.
        sets priority of transition at index idxes[i] in buffer
        to priorities[i].

        Parameters
        ----------
        idxes: [int]
            List of idxes of sampled transitions
        priorities: [float]
            List of updated priorities corresponding to
            transitions at the sampled idxes denoted by
            variable `idxes`.
        """
        assert len(idxes) == len(priorities)
        for idx, priority in zip(idxes, priorities):
            assert priority > 0
            assert 0 <= idx < len(self._storage)
            priority_alpha = priority ** self._alpha
            self._it_sum[idx] = priority_alpha
            self._it_min[idx] = priority_alpha

            self._max_priority = max(self._max_priority, priority)