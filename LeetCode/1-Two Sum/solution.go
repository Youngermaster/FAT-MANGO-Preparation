func twoSum(nums []int, target int) []int {
    for index := 0; index < len(nums); index++ {
		for index2 := index + 1; index2 < len(nums); index2++ {
			if nums[index] + nums[index2] == target {
				return []int{index, index2}
			}
		}
	}
	return []int{0, 1}
}