impl Solution {
    pub fn defang_i_paddr(address: String) -> String {
        let mut defangedString = String::from("");

        for i in address.chars() {
            if i == '.' {
                defangedString.push_str("[.]");
            } else {
                defangedString.push(i);
            }
        }
        return defangedString;
    }
}