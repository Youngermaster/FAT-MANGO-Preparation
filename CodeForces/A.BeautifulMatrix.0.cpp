#include <iostream>

using namespace std;

int main(int argc, char const *argv[]) {
    int stepsForBeautifulMatrix(0), row, column, number;

    for (int i = 1; i <= 5; i++) {
        for (int j = 1; j <= 5; j++) {
            cin >> number;
            if (number == 1) {
                row = i;
                column = j;
            }
        }
    }

    if (row > 3) {
        stepsForBeautifulMatrix += row - 3;
    } else if (row < 3) {
        stepsForBeautifulMatrix += 3 - row;
    }

    if (column > 3) {
        stepsForBeautifulMatrix += column - 3;
    } else if (column < 3) {
        stepsForBeautifulMatrix += 3 - column;
    }

    cout << stepsForBeautifulMatrix << endl;
    return 0;
}
