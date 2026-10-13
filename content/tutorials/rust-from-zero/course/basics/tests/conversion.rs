use rust_basics::math::celsius_to_fahrenheit;

#[test]
fn boiling_point_through_public_api() {
    assert!((celsius_to_fahrenheit(100.0) - 212.0).abs() < 1e-10);
}
