#[derive(Debug)]
struct Task {
    title: String,
    done: bool,
}

impl Task {
    fn new(title: &str) -> Self {
        Self {
            title: title.to_string(),
            done: false,
        }
    }

    fn complete(&mut self) {
        self.done = true;
    }

    fn label(&self) -> &str {
        &self.title
    }
}

enum Command {
    Add(String),
    Done(u64),
    List,
}

fn describe(command: &Command) {
    match command {
        Command::Add(title) => println!("新增：{title}"),
        Command::Done(id) => println!("完成编号：{id}"),
        Command::List => println!("列出全部任务"),
    }
}

fn first_task(tasks: &[Task]) -> Option<&Task> {
    tasks.first()
}

fn main() {
    let mut task = Task::new("学习枚举");
    task.complete();
    println!("{}：{}", task.label(), task.done);
    let tasks = vec![task];
    match first_task(&tasks) {
        Some(task) => println!("第一项：{}", task.label()),
        None => println!("还没有任务"),
    }
    if let Some(task) = first_task(&tasks) {
        println!("找到：{}", task.label());
    }
    describe(&Command::Add(String::from("写练习")));
    describe(&Command::Done(1));
    describe(&Command::List);
}
