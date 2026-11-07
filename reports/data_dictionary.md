# Player-season data dictionary

One row in `data/processed/player_season.csv` is a player at one club in one league season.
A transfer during the season stays as two rows. Per-90 rates below are the figures FBref publishes;
this table does not recompute them, and it does not drop players below a minutes cutoff.

| column | meaning | source |
| --- | --- | --- |
| `player` | Player name, as published by FBref. Two people at the same club can share a name; birth year tells them apart. | all FBref pages (merge key) |
| `team` | Club the stats were recorded for. A mid-season move is a second row. | all FBref pages (merge key) |
| `league` | soccerdata league name, such as ENG-Premier League. | all FBref pages (merge key) |
| `season` | soccerdata season code. 2526 means the 2025-26 season. | all FBref pages (merge key) |
| `position` | Position codes from FBref, such as DF or MF,FW. | fbref standard |
| `age` | Age in whole years at the season in question. | fbref standard |
| `birth_year` | Year of birth. | fbref standard |
| `nationality` | Three-letter nationality code. | fbref standard |
| `minutes` | Minutes played for this club in this season. | fbref standard |
| `matches` | Matches played. | fbref standard |
| `starts` | Matches started. | fbref standard |
| `nineties` | Minutes played divided by 90. | fbref standard |
| `goals` | Goals. | fbref standard |
| `assists` | Assists. | fbref standard |
| `goals_plus_assists` | Goals plus assists. | fbref standard |
| `non_penalty_goals` | Goals excluding penalties. | fbref standard |
| `penalty_goals` | Penalty goals. | fbref standard |
| `penalty_attempts` | Penalty kicks taken. | fbref standard |
| `yellow_cards` | Yellow cards. | fbref standard |
| `red_cards` | Red cards. | fbref standard |
| `goals_per_90` | Goals per 90 minutes, as published by FBref. Not recomputed here. | fbref standard |
| `assists_per_90` | Assists per 90 minutes, as published by FBref. | fbref standard |
| `goals_plus_assists_per_90` | Goals plus assists per 90, as published by FBref. | fbref standard |
| `non_penalty_goals_per_90` | Non-penalty goals per 90, as published by FBref. | fbref standard |
| `non_penalty_goals_plus_assists_per_90` | Non-penalty goals plus assists per 90, as published by FBref. | fbref standard |
| `shots` | Shots, excluding penalty kicks. | fbref shooting |
| `shots_on_target` | Shots on target, excluding penalty kicks. | fbref shooting |
| `shots_on_target_pct` | Shots on target as a percentage of shots. | fbref shooting |
| `shots_per_90` | Shots per 90 minutes, as published by FBref. | fbref shooting |
| `shots_on_target_per_90` | Shots on target per 90 minutes, as published by FBref. | fbref shooting |
| `goals_per_shot` | Goals per shot. | fbref shooting |
| `goals_per_shot_on_target` | Goals per shot on target. | fbref shooting |
| `minutes_per_match` | Average minutes per match played. | fbref playing_time |
| `squad_minutes_pct` | Share of the club's season minutes this player was on the pitch. | fbref playing_time |
| `minutes_per_start` | Average minutes in matches that were started. | fbref playing_time |
| `complete_matches` | Starts that lasted the full match. | fbref playing_time |
| `substitute_appearances` | Matches entered as a substitute. | fbref playing_time |
| `minutes_per_substitute_appearance` | Average minutes after coming on as a substitute. | fbref playing_time |
| `unused_substitute` | Matches spent on the bench unused. | fbref playing_time |
| `points_per_match` | Team points per match while the player was on the pitch. | fbref playing_time |
| `team_goals_on_pitch` | Team goals scored while the player was on the pitch. | fbref playing_time |
| `team_goals_against_on_pitch` | Team goals conceded while the player was on the pitch. | fbref playing_time |
| `goal_difference_on_pitch` | Goal difference while the player was on the pitch. | fbref playing_time |
| `goal_difference_on_pitch_per_90` | On-pitch goal difference per 90 minutes. | fbref playing_time |
| `on_off_goal_difference` | On-pitch goal difference per 90 minus the same rate when the player was off. | fbref playing_time |
| `second_yellow_cards` | Second yellow cards. | fbref misc |
| `fouls_committed` | Fouls committed. | fbref misc |
| `fouls_drawn` | Fouls drawn. | fbref misc |
| `offsides` | Offsides. | fbref misc |
| `crosses` | Crosses. | fbref misc |
| `interceptions` | Interceptions. | fbref misc |
| `tackles_won` | Tackles in which the team won the ball. | fbref misc |
| `penalties_won` | Penalties won. | fbref misc |
| `penalties_conceded` | Penalties conceded. | fbref misc |
| `own_goals` | Own goals. | fbref misc |
| `source` | Which feed produced the row. FBref rows are 'fbref'. | assigned here |
