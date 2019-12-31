package main

import (
	"fmt"
)

func main() {
	fmt.Println(solution("pwwkew"))
}

func solution(fullString string) int {
	character := 0
	subString := make([]byte, 0, len(fullString))
	for index := 0; index < len(fullString); index++ {
		if !checkInList(fullString[index], subString) {
			character++
			subString = append(subString, fullString[index])
		} else {
			return character
		}
	}

	return character
}

func checkInList(numberToCheck byte, list []byte) bool {
	for index := 0; index < len(list); index++ {
		if list[index] == numberToCheck {
			return true
		}
	}
	return false
}