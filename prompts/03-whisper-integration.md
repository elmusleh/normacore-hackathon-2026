# Prompt: Spracheingabe der Web-Konsole auf OpenAI gpt-transcribe umstellen

Alles unterhalb der Linie in Claude Code einfügen, geöffnet im Repo `carearm-feeding-robot`.

---

Die Web-Konsole (`./cli.sh console`, http://localhost:8890) transkribiert Spracheingaben heute lokal mit faster-whisper. Ersetze das durch die OpenAI-Transkription, die `src/speech.py` verwendet. Bedienung und Ablauf der Seite bleiben unverändert.

## Ausgangslage

- **Server:** `src/web_console.py`. Die Klasse `SpeechToText` lädt faster-whisper im Hintergrund (Status `idle`/`loading`/`ready`/`error`). `transcribe(audio: bytes)` bekommt die Browser-Aufnahme (webm/ogg/wav), `_decode_audio` wandelt sie mit PyAV in 16-kHz-Mono um. Die Endpunkte `/api/stt` (Status) und `/api/transcribe` (POST mit den Audio-Bytes, Antwort `{"ok", "text", "seconds"}`) bleiben in ihrer Form erhalten.
- **Seite:** `src/web/console.html`. Push-to-talk: Mikrofon-Button klicken oder Leertaste halten, `MediaRecorder` nimmt auf und schickt die Aufnahme an `/api/transcribe`. Meldet `/api/stt` nicht `ready`, fällt die Seite auf die Spracherkennung des Browsers zurück.
- **Vorlage:** `src/speech.py`, die Funktion `transcribe(path)`: OpenAI-Client (`timeout=15.0, max_retries=1`), `client.audio.transcriptions.create(model="gpt-transcribe", file=..., languages=["de", "en"], keywords=[...])`. Übernimm genau diesen Aufruf mit Modell, Sprachen und Keywords.

## Was zu tun ist

1. **Backend tauschen.** `SpeechToText` ruft gpt-transcribe auf wie in `speech.py`, statt faster-whisper zu laden.
   - Nutze den Aufruf aus `speech.py` wieder (importieren oder in eine gemeinsame Funktion auslagern), statt ihn zu kopieren. Das Verhalten von `speech.py` als eigenständiges CLI darf sich dabei nicht ändern.
   - Wandle die Browser-Aufnahme vor dem Senden in eine WAV-Datei (16 kHz, mono, 16 bit) um, wie `speech.py` sie schreibt. Die vorhandene PyAV-Dekodierung kannst du dafür weiterverwenden. Hängt PyAV bisher nur über faster-whisper mit dran, trag `av` direkt in `requirements.txt` ein.
   - Keywords: die Liste aus `speech.py`, ergänzt um die Begriffe aus `DEFAULT_STT_PROMPT` (die Demo-Speisen und -Befehle). Die Umgebungsvariable `WEB_CONSOLE_STT_PROMPT` entfällt oder wird zu einer Keyword-Liste umgedeutet. Entscheide dich und dokumentiere es.
2. **Status.** Es gibt kein Modell mehr zu laden. Ist `OPENAI_API_KEY` gesetzt, ist der Status sofort `ready`. Fehlt er, ist er `error` mit einer klaren Meldung, und die Seite fällt wie bisher auf die Browser-Spracherkennung zurück. Die Felder `model` und `device` in `/api/stt` sind weiter befüllt (z. B. `model: "gpt-transcribe"`, `device: "openai"`).
3. **API-Key.** `OPENAI_API_KEY` steht in `.env`, und `./cli.sh console` lädt `.env` bereits. Lies den Key nur aus der Umgebung. Übernimm nicht den Fallback auf die Datei `keys` aus `speech.py`. Gib den Key nie aus, auch nicht in Logs oder Fehlermeldungen, und öffne oder ändere `.env` nicht.
4. **Seite anpassen** (`console.html`), nur bei den Texten:
   - Die Engine-Anzeige nennt sinngemäß "OpenAI gpt-transcribe (sends audio to OpenAI)" statt "Local speech-to-text (… GPU/CPU)".
   - Die Fehlermeldung "install faster-whisper" wird zu einem Hinweis auf `OPENAI_API_KEY` in `.env`.
   - Der Lade-Zustand ("Loading speech model…") darf bleiben, wird aber praktisch nicht mehr angezeigt.
5. **Aufräumen.**
   - faster-whisper aus `requirements.txt` und dem Code entfernen, `openai` hinzufügen.
   - `--no-stt` behalten (Browser-Erkennung erzwingen).
   - `WEB_CONSOLE_STT_MODEL` darf das OpenAI-Modell überschreiben, Standard `gpt-transcribe`.
   - Den Docstring von `web_console.py` und die Sprache-Abschnitte in `docs/mcp_server.md` aktualisieren.

## Nicht übernehmen

Aus `speech.py` kommt nur der Transkriptionsaufruf. Nicht übernommen wird:
- das Aktivierungswort "Robo" samt Varianten, dem Folgefenster und `parse_command`;
- die Stoppwörter "Stopp"/"Stop"/"Halt" mit Pause-Zustand und "Robo, weiter";
- das Dauerzuhören mit silero-vad und sounddevice.

Die Konsole bleibt Push-to-talk. Jede Aufnahme geht als Ganzes in den Chat. Das bestehende Anhalten bleibt, wie es ist: "stop" im Chat und der Stop-Button.

## Tests und Abschluss

- `tests/test_web_console.py` anpassen bzw. ergänzen:
  - Status `ready` mit gesetztem Key und `error` ohne Key (per `monkeypatch`).
  - `/api/transcribe` mit einem gemockten OpenAI-Client: Prüfe, dass Modell, `languages` und `keywords` übergeben werden und WAV gesendet wird.
  - Tests dürfen nie das Netz oder die echte API benutzen.
- Prüfe gegen die installierte `openai`-Version, dass `transcriptions.create` die Parameter `languages` und `keywords` so akzeptiert wie in `speech.py`. Weicht die API ab, frag mich, bevor du etwas umbaust.
- `.venv/bin/python -m pytest tests/` muss grün sein.
- Manuell: `./cli.sh console` starten. Die Seite zeigt die OpenAI-Engine, und ein gesprochener Satz erscheint im Chat. Ohne Key fällt die Seite auf die Browser-Erkennung zurück.
- Halte dich an `AGENTS.md`: `.ai-sync/HANDOFF.md` und `PROGRESS.md` aktualisieren, ein Commit pro Änderung. Nichts pushen.
