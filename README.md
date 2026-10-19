# Tea Timer: tea list

The tea list for the [Tea Timer](https://github.com/GoodGuyTuring/TeaTimer) Android app.
The app downloads [`teas.json`](teas.json) from here when you tap **Update teas**.

## Where the data comes from

`teas.json` is generated from the *Tea Brewing Reference* note (Obsidian), the brewing
reference for the teas I own:

```bash
python tools/from_brewing_reference.py "path/to/Tea Brewing Reference.md"
```

After changing the reference, run the script again, commit and push `teas.json`; then tap
**Update teas** in the app.

What the script takes over:

- One **method** per table: Gongfu 90 ml, Gongfu 60 ml, Western 350 ml, Western 1 L.
- **Light / Medium / Strong** are the reference's min / mid / max times. Medium uses the
  "Ideal (mid)" time where the reference gives one: the mid times there are rounded to fit
  a slot timer, which Tea Timer doesn't need.
- Temperature and "optional" per infusion, the leaf amount per method, and the notes.
- A **Test** tea with 5-second steps is added at the end, for checking the alarm.

## Format

```json
{
  "version": 2,
  "updated": "Oct 17, 2026",
  "teas": [
    {
      "type": "Oolong",
      "name": "Da Hong Pao",
      "note": "2.8 g/tsp (strip yancha). …",
      "methods": [
        {
          "name": "Gongfu 90 ml",
          "amount": "2.25 tsp (~6.5 g)",
          "note": "No rinse. …",
          "infusions": [
            { "temp": "100°C", "light": "0:10", "medium": "0:15", "strong": "0:20" },
            { "temp": "100°C", "light": "3:00", "medium": "4:00", "strong": "4:30", "optional": true }
          ]
        }
      ]
    }
  ]
}
```

- `type`: tab in the app. `name`: the tea.
- `methods[].infusions`: in brewing order. Times are `m:ss`. `light` and `strong` are
  optional; a method without them only offers Medium.
- `note`, `amount`, `temp` and `optional` are optional too.
