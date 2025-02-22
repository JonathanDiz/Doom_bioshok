import os
import json

class GameStats:
    def __init__(self, filename="stats.json"):
        self.filename = filename
        self.deaths = 0
        self.wins = 0
        self.load_stats()

    def load_stats(self):
        """Carga las estadísticas desde el archivo JSON, si existe."""
        if os.path.exists(self.filename):
            try:
                with open(self.filename, "r", encoding="utf-8") as file:
                    data = json.load(file)
                    self.deaths = data.get("deaths", 0)
                    self.wins = data.get("wins", 0)
            except Exception as e:
                print("Error al cargar las estadísticas:", e)
                self.deaths = 0
                self.wins = 0
        else:
            self.save_stats()  # Crea el archivo con valores iniciales

    def save_stats(self):
        """Guarda las estadísticas actuales en un archivo JSON."""
        data = {"deaths": self.deaths, "wins": self.wins}
        try:
            with open(self.filename, "w", encoding="utf-8") as file:
                json.dump(data, file, indent=4)
        except Exception as e:
            print("Error al guardar las estadísticas:", e)

    def increment_deaths(self):
        """Incrementa el contador de muertes y guarda el archivo."""
        self.deaths += 1
        self.save_stats()

    def increment_wins(self):
        """Incrementa el contador de victorias y guarda el archivo."""
        self.wins += 1
        self.save_stats()

    def reset(self):
        """Reinicia las estadísticas a cero y guarda el archivo."""
        self.deaths = 0
        self.wins = 0
        self.save_stats()

    def get_stats(self):
        """Devuelve un diccionario con las estadísticas actuales."""
        return {"deaths": self.deaths, "wins": self.wins}
