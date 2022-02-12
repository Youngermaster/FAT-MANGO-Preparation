def largest_range(array):
    numbers = {x: 0 for x in array}
    left = 0
    right = 0

    for number in array:
        if numbers[number] == 0:
            left_counter = number - 1
            right_counter = number + 1

        while left_counter in numbers:
            numbers[left_counter] = 1
            left_counter -= 1

        left_counter += 1

        while right_counter in numbers:
            numbers[right_counter] = 1
            right_counter += 1

        right_counter -= 1

        if (right - left) <= (right_counter - left_counter):
            right = right_counter
            left = left_counter

    return [left, right]


if __name__ == "__main__":
    array = [2, 3, 4, 5, 6]
    print(largest_range(array))
