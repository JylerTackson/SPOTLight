from textaxes import parse_num, calibrate_axis

def test_axes():
    assert parse_num('83.5 °C') == 83.5
    assert parse_num('pump') is None
    fit = calibrate_axis([(0,0),(10,10),(20,20),(30,290)])
    assert fit and sum(fit[2]) == 3
    assert calibrate_axis([(0,0),(10,10)]) is None
