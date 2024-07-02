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
    vector<int> a(n);
    int taxis_needed = 0;

    forn(i, n) { cin >> a[i]; }

    sort(all(a));

    forn(i, n) {
        if (a[i] == 4) {
            taxis_needed++;
        } else if (a[i] == 3) {
            if (a[i + 1] == 1) {
                taxis_needed++;
                i++;
            } else {
                taxis_needed++;
            }
        } else if (a[i] == 2) {
            if (a[i + 1] == 2) {
                taxis_needed++;
                i++;
            } else if (a[i + 1] == 1) {
                if (a[i + 2] == 1) {
                    taxis_needed++;
                    i += 2;
                } else {
                    taxis_needed++;
                    i++;
                }
            } else {
                taxis_needed++;
            }
        } else if (a[i] == 1) {
            if (a[i + 1] == 1) {
                if (a[i + 2] == 1) {
                    taxis_needed++;
                    i += 2;
                } else {
                    taxis_needed++;
                    i++;
                }
            } else {
                taxis_needed++;
            }
        }
    }

    cout << taxis_needed << el;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    cout.tie(NULL);

    solve();
}