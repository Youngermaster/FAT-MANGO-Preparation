class Solution {
public:
    string defangIPaddr(string address) {
        string defangedIPAddress = "";
            
        for (int i = 0; i < address.size(); i++) {
            if (address[i] == '.')
                defangedIPAddress += "[.]";
            else
                defangedIPAddress += address[i];
        }
        return defangedIPAddress;
    }
};