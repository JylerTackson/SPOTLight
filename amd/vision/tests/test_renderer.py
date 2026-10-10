from scripts.render_synth import render

def test_deterministic():
    for measurement,value in [('TEMPERATURE_C',70),('PRESSURE_PSI',100)]:
        assert render('R1','true',measurement,value)[0]==render('R1','true',measurement,value)[0]
