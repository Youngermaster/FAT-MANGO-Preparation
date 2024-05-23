#include <iostream>

using namespace std;

int main() {
    int n, Petya, Vasya, Tonya, problemsToSolve(0);

    cin >> n;
    while (n--) {
        cin >> Petya >> Vasya >> Tonya;
        if (Petya + Vasya + Tonya >= 2)
            problemsToSolve += 1;
    }
    cout << problemsToSolve << endl;
    return 0;
}