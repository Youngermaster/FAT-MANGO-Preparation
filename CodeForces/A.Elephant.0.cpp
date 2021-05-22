#include <iostream>

using namespace std;

int main(int argc, char const *argv[]) {
    int x, steps(0);
    cin >> x;

    while (x) {
        if (x - 5 >= 0)
            x -= 5;
        else if (x - 4 >= 0)
            x -= 4;
        else if (x - 3 >= 0)
            x -= 3;
        else if (x - 2 >= 0)
            x -= 2;
        else if (x - 1 >= 0)
            x--;

        steps++;
    }

    cout << steps;
    return 0;
}
