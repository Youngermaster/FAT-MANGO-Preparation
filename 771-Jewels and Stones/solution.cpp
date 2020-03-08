#include <iostream>
#include <string>
#include <map>

class Solution
{
public:
    int numJewelsInStones(std::string J, std::string S)
    {
        std::map<char, bool> isVisited;
        for (int i = 0; i < J.size(); i++)
            isVisited[J[i]] = true;
        int jewelCounter = 0;
        for (int i = 0; i < S.size(); i++)
        {
            if (isVisited[S[i]])
                jewelCounter++;
        }

        return jewelCounter;
    }
};

int main(int argc, char const *argv[])
{
    std::cout << Solution().numJewelsInStones("aA", "aAAbbb") << std::endl;
    return 0;
}
