use taskbook::{add_task, mark_done, render_tasks};

fn main() -> Result<(), String> {
    let mut tasks = Vec::new();
    add_task(&mut tasks, "学习 Rust")?;
    add_task(&mut tasks, "写练习")?;
    mark_done(&mut tasks, 1)?;
    print!("{}", render_tasks(&tasks));
    Ok(())
}
