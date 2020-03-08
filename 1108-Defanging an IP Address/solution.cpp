#include <iostream>
#include <string>

class Solution
{
public:
    std::string defangingIPaddr(std::string address)
    {
        std::string defangedIPAddress = "";
        for (int iterator = 0; iterator < address.size(); iterator++)
        {
            if (address[iterator] == '.')
                defangedIPAddress += "[.]";
            else
                defangedIPAddress += address[iterator];
        }
        return defangedIPAddress;
    }
};

int main(int argc, char const *argv[])
{
    std::cout << (Solution().defangingIPaddr("1.1.1.1.1")) << std::endl;
    return 0;
}
