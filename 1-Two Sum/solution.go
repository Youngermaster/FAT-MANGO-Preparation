package main

import "fmt"

func main() {
	array := []int{15, 11, 2, 7}
	fmt.Println(twoSum(array, 9))
}

func twoSum(nums []int, target int) [2]int {
	for index := 0; index < len(nums); index++ {
		for index2 := 0; index2 < len(nums); index2++ {
			if nums[index] + nums[index2] == target {
				return [2]int{index, index2}
			}
		}
		nums = nums[index:]
	}
	return [2]int{0, 1}
}