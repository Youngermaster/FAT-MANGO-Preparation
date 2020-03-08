class Solution {
    public:
    int rangeSumBTS(Treenode* root, int L, int R) {
        if (root == NULL)
            return 0;
        else
        {
            int sum = rangeSumBTS(root->left, L, R) + rangeSumBTS(root->right, L, R);

            if (root->val >= L && root->val <= R)
                sum += root->val;
        }
        
    }
};