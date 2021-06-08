#include <iostream>

using namespace std;

int main() {
    int k, n, w, moneyToBorrow;

    cin >> k >> n >> w;

    w = w * (w + 1) / 2;
    moneyToBorrow = k * w - n;
    if (moneyToBorrow <= 0)
        moneyToBorrow = 0;
    cout << moneyToBorrow << endl;
    return 0;
}