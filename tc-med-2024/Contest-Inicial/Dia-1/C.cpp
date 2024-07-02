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
    int n, m, k;
    cin >> n >> m >> k;
    vector<int> desired(n);
    vector<int> apartments(m);

    for (int i = 0; i < n; ++i) cin >> desired[i];
    for (int i = 0; i < m; ++i) cin >> apartments[i];

    sort(all(desired));
    sort(all(apartments));

    int result = 0;
    int i = 0, j = 0;
    while (i < n && j < m) {
        if (apartments[j] < desired[i] - k) {
            j++;
        } else if (apartments[j] > desired[i] + k) {
            i++;
        } else {
            result++;
            i++;
            j++;
        }
    }

    cout << result << endl;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    cout.tie(NULL);

    solve();
}