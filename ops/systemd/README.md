# Daily fund snapshot timer

Runs `p50k.jobs.fund_snapshots` on weekday evenings as a systemd user timer. TEFAS serves only today's fund size, units outstanding and investor count, so a day without a run is lost for good.

The unit assumes the repo at `~/Documents/project-50k` and Python at `~/miniforge3/bin/python3`; edit `p50k-fund-snapshots.service` if yours differ. Data goes to `~/.local/share/project-50k/fund_snapshots.sqlite3`, outside git, because TEFAS data rights have not been reviewed.

Install:

```sh
mkdir -p ~/.config/systemd/user
cp ops/systemd/p50k-fund-snapshots.service ops/systemd/p50k-fund-snapshots.timer ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now p50k-fund-snapshots.timer
```

Check:

```sh
systemctl --user list-timers p50k-fund-snapshots.timer
journalctl --user -u p50k-fund-snapshots.service -n 20
```

Remove:

```sh
systemctl --user disable --now p50k-fund-snapshots.timer
rm ~/.config/systemd/user/p50k-fund-snapshots.service ~/.config/systemd/user/p50k-fund-snapshots.timer
systemctl --user daemon-reload
```

User timers run while you are logged in. If the machine is asleep at 21:00, the run happens when it wakes.

## Warning: snapshot runs and sealed research bundles

The service sets no `P50K_DATA_DIR`, so a run writes the default
`~/.local/share/project-50k/fund_snapshots.sqlite3`. Sealed v1/v2 research bundles
built from that database re-read it on every load, and a new row for one of the 100
selected funds changes their name/category projection, so the app then refuses the
bundle until it is resealed. Dated bundles (DEC-026) read only rows retrieved before
the D1 calibration run and tolerate rows appended later. Installing the timer remains
an owner decision.
