import matplotlib.pyplot as plt
import numpy as np

# Zeitachse
t = np.linspace(0, 1, 100)
# Ideales Signal: Eine Sakkade (schneller Sprung)
ideal = np.where(t < 0.5, 0, 100)
# Rohsignal mit Rauschen (Jitter)
noise = np.random.normal(0, 5, 100)
raw_signal = ideal + noise

# 1. Gleitender Durchschnitt (SMA) - Erzeugt Latenz
window_size = 10
sma = np.convolve(raw_signal, np.ones(window_size)/window_size, mode='same')

# 2. One-Euro-Filter (Vereinfachte Darstellung des adaptiven Verhaltens)
# Bei Sprung (t=0.5) reagiert er schneller als der SMA
one_euro = np.copy(raw_signal)
for i in range(1, len(one_euro)):
    # Simulierter adaptiver Faktor: Kleiner bei Ruhe, groß bei Bewegung
    alpha = 0.1 if abs(raw_signal[i] - raw_signal[i-1]) < 10 else 0.8
    one_euro[i] = alpha * raw_signal[i] + (1 - alpha) * one_euro[i-1]

# Plot erstellen
plt.figure(figsize=(10, 6))
plt.plot(t, raw_signal, label='Rohsignal (Webcam-Jitter)', alpha=0.3, color='gray')
plt.plot(t, sma, label='Gleitender Durchschnitt (Hohe Latenz)', color='red', linestyle='--')
plt.plot(t, one_euro, label='One-Euro-Filter (Adaptiv & Reaktiv)', color='green', linewidth=2)
plt.axvline(x=0.5, color='blue', alpha=0.2, label='Bewegungsstart')

plt.title('Vergleich der Signalverarbeitung: Stabilität vs. Reaktivität')
plt.xlabel('Zeit (s)')
plt.ylabel('Cursor-Position (Pixel)')
plt.legend()
plt.grid(True, alpha=0.3)
plt.show()