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
    bool is_dangerous = false;
    bool is_one = false;
    bool is_zero = false;
    int number_of_players = 0;

    cin >> players;

    for (int i = 0; i < players.size() - 2; i++) {
        if (number_of_players >= 7) {
            is_dangerous = true;
            break;
        }

        if (players[i] == 1) {
            is_one = true;
        } else if (players[i] == 0) {
            is_zero = true;
        }

        if (is_one && players[i + 1] == 1) {
            number_of_players++;
            continue;
        } else if (is_one && players[i + 1] == 0) {
            number_of_players = 0;
            continue;
        }

        if (is_zero && players[i + 1] == 0) {
            number_of_players++;
            continue;
        } else if (is_zero && players[i + 1] == 1) {
            number_of_players = 0;
            continue;
        }
    }

    if (number_of_players >= 7) {
        is_dangerous = true;
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