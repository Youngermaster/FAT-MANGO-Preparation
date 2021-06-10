#include <iostream>
#include <vector>

using namespace std;

vector<int> runningSum(vector<int>& nums) {
    int accummulated(0);
    vector<int> accummulatedVector;
    for (auto&& i : nums) {
        accummulated += i;
        accummulatedVector.push_back(accummulated);
    }
    return accummulatedVector;
}