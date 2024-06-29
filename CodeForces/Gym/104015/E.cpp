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
    vector<int> a;

    cin >> n;

    // Read the input values into the vector
    forn(i, n) {
        int value;
        cin >> value;
        a.pb(value);  // Use push_back to add values to the vector
    }

    // Iterate through the vector to check if the elements are even or odd
    forn(i, n) {
        if (a[i] % 2 == 0) {
            cout << a[i] << " is even" << el;
        } else {
            cout << a[i] << " is odd" << el;
        }
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    cout.tie(NULL);

    solve();
}
