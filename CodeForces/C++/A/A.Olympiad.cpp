#include <iostream>
#include <set>

int n;
int arrayn[101];

int main()
{
    std::cin >> n;
    for (int y = 0; y < n; y++)
        std::cin >> arrayn[y];

    std::set<int> s;
    for (int z = 0; z < n; z++)
    {
        if (arrayn[z] == 0)
        {
            continue;
        }
        else
        {
            s.insert(arrayn[z]);
        }
    }
    std::cout << s.size();
    return 0;
}