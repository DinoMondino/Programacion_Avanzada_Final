from modules.departamentos import Analitica, ReporteHTML

def test_calculo_mediana_eficiente(gestor_servicio):
    # Inicializamos analítica con la fixture que SÍ existe
    analitica = Analitica(gestor_servicio)
    
    # Caso impar
    assert analitica.calcular_mediana([10, 2, 5]) == 5.0
    
    # Caso par
    assert analitica.calcular_mediana([1, 2, 10, 20]) == 6.0

def test_generar_reporte_html(gestor_servicio):
    analitica = Analitica(gestor_servicio)
    
    # Datos de prueba mínimos para que no falle el reporte
    datos_mock = {
        'stats': {
            'pendientes': 5,
            'mediana_en_proceso': 1.5,
            'mediana_resueltos': 2.0
        },
        'lista_reclamos': []
    }
    
    reporte = ReporteHTML().exportar("Test Titulo", datos_mock)
    
    assert "<h1>Test Titulo</h1>" in reporte
    assert "Estadísticas:" in reporte