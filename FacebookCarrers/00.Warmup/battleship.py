from typing import List
# Write any import statements here


def getHitProbability(R: int, C: int, G: List[List[int]]) -> float:
    # Write your code here
    counter: int = 0
    for i in G:
        for j in i:
            if j == 1:
                counter += 1

    return counter / (R * C)


test = [[0, 0, 1], [1, 0, 1]]
print(getHitProbability(2, 3, test))
