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
    int eight_count = 0;
    int n;
    cin >> n;
    string a;
    cin >> a;
    int possible_phone_numbers = n / 11;

    forn(i, n) {
        if (a[i] == '8') {
            eight_count++;
        }
    }

    if (eight_count == 0) {
        cout << 0 << el;
    } else {
        cout << min(possible_phone_numbers, eight_count) << el;
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    cout.tie(NULL);

    solve();
}