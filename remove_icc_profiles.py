import os
from PIL import Image
from PIL.PngImagePlugin import PngInfo

def remove_icc_profile(image_path):
    try:
        with Image.open(image_path) as img:
            # Eliminar perfil ICC y chunks problemáticos
            problematic_chunks = ['icc_profile', 'cHRM', 'gAMA', 'sRGB']
            for chunk in problematic_chunks:
                if chunk in img.info:
                    del img.info[chunk]
            
            # Conservar otros metadatos
            metadata = PngInfo()
            for key, value in img.info.items():
                if key not in problematic_chunks:
                    if isinstance(value, (bytes, str)):
                        metadata.add_text(key, str(value), 0)
            
            # Guardar optimizado
            img.save(
                image_path,
                format='PNG',
                pnginfo=metadata,
                optimize=True,
                compress_level=9
            )
            print(f"✅ {os.path.basename(image_path)} procesado correctamente")
            return True
            
    except Exception as e:
        print(f"❌ Error en {os.path.basename(image_path)}: {str(e)}")
        return False

def process_resources():
    # Procesa la carpeta resources y sus subdirectorios
    current_dir = os.path.dirname(os.path.abspath(__file__))
    resources_path = os.path.join(current_dir, 'resources')
    
    if not os.path.exists(resources_path):
        print("⚠️ Carpeta 'resources' no encontrada")
        return
    
    print(f"🔍 Buscando PNG en: {resources_path}")
    for root, _, files in os.walk(resources_path):
        for file in files:
            if file.lower().endswith('.png'):
                full_path = os.path.join(root, file)
                remove_icc_profile(full_path)
    
    print("✨ Proceso completado")

if __name__ == "__main__":
    process_resources()