#include <cstdio>
#include <iostream>

using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int w;
    scanf("%d", &w);
    if (w % 2 == 0 && w > 2) {
        printf("YES\n");
    } else {
        printf("NO\n");
    }

    return 0;
}
