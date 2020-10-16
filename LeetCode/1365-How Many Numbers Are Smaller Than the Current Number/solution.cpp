class Solution {
public:
    vector<int> smallerNumbersThanCurrent(vector<int>& nums) {
        vector<int> cnt(101, 0);
        for (int i = 0; i < nums.size(); ++i)
            cnt[nums[i]]++;
        
        for (int i = 1; i < 101; ++i)
            cnt[i] += cnt[i - 1];
        
        vector<int> ans(nums.size(), 0);

        for (int i = 0; i < nums.size(); ++i)
            ans[i] = (nums[i] == 0 ? 0 : cnt[nums[i] - 1]);

        return ans;
    }
};