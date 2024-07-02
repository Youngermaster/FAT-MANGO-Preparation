#include <bits/stdc++.h>

#include <cmath>
#include <iomanip>
#include <iostream>
#include <map>
#include <vector>

#define forn(i, n) for (int i = 0; i < (int)n; ++i)
#define fora(i, x, n) for (int i = (int)x; i < (int)n; ++i)
#define el '\n'
#define pb push_back
#define d(x) cout << #x << " " << x << el
#define all(v) v.begin(), v.end()
#define sz(v) v.size()
#define fi first
#define se second
#define mem(v, val) memset(v, (val), sizeof(v))

using namespace std;

typedef vector<int> vi;
typedef long double ld;

void solve() {
    int n;
    cin >> n;
    vector<int> count(5, 0);

    for (int i = 0; i < n; ++i) {
        int num;
        cin >> num;
        count[num]++;
    }

    int taxis = 0;

    taxis += count[4];

    int min_three_one = min(count[3], count[1]);
    taxis += min_three_one;
    count[3] -= min_three_one;
    count[1] -= min_three_one;

    taxis += count[3];

    taxis += count[2] / 2;
    count[2] %= 2;

    if (count[2] == 1) {
        if (count[1] >= 2) {
            taxis++;
            count[1] -= 2;
        } else {
            taxis++;
            count[1] = 0;
        }
    }

    taxis += count[1] / 4;
    if (count[1] % 4 != 0) taxis++;

    cout << taxis << endl;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    cout.tie(NULL);

    solve();
}