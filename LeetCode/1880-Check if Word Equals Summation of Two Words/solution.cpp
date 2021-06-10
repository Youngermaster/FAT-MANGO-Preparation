#include <iostream>
#include <string>

using namespace std;

bool isSumEqual(string firstWord, string secondWord, string targetWord) {
    return stringToNumber(firstWord) + stringToNumber(secondWord) == stringToNumber(targetWord);
}

int stringToNumber(string s) {
    int number(0), base(1);

    for (int i = s.length() - 1; i >= 0; i--) {
        number += (s[i] - 'a') * base;
        base *= 10;
    }

    return number;
}