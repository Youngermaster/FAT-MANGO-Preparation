/**
    Input: (2 -> 4 -> 3) + (5 -> 6 -> 4)
    Output: 7 -> 0 -> 8
    Explanation: 342 + 465 = 807.

*/
// ! I'll use arrays instead of linked list
// ! because right now I don't know how to do it.
package main

import (
	"fmt"
	"math"
)

func main() {
	list1 := []int{2, 4, 3}
	list2 := []int{5, 6, 4}
	fmt.Println(addTwoNumbers(list1, list2))
}

func addTwoNumbers(list1 []int, list2 []int) []int {
	result := make([]int, 0, (len(list1) + 1))
	carryOver := 0

	for index := 0; index < len(list1); index++ {
		result = append(result, list1[index] + list2[index] + carryOver)
		carryOver = math.Floor((*(*float64) &(result[index])) / 10)
		fmt.Println(math.Floor(1.24))
	}

	return result
}