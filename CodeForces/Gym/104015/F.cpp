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
    sort(all(factors), greater<long long>());
    return factors;
}

void solve() {
    int n;
    cin >> n;
    vector<long long> a(n);
    map<long long, long long> factor_count;

    for (int i = 0; i < n; ++i) {
        cin >> a[i];
        vector<long long> factors = get_factors(a[i]);
        for (long long factor : factors) {
            if (a[i] == 1) {
                factor_count[1] += 1;
                continue;
            }
            factor_count[factor] += a[i];
        }
    }

    long long max_coconuts = 0;
    for (auto& [factor, count] : factor_count) {
        cout << "factor: " << factor << " count: " << count << el;
        if (factor != 1) {
            max_coconuts = max(max_coconuts, count);
        }
    }

    cout << max_coconuts << endl;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    cout.tie(NULL);

    solve();
}
