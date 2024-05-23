#include <iostream>

using namespace std;

int main() {
    int w;
    cin >> w;
    // ! Avoid using endl: Using endl flushes the output buffer, which can be slower compared to using '\n'.
    cout << (w % 2 == 0 && w > 2 ? "YES" : "NO") << '\n';
    return 0;
}
