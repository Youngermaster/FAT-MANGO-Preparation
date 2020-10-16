class Solution {
public:
    vector<int> twoSum(vector<int>& nums, int target) {
        for (int indexOne = 0; indexOne < nums.size(); indexOne++) {
            for (int indexTwo = indexOne + 1; indexTwo < nums.size(); indexTwo++){
                if (nums[indexOne] + nums[indexTwo] == target)
                    return {indexOne, indexTwo};
            }
        }
        return {0, 0};
    }
};