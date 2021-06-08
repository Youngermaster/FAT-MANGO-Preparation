use std::io;

fn main() {
    let mut weight = String::new();
    io::stdin()
        .read_line(&mut weight)
        .expect("Failed to read line");

    let weight: u32 =  weight.trim().parse().unwrap();

    if weight % 2 == 0 && weight > 2 {
        println!("YES");
    } else {
        println!("NO");
    }
}
