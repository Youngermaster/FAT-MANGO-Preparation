#include <bits/stdc++.h>

#include <iostream>
#include <map>
#include <vector>
#include <cmath>
#include <iomanip> // for fixed and setprecision

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
    int output = 0;
    int n, t;
    cin >> n >> t;

    vector<int> p;
    vector<int> np;

    forn(i, n) {
        char ch;
        int mb;
        cin >> ch >> mb;
        if (ch == 'P') {
            p.pb(mb);
        } else {
            np.pb(mb);
        }
    }

    ld offset_seconds = 0.0;

    while (!p.empty() || !np.empty()) {
        vector<int> pi_to_remove;
        vector<int> npi_to_remove;

        forn(i, p.size()) {
            if (p[i] == 0) {
                pi_to_remove.pb(i);
                continue;
            }
            if (np.empty()) {
                p[i] -= t / p.size();
            } else {
                ld dp = (t * 0.75) / p.size();
                p[i] -= dp;
            }
            if (p[i] <= 0) {
                pi_to_remove.pb(i);
                if (p[i] < 0) {
                    offset_seconds += abs((ld)p[i] / t);
                }
            }
        }

        forn(i, np.size()) {
            if (np[i] == 0) {
                npi_to_remove.pb(i);
                continue;
            }
            if (p.empty()) {
                np[i] -= t / np.size();
            } else {
                ld ndp = (t * 0.25) / np.size();
                np[i] -= ndp;
            }
            if (np[i] <= 0) {
                npi_to_remove.pb(i);
                if (np[i] < 0) {
                    offset_seconds += abs((ld)np[i] / t);
                }
            }
        }

        // Remove elements in reverse order to avoid shifting issues
        for (int i = pi_to_remove.size() - 1; i >= 0; --i) {
            p.erase(p.begin() + pi_to_remove[i]);
        }
        for (int i = npi_to_remove.size() - 1; i >= 0; --i) {
            np.erase(np.begin() + npi_to_remove[i]);
        }

        output += 1;
    }

    cout << fixed << setprecision(10) << (output - offset_seconds) << el;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    cout.tie(NULL);

    solve();
}
