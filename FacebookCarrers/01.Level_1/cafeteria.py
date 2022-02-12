import math
from typing import List
# Write any import statements here


def getMaxAdditionalDinersCount(N: int, K: int, M: int, S: List[int]) -> int:
    S.sort()
    start, res = 1, 0
    S.append(N+K+1)
    for s in S:
        delta = s-K-start
        if delta > 0:
            res += math.ceil(delta / (K+1))
        start = s+K+1
    return res


if __name__ == "__main__":
    N = 10
    K = 1
    M = 2
    S = [2, 6]
    print(getMaxAdditionalDinersCount(N, K, M, S))
