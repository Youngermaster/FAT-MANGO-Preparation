impl Solution {
    pub fn number_of_steps (num: i32) -> i32 {
        let mut numberOfSteps = 0;
        let mut number = num;
        while number != 0 {
            if number % 2 == 0 {
                number /= 2;
            } else {
                number -= 1;
            }
            numberOfSteps = numberOfSteps + 1;
        }
        return numberOfSteps;
    }
}