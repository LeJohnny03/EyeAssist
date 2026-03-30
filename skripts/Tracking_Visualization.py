import pandas as pd
import matplotlib.pyplot as plt

def plot_tracking_trace(csv_file_1, csv_file_2, screen_w=1920, screen_h=1080):
    # Lade die CSV-Daten
    df1 = pd.read_csv(csv_file_1)
    df2 = pd.read_csv(csv_file_2)

    # Erstelle einen Plot mit zwei nebeneinanderliegenden Graphen
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 7), sharex=True, sharey=True)
    fig.suptitle('Vergleich der Cursor-Spuren (Multi-Target Acquisition)', fontsize=16, fontweight='bold')

    # Zielparameter aus deiner Arbeit
    target_radius = 25      # 50 Pixel Durchmesser
    acceptance_radius = 20  # 20 Pixel Akzeptanz-Radius

    def draw_target_and_trace(ax, df, title, color):
        ax.set_title(title, fontsize=14)
        ax.set_xlabel('Bildschirm X (Pixel)')
        ax.set_ylabel('Bildschirm Y (Pixel)')
        
        # Feste Bildschirmgrenzen setzen und Y-Achse invertieren (0 ist oben)
        ax.set_xlim(0, screen_w)
        ax.set_ylim(screen_h, 0) 
        ax.grid(True, linestyle='--', alpha=0.6)

        # Daten trennen in Frames (Bewegung) und Klicks (Ziele)
        frames = df[df['event_type'] == 'frame']
        clicks = df[df['event_type'] == 'click_registered']

        # 1. Ziele einzeichnen basierend auf den Klick-Events
        for idx, row in clicks.iterrows():
            target_x, target_y = row['x'], row['y']
            
            # Labels nur beim ersten Ziel setzen, damit die Legende nicht überläuft
            label_target = 'Ziel (50px)' if idx == clicks.index[0] else ""
            label_acc = 'Akzeptanz (20px)' if idx == clicks.index[0] else ""
            
            target_circle = plt.Circle((target_x, target_y), target_radius, color='lightgray', fill=True, label=label_target)
            acc_circle = plt.Circle((target_x, target_y), acceptance_radius, color='green', fill=False, linestyle='--', linewidth=2, label=label_acc)
            
            ax.add_patch(target_circle)
            ax.add_patch(acc_circle)
            
            # Markiere den exakten Klick-Punkt mit einem roten X
            label_click = 'Registrierter Klick' if idx == clicks.index[0] else ""
            ax.plot(target_x, target_y, marker='x', color='red', markersize=8, label=label_click)

        # 2. Tracking-Spur zeichnen
        ax.plot(frames['x'], frames['y'], marker='.', markersize=2, linestyle='-', color=color, alpha=0.6, label='Cursor-Pfad')
        
        # 3. Startpunkt markieren
        if not frames.empty:
            ax.plot(frames['x'].iloc[0], frames['y'].iloc[0], marker='o', color='black', markersize=8, label='Startpunkt')

        ax.legend(loc='upper left', fontsize=9)

    # Zeichne Graph 1 (Experiment 1) und Graph 2 (Experiment 4)
    # TIPP: Falls du das Skript erstmal nur mit einer CSV testen willst, kannst du df1 und df2 mit der gleichen Datei füttern.
    draw_target_and_trace(ax1, df1, 'Exp. 1: Reines Eye-Tracking', 'red')
    draw_target_and_trace(ax2, df2, 'Exp. 4: Hybrides Head-Tracking', 'blue')

    plt.tight_layout()
    plt.savefig('tracking_trace_vergleich.png', dpi=300, bbox_inches='tight')
    plt.show()

if __name__ == "__main__":
    # Ersetze die Dateinamen mit deinen echten CSV-Dateien
    plot_tracking_trace('metrics\Eye_Metric.csv', 'metrics\Main_Metric.csv')