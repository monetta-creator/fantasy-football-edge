# Feature backlog

Seeded by hand from the handoff and from what the Phase 0 data showed. The Phase 4 recommender will append weekly proposals in the same format. Point impacts are estimates.

| # | Status | Feature | Mechanism that produces points | Est. impact / season | Effort | Pitch |
|---|--------|---------|-------------------------------|----------------------|--------|-------|
| 1 | proposed | Yahoo live-draft sync | Read `league/draftresults` every 10 s during the draft so picks appear without tapping | 0 pts directly; removes tap latency under the 2-min clock | M | Never miss a pick because you were typing. |
| 2 | proposed | QB-depth tracker in draft | Count QBs drafted vs. ADP; alert when the last elite-tier QB (6-pt TD scoring) is about to go | ~15-25 pts (QB1 vs QB replacement gap is 97 pts; timing matters) | S | The model says wait on QB; this tells you exactly how long. |
| 3 | proposed | Tuesday IR choreography | Auto-propose bench→IR moves Monday night; keep one bench slot open before waiver processing | ~20-40 pts (one extra live roster spot for ~10 weeks) | M | Run 15 players while everyone else runs 12. |
| 4 | proposed | Drop watcher + instant claim queue | Poll transactions every 60 s post-waivers; rank dropped players by league VORP; one-tap add | ~30-60 pts (2-4 startable pickups/season before opponents react) | M | Standings-based waivers punish winners; speed doesn't. |
| 5 | proposed | Vegas-implied DST streamer | Weekly DST ranking from opponent implied totals (points-allowed buckets dominate DST scoring) | ~15-30 pts vs. holding one DST | S | Stream the defense facing the lowest implied total. |
| 6 | proposed | Kicker leg model | Weight 50+ attempts (5 pts) and dome/altitude; stream Ks by implied total | ~8-15 pts | S | Long legs are worth more here than in most leagues. |
| 7 | proposed | Source-disagreement alerts | Flag players where ESPN and Rotowire differ by >40 pts; check news before drafting | risk reduction | S | Big projection spread = something the market knows. |
| 8 | proposed | Injury return calendar | Weekly view of every IR-stashed player's expected return vs. playoff weeks 15-17 | enables 3 & 4 | S | See when the cavalry arrives. |
| 9 | proposed | Opponent tendency profiles | Learn each manager's draft/waiver habits (reach positions, drop timing) from transaction history | trade + waiver edges | L | Know who overpays for RBs. |
