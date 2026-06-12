import sys
import networkx as nx
import math
from PyQt6.QtWidgets import (QApplication, QMainWindow, QGraphicsScene, 
                             QGraphicsView, QVBoxLayout, QHBoxLayout, QWidget, 
                             QLabel, QComboBox, QGroupBox, QPushButton, QCompleter)
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QPen, QColor, QPainter, QFont

class CitySimulation(QMainWindow):
    print("wryyyyyyyyyyyyyyyyyyy")
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Dynamic Traffic Simulation")
        self.resize(1050, 1050)
        
        self.grid_size = 100
        self.cell_size = 8

        
        self.start_node = None
        self.end_node = None
        self.vehicle_node = None
        self.current_path = []
        self.viaje_en_curso = False
        self.time_minutes = 7 * 60 + 30  
        self.streets_closed = False
        self.restricted_edges = []
        self.restricted_line_items = []
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        self.generate_graphs()
        
        top_panel = QGroupBox("Control & Simulation Status")
        top_layout = QHBoxLayout(top_panel)
        
        self.lbl_clock = QLabel("07:30")
        self.lbl_clock.setFont(QFont("Courier", 18, QFont.Weight.Bold))
        self.lbl_clock.setStyleSheet("color: #333;")
        top_layout.addWidget(QLabel("Time:"))
        top_layout.addWidget(self.lbl_clock)
        top_layout.addSpacing(20)
        
        self.combo_origen = QComboBox()
        self.combo_origen.setEditable(True)
        self.combo_origen.completer().setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        nodos_ordenados = sorted(list(self.G_full.nodes()))
        self.combo_origen.addItems([f"{n[0]},{n[1]}" for n in nodos_ordenados])
        self.combo_origen.setCurrentText("00,00")
        self.combo_origen.currentTextChanged.connect(self.on_search_origen_changed)
        top_layout.addWidget(QLabel("Origen (x,y):"))
        top_layout.addWidget(self.combo_origen)
        
        self.combo_destino = QComboBox()
        self.combo_destino.setEditable(True)
        self.combo_destino.addItems([f"{n[0]},{n[1]}" for n in nodos_ordenados])
        self.combo_destino.setCurrentText("14,49")
        self.combo_destino.currentTextChanged.connect(self.on_search_destino_changed)
        top_layout.addWidget(QLabel("Destino (x,y):"))
        top_layout.addWidget(self.combo_destino)
        
        self.btn_iniciar = QPushButton("Iniciar Viaje")
        self.btn_iniciar.clicked.connect(self.iniciar_viaje)
        top_layout.addWidget(self.btn_iniciar)
        main_layout.addWidget(top_panel)
        
        legend_layout = QHBoxLayout()
        legend_layout.addWidget(QLabel("Orange is Restricted Zone (Open)"))
        legend_layout.addWidget(QLabel("Red is Restricted Zone (Closed 8-10am, 5-7pm)"))
        legend_layout.addWidget(QLabel("Blue corresponds to the highways (they do not close)"))
        legend_layout.addStretch()
        main_layout.addLayout(legend_layout)
        
        self.scene = QGraphicsScene()
        self.view = QGraphicsView(self.scene)
        self.view.setRenderHint(QPainter.RenderHint.Antialiasing)
        main_layout.addWidget(self.view)
        
        self.draw_city()
        self.on_search_origen_changed(self.combo_origen.currentText())
        self.on_search_destino_changed(self.combo_destino.currentText())
        
        self.global_timer = QTimer()
        self.global_timer.timeout.connect(self.simulation_tick)
        self.global_timer.start(50)
        
        print(f" The world El tiempo avanza a partir de las {self.lbl_clock.text()}")

    def calculate_distance(self, node1, node2):
        """Calcula la distancia euclidiana entre dos nodos"""
        return math.sqrt((node1[0] - node2[0])**2 + (node1[1] - node2[1])**2)
    
    def is_avenue(self, u, v):
        # Avenidas horizontales (y es múltiplo de 5)
        if u[0] == v[0] and (u[1] % 5 == 0 or v[1] % 5 == 0):
            return True
        # Avenidas verticales (x es múltiplo de 5)
        if u[1] == v[1] and (u[0] % 5 == 0 or v[0] % 5 == 0):
            return True
        return False
        
    def is_highway(self, u, v):
        
        if u[1] == 50 and (v[1] ==50):
            return True
        if u[0] == 50 and  (v[0] == 50): 
            return True
        return False


    def generate_graphs(self):
        # Crear grafo base con pesos
        self.G_full = nx.Graph()
        
        # Agregar todos los nodos
        for x in range(self.grid_size):
            for y in range(self.grid_size):
                self.G_full.add_node((x, y))
        
        # Agregar aristas de la cuadrícula básica con pesos basados en distancia
        for x in range(self.grid_size):
            for y in range(self.grid_size):
                # Conexión derecha
                if x < self.grid_size - 1:
                    dist = self.calculate_distance((x, y), (x+1, y))
                    # Las avenidas son más rápidas (menor peso)
                    weight = dist * 0.3 if self.is_avenue((x, y), (x+1, y)) else dist
                    self.G_full.add_edge((x, y), (x+1, y), weight=weight)
                
                # Conexión abajo
                if y < self.grid_size - 1:
                    dist = self.calculate_distance((x, y), (x, y+1))
                    weight = dist * 0.3 if self.is_avenue((x, y), (x, y+1)) else dist
                    self.G_full.add_edge((x, y), (x, y+1), weight=weight)
        
        # Agregar diagonales con peso basado en distancia
        for x in range(self.grid_size - 1):
            for y in range(self.grid_size - 1):
                # Diagonal principal
                dist = self.calculate_distance((x, y), (x+1, y+1))
                self.G_full.add_edge((x, y), (x+1, y+1), weight=dist * 1.2)  # Un poco más lentas
                
                # Diagonal 
                dist = self.calculate_distance((x+1, y), (x, y+1))
                self.G_full.add_edge((x+1, y), (x, y+1), weight=dist * 1.2)
        
        print(f"Mapa con {self.G_full.number_of_nodes()} nodos y {self.G_full.number_of_edges()} aristas.")
        
        self.G_current = self.G_full.copy()
        
        # Aristas restringidas
        target_edges = [


            ((23, 67), (24, 67)),
            ((24, 67), (25, 67)),
            ((25, 67), (26, 67)),
            ((26, 67), (27, 67)),
            ((27, 67), (28, 67)),
            ((28, 67), (29, 67)),
            ((29, 67), (30, 67)),
            ((30, 67), (31, 67)),
            ((31, 67), (32, 67)),
            ((32, 67), (33, 67)),



            ((14, 41), (14, 42)),
            ((14, 42), (14, 43)),
            ((14, 43), (14, 44)),
            ((14, 44), (14, 45)),
            ((14, 45), (14, 46)),
            ((14, 46), (14, 47)),
            ((14, 47), (14, 48)),
            ((14, 48), (14, 49)),
            ((14, 49), (14, 50)),
            ((14, 50), (14, 51)),

        ]

        self.higway_edges = set()
        for x in range(0, self.grid_size, 5):
            for y in range(self.grid_size):
                if x < self.grid_size - 1:
                    self.higway_edges.add(((x, 50), (x+1, 50)))
                if y < self.grid_size - 1:
                    self.higway_edges.add(((50, y), (50, y+1)))
        
        for(u, v) in self.higway_edges:
            dist = self.calculate_distance(u, v)
            weight = dist * 0.1
            self.G_full.add_edge(u, v, weight=weight)
            self.G_current.add_edge(u, v, weight=weight)
        self.restricted_edges = []
        for u, v in self.G_full.edges():
            if (u, v) in target_edges or (v, u) in target_edges:
                self.restricted_edges.append((u, v))

        self.restricted_nodes = set()
        for u, v in self.restricted_edges:
            self.restricted_nodes.add(u)
            self.restricted_nodes.add(v)

    def draw_city(self):
        self.scene.clear()
        pen_normal = QPen(QColor(220, 220, 220), 0.5)
        pen_open = QPen(QColor(255, 165, 0), 1.5) 
        pen_avenue = QPen(QColor(180, 180, 180), 1.5)  
        
        self.restricted_line_items = []
        
        for u, v in self.G_full.edges():
            is_restricted = (u, v) in self.restricted_edges or (v, u) in self.restricted_edges
            is_hw = self.is_highway(u, v)
            
            if is_restricted:
                pen = pen_open
            elif is_hw:
                pen = QPen(QColor(0, 180, 255), 3)
            elif self.is_avenue(u, v):
                pen = pen_avenue
            else:
                pen = pen_normal
            
            line = self.scene.addLine(u[0]*self.cell_size, u[1]*self.cell_size, 
                                      v[0]*self.cell_size, v[1]*self.cell_size, pen)
            
            if is_restricted:
                self.restricted_line_items.append(line)
        
        self.start_marker = self.scene.addEllipse(-4, -4, 8, 8, QPen(Qt.GlobalColor.black), QColor(0, 255, 0))
        self.end_marker = self.scene.addEllipse(-4, -4, 8, 8, QPen(Qt.GlobalColor.black), QColor(255, 0, 0))
        self.vehicle_marker = self.scene.addEllipse(-6, -6, 12, 12, QPen(Qt.GlobalColor.black), QColor(255, 215, 0))
        
        self.start_marker.hide()
        self.end_marker.hide()
        self.vehicle_marker.hide()

    def simulation_tick(self):
        self.time_minutes += 1
        if self.time_minutes >= 24 * 60:
            self.time_minutes = 0
            
        hours = self.time_minutes // 60
        minutes = self.time_minutes % 60
        self.lbl_clock.setText(f"{hours:02d}:{minutes:02d}")
        
        is_rush_hour = (8 <= hours < 10) or (17 <= hours < 19)
        
        if is_rush_hour != self.streets_closed:
            self.toggle_streets(is_rush_hour)
        
        if self.viaje_en_curso:
            self.mover_vehiculo()

    def toggle_streets(self, close_them):
        self.streets_closed = close_them
        
        if close_them:
            # Eliminar aristas restringidas
            edges_to_remove = [(u, v) for u, v in self.restricted_edges 
                            if self.G_current.has_edge(u, v)]
            self.G_current.remove_edges_from(edges_to_remove)
            
            # Eliminar también los nodos restringidos (y sus aristas adyacentes)
            nodes_to_remove = [n for n in self.restricted_nodes 
                            if self.G_current.has_node(n)
                            and n[0] != 50
                            and n[1] != 50
                            ]
            self.G_current.remove_nodes_from(nodes_to_remove)
            
            pen_color = QPen(QColor(255, 0, 0), 2)
        else:
            # Restaurar nodos restringidos
            for n in self.restricted_nodes:
                if not self.G_current.has_node(n):
                    self.G_current.add_node(n)
            
            # Restaurar todas las aristas que tocaban esos nodos (desde G_full)
            for u, v, data in self.G_full.edges(data=True):
                if u in self.restricted_nodes or v in self.restricted_nodes:
                    if self.G_current.has_node(u) and self.G_current.has_node(v):
                        self.G_current.add_edge(u, v, **data)
            for (u, v) in self.higway_edges:
                if self.G_current.has_node(u) and self.G_current.has_node(v):
                    dist = self.calculate_distance(u, v)
                    self.G_current.add_edge(u, v, weight=dist * 0.1)
            # Restaurar aristas restringidas con sus pesos originales
            for u, v in self.restricted_edges:
                if u in self.G_current and v in self.G_current:
                    if self.G_full.has_edge(u, v):
                        original_weight = self.G_full[u][v]['weight']
                        self.G_current.add_edge(u, v, weight=original_weight)
            
            pen_color = QPen(QColor(255, 165, 0), 2)
            
        for line in self.restricted_line_items:
            line.setPen(pen_color)
            
        if self.viaje_en_curso:
            self.recalculate_path()

    def update_markers_visuals(self):
        if self.start_node:
            self.start_marker.setPos(self.start_node[0]*self.cell_size, self.start_node[1]*self.cell_size)
            self.start_marker.show()
        if self.end_node:
            self.end_marker.setPos(self.end_node[0]*self.cell_size, self.end_node[1]*self.cell_size)
            self.end_marker.show()
        if self.vehicle_node:
            self.vehicle_marker.setPos(self.vehicle_node[0]*self.cell_size, self.vehicle_node[1]*self.cell_size)
            self.vehicle_marker.show()
            self.vehicle_marker.setZValue(10)

    def iniciar_viaje(self):
        if self.start_node and self.end_node and not self.viaje_en_curso:
            if self.start_node not in self.G_current:
                print("Nodo de inicio no disponible en este momento")
                return
                
            self.viaje_en_curso = True
            self.btn_iniciar.setEnabled(False)
            self.combo_origen.setEnabled(False)
            self.combo_destino.setEnabled(True) 
            self.vehicle_node = self.start_node
            self.recalculate_path()

    def on_search_origen_changed(self, text):
        if self.viaje_en_curso: 
            return
        try:
            clean_text = text.replace(" ", "")
            x, y = map(int, clean_text.split(','))
            if (x, y) in self.G_full:
                self.start_node = (x, y)
                self.vehicle_node = (x, y)
                self.update_markers_visuals()
        except Exception: 
            pass

    def on_search_destino_changed(self, text):
        try:
            clean_text = text.replace(" ", "")
            x, y = map(int, clean_text.split(','))
            if (x, y) in self.G_full:
                self.end_node = (x, y)
                self.update_markers_visuals()
                print(f"Destino establecido: {self.end_node}")
                
                if self.viaje_en_curso:
                    self.recalculate_path()
        except Exception: 
            pass

    def recalculate_path(self):
        try:
            if self.vehicle_node not in self.G_current or self.end_node not in self.G_current or self.vehicle_node in self.restricted_nodes and self.vehicle_node not in self.G_current:
                self.current_path = []
                print(f"[{self.lbl_clock.text()}] No hy nodos disponibles el programa parara hasta que el nodo sea liberado")
                return
                
            # Encontrar la ruta más corta usando los pesos
            self.current_path = nx.shortest_path(self.G_current, source=self.vehicle_node, 
                                               target=self.end_node, weight='weight')
            if self.current_path:
                self.current_path.pop(0)  # Remover el nodo actual
                
                # Mostrar información de la ruta
                total_weight = nx.shortest_path_length(self.G_current, source=self.vehicle_node,
                                                     target=self.end_node, weight='weight')
                print(f"[{self.lbl_clock.text()}] D4C llevame  a {self.end_node} - Distancia: {total_weight:.2f}")
                
        except nx.NetworkXNoPath:
            self.current_path = []
            print(f"[{self.lbl_clock.text()}] No hay ruta disponible. Esperando que abran las calles")

    def mover_vehiculo(self):
        if self.current_path:
            self.vehicle_node = self.current_path.pop(0)
            self.update_markers_visuals()
            
            if self.vehicle_node == self.end_node:
                print(f"[{self.lbl_clock.text()}] Llegaste ")
                self.viaje_en_curso = False
                self.btn_iniciar.setEnabled(True)
                self.combo_origen.setEnabled(True)
                self.combo_destino.setEnabled(True)
                self.start_node = self.vehicle_node
        else:
            if self.vehicle_node != self.end_node:
                self.recalculate_path()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = CitySimulation()
    window.show()
    sys.exit(app.exec())

