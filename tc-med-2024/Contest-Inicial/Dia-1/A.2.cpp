#include <bits/stdc++.h>
using namespace std;

vector<int> permutation(int n) {
    vector<int> ans;
    if (n <= 3) {
        ans.push_back(-1);
    }

    if (n % 2 == 0) {
        for (int i = 2; i <= n; i += 2) {
            ans.push_back(i);
        }
        for (int i = 1; i < n; i += 2) {
            ans.push_back(i);
        }
    }

    else {
        for (int i = 2; i <= n - 1; i += 2) {
            ans.push_back(i);
        }
        for (int j = 1; j <= n; j += 2) {
            ans.push_back(j);
        }
    }
    return ans;
}

int main() {
    int N = 5;
    vector<int> ans = permutation(N);
    for (int x : ans)
        cout << x << " ";
    return 0;
}