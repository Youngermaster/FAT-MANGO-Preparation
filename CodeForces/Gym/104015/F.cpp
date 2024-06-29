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

vector<long long> get_factors(long long x) {
    vector<long long> factors;
    for (long long i = 1; i <= sqrt(x); ++i) {
        if (x % i == 0) {
            factors.push_back(i);
            if (i != x / i) {
                factors.push_back(x / i);
            }
        }
    }
    return factors;
}

void solve() {
    int n;
    cin >> n;
    vector<long long> a(n);
    map<long long, int> power_count;

    forn(i, n) {
        int value;
        cin >> value;
        a[i] = value;
    }

    long long max_coconuts = 0;

    sort(all(a), greater<long long>());

    map<long long, vector<long long>> factors_map;

    forn(i, n) {
        factors_map[a[i]] = get_factors(a[i]);
    }

    forn(i, n) {
        cout << "Factors of " << a[i] << ": ";
        for (auto x : factors_map[a[i]]) {
            cout << x << " ";
        }
    }

    cout << max_coconuts << el;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    cout.tie(NULL);

    solve();
}
