use std::io;

fn main() {
    let mut input = String::new();

    io::stdin().read_line(&mut input)
        .ok()
        .expect("Couldn't read line");    

    for i in 0..input.len() {
        if i == 0 {   
            print!("{}", input.as_bytes()[i].to_ascii_uppercase() as char);
        } else {
            print!("{}", input.as_bytes()[i] as char);
        }        
    }
}