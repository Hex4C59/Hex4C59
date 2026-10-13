/// 把摄氏温度转换为华氏温度。
///
/// ```
/// assert_eq!(rust_basics::math::celsius_to_fahrenheit(0.0), 32.0);
/// ```
pub fn celsius_to_fahrenheit(celsius: f64) -> f64 {
    celsius * 1.8 + 32.0
}

#[cfg(test)]
mod tests {
    use super::celsius_to_fahrenheit;

    #[test]
    fn freezing_point() {
        assert!((celsius_to_fahrenheit(0.0) - 32.0).abs() < 1e-10);
    }

    #[test]
    fn negative_temperature() {
        assert!((celsius_to_fahrenheit(-40.0) + 40.0).abs() < 1e-10);
    }
}
