# EyeAssist – Hybrid Tracking Mouse Control

EyeAssist ist eine barrierefreie Desktop-Anwendung, die es ermöglicht,
den Mauszeiger ausschließlich durch Kopf- und Augenbewegungen zu steuern.
Die Steuerung erfolgt kamerabasiert mittels MediaPipe Face Mesh – ohne
zusätzliche Hardware.

---

## Funktionsübersicht

- **Hybrid-Tracking:** Kombination aus Kopfbewegung (Nase als Anker) und
  Iris-Tracking für präzise Maussteuerung
- **Gestensteuerung:** Konfigurierbare Gestenaktionen (Mund öffnen, Lächeln,
  Kopfneigung u. a.) für Mausklicks, Scrollen und Tastatureingaben
- **One-Euro-Filter:** Adaptiver Glättungsfilter zur Reduktion von Jitter
- **Kalibrierung:** Automatische Referenzpunkt-Kalibrierung beim Start
- **Grafische Oberfläche:** Tkinter-basiertes GUI mit Hell- und Dunkel-Modus
- **Konfigurierbar:** Alle Parameter über `config.json` oder das
  Einstellungs-Fenster anpassbar

---

## Voraussetzungen

| Anforderung | Version |
|---|---|
| Python | 3.11 (empfohlen) |
| Betriebssystem | Windows 10/11 |
| Webcam | Beliebige USB- oder integrierte Kamera |

> **Hinweis:** Die Anwendung wurde primär unter Windows entwickelt und
> getestet. Unter Linux/macOS kann `pynput` eine abweichende Konfiguration
> erfordern.

---

## Installation

### 1. Repository klonen

```bash
git clone https://github.com/LeJohnny03/EyeAssist.git
cd EyeAssist
git checkout hybrid-tracking
```

### 2. Virtuelle Umgebung erstellen (empfohlen)

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux/macOS
```

### 3. Abhängigkeiten installieren

Für den normalen Betrieb genügen die fünf Kernbibliotheken:

```bash
pip install mediapipe==0.10.21 numpy==1.26.4 opencv-python==4.10.0.84 pynput==1.8.1 PyQt6==6.10.0
```

Alternativ alle Abhängigkeiten aus der vollständigen Liste:

```bash
pip install -r requirements.txt
```

---

## Anwendung starten

```bash
cd src
python main.py
```

Das Hauptfenster öffnet sich. Die Kamera wird erst aktiviert, wenn
„**▶ Tracking starten**" geklickt wird.

---

## Projektstruktur
EyeAssist/
├── config.json # Konfigurationsdatei (alle Parameter)
├── requirements.txt # Python-Abhängigkeiten
└── src/
├── main.py # Einstiegspunkt
├── core/
│ ├── application.py # Hauptsteuerung (Tracking-Loop)
│ ├── tracker_engine.py # Kopf- & Iris-Tracking (MediaPipe)
│ ├── mouse_controller.py # Maussteuerung (pynput) + One-Euro-Filter
│ └── gesture_recognizer.py# Gestenerkennung & Aktionsausführung
├── gui/
│ ├── theme.py # Gemeinsame Farbpaletten (Hell/Dunkel)
│ ├── overlay.py # OpenCV-Vorschau-Overlay
│ ├── calibration_wizard.py# Kalibrierungs-Logik & Fortschrittsanzeige
│ ├── tray_icon.py # System-Tray-Integration
│ └── windows/
│ ├── main_window.py # Hauptfenster
│ ├── settings_window.py # Einstellungs-Fenster (alle Parameter)
│ ├── gesture_mapping_window.py # Gesten-Konfiguration
│ └── preview_window.py # Kamera-Vorschaufenster
└── utils/
└── config_manager.py # JSON-Konfigurationsverwaltung

---

## Konfiguration

Alle Einstellungen werden in `config.json` im Wurzelverzeichnis gespeichert
und können entweder direkt in der Datei oder über
**⚙ Einstellungen** im GUI bearbeitet werden.

### Wichtige Parameter

#### Kamera (`camera`)
| Parameter | Standard | Beschreibung |
|---|---|---|
| `camera_id` | `0` | Index der Webcam (0 = erste Kamera) |
| `width` / `height` | `640` / `480` | Auflösung des Kamera-Streams |
| `flip_horizontal` | `true` | Bild horizontal spiegeln (Spiegeleffekt) |
| `fps_target` | `30` | Ziel-Framerate |

#### Tracking (`tracking`)
| Parameter | Standard | Beschreibung |
|---|---|---|
| `min_detection_confidence` | `0.5` | Mindestkonfidenz für Gesichtserkennung |
| `min_tracking_confidence` | `0.5` | Mindestkonfidenz für Tracking |
| `refine_landmarks` | `true` | Iris-Landmarks aktivieren (nötig für Iris-Tracking) |

#### Maussteuerung (`mouse`)
| Parameter | Standard | Beschreibung |
|---|---|---|
| `sensitivity_x/y` | `8.0` / `10.0` | Kopf-Tracking-Empfindlichkeit |
| `iris_sensitivity_x/y` | `3.0` / `3.0` | Iris-Tracking-Empfindlichkeit |
| `smoothing_buffer_size` | `4` | Glättungspuffer (höher = ruhiger, aber träger) |
| `min_cutoff` / `beta` | `0.5` / `0.003` | One-Euro-Filter-Parameter |
| `pixel_deadzone` | `8` | Mindestbewegung in Pixel vor Mausbewegung |

#### Gesten (`gesture_actions`)

Jede Geste besitzt folgende Felder:

| Feld | Beschreibung |
|---|---|
| `enabled` | Geste aktiv oder nicht |
| `action` | Auszuführende Aktion (siehe Liste unten) |
| `threshold` | Auslöseschwelle (0.005 – 0.2) |
| `cooldown_frames` | Frames bis zur erneuten Auslösung |

**Verfügbare Aktionen:** `left_click`, `right_click`, `double_click`,
`middle_click`, `scroll_up`, `scroll_down`, `drag_toggle`, `key_enter`,
`key_space`, `key_escape`, `key_left`, `key_right`, `key_up`, `key_down`,
`disabled`

---

## Standard-Hotkeys

| Taste | Funktion |
|---|---|
| `F9` | Tracking ein-/ausschalten |
| `F10` | Neu kalibrieren |
| `F11` | Vorschau-Fenster ein-/ausschalten |
| `F12` | Anwendung beenden |

> Hotkeys können in `config.json` unter `hotkeys` angepasst werden.

---

## Kalibrierung

Beim Start des Trackings wird automatisch eine Kalibrierung durchgeführt:

1. Kopf gerade in die Kamera schauen
2. Ruhig halten bis der Fortschrittsbalken abgeschlossen ist
   (Standard: 30 Frames ≈ 1 Sekunde)
3. Diese Position wird als Neutral-Position (Bildschirmmitte) gespeichert

Eine manuelle Neukalibrierung ist jederzeit über `F10` oder den
Button **🔄 Rekalibrieren** im Hauptfenster möglich.

---

## Bekannte Einschränkungen

- Die Anwendung befindet sich im **Beta-Stadium** – manche Einstellungen
  werden möglicherweise nicht sofort übernommen und erfordern einen Neustart
  des Trackings
- Starke Lichtwechsel oder verdecktes Gesicht unterbrechen das Tracking
- Bei mehreren Monitoren wird die Maus standardmäßig auf dem Primärmonitor
  gesteuert
- `static_image_mode: true` deaktiviert das kontinuierliche Tracking und
  eignet sich nur für Tests

---

## Abhängigkeiten (Kernbibliotheken)

| Bibliothek | Version | Zweck |
|---|---|---|
| `mediapipe` | 0.10.21 | Face Mesh & Iris Landmark Detection |
| `opencv-python` | 4.10.0.84 | Kamerastream & Bildverarbeitung |
| `numpy` | 1.26.4 | Vektorberechnungen für Tracking |
| `pynput` | 1.8.1 | Maus- & Tastatursteuerung |
| `PyQt6` | 6.10.0 | (Optional) Erweiterte GUI-Komponenten |