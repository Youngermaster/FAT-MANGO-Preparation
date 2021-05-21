#include <algorithm>
#include <iostream>
#include <string>

using namespace std;

int main() {
    string name;
    cin >> name;
    sort(name.begin(), name.end());
    name.erase(unique(name.begin(), name.end()), name.end());
    if (name.length() % 2 == 0) {
        cout << "CHAT WITH HER!" << endl;
    } else {
        cout << "IGNORE HIM!" << endl;
    }
    return 0;
}