# Write any import statements here

def getWrongAnswers(N: int, C: str) -> str:
    # Write your code here
    D = ''
    for i in C:
        if i == 'A':
            D += 'B'
            continue
        elif i == 'B':
            D += 'A'
            continue
        else:
            return C

    return D


print(getWrongAnswers(3, 'ABA'))
