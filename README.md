# EDG Abfallkalender Dortmund für Home Assistant

Custom Integration, die die Abfuhrtermine der EDG Entsorgung Dortmund
für deine Adresse in Home Assistant anzeigt. Die Daten kommen aus dem
EDG-Kundenportal (dasselbe wie unter <https://www.edg.de/abfallkalender>).

Die Integration läuft lokal in deinem Home Assistant. Kein Cloud-Konto
und kein Zusatzdienst ist nötig. Nur die Termine werden alle 12 Stunden
beim EDG-Portal abgefragt.

## Was du bekommst

Pro Adresse ein Gerät „EDG Abfall <Straße Nr>“ mit:

| Entität | Inhalt |
|---|---|
| `sensor.…_restabfall`, `…_wertstoffe`, `…_bioabfall`, `…_altpapier` | Datum der nächsten Leerung (je nach Adresse nur die Tonnen, die es dort gibt) |
| `sensor.…_next_collection` („Nächste Abholung“) | nächster Termin überhaupt und welche Tonne(n) |
| `calendar.…_waste_calendar` („Abfallkalender“) | alle Termine als ganztägige Ereignisse |

Attribute der Tonnen-Sensoren: `days_until` (Tage bis zur Leerung),
`upcoming` (alle kommenden Termine), `frequency`, `bin_size`.

## Installation

Die Integration ist der Ordner `custom_components/edg_dortmund`. Er muss
auf deinem Home-Assistant-Gerät nach `/config/custom_components/edg_dortmund`.

### Variante A: Samba-Freigabe (am einfachsten von Windows aus)

1. In Home Assistant: **Einstellungen → Apps (Add-ons) → App-Store** →
   „Samba share“ installieren, Benutzer und Passwort setzen, starten.
2. Im Windows-Explorer `\\homeassistant.local\config` öffnen
   (oder `\\<IP-deines-HA>\config`).
3. Dort ggf. den Ordner `custom_components` anlegen und
   `edg_dortmund` hineinkopieren.
4. Home Assistant neu starten (**Einstellungen → System → Neu starten**).

### Variante B: Studio Code Server / File editor im Browser

App „Studio Code Server“ installieren, öffnen, den Ordner
`custom_components/edg_dortmund` per Drag-and-drop nach
`/config/custom_components/` ziehen, Home Assistant neu starten.

### Variante C: SSH

Mit der App „Terminal & SSH“:

```bash
scp -r custom_components/edg_dortmund root@homeassistant.local:/config/custom_components/
```

Danach Home Assistant neu starten.

### Variante D: HACS (für Updates per Klick)

Diesen Ordner als GitHub-Repository veröffentlichen, dann in HACS:
**⋮ → Benutzerdefinierte Repositories** → Repo-URL, Typ „Integration“
→ „EDG Abfallkalender Dortmund“ herunterladen → neu starten.

## Einrichten

**Einstellungen → Geräte & Dienste → Integration hinzufügen →
„EDG Abfallkalender Dortmund“**, dann Straße und Hausnummer eingeben.

- „Hohe Straße“, „Hohe Str.“ und „hohe strasse“ funktionieren gleich.
- Passen mehrere Straßen, kommt eine Auswahlliste.
- Ist die Hausnummer im Portal anders hinterlegt (z. B. „11 -13“),
  kommt eine Liste der Hausnummern zum Auswählen.

Für mehrere Adressen die Integration einfach mehrmals hinzufügen.

## Beispiel: Erinnerung am Vorabend

```yaml
automation:
  - alias: Mülltonne rausstellen
    triggers:
      - trigger: time
        at: "19:00:00"
    conditions:
      - condition: template
        value_template: >
          {{ state_attr('sensor.edg_abfall_baackweg_1_next_collection', 'days_until') == 1 }}
    actions:
      - action: notify.notify
        data:
          message: >
            Morgen: {{ state_attr('sensor.edg_abfall_baackweg_1_next_collection', 'types') | join(', ') }}
```

Die Entity-IDs hängen von deiner Adresse ab. Du findest sie unter
**Einstellungen → Geräte & Dienste → EDG Abfallkalender**.

## Grenzen

- Das EDG-Portal zeigt Termine nur bis zum Jahresende. Neue Termine
  erscheinen automatisch, sobald die EDG sie veröffentlicht.
- Es gibt keine offizielle API. Ändert die EDG ihr Portal, kann die
  Integration angepasst werden müssen.

## Tests

Die Tests in `tests/` laufen live gegen das EDG-Portal (Linux/WSL,
weil Home Assistant nicht nativ unter Windows läuft):

```bash
pip install pytest-homeassistant-custom-component
pytest tests
```
