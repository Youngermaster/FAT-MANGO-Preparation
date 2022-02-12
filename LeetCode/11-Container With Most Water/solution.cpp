class Solution {
public:
    int maxArea(vector<int>& height) {
        int i = 0, j = height.size()-1;
        int m = 0,m1;
        while(i<j){
            m1 = min(height[i], height[j]) * (j-i);
            m = max(m, m1);
            height[i]<height[j] ? i++ : j--;
        }
        return m;
    }
};

