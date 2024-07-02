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
    string players;
    cin >> players;

    char current_char = players[0];
    int count = 1;
    bool is_dangerous = false;

    for (int i = 1; i < players.size(); i++) {
        if (players[i] == current_char) {
            count++;
        } else {
            current_char = players[i];
            count = 1;
        }

        if (count >= 7) {
            is_dangerous = true;
            break;
        }
    }

    if (is_dangerous) {
        cout << "YES" << el;
    } else {
        cout << "NO" << el;
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    cout.tie(NULL);

    solve();
}