# Prompt: Ziel-Agent für die Web-Konsole

Alles unterhalb der Linie in Claude Code einfügen, geöffnet im Repo `carearm-feeding-robot`.

---

Baue einen Agenten, der ein Ziel aus der Web-Konsole (`./cli.sh console`, http://localhost:8890) selbstständig verfolgt, zum Beispiel "Nimm eine Traube und leg sie in die Box". Er wiederholt eine feste Schleife (alle Kameras auswerten → Zustand sammeln → einen Schritt planen → ausführen), bis das Ziel erreicht ist oder `MAX_ITERATIONS` überschritten ist.

## Ausgangslage (bitte zuerst lesen)

- `src/console_agent.py`, `ConsoleAgent`: der heutige Chat-Agent. Er startet den `elrobot`-MCP-Server aus `.mcp.json` und führt eine freie Werkzeug-Schleife auf der Claude API aus (bis zu 25 Runden pro Nachricht). Schreibt alles in den Chat. Stoppwörter ("stop", "halt", "wait") und der STOP-Button gehen nie an Claude: Der laufende Zug wird abgebrochen und `stop` direkt aufgerufen.
- `src/web_console.py`: `create_app(..., agent_factory=...)` baut den Agenten mit `agent_factory(chat.add)` und ruft `start()`, `submit(text)`, `emergency_stop()` und `close()` auf.
- `src/robot_mcp_server.py` und `src/robot_tools.py`: die Werkzeuge `get_robot_state`, `look`, `list_cameras`, `list_waypoints`, `go_to_waypoint`, `nudge_joint`, `set_gripper`, `enable_torque`, `stop`, `teach_waypoint`. Darin liegen alle Sicherheitsgrenzen: der Bewegungsschalter `ELROBOT_ALLOW_MOTION`, die Begrenzung auf den kalibrierten Bereich, die Geschwindigkeitsgrenze, Nudges bis 5 %, höchstens 1500 Schritte pro Abschnitt und der Überlastschutz.
- `config/elrobot.json` (joint_map, gripper, cameras, agent-Grenzen, workspace) und `config/waypoints.json`.
- `agent.py` im Repo-Wurzelordner: **nur als Vorlage**. Ein Greif-Agent aus einer MuJoCo-Simulation, der hier nicht lauffähig ist (`sim.py` fehlt). Nicht ändern, nicht ausführen, nicht committen. Übernimm daraus diese Muster:
  - genau ein Werkzeug pro Antwort, davor ein Satz, was zu sehen ist und warum dieser Schritt;
  - ein Abschluss-Werkzeug (`fertig` mit `gegriffen` und `begruendung`);
  - eine unabhängige Prüfung, ob das Ziel wirklich erreicht ist ("Claudes Einschätzung" gegen "Physik"; hier gegen eine zweite Bildauswertung, siehe unten);
  - eine Rundengrenze mit Meldung, wenn sie erreicht ist;
  - Token-Zählung und eine Zusammenfassung am Ende;
  - saubere Fehlerbehandlung der API (Authentifizierung, Verbindung, Status).

## Was der Agent tun soll

Neues Modul `src/goal_agent.py` mit einer Klasse `GoalAgent`, die dieselbe Schnittstelle wie `ConsoleAgent` hat (`start`, `submit`, `emergency_stop`, `close`). Den MCP-Start (`load_mcp_server_config`, Session) und die Stopp-Logik von `ConsoleAgent` wiederverwenden, nicht kopieren. Jede Chat-Nachricht, die kein Stoppwort ist, ist ein neues **Ziel**. Ein neues Ziel während eines laufenden Ziels bricht das alte ab und meldet das im Chat.

Pro Iteration (`1 … MAX_ITERATIONS`):

1. **Bilder auswerten.** Alle live Kameras holen: `list_cameras`, dann `look` für jede, mit Namen (`table`, `gripper`) oder Queue-ID für Kameras ohne Namen. Jedes Bild geht in einem **eigenen Claude-API-Aufruf** an ein Vision-Modell, gern parallel. Ergebnis ist pro Kamera eine **textuelle Beschreibung**: welche Objekte wo (relativ zu Arm, Greifer und Tischkanten), Lage des Greifers, ob etwas im Greifer ist, Hindernisse, Personen, Unsicherheiten. Das Ziel geht mit in den Aufruf, damit die Beschreibung darauf achtet. Kann eine Kamera kein Bild liefern oder ist es älter als 2 s, steht das als Text in der Beschreibung.
2. **Konfiguration als ein Objekt.** Ein JSON-Objekt `robot` mit allem, was zum Planen nötig ist:
   - `state`: Ergebnis von `get_robot_state` (Gelenke in % und roh, Torque, Strom, Fehler, Greiferöffnung, nächster Wegpunkt);
   - `waypoints`: Ergebnis von `list_waypoints`;
   - `config`: die relevanten Teile von `config/elrobot.json` (`joint_map`, `gripper`, `agent`-Grenzen, `workspace`, `cameras`);
   - `motion_allowed`;
   - `cameras`: die Beschreibungen aus Schritt 1, nach Kamera;
   - `iteration` und `max_iterations`;
   - `last_action` mit Ergebnis (inklusive `dry_run`, Fehlern, Überlast).
3. **Nächsten Schritt planen.** Ein Planungs-Aufruf an Claude bekommt das Ziel, das Objekt `robot` und eine **kompakte** Historie der bisherigen Schritte (Aktion, Ergebnis, Kurzfassung der Beschreibungen; nur die letzten N vollständig, damit der Kontext nicht wächst). Der Planer sieht **keine Rohbilder**, nur die Texte. Er ruft genau ein Werkzeug auf:
   - ein Bewegungswerkzeug des MCP-Servers (`go_to_waypoint`, `nudge_joint`, `set_gripper`, `enable_torque`);
   - `ziel_erreicht(begruendung)`;
   - `aufgeben(begruendung)`, wenn das Ziel mit den vorhandenen Wegpunkten nicht erreichbar ist oder dieselbe Aktion zweimal gescheitert ist;
   - `frage_stellen(frage)`, wenn das Ziel mehrdeutig ist. Dann pausiert der Agent; die nächste Chat-Nachricht ist die Antwort und setzt dasselbe Ziel fort.

   `teach_waypoint` und `stop` bekommt der Planer nicht. Vor dem Werkzeugaufruf schreibt er einen Satz: was er sieht und warum dieser Schritt.
4. **Ausführen.** Das Werkzeug über die MCP-Session aufrufen. Ergebnis als `last_action` merken. Meldet das Ergebnis `dry_run`, weil Bewegungen ausgeschaltet sind, beendet der Agent das Ziel sofort mit dem Hinweis auf `ELROBOT_ALLOW_MOTION`. Er schleift dann nicht weiter.
5. **Ziel prüfen.** Ruft der Planer `ziel_erreicht`, macht der Agent einen **unabhängigen Prüf-Aufruf**: neue Bilder aller Kameras plus Ziel, mit der Frage "Ist das Ziel erreicht? Ja/Nein mit Begründung", als strukturierte Ausgabe. Nur bei "Ja" endet das Ziel erfolgreich. Bei "Nein" geht die Begründung als `last_action` zurück, und die Schleife läuft weiter. Widersprechen sich Planer und Prüfer, steht das deutlich im Chat (wie "ACHTUNG" in `agent.py`).

**Abbruch:** Ziel erreicht und bestätigt, `aufgeben`, `MAX_ITERATIONS` überschritten, Stoppwort oder STOP-Button (bricht sofort ab und ruft `stop`), ein neues Ziel, ein API-Fehler oder `dry_run`. In jedem Fall gibt es eine Abschlussmeldung im Chat: Ergebnis, Anzahl der Iterationen, Tokens (Vision, Planung, Prüfung getrennt).

## Chat-Ausgabe

Pro Iteration kurz und lesbar: `Schritt 3/20`, je Kamera ein bis zwei Sätze Beschreibung, der Plan-Satz, das Werkzeug mit Parametern und das Ergebnis. Die vollständigen Beschreibungen und Objekte gehen ins Log (`logs/`), nicht in den Chat.

## Einstellungen

Konstanten oben im Modul, überschreibbar per Umgebungsvariable:
- `MAX_ITERATIONS` (Standard 20);
- Modelle für Vision, Planung und Prüfung (Standard `claude-opus-5-5`, wie `WEB_CONSOLE_MODEL`);
- `MAX_TOKENS`;
- Anzahl der vollständig behaltenen Historien-Schritte.

Die Konsole nutzt standardmäßig `GoalAgent`. Mit `./cli.sh console --agent chat` lässt sich der alte `ConsoleAgent` wählen. In `web_console.py` und `cli.sh` umsetzen, Hilfetext anpassen.

## Sicherheit (nicht verhandelbar)

- Bewegung nur über die MCP-Werkzeuge, kein direkter Hardware-Zugriff, keine neuen Bewegungswege. Alle Grenzen des MCP-Servers gelten unverändert.
- `ELROBOT_ALLOW_MOTION` nicht anfassen, nicht umgehen, `.mcp.json` nicht ändern. Die Datei ist lokal gerade geändert; nicht committen.
- Stoppwörter und STOP-Button müssen jederzeit sofort wirken, auch während der Bild-Auswertung oder einer laufenden API-Anfrage. Laufende Aufrufe abbrechen, dann `stop`.
- Der Planer bewegt nichts, wenn ein benötigtes Objekt in keiner Beschreibung vorkommt, ein Wegpunkt fehlt oder eine Kamera ausgefallen ist, die er braucht. Dann `frage_stellen` oder `aufgeben`.
- API-Keys nie ausgeben oder loggen.

## Tests und Abschluss

- `tests/test_goal_agent.py` mit einem gefälschten Anthropic-Client und einer gefälschten MCP-Session, ohne Netz und ohne Arm:
  - Ziel erreicht und vom Prüfer bestätigt → Ende mit Erfolg;
  - Prüfer sagt "Nein" → die Schleife läuft weiter;
  - `MAX_ITERATIONS` → Ende mit Meldung;
  - `aufgeben` und `frage_stellen` (Pause und Fortsetzung);
  - `dry_run` → sofortiges Ende mit Hinweis;
  - STOP während einer Bild-Auswertung → Abbruch und `stop` wurde aufgerufen;
  - Kamera ohne Bild → steht in der Beschreibung, kein Absturz;
  - das Objekt `robot` enthält alle oben genannten Felder.
- `.venv/bin/python -m pytest tests/` muss grün sein.
- Manuell mit Bewegungen **aus**: Konsole starten, Ziel eingeben, Bildbeschreibungen und Plan im Chat prüfen. Der Agent endet beim ersten `dry_run` mit Hinweis. Mit Bewegungen **an** nur, wenn ich dabei bin. Vorher fragen.
- `docs/mcp_server.md` (Abschnitt Web-Konsole) um den Ziel-Agenten ergänzen. Nach `AGENTS.md` `.ai-sync/HANDOFF.md` und `PROGRESS.md` aktualisieren, ein Commit pro Änderung, nichts pushen.
