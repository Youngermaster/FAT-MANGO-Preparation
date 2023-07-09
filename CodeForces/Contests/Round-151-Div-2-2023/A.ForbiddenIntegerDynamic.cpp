#include <iostream>
#include <vector>

using namespace std;

void solve() {
    int n, k, x;
    cin >> n >> k >> x;

    // handle the case where k equals x and n is greater than k
    if (k == x && (n > k || n == x)) {
        cout << "NO" << endl;
        return;
    }

    vector<int> ans;

    // Use dynamic programming to solve the problem
    vector<int> dp(n + 1, 0);
    dp[0] = 1;

    for (int i = 1; i <= k; ++i) {
        if (i != x) {
            for (int j = i; j <= n; ++j) {
                dp[j] |= dp[j - i];
            }
        }
    }

    if (dp[n]) {
        cout << "YES" << endl;
        for (int i = k; i >= 1; --i) {
            if (i == x) continue;
            while (n >= i && dp[n - i]) {
                ans.push_back(i);
                n -= i;
            }
        }
        cout << ans.size() << endl;
        for (int a : ans) {
            cout << a << " ";
        }
        cout << endl;
    } else {
        cout << "NO" << endl;
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
