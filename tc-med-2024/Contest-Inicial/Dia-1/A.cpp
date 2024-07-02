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

    if (n <= 3) {
        cout << "NO SOLUTION" << el;
        return;
    }

    vector<int> a(n);
    for (int i = 0; i < n; ++i) {
        a[i] = i + 1;
    }

    int i, j, k, l, aux;
    i = a.size() / 2 - 1;
    j = a.size() / 2;
    k = 0;
    l = a.size() - 1;
    for (i = a.size() / 2 - 1; i >= 0; --i) {
        aux = a[i];
        a[i] = a[k];
        a[k] = aux;
        k++;

        aux = a[j];
        a[j] = a[l];
        a[l] = aux;
        l--;
        j++;

        if (k == a.size() / 2 - 1) {
            break;
        }
    }

    for (int i = 0; i < n; ++i) {
        cout << a[i] << " ";
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    cout.tie(NULL);

    solve();
}
