fn get_input() -> String {
    let mut buffer = String::new();
    std::io::stdin().read_line(&mut buffer).expect("Failed");
    buffer
}

fn main() {
    let n = get_input().trim().parse::<i64>().unwrap();
    for _i in 0..n {
        let word = get_input();
        if word.len() > 10 {
            let mut b: i32 = (word.len() as i32) - 2;
            b -= 2;
            println!(
                "{}{}{}",
                &word[0..1],
                b,
                word.trim().chars().last().unwrap()
            );
        } else {
            println!("{}", word.trim());
        }
    }
}
