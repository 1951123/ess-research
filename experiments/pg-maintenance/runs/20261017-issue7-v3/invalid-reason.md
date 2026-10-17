# Invalidity note

The v3 run correctly captured post-warm-up payload metadata and completed the
336 timed observations, but the intended low-correlation regime used 1,000
categories per column.  Its two-column combinations were almost all unique,
so a subset of MCV objects had no serialized MCV payload.  The correlated
regime did build payloads for all objects.  The v3 evidence is retained, but it
is not used as the final comparison of MCV refresh costs.  The low-correlation
fixture was corrected to 100 categories per column, preserving 200,000 rows
and the same schema while ensuring repeated, weakly correlated pairs; the
complete matrix was rerun in v4.
