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
    string s;
    int x;

    cin >> s;
    cin >> x;
    int n = s.size();

    for (int len = 1; len <= n / 2; ++len) {
        for (int i = 0; i + 2 * len <= n; ++i) {
            long long a = stoll(s.substr(i, len));
            long long b = stoll(s.substr(i + len, len));
            if (a + b == x) {
                cout << i + 1 << " " << i + len << endl;
                cout << i + len + 1 << " " << i + 2 * len << endl;
                return;
            }
        }
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    cout.tie(NULL);

    solve();
}
