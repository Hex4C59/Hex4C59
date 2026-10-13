use taskbook::{add_task, mark_done, render_tasks};
use taskbook_plus::{pending, render_selection};

fn main() -> Result<(), String> {
    let mut tasks = Vec::new();
    add_task(&mut tasks, "学习 Rust")?;
    let selected = pending(&tasks);
    print!("{}", render_selection(&selected));
    mark_done(&mut tasks, 1)?;
    print!("{}", render_tasks(&tasks));
    Ok(())
}
