#include <iostream>

using namespace std;

int main(int argc, char const *argv[]) {
    int k, n, w, moneyToBorrow(0);

    cin >> k >> n >> w;

    for (int i = 1; i <= w; i++)
        moneyToBorrow += k * i;

    moneyToBorrow -= n;

    if (moneyToBorrow <= 0)
        moneyToBorrow = 0;

    cout << moneyToBorrow;
    return 0;
}
