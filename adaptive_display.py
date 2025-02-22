import pygame as pg

def initialize_adaptive_display(fullscreen=True):
    """
    Inicializa la pantalla adaptándose a la resolución del dispositivo.
    
    Args:
        fullscreen (bool): Si es True, se crea la pantalla en modo pantalla completa;
                           de lo contrario, se crea una ventana con el tamaño del display.
                           
    Returns:
        tuple: (screen, width, height)
    """
    # Se obtiene la información de la pantalla actual
    display_info = pg.display.Info()
    width, height = display_info.current_w, display_info.current_h

    # Define las banderas de visualización
    flags = pg.FULLSCREEN if fullscreen else 0

    # Crea la ventana o pantalla completa con la resolución del dispositivo
    screen = pg.display.set_mode((width, height), flags)
    return screen, width, height

# Ejemplo de uso:
if __name__ == "__main__":
    pg.init()
    screen, width, height = initialize_adaptive_display(fullscreen=True)
    print("Resolución del dispositivo:", width, "x", height)
    pg.display.set_caption("Pantalla adaptativa")
    
    running = True
    clock = pg.time.Clock()
    while running:
        for event in pg.event.get():
            if event.type == pg.QUIT or (event.type == pg.KEYDOWN and event.key == pg.K_ESCAPE):
                running = False

        screen.fill((0, 0, 0))
        pg.display.flip()
        clock.tick(60)
    pg.quit()
