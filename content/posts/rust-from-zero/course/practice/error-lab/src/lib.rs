use std::error::Error;
use std::fmt;
use std::fs;
use std::io;
use std::num::ParseIntError;
use std::path::Path;

#[derive(Debug)]
pub enum AppError {
    Io(io::Error),
    Number(ParseIntError),
    ZeroMinutes,
    Usage,
}

impl fmt::Display for AppError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Io(_) => write!(f, "无法读取分钟文件"),
            Self::Number(_) => write!(f, "分钟数不是有效的非负整数"),
            Self::ZeroMinutes => write!(f, "分钟数必须大于 0"),
            Self::Usage => write!(f, "用法：error-lab <分钟> | --file <文件路径>"),
        }
    }
}

impl Error for AppError {
    fn source(&self) -> Option<&(dyn Error + 'static)> {
        match self {
            Self::Io(error) => Some(error),
            Self::Number(error) => Some(error),
            Self::ZeroMinutes | Self::Usage => None,
        }
    }
}

impl From<io::Error> for AppError {
    fn from(error: io::Error) -> Self {
        Self::Io(error)
    }
}

impl From<ParseIntError> for AppError {
    fn from(error: ParseIntError) -> Self {
        Self::Number(error)
    }
}

pub fn parse_minutes(input: &str) -> Result<u32, AppError> {
    let minutes = input.trim().parse::<u32>()?;
    if minutes == 0 {
        return Err(AppError::ZeroMinutes);
    }
    Ok(minutes)
}

pub fn read_minutes(path: &Path) -> Result<u32, AppError> {
    let content = fs::read_to_string(path)?;
    parse_minutes(&content)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parses_valid_minutes_and_distinguishes_failures() {
        assert!(matches!(parse_minutes(" 30 "), Ok(30)));
        assert!(matches!(parse_minutes("0"), Err(AppError::ZeroMinutes)));
        for input in ["abc", "-1", "4294967296", ""] {
            assert!(matches!(parse_minutes(input), Err(AppError::Number(_))));
        }
    }

    #[test]
    fn preserves_sources_for_lower_level_errors() {
        let number = parse_minutes("abc").unwrap_err();
        assert_eq!(number.to_string(), "分钟数不是有效的非负整数");
        assert!(number.source().is_some());
        assert!(parse_minutes("0").unwrap_err().source().is_none());
        let io = AppError::from(io::Error::from(io::ErrorKind::NotFound));
        assert!(matches!(io, AppError::Io(_)));
        assert!(io.source().is_some());
    }
}
