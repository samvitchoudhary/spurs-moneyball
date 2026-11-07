# Data source probe

Premier League 2025-26 player-season stats only. soccerdata 2026.43.0.

## Summary

| source | works? | attacking | passing | defensive | xG available | notes |
| --- | --- | --- | --- | --- | --- | --- |
| FBref | yes | yes | no | yes | no | standard, shooting, playing_time, misc, and keeper return data (551, 551, 693, 551, and 40 rows; the combined count is the sum, not unique players). passing, passing_types, defense, possession, and gca are rejected. Shots are present. No xG, xA, key passes, progressive passes, or pass completion. Defensive stats are only interceptions and tackles won on misc — no blocks, clearances, or aerials. |
| FotMob | no | no | no | no | no | soccerdata 2026.43.0 does not export FotMob. The 1.9.0 release removed the FotMob scraper. |
| Sofascore | no | no | no | no | no | Sofascore exposes league table and schedule only. No player-season method, so nothing was downloaded. |
| WhoScored | no | no | no | no | no | WhoScored subclasses BaseSeleniumReader and needs Chrome via Selenium. No player-season method (schedule, events, and missing players only). Browser was not launched and nothing was installed. |
| Understat | no | no | no | no | no | Retry still fails. /getStatData returns the HTML page 'We will come back soon', which is not JSON. |

## FBref

- Status: works
- Rows: 2386
- Coverage: attacking yes, passing no, defensive yes, xG no
- Notes: standard, shooting, playing_time, misc, and keeper return data (551, 551, 693, 551, and 40 rows; the combined count is the sum, not unique players). passing, passing_types, defense, possession, and gca are rejected. Shots are present. No xG, xA, key passes, progressive passes, or pass completion. Defensive stats are only interceptions and tackles won on misc — no blocks, clearances, or aerials.
- Columns with real values:
  - `90s`
  - `Penalty Kicks | PKA`
  - `Penalty Kicks | PKatt`
  - `Penalty Kicks | PKm`
  - `Penalty Kicks | PKsv`
  - `Penalty Kicks | Save%`
  - `Per 90 Minutes | Ast`
  - `Per 90 Minutes | G+A`
  - `Per 90 Minutes | G+A-PK`
  - `Per 90 Minutes | G-PK`
  - `Per 90 Minutes | Gls`
  - `Performance | 2CrdY`
  - `Performance | Ast`
  - `Performance | CS`
  - `Performance | CS%`
  - `Performance | CrdR`
  - `Performance | CrdY`
  - `Performance | Crs`
  - `Performance | D`
  - `Performance | Fld`
  - `Performance | Fls`
  - `Performance | G+A`
  - `Performance | G-PK`
  - `Performance | GA`
  - `Performance | GA90`
  - `Performance | Gls`
  - `Performance | Int`
  - `Performance | L`
  - `Performance | OG`
  - `Performance | Off`
  - `Performance | PK`
  - `Performance | PKatt`
  - `Performance | Save%`
  - `Performance | Saves`
  - `Performance | SoTA`
  - `Performance | TklW`
  - `Performance | W`
  - `Playing Time | 90s`
  - `Playing Time | MP`
  - `Playing Time | Min`
  - `Playing Time | Min%`
  - `Playing Time | Mn/MP`
  - `Playing Time | Starts`
  - `Standard | G/Sh`
  - `Standard | G/SoT`
  - `Standard | Gls`
  - `Standard | PK`
  - `Standard | PKatt`
  - `Standard | Sh`
  - `Standard | Sh/90`
  - `Standard | SoT`
  - `Standard | SoT%`
  - `Standard | SoT/90`
  - `Starts | Compl`
  - `Starts | Mn/Start`
  - `Starts | Starts`
  - `Subs | Mn/Sub`
  - `Subs | Subs`
  - `Subs | unSub`
  - `Team Success | +/-`
  - `Team Success | +/-90`
  - `Team Success | On-Off`
  - `Team Success | PPM`
  - `Team Success | onG`
  - `Team Success | onGA`
  - `age`
  - `born`
  - `nation`
  - `pos`

Tottenham sample:

```
('ENG-Premier League', '2526', 'Tottenham', 'Antonín Kinský')
{
  "nation": "CZE",
  "pos": "GK",
  "age": "22",
  "born": "2003",
  "Playing Time | MP": "7",
  "Playing Time | Starts": "7",
  "Playing Time | Min": "630",
  "Playing Time | 90s": 7.0,
  "Performance | Gls": "0",
  "Performance | Ast": "0",
  "Performance | G+A": "0",
  "Performance | G-PK": "0",
  "Performance | PK": "0",
  "Performance | PKatt": "0",
  "Performance | CrdY": "1",
  "Performance | CrdR": "0",
  "Per 90 Minutes | Gls": 0.0,
  "Per 90 Minutes | Ast": 0.0,
  "Per 90 Minutes | G+A": 0.0,
  "Per 90 Minutes | G-PK": 0.0,
  "Per 90 Minutes | G+A-PK": 0.0
}
```

### standard

- Status: works
- Rows: 551
- Coverage: attacking no, passing no, defensive no, xG no
- Columns with real values:
  - `nation`
  - `pos`
  - `age`
  - `born`
  - `Playing Time | MP`
  - `Playing Time | Starts`
  - `Playing Time | Min`
  - `Playing Time | 90s`
  - `Performance | Gls`
  - `Performance | Ast`
  - `Performance | G+A`
  - `Performance | G-PK`
  - `Performance | PK`
  - `Performance | PKatt`
  - `Performance | CrdY`
  - `Performance | CrdR`
  - `Per 90 Minutes | Gls`
  - `Per 90 Minutes | Ast`
  - `Per 90 Minutes | G+A`
  - `Per 90 Minutes | G-PK`
  - `Per 90 Minutes | G+A-PK`

```
('ENG-Premier League', '2526', 'Tottenham', 'Antonín Kinský')
{
  "nation": "CZE",
  "pos": "GK",
  "age": "22",
  "born": "2003",
  "Playing Time | MP": "7",
  "Playing Time | Starts": "7",
  "Playing Time | Min": "630",
  "Playing Time | 90s": 7.0,
  "Performance | Gls": "0",
  "Performance | Ast": "0",
  "Performance | G+A": "0",
  "Performance | G-PK": "0",
  "Performance | PK": "0",
  "Performance | PKatt": "0",
  "Performance | CrdY": "1",
  "Performance | CrdR": "0",
  "Per 90 Minutes | Gls": 0.0,
  "Per 90 Minutes | Ast": 0.0,
  "Per 90 Minutes | G+A": 0.0,
  "Per 90 Minutes | G-PK": 0.0,
  "Per 90 Minutes | G+A-PK": 0.0
}
```

### shooting

- Status: works
- Rows: 551
- Coverage: attacking yes, passing no, defensive no, xG no
- Columns with real values:
  - `nation`
  - `pos`
  - `age`
  - `born`
  - `90s`
  - `Standard | Gls`
  - `Standard | Sh`
  - `Standard | SoT`
  - `Standard | SoT%`
  - `Standard | Sh/90`
  - `Standard | SoT/90`
  - `Standard | G/Sh`
  - `Standard | G/SoT`
  - `Standard | PK`
  - `Standard | PKatt`

```
('ENG-Premier League', '2526', 'Tottenham', 'Antonín Kinský')
{
  "nation": "CZE",
  "pos": "GK",
  "age": "22",
  "born": "2003",
  "90s": 7.0,
  "Standard | Gls": "0",
  "Standard | Sh": "0",
  "Standard | SoT": "0",
  "Standard | Sh/90": 0.0,
  "Standard | SoT/90": 0.0,
  "Standard | PK": "0",
  "Standard | PKatt": "0"
}
```

### passing

- Status: fails
- Error: Invalid argument: stat_type should be in ['standard', 'keeper', 'shooting', 'playing_time', 'misc']
- Rows: 0
- Coverage: attacking no, passing no, defensive no, xG no
- Columns with real values:
  - (none)

### passing_types

- Status: fails
- Error: Invalid argument: stat_type should be in ['standard', 'keeper', 'shooting', 'playing_time', 'misc']
- Rows: 0
- Coverage: attacking no, passing no, defensive no, xG no
- Columns with real values:
  - (none)

### defense

- Status: fails
- Error: Invalid argument: stat_type should be in ['standard', 'keeper', 'shooting', 'playing_time', 'misc']
- Rows: 0
- Coverage: attacking no, passing no, defensive no, xG no
- Columns with real values:
  - (none)

### possession

- Status: fails
- Error: Invalid argument: stat_type should be in ['standard', 'keeper', 'shooting', 'playing_time', 'misc']
- Rows: 0
- Coverage: attacking no, passing no, defensive no, xG no
- Columns with real values:
  - (none)

### misc

- Status: works
- Rows: 551
- Coverage: attacking no, passing no, defensive yes, xG no
- Columns with real values:
  - `nation`
  - `pos`
  - `age`
  - `born`
  - `90s`
  - `Performance | CrdY`
  - `Performance | CrdR`
  - `Performance | 2CrdY`
  - `Performance | Fls`
  - `Performance | Fld`
  - `Performance | Off`
  - `Performance | Crs`
  - `Performance | Int`
  - `Performance | TklW`
  - `Performance | OG`

```
('ENG-Premier League', '2526', 'Tottenham', 'Antonín Kinský')
{
  "nation": "CZE",
  "pos": "GK",
  "age": "22",
  "born": "2003",
  "90s": 7.0,
  "Performance | CrdY": "1",
  "Performance | CrdR": "0",
  "Performance | 2CrdY": "0",
  "Performance | Fls": "0",
  "Performance | Fld": "1",
  "Performance | Off": "0",
  "Performance | Crs": "0",
  "Performance | Int": "0",
  "Performance | TklW": "0",
  "Performance | OG": "0"
}
```

### playing_time

- Status: works
- Rows: 693
- Coverage: attacking no, passing no, defensive no, xG no
- Columns with real values:
  - `nation`
  - `pos`
  - `age`
  - `born`
  - `Playing Time | MP`
  - `Playing Time | Min`
  - `Playing Time | Mn/MP`
  - `Playing Time | Min%`
  - `Playing Time | 90s`
  - `Starts | Starts`
  - `Starts | Mn/Start`
  - `Starts | Compl`
  - `Subs | Subs`
  - `Subs | Mn/Sub`
  - `Subs | unSub`
  - `Team Success | PPM`
  - `Team Success | onG`
  - `Team Success | onGA`
  - `Team Success | +/-`
  - `Team Success | +/-90`
  - `Team Success | On-Off`

```
('ENG-Premier League', '2526', 'Tottenham', 'Antonín Kinský')
{
  "nation": "CZE",
  "pos": "GK",
  "age": "22",
  "born": "2003",
  "Playing Time | MP": "7",
  "Playing Time | Min": "630",
  "Playing Time | Mn/MP": "90",
  "Playing Time | Min%": 18.4,
  "Playing Time | 90s": 7.0,
  "Starts | Starts": "7",
  "Starts | Mn/Start": "90",
  "Starts | Compl": "7",
  "Subs | Subs": "0",
  "Subs | unSub": "30",
  "Team Success | PPM": 1.57,
  "Team Success | onG": "8",
  "Team Success | onGA": "7",
  "Team Success | +/-": "1",
  "Team Success | +/-90": 0.14,
  "Team Success | On-Off": 0.47
}
```

### keeper

- Status: works
- Rows: 40
- Coverage: attacking no, passing no, defensive no, xG no
- Columns with real values:
  - `nation`
  - `pos`
  - `age`
  - `born`
  - `Playing Time | MP`
  - `Playing Time | Starts`
  - `Playing Time | Min`
  - `Playing Time | 90s`
  - `Performance | GA`
  - `Performance | GA90`
  - `Performance | SoTA`
  - `Performance | Saves`
  - `Performance | Save%`
  - `Performance | W`
  - `Performance | D`
  - `Performance | L`
  - `Performance | CS`
  - `Performance | CS%`
  - `Penalty Kicks | PKatt`
  - `Penalty Kicks | PKA`
  - `Penalty Kicks | PKsv`
  - `Penalty Kicks | PKm`
  - `Penalty Kicks | Save%`

```
('ENG-Premier League', '2526', 'Tottenham', 'Antonín Kinský')
{
  "nation": "CZE",
  "pos": "GK",
  "age": "22",
  "born": "2003",
  "Playing Time | MP": "7",
  "Playing Time | Starts": "7",
  "Playing Time | Min": "630",
  "Playing Time | 90s": 7.0,
  "Performance | GA": "7",
  "Performance | GA90": 1.0,
  "Performance | SoTA": "17",
  "Performance | Saves": "10",
  "Performance | Save%": 58.8,
  "Performance | W": "3",
  "Performance | D": "2",
  "Performance | L": "2",
  "Performance | CS": "2",
  "Performance | CS%": 28.6,
  "Penalty Kicks | PKatt": "1",
  "Penalty Kicks | PKA": "1",
  "Penalty Kicks | PKsv": "0",
  "Penalty Kicks | PKm": "0",
  "Penalty Kicks | Save%": 0.0
}
```

### gca

- Status: fails
- Error: Invalid argument: stat_type should be in ['standard', 'keeper', 'shooting', 'playing_time', 'misc']
- Rows: 0
- Coverage: attacking no, passing no, defensive no, xG no
- Columns with real values:
  - (none)

## FotMob

- Status: fails
- Error: AttributeError: soccerdata has no FotMob class (removed from the package)
- Rows: 0
- Coverage: attacking no, passing no, defensive no, xG no
- Notes: soccerdata 2026.43.0 does not export FotMob. The 1.9.0 release removed the FotMob scraper.
- Columns with real values:
  - (none)

## Sofascore

- Status: fails
- Error: AttributeError: no player-season method; read_* methods: read_league_table, read_leagues, read_schedule, read_seasons
- Rows: 0
- Coverage: attacking no, passing no, defensive no, xG no
- Notes: Sofascore exposes league table and schedule only. No player-season method, so nothing was downloaded.
- Columns with real values:
  - (none)

## WhoScored

- Status: fails
- Error: AttributeError: no player-season method; read_* methods: read_events, read_leagues, read_missing_players, read_schedule, read_season_stages, read_seasons
- Rows: 0
- Coverage: attacking no, passing no, defensive no, xG no
- Notes: WhoScored subclasses BaseSeleniumReader and needs Chrome via Selenium. No player-season method (schedule, events, and missing players only). Browser was not launched and nothing was installed.
- Columns with real values:
  - (none)

## Understat

- Status: fails
- Error: JSONDecodeError: Expecting value: line 1 column 1 (char 0)
- Rows: 0
- Coverage: attacking no, passing no, defensive no, xG no
- Notes: Retry still fails. /getStatData returns the HTML page 'We will come back soon', which is not JSON.
- Columns with real values:
  - (none)
