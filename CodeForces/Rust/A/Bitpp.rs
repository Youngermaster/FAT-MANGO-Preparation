#include <iostream>
#include <string>

using namespace std;

int main()
{
    int n, x(0);
    // Just a test if the performance would change, but with so little data it doesn't change
    ios_base::sync_with_stdio(false); 

    cin >> n;

    string s;
    while (n--)
    {
        cin >> s;
        if (s[1] == '+')
            ++x;
        else
            --x;
    }

    cout << x << endl;
    return 0;
}