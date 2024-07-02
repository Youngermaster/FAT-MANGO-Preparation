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
    int n, m;
    cin >> n >> m;
    vector<int> names_needed(n);
    for (int i = 0; i < n; i++) {
        cin >> names_needed[i];
    }

    vector<int> page_turns(n, 0);
    int carry_over = 0;

    for (int i = 0; i < n; i++) {
        int total_names = names_needed[i] + carry_over;
        page_turns[i] = total_names / m;
        carry_over = total_names % m;
    }

    for (int turns : page_turns) {
        cout << turns << " ";
    }
    cout << endl;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    cout.tie(NULL);

    solve();
}