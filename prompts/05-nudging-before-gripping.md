# Prompt: Nachjustieren vor dem Greifen und Greifprüfung danach

Alles unterhalb der Linie in Claude Code einfügen, geöffnet im Repo `normacore-hackathon-2026` (Branch `jan`).

---

Die Fütterungsabläufe sind heute starr: Claude wählt zum Essen einen aufgenommenen Ablauf und spielt ihn mit `play_sequence(name)` in einem Zug ab. Liegt die Traube etwa 1 cm neben der aufgenommenen Stelle, greift der Arm daneben und bringt einen leeren Greifer zum Mund, ohne es zu merken. Baue zwei Verbesserungen ein, mit dem bestehenden **Chat-Agenten** (`src/console_agent.py`). Einen neuen Agenten gibt es nicht.

1. **Nachjustieren vor dem Greifen:** Der Ablauf hält offen über dem Essen an. Claude schaut in die Greiferkamera und korrigiert mit kleinen Drehungen der Basis, bis das Essen mittig zwischen den Backen liegt.
2. **Greifprüfung nach dem Zugreifen:** Erst danach schließt der Greifer. `set_gripper` meldet `holding_object` oder `closed_empty`, dazu kommt ein Blick in die Greiferkamera. Nur wenn etwas im Greifer ist, geht es weiter zum Mund. Sonst Greifer auf, zurück in eine sichere Pose, der Person Bescheid sagen und höchstens einen zweiten Versuch machen.

## Ausgangslage (bitte zuerst lesen)

- `src/console_agent.py` (`CONSOLE_PROMPT`) und `src/robot_mcp_server.py` (Server-`INSTRUCTIONS` und Werkzeuge). Die Anweisungen sagen heute: "Recorded feeding plans come first … run play_sequence(name) once … Do not add moves before or after it, and do not rebuild a plan from single waypoints." Das muss für Essen mit Greifprüfung geändert werden.
- `src/robot_tools.py`: `list_sequences`, `play_sequence(name)`, `set_gripper` (Ergebnis `holding_object` / `closed_empty` / `blocked`, Warnung bei `gripper.verified=false`), `nudge_joint` (höchstens `agent.max_nudge_percent` = 5 % pro Aufruf), `look`, `stop_now` (unterbricht auch laufende Abläufe).
- `src/sequence_player.py`: `plan_legs`, `run_legs` (Hinderniswächter, "near"-Toleranz, Pause, Abbruch über das Stop-Ereignis).
- `config/elrobot.json` (`foods`, `agent`, `gripper`, `joint_map` ist noch **leer**), `config/sequences.json`, `config/waypoints.json`.
- Ablauf `grapes`: `start_position → start_2 → grape_open → grape_close → feed_1 → feed_2 → feed_3 → feed_stop → reset`.

## Offene Fakten, die du zuerst klären musst (nicht raten)

- **`grape_open` und `grape_close` sind in `config/waypoints.json` identisch** (alle 8 Motoren gleich, Greifer bei 1847). Der Greifer geht schon auf dem Weg von `start_2` (Greifer 2487) nach `grape_open` zu, also gleichzeitig mit dem Absenken. Eine Pose "offen über dem Essen" gibt es in dieser Aufnahme nicht. **Frag mich**, ob wir die Posen neu aufnehmen. Mein Vorschlag: `grape_hover` (offen, über der Traube), `grape_open` (offen, Backen um die Traube), danach schließen per `set_gripper`. Ohne eine offene Pose vor dem Schließen lässt sich nichts nachjustieren.
- **Greiferrichtung:** `gripper.open_at` ist nicht bestätigt (`verified: false`). Vor jeder Greifprüfung muss das mit `./cli.sh hw identify 8` geprüft und in der Config auf `verified: true` gesetzt sein.
- **Basis-Motor und Richtung:** `joint_map` ist leer. Mit `./cli.sh hw identify 1` (oder dem Motor, der die Basis dreht) bestimmen, welcher Motor die Basis dreht und in welche Richtung "+" geht. Das mache ich am Arm, du gibst mir die Befehle.
- **Kamera-Richtung:** In welche Richtung wandert das Essen im Bild der Greiferkamera, wenn die Basis um "+" dreht? Das bestimmen wir einmal am Arm (Pose `grape_open`, `nudge` +2 %, Bild vorher und nachher vergleichen) und speichern es in der Config. So muss Claude die Richtung nicht jedes Mal neu erraten.

## Was zu bauen ist

### 1. Abläufe teilen (Code, deterministisch)

- `play_sequence(name, start_at=None, stop_after=None)`: optional nur einen Teil des Ablaufs spielen, mit den gleichen Prüfungen wie heute. Unbekannte Schrittnamen oder `start_at` nach `stop_after` ergeben einen Fehler. Ohne die Parameter verhält sich alles wie bisher, auch `./cli.sh hw play`.
- In `config/elrobot.json` bekommt ein Essen optional einen Greifabschnitt, zum Beispiel:
  ```json
  "grapes": {
    "sequence": "grapes",
    "grasp": {"approach": "grape_open", "close_percent": 30, "continue_at": "feed_1"},
    "note": "..."
  }
  ```
  `approach` ist die letzte Pose mit **offenem** Greifer über bzw. um das Essen. `continue_at` ist der erste Schritt nach dem Greifen. Essen ohne `grasp` laufen weiter in einem Zug. `list_sequences` zeigt `grasp` mit an und prüft, dass `approach` vor `continue_at` liegt.
- **Falle:** Nach dem Nachjustieren **nicht** die Greif-Pose (`grape_close`) anfahren. Sie würde die Korrektur rückgängig machen, weil der Wegpunkt die alte Basisstellung enthält. Geschlossen wird mit `set_gripper(close_percent)`, dann geht es direkt mit `continue_at` weiter. Die erste Bewegung startet dann von der korrigierten Stellung aus; die Planprüfung (Schrittgrenze, Klemmen) muss dabei greifen.

### 2. Begrenztes Nachjustieren (Code erzwingt die Grenzen, Claude entscheidet)

Neues MCP-Werkzeug `align_base(delta_percent)`:
- dreht nur den in der Config hinterlegten Basis-Motor (`grasp_alignment.motor`);
- höchstens 2 % pro Aufruf;
- in Summe höchstens ±6 % seit dem letzten `play_sequence(..., stop_after=approach)`;
- nur erlaubt, wenn der Arm an der `approach`-Pose steht (Toleranz wie `AT_WAYPOINT_TOLERANCE`);
- gibt die bisherige Summe zurück;
- alle Werte in `config/elrobot.json` unter `agent` / `grasp_alignment`;
- `stop` wirkt wie überall.

So bleibt die Schleife beim Agenten ("schauen → kleiner Schritt → schauen"), aber die Grenzen sind fest im Code.

### 3. Greifprüfung

Nach `set_gripper(close_percent)` zählt der Griff nur, wenn **beides** stimmt: das Ergebnis ist `holding_object`, **und** `look("gripper")` zeigt das Essen zwischen den Backen. Widersprechen sich die beiden, gilt der Griff als **leer**. Bei einer kleinen, weichen Traube ist die Strommessung womöglich unzuverlässig. Prüfe das am Arm: einmal ins Leere schließen, einmal auf die Traube, und notiere die Ergebnisse im Handoff.

### 4. Anweisungen für Claude

Passe `INSTRUCTIONS` in `robot_mcp_server.py` und `CONSOLE_PROMPT` an. Für ein Essen mit `grasp`:
1. `play_sequence(food_plan, stop_after=approach)`
2. `look("gripper")`. Liegt das Essen nicht mittig zwischen den Backen: `align_base` in kleinen Schritten, nach jedem Schritt wieder `look("gripper")`. Höchstens 3 Korrekturen. Liegt es dann noch nicht mittig, nicht greifen: der Person sagen, was zu sehen ist.
3. `set_gripper(close_percent)`, dann `look("gripper")`.
4. Gehalten: `play_sequence(food_plan, start_at=continue_at)`, also der Rest bis zum Mund und zurück.
5. Leer: `set_gripper(100)`, dann in eine sichere Pose (`play_sequence(food_plan, start_at=…)` nur, wenn der Ablauf dafür einen Schritt hat; sonst `go_to_waypoint("clear")`). Der Person kurz sagen, dass der Griff verfehlt wurde. **Höchstens einen** zweiten Versuch, ab Schritt 1. Danach aufhören und fragen.

Essen ohne `grasp` laufen unverändert in einem Zug. Nie einen leeren Greifer zum Mund fahren.

## Sicherheit (nicht verhandelbar)

- Alle bestehenden Grenzen bleiben: Bewegungsschalter, Begrenzung auf den kalibrierten Bereich, Geschwindigkeit, Überlastwächter, Prüfung auf laufende Teleoperation, `stop` jederzeit.
- `align_base` niemals außerhalb der `approach`-Pose, niemals ein anderer Motor, keine Summe über das Limit.
- Bewegungen am echten Arm nur, wenn ich dabei bin und die Hand am Netzschalter habe. **Vorher fragen.** Erst trocken testen (`ELROBOT_ALLOW_MOTION` "0", nur für den Test lokal, nicht committen), dann mit Bewegung.
- `.mcp.json` nicht committen, wenn du sie für einen Test änderst.

## Tests und Abschluss

- `tests/test_robot_mcp.py` / `tests/test_hw_day.py` mit dem vorhandenen `FakeArm`:
  - Teilabläufe (`start_at`, `stop_after`, ungültige Namen, unverändertes Verhalten ohne Parameter);
  - `align_base`: nur Basis-Motor, Grenze pro Aufruf, Grenze in Summe, nur an der `approach`-Pose, Rücksetzen beim nächsten Ablauf, Bewegung aus → `dry_run`;
  - `list_sequences` zeigt `grasp` und meldet eine falsche Reihenfolge.
- `tests/test_console_agent.py`: Der Prompt enthält den neuen Ablauf. Optional ein Durchlauf mit gefälschtem Claude: Ablauf-Teil 1 → `look` → `align_base` → `set_gripper` meldet `closed_empty` → kein Aufruf mit `start_at=continue_at`.
- `.venv/bin/python -m pytest tests/` grün.
- Am Arm, mit mir zusammen:
  1. Basis-Motor und Kamera-Richtung bestimmen;
  2. Traube genau an der aufgenommenen Stelle: greift ohne Korrektur;
  3. Traube 1 cm nach links, dann 1 cm nach rechts: Claude korrigiert und greift;
  4. Traube weg: Claude erkennt den leeren Griff und fährt **nicht** zum Mund.
- `docs/mcp_server.md` und `docs/elrobot_hardware_bridge.md` ergänzen. Nach `AGENTS.md` `.ai-sync/HANDOFF.md` und `PROGRESS.md` aktualisieren, ein Commit pro Änderung, nichts pushen.
