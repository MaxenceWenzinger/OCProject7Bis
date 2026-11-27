# RAG quality evaluation: first run

Run on the 20 questions of `tests/data/questions.json` (one run, 2026-11-20).
The raw answers, retrieved events and judge reasons of this run are in `tests/reports/rag_quality/<question id>.json`. They're overwritten by the next run.

## Setup

| | |
|---|---|
| Pipeline model | Claude Haiku 5.5 (date extraction and answer), effort `low`, answer `max_tokens` 4096 |
| Retrieval | BGE-M3 dense + sparse, `top_k` = 30 distinct events, filtered on the extracted periods |
| Judge | Claude Sonnet 5.5 (effort `low`) through DeepEval 4.3 |
| Reference date | Friday 2026-11-20, so the expected dates of the dataset stay valid |
| Duration | about 4 min 40 s with 4 questions in parallel (`-n 4`) |

Metrics, each scored from 0 to 1 by the judge:

- **Faithfulness** (threshold 0.8): the judge extracts the claims of the answer and checks each one against the retrieved events. A low score means invented or distorted information.
- **Answer relevancy** (threshold 0.7): share of the answer's statements that address the question. It's skipped for the two questions with no possible answer, because an honest "nothing found" would be scored as irrelevant.
- **Constraints respected** (custom G-Eval criterion, threshold 0.7): every recommended event must match the requested place, type and period according to the retrieved events, and if nothing matches the answer must say so instead of recommending unrelated events.

## Results

### Date extraction: 20/20

Every period extracted by Haiku matched the expected one: explicit dates, relative days, "ce week-end", "la semaine prochaine", times of day, several weekdays, two separate slots, recurring days, and past periods.

### Answers: 16/20 pass

| Question | Query | Faithfulness | Constraints | Relevancy | Result |
|---|---|---|---|---|---|
| after_hour | Que faire à Paris après 20h ce samedi ? | 1.00 | 0.70 | 1.00 | pass (borderline) |
| around_hour | Un spectacle vers 15h dimanche à Rouen | 1.00 | 0.90 | 1.00 | pass |
| between_holidays | Un spectacle de cirque entre Noël et le jour de l'an | 1.00 | 0.90 | 1.00 | pass |
| christmas_day | Une activité en famille à Toulouse le jour de Noël | 1.00 | 0.90 | 1.00 | pass |
| every_saturday | Une visite guidée à Marseille, je suis libre tous les samedis | 1.00 | **0.50** | 1.00 | **fail** |
| explicit_date | Y a-t-il un marché de Noël à Lille le 12 décembre ? | 1.00 | 0.90 | 1.00 | pass |
| month | Un opéra à Bordeaux en janvier | 1.00 | **0.50** | 0.76 | **fail** |
| next_week | Des expositions à Toulouse la semaine prochaine | 0.91 | 0.90 | 0.85 | pass |
| no_answer_date | Une démonstration de forge médiévale à Alès le 5 décembre | 1.00 | 0.80 | – | pass |
| no_answer_tonight | Un tournoi de curling sous-marin à Draguignan ce soir | 0.89 | 0.90 | – | pass |
| no_date | Un concert de jazz à Bordeaux | 1.00 | 0.90 | 1.00 | pass |
| past_month | Quels concerts y avait-il à Lille le mois dernier ? | 1.00 | 0.80 | 1.00 | pass |
| rare_type | Une séance de yoga ou de méditation à Nantes | 1.00 | 0.90 | 0.92 | pass |
| several_days | Des contes pour enfants à Nantes mardi, vendredi ou dimanche | 1.00 | 0.80 | 0.81 | pass |
| tomorrow_morning | Une sortie culturelle à Rouen demain matin | 1.00 | 0.80 | 1.00 | pass |
| tonight | Une pièce de théâtre à Paris ce soir | 1.00 | 0.80 | 0.97 | pass |
| two_slots | Un concert à Toulouse samedi matin ou dimanche soir | 0.94 | **0.40** | 1.00 | **fail** |
| weekday_afternoon | Un atelier pour enfants à Rennes mercredi après-midi | 1.00 | 0.90 | 1.00 | pass |
| weekend | Que faire à Nantes ce week-end ? | 1.00 | 0.90 | 1.00 | pass (but truncated, see below) |
| yearly_event | Un festival qui a lieu tous les ans à Rennes | 1.00 | **0.60** | 1.00 | **fail** |

Averages: faithfulness 0.99, constraints 0.80, answer relevancy 0.96.

## Reading the scores

**The system doesn't invent things.** Faithfulness is 1.00 on 16 questions, and the 4 below 1 come from small slips, not invented events:
- **next_week:** the answer linked the exhibition "Dans la forêt" to the photography bicentenary, while the data links it to another project.
- **two_slots:** it gave opening hours and a season title that aren't in the data.
- **no_answer_tonight:** it said the play TERREUR is in Draguignan. Here the two judge calls disagreed: the Constraints judge says the data does put it in Draguignan.

**Dates are well respected.** No answer recommended an event outside the requested period. The only remarks are about events announced as "all day" (stored as 00:00–23:59) being offered for "demain matin" or "après 20h". That's a consequence of our choice to keep events without precise hours.

**The weak point is the place and type constraints.** All failures and most deductions come from it, for the reasons below.

## Findings

### 1. Retrieval ignores the place

The embedding search matches the type of event well but barely takes the city into account. In `every_saturday` ("visite guidée à Marseille"), the first 10 retrieved events are the same guided tour from Roubaix. The other guided tours found are in Lille, Amiens, Toulouse and Paris; none is in Marseille. Other questions show the same thing to a lesser degree:
- **christmas_day** (Toulouse): the first result is the Bordeaux Christmas market.
- **two_slots** (Toulouse): a candlelight concert in Marseille is in the top 10.
- **tonight** (Paris): the first recommended play is in Sevran.

The answer model compensates by discarding events from other cities, but the slots used by those events are lost. For example, the answer for Marseille ends up with "no guided tour found", though one might exist further down the ranking.

**Possible fix:** extract the place in the first LLM call, alongside the dates, and filter on city or department in SQL like the periods.

### 2. Duplicated events take up the retrieval slots

The same event is often published several times under different IDs:
- "Visite guidée - Ni Dieu ni maître !": at least 10 times in the top 10 of `every_saturday`;
- "Bienvenue à La Criée, 40 ans de création…": 5 times;
- "Bialowieza, la forêt vivante…": 3 times;
- "LES TRAVIATAS…" and "Les 10 ans Des Pies Chicaillent": twice each.

With `top_k` = 30, this can halve the number of distinct events actually offered to the answer model.

**Possible fix:** deduplicate on title and place, either when retrieving (`DISTINCT ON` title and city, like the deduplication by event) or once in the data itself.

### 3. When nothing matches, the answer still offers "alternatives"

In every question where nothing matched, Haiku said so first and then listed non-matching events, clearly labelled as such:
- **two_slots:** a guitar masterclass and a dance show instead of a concert;
- **every_saturday:** exhibitions instead of a guided tour;
- **month:** operas in Lille and Meudon besides the one in Bordeaux;
- **explicit_date:** the Christmas market of Lezennes, next to Lille;
- **no_answer_\*:** the other events in Alès and Draguignan that day.

The judge is not consistent about this. The same behaviour scored 0.9 in `between_holidays` and `explicit_date`, but 0.4–0.5 in `two_slots` and `every_saturday`. The criterion doesn't say clearly whether labelled alternatives are acceptable, so the judge decides case by case.

**Decision needed:** whether alternatives are wanted. Either way, both the answer prompt and the judge criterion should state the rule explicitly:
- If they're wanted (a nearby town or a close type of event is often useful), allow at most 2 or 3 alternatives, clearly separated from the matches.
- If they're not, the answer should only say that nothing was found and suggest how to widen the search.

### 4. Answers mention the events they excluded

Several answers end with a sentence about candidates from other cities ("…se déroulent à Rennes et Toulouse", "…à Orléans… à Avignon", "…Anatomik Park se tient à Bordeaux, donc hors zone"). This is what lowered answer relevancy in `next_week` (0.85), `several_days` (0.81), `rare_type` (0.92) and `month` (0.76). The judge counts these sentences as off-topic, and they add nothing for the user.

**Possible fix:** one line in the answer prompt: "don't mention the candidates you discarded". Fixing finding 1 would also remove most of them.

### 5. One answer was cut off by the token limit

The `weekend` answer stops mid-sentence ("…samedi 21, 15h-16h30, Mus") at about 6,200 characters. "Que faire à Nantes ce week-end ?" matches many events, and the answer listed most of them until it hit `max_tokens` = 4096, which counts the model's reasoning as well. The judges didn't penalise it much (0.90), but the user gets an incomplete answer. Other long answers (`past_month` 4,900 characters, `after_hour` 4,400) came close.

**Possible fix:**
- **Shorter answers:** ask for at most 5–8 recommendations, chosen as the best matches.
- **More room:** raise `max_tokens`.
- **Detection:** check `stop_reason == "max_tokens"` so a truncated answer can be detected.

### 6. The `yearly_event` question is too vague

"Un festival qui a lieu tous les ans à Rennes": the data never says whether an event is annual, so no answer can satisfy the constraint. The answer was honest about it ("les données ne précisent pas explicitement qu'ils ont lieu chaque année"), yet scored 0.6. The question tests a limit of the data, not of the system. It should be reworded (e.g. "un festival à Rennes cette année") or kept as a known limitation and excluded from the pass rate.

## Limits of this evaluation

- **One run, 20 questions.** LLM-judge scores vary by about ±0.1 from one run to another, so a question near a threshold (`after_hour` at exactly 0.70) can pass or fail by chance. Differences between two versions of the system should be confirmed over several runs.
- **The judge is also an LLM.** It sometimes contradicts itself: the TERREUR location in `no_answer_tonight`, and the uneven treatment of alternatives in finding 3. Its reasons in the reports are worth reading before trusting a score.
- **Retrieval isn't measured on its own.** We only see it through the answers. A retrieval metric (contextual relevancy, or checking that the expected city and type appear in the retrieved events) would separate retrieval problems from answer problems.
- **Cost isn't recorded.** The run uses about 40 Haiku calls for the pipeline and around 100 Sonnet calls for the judge. Order of magnitude: one to two dollars per full run.

## Suggested next steps, by expected impact

1. **Place filtering** (finding 1): extract the city or department with the dates and filter in SQL. This should fix most constraint failures.
2. **Deduplicate events** by title and place (finding 2).
3. **Decide the rule for alternatives**, and state it in both the answer prompt and the judge criterion (finding 3).
4. **Answer prompt tweaks** (findings 4 and 5): limit the number of recommendations, don't mention discarded candidates, and detect `max_tokens` truncation.
5. **Reword `yearly_event`** (finding 6), then rerun to compare.
