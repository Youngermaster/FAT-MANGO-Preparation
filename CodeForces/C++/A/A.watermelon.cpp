#include <iostream>

using namespace std;

int main(int argc, char const *argv[])
{
    int w;
    cin >> w;
    w % 2 == 0 && w > 2 ? cout << "YES" << endl : cout << "NO" << endl;
    return 0;
}
