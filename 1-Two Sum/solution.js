function twoSum(nums, target) {
    const previousValues = {};
    for (let index = 0; index < nums.length; index++) {
        const currentNumber = nums[index];
        const neededValue = target - currentNumber;
        const index2 = previousValues[neededValue];
        if (index2 != null) {
            return [index2, index]
        } else {
            previousValues[currentNumber] = index;
        }
    }
}

console.log('Solution:', twoSum([2, 7, 11, 15], 9));