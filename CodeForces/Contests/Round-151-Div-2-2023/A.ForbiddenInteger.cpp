#include <iostream>
#include <vector>

using namespace std;

void solve() {
    int n, k, x;
    cin >> n >> k >> x;

    vector<int> ans;

    for (int i = k; i >= 1; i--) {
        if (i == x) continue;
        while (n >= i) {
            ans.push_back(i);
            n -= i;
        }
    }

    if (n != 0) {
        cout << "NO" << endl;
    } else {
        cout << "YES" << endl;
        cout << ans.size() << endl;
        for (int a : ans) {
            cout << a << " ";
        }
        cout << endl;
    }
}

int main() {
    int t;
    cin >> t;
    while (t--) {
        solve();
    }
    return 0;
}
