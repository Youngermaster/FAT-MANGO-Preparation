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
    vector<long long> a(n);
    long long total_sum = 0;

    for (int i = 0; i < n; ++i) {
        cin >> a[i];
        total_sum += a[i];
    }

    long long k = total_sum / n;
    long long double_k = 2 * k;

    map<long long, int> freq;
    long long result = 0;

    for (int i = 0; i < n; ++i) {
        long long complement = double_k - a[i];

        if (freq.find(complement) != freq.end()) {
            result += freq[complement];
        }

        freq[a[i]]++;
    }

    cout << result << endl;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    cout.tie(NULL);

    solve();
}
